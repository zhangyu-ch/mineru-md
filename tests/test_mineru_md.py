import argparse
import importlib.util
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "mineru-md" / "scripts" / "mineru_md.py"
SPEC = importlib.util.spec_from_file_location("mineru_md", SCRIPT)
mineru_md = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = mineru_md
SPEC.loader.exec_module(mineru_md)


def args(**overrides):
    data = {
        "model": "vlm",
        "ocr": False,
        "no_formula": False,
        "no_table": False,
        "language": "auto",
        "pages": None,
    }
    data.update(overrides)
    return argparse.Namespace(**data)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return FakeResponse(self.payloads.pop(0))


class MinerUMdTests(unittest.TestCase):
    def test_token_priority(self):
        with tempfile.TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text("from-file\n", encoding="utf-8")
            old_mineru = os.environ.get("MINERU_TOKEN")
            old_api = os.environ.get("MINERU_API_TOKEN")
            try:
                os.environ["MINERU_TOKEN"] = "from-env"
                os.environ["MINERU_API_TOKEN"] = "from-api-env"
                self.assertEqual(mineru_md.resolve_token("from-arg", token_file), "from-arg")
                self.assertEqual(mineru_md.resolve_token(None, token_file), "from-env")
                del os.environ["MINERU_TOKEN"]
                self.assertEqual(mineru_md.resolve_token(None, token_file), "from-api-env")
                del os.environ["MINERU_API_TOKEN"]
                self.assertEqual(mineru_md.resolve_token(None, token_file), "from-file")
            finally:
                if old_mineru is None:
                    os.environ.pop("MINERU_TOKEN", None)
                else:
                    os.environ["MINERU_TOKEN"] = old_mineru
                if old_api is None:
                    os.environ.pop("MINERU_API_TOKEN", None)
                else:
                    os.environ["MINERU_API_TOKEN"] = old_api

    def test_model_selection_pdf_and_html(self):
        pdf = mineru_md.make_source("file", "C:/docs/paper.pdf", "paper.pdf")
        html = mineru_md.make_source("url", "https://example.com/page.html", "page.html")
        self.assertEqual(mineru_md.select_model(pdf, "vlm"), "vlm")
        self.assertEqual(mineru_md.select_model(pdf, "pipeline"), "pipeline")
        self.assertEqual(mineru_md.select_model(html, "pipeline"), "MinerU-HTML")

    def test_parse_args_accepts_documented_languages(self):
        for language in ("latin", "ch_server", "devanagari"):
            parsed = mineru_md.parse_args(
                ["--url", "https://example.com/paper.pdf", "--language", language]
            )
            self.assertEqual(parsed.language, language)

    def test_payloads_for_local_pdf_and_url_html(self):
        pdf = mineru_md.make_source("file", "C:/docs/paper.pdf", "paper.pdf")
        pdf_url = mineru_md.make_source("url", "https://example.com/paper.pdf", "paper.pdf")
        html = mineru_md.make_source("url", "https://example.com/page.html", "page.html")
        pdf_payload = mineru_md.build_local_upload_payload(
            pdf, args(ocr=True, language="latin", pages="1-5")
        )
        self.assertEqual(pdf_payload["model_version"], "vlm")
        self.assertEqual(pdf_payload["files"][0]["is_ocr"], True)
        self.assertEqual(pdf_payload["files"][0]["page_ranges"], "1-5")
        self.assertEqual(pdf_payload["enable_formula"], True)
        self.assertEqual(pdf_payload["enable_table"], True)
        self.assertEqual(pdf_payload["language"], "latin")

        pdf_url_payload = mineru_md.build_url_task_payload(pdf_url, args(language="ch_server"))
        self.assertEqual(pdf_url_payload["language"], "ch_server")

        auto_payload = mineru_md.build_local_upload_payload(pdf, args(language="auto"))
        self.assertNotIn("language", auto_payload)

        html_payload = mineru_md.build_url_task_payload(html, args())
        self.assertEqual(html_payload["model_version"], "MinerU-HTML")
        self.assertNotIn("enable_formula", html_payload)
        self.assertNotIn("enable_table", html_payload)
        self.assertNotIn("is_ocr", html_payload)

    def test_safe_extract_rejects_zip_slip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "bad.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("../escape.md", "bad")
            with self.assertRaises(mineru_md.MinerUError):
                mineru_md.safe_extract_zip(archive, root / "out")

    def test_finalize_and_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "full.md").write_text("# ok\n", encoding="utf-8")
            md_path = mineru_md.finalize_extracted_output(out, "paper")
            self.assertEqual(md_path, out / "paper.md")
            self.assertTrue(md_path.exists())

            manifest = {
                "status": "done",
                "markdown_path": str(md_path),
            }
            (out / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            self.assertTrue(mineru_md.should_resume(out))

    def test_poll_batch_pending_then_done(self):
        session = FakeSession(
            [
                {"code": 0, "data": {"extract_result": [{"state": "pending"}]}},
                {
                    "code": 0,
                    "data": {
                        "extract_result": [
                            {"state": "done", "full_zip_url": "https://example.com/result.zip"}
                        ]
                    },
                },
            ]
        )
        with mock.patch.object(mineru_md.time, "sleep", lambda _seconds: None):
            with mock.patch.object(mineru_md.time, "monotonic", side_effect=[0, 0, 0]):
                result = mineru_md.poll_batch_result(session, "token", "batch", 10, 1)
        self.assertEqual(result["state"], "done")
        self.assertIn("/extract-results/batch/batch", session.calls[0][1])

    def test_poll_batch_failed_and_timeout(self):
        failed = FakeSession(
            [
                {
                    "code": 0,
                    "data": {"extract_result": [{"state": "failed", "err_msg": "bad file"}]},
                }
            ]
        )
        with mock.patch.object(mineru_md.time, "monotonic", side_effect=[0, 0]):
            with self.assertRaisesRegex(mineru_md.MinerUError, "bad file"):
                mineru_md.poll_batch_result(failed, "token", "batch", 10, 1)

        never_polled = FakeSession([])
        with mock.patch.object(mineru_md.time, "monotonic", side_effect=[0, 2]):
            with self.assertRaisesRegex(mineru_md.MinerUError, "Timed out"):
                mineru_md.poll_batch_result(never_polled, "token", "batch", 1, 1)


if __name__ == "__main__":
    unittest.main()
