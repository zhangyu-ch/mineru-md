#!/usr/bin/env python3
"""Convert PDF and HTML files or URLs to Markdown with MinerU v4."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import shutil
import sys
import time
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import requests

API_BASE = "https://mineru.net/api/v4"
MAX_FILE_BYTES = 200 * 1024 * 1024
SUPPORTED_SUFFIXES = {".pdf", ".html", ".htm"}
PDF_MODELS = {"pipeline", "vlm"}
LANGUAGE_OPTIONS = {
    "auto",
    "ch",
    "ch_server",
    "en",
    "japan",
    "korean",
    "chinese_cht",
    "ta",
    "te",
    "ka",
    "el",
    "th",
    "latin",
    "arabic",
    "cyrillic",
    "east_slavic",
    "devanagari",
}
DONE_STATES = {"done"}
FAILED_STATES = {"failed"}
WAIT_STATES = {"pending", "running", "converting", "uploading", "waiting-file"}


class MinerUError(RuntimeError):
    """Raised for expected MinerU workflow failures."""


@dataclass(frozen=True)
class SourceItem:
    kind: str
    source: str
    name: str
    suffix: str
    output_stem: str
    data_id: str

    @property
    def is_html(self) -> bool:
        return self.suffix.lower() in {".html", ".htm"}


@dataclass
class ProcessOutcome:
    source: str
    output_dir: str
    status: str
    skipped: bool = False
    error: str | None = None


def sha8(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()[:8]


def filesystem_safe_stem(stem: str, fallback_seed: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", stem).strip(" .")
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned:
        cleaned = f"document-{sha8(fallback_seed)}"
    return cleaned[:120]


def api_data_id(stem: str, fallback_seed: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", stem).strip("._-")
    if not cleaned:
        cleaned = "document"
    suffix = sha8(fallback_seed)
    max_base = 128 - len(suffix) - 1
    return f"{cleaned[:max_base]}-{suffix}"


def source_name_from_url(url: str) -> str:
    parsed = urlparse(url)
    name = Path(unquote(parsed.path)).name
    if not name:
        raise MinerUError(f"URL must end with a supported file name: {url}")
    return name


def validate_supported_name(name: str) -> str:
    suffix = Path(name).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        supported = ", ".join(sorted(SUPPORTED_SUFFIXES))
        raise MinerUError(f"Unsupported input type for {name!r}; supported suffixes: {supported}")
    return suffix


def make_source(kind: str, source: str, name: str) -> SourceItem:
    suffix = validate_supported_name(name)
    stem = Path(name).stem
    return SourceItem(
        kind=kind,
        source=source,
        name=name,
        suffix=suffix,
        output_stem=filesystem_safe_stem(stem, source),
        data_id=api_data_id(stem, source),
    )


def resolve_token(token_arg: str | None, token_file: Path | None = None) -> str:
    if token_arg:
        return token_arg.strip()
    for env_name in ("MINERU_TOKEN", "MINERU_API_TOKEN"):
        token = os.environ.get(env_name)
        if token:
            return token.strip()
    token_path = token_file or (Path.home() / ".config" / "mineru" / "token")
    if token_path.exists():
        token = token_path.read_text(encoding="utf-8").strip()
        if token:
            return token
    raise MinerUError(
        "No MinerU token found. Set MINERU_TOKEN, MINERU_API_TOKEN, "
        "create ~/.config/mineru/token, or pass --token."
    )


def auth_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "*/*",
    }


def select_model(item: SourceItem, requested_pdf_model: str) -> str:
    if item.is_html:
        return "MinerU-HTML"
    if requested_pdf_model not in PDF_MODELS:
        raise MinerUError(f"Unsupported PDF model: {requested_pdf_model}")
    return requested_pdf_model


def extraction_options(item: SourceItem, args: argparse.Namespace) -> dict[str, Any]:
    if item.is_html:
        return {}
    options: dict[str, Any] = {
        "is_ocr": bool(args.ocr),
        "enable_formula": not bool(args.no_formula),
        "enable_table": not bool(args.no_table),
    }
    if args.language != "auto":
        options["language"] = args.language
    if args.pages:
        options["page_ranges"] = args.pages
    return options


def build_local_upload_payload(item: SourceItem, args: argparse.Namespace) -> dict[str, Any]:
    file_entry: dict[str, Any] = {"name": item.name, "data_id": item.data_id}
    options = extraction_options(item, args)
    for key in ("is_ocr", "page_ranges"):
        if key in options:
            file_entry[key] = options[key]
    payload: dict[str, Any] = {
        "files": [file_entry],
        "model_version": select_model(item, args.model),
    }
    for key in ("enable_formula", "enable_table", "language"):
        if key in options:
            payload[key] = options[key]
    return payload


def build_url_task_payload(item: SourceItem, args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "url": item.source,
        "data_id": item.data_id,
        "model_version": select_model(item, args.model),
    }
    payload.update(extraction_options(item, args))
    return payload


def request_json(
    session: requests.Session,
    method: str,
    url: str,
    *,
    token: str,
    retries: int = 3,
    **kwargs: Any,
) -> dict[str, Any]:
    last_error: Exception | None = None
    request_timeout = kwargs.pop("timeout", 60)
    for attempt in range(retries):
        try:
            response = session.request(
                method,
                url,
                headers=auth_headers(token),
                timeout=request_timeout,
                **kwargs,
            )
            response.raise_for_status()
            data = response.json()
            if data.get("code", 0) != 0:
                raise MinerUError(f"MinerU API error {data.get('code')}: {data.get('msg', data)}")
            return data
        except (requests.RequestException, ValueError, MinerUError) as exc:
            last_error = exc
            if attempt == retries - 1:
                break
            time.sleep(2**attempt)
    raise MinerUError(str(last_error))


def upload_file_with_retry(upload_url: str, path: Path, retries: int = 3) -> None:
    last_error: str | None = None
    for attempt in range(retries):
        try:
            with path.open("rb") as handle:
                response = requests.put(upload_url, data=handle, timeout=300)
            if response.status_code in {200, 201, 203, 204}:
                return
            last_error = f"HTTP {response.status_code}: {response.text[:200]}"
        except requests.RequestException as exc:
            last_error = str(exc)
        if attempt < retries - 1:
            time.sleep(2**attempt)
    raise MinerUError(f"Upload failed for {path.name}: {last_error}")


def submit_local_file(
    session: requests.Session,
    token: str,
    item: SourceItem,
    path: Path,
    args: argparse.Namespace,
) -> str:
    if path.stat().st_size > MAX_FILE_BYTES:
        raise MinerUError(f"{path} is larger than 200 MB")
    data = request_json(
        session,
        "POST",
        f"{API_BASE}/file-urls/batch",
        token=token,
        json=build_local_upload_payload(item, args),
        timeout=60,
    )
    batch_id = data["data"]["batch_id"]
    upload_entry = data["data"]["file_urls"][0]
    upload_url = upload_entry.get("url") if isinstance(upload_entry, dict) else upload_entry
    if not upload_url:
        raise MinerUError(f"MinerU response did not include an upload URL: {data}")
    upload_file_with_retry(upload_url, path)
    return batch_id


def submit_url_task(
    session: requests.Session,
    token: str,
    item: SourceItem,
    args: argparse.Namespace,
) -> str:
    data = request_json(
        session,
        "POST",
        f"{API_BASE}/extract/task",
        token=token,
        json=build_url_task_payload(item, args),
        timeout=60,
    )
    return data["data"]["task_id"]


def poll_url_task(
    session: requests.Session,
    token: str,
    task_id: str,
    timeout: int,
    poll_interval: int,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        data = request_json(
            session,
            "GET",
            f"{API_BASE}/extract/task/{task_id}",
            token=token,
            timeout=30,
        )["data"]
        state = data.get("state")
        if state in DONE_STATES:
            return data
        if state in FAILED_STATES:
            raise MinerUError(data.get("err_msg") or f"Task failed: {data}")
        if state not in WAIT_STATES:
            print(f"Unknown task state {state!r}; continuing to poll", file=sys.stderr)
        time.sleep(poll_interval)
    raise MinerUError(f"Timed out waiting for task {task_id}")


def poll_batch_result(
    session: requests.Session,
    token: str,
    batch_id: str,
    timeout: int,
    poll_interval: int,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        data = request_json(
            session,
            "GET",
            f"{API_BASE}/extract-results/batch/{batch_id}",
            token=token,
            timeout=30,
        )["data"]
        results = data.get("extract_result") or []
        if not results:
            time.sleep(poll_interval)
            continue
        result = results[0]
        state = result.get("state")
        if state in DONE_STATES:
            return result
        if state in FAILED_STATES:
            raise MinerUError(result.get("err_msg") or f"Batch failed: {result}")
        if state not in WAIT_STATES:
            print(f"Unknown batch state {state!r}; continuing to poll", file=sys.stderr)
        time.sleep(poll_interval)
    raise MinerUError(f"Timed out waiting for batch {batch_id}")


def candidate_download_urls(url: str) -> list[str]:
    urls = [url]
    old_host = "cdn-mineru.openxlab.org.cn"
    new_host = "mineru.oss-cn-shanghai.aliyuncs.com"
    if old_host in url:
        urls.append(url.replace(old_host, new_host))
    return urls


def download_zip(url: str, zip_path: Path, retries: int = 3) -> None:
    last_error: str | None = None
    for candidate in candidate_download_urls(url):
        for attempt in range(retries):
            try:
                with requests.get(candidate, stream=True, timeout=300) as response:
                    response.raise_for_status()
                    with zip_path.open("wb") as handle:
                        for chunk in response.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                handle.write(chunk)
                return
            except requests.RequestException as exc:
                last_error = str(exc)
                if attempt < retries - 1:
                    time.sleep(2**attempt)
    raise MinerUError(f"Could not download result ZIP: {last_error}")


def is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def safe_extract_zip(zip_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    base = destination.resolve()
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if not is_relative_to(target, base):
                raise MinerUError(f"Unsafe ZIP member path: {member.filename}")
        archive.extractall(destination)


def finalize_extracted_output(output_dir: Path, output_stem: str) -> Path | None:
    preferred = output_dir / "full.md"
    if not preferred.exists():
        matches = sorted(output_dir.rglob("full.md"))
        preferred = matches[0] if matches else None
    if preferred is None or not preferred.exists():
        matches = sorted(output_dir.rglob("*.md"))
        preferred = matches[0] if matches else None
    if preferred is None:
        return None

    target = output_dir / f"{output_stem}.md"
    if preferred.resolve() != target.resolve():
        if target.exists():
            target.unlink()
        shutil.move(str(preferred), str(target))
    return target


def manifest_path(output_dir: Path) -> Path:
    return output_dir / "manifest.json"


def should_resume(output_dir: Path) -> bool:
    path = manifest_path(output_dir)
    if not path.exists():
        return False
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    markdown_path = manifest.get("markdown_path")
    return manifest.get("status") == "done" and bool(markdown_path) and Path(markdown_path).exists()


def write_manifest(output_dir: Path, manifest: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path(output_dir).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def process_item(item: SourceItem, args: argparse.Namespace, token: str, root_output: Path) -> ProcessOutcome:
    output_dir = root_output / item.output_stem
    if args.resume and should_resume(output_dir):
        return ProcessOutcome(str(item.source), str(output_dir), "done", skipped=True)

    output_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    model = select_model(item, args.model)
    manifest: dict[str, Any] = {
        "source": item.source,
        "source_kind": item.kind,
        "name": item.name,
        "model": model,
        "data_id": item.data_id,
        "status": "running",
        "started_at": int(time.time()),
        "markdown_path": None,
        "error": None,
    }
    write_manifest(output_dir, manifest)

    session = requests.Session()
    zip_path = output_dir / f"{item.output_stem}.zip"
    try:
        if item.kind == "file":
            local_path = Path(item.source)
            batch_id = submit_local_file(session, token, item, local_path, args)
            manifest["batch_id"] = batch_id
            write_manifest(output_dir, manifest)
            result = poll_batch_result(session, token, batch_id, args.timeout, args.poll_interval)
        else:
            task_id = submit_url_task(session, token, item, args)
            manifest["task_id"] = task_id
            write_manifest(output_dir, manifest)
            result = poll_url_task(session, token, task_id, args.timeout, args.poll_interval)

        zip_url = result.get("full_zip_url")
        if not zip_url:
            raise MinerUError(f"MinerU response did not include full_zip_url: {result}")

        download_zip(zip_url, zip_path)
        safe_extract_zip(zip_path, output_dir)
        if not args.keep_zip and zip_path.exists():
            zip_path.unlink()

        markdown_path = finalize_extracted_output(output_dir, item.output_stem)
        manifest.update(
            {
                "status": "done",
                "duration_seconds": round(time.monotonic() - started, 2),
                "markdown_path": str(markdown_path) if markdown_path else None,
                "result": result,
            }
        )
        write_manifest(output_dir, manifest)
        return ProcessOutcome(str(item.source), str(output_dir), "done")
    except Exception as exc:
        manifest.update(
            {
                "status": "failed",
                "duration_seconds": round(time.monotonic() - started, 2),
                "error": str(exc),
            }
        )
        write_manifest(output_dir, manifest)
        return ProcessOutcome(str(item.source), str(output_dir), "failed", error=str(exc))


def collect_sources(args: argparse.Namespace) -> list[SourceItem]:
    sources: list[SourceItem] = []
    if args.file:
        path = Path(args.file).expanduser().resolve()
        if not path.is_file():
            raise MinerUError(f"File not found: {path}")
        sources.append(make_source("file", str(path), path.name))
    elif args.dir:
        root = Path(args.dir).expanduser().resolve()
        if not root.is_dir():
            raise MinerUError(f"Directory not found: {root}")
        pattern = "**/*" if args.recursive else "*"
        for path in sorted(root.glob(pattern)):
            if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
                sources.append(make_source("file", str(path), path.name))
    elif args.url:
        sources.append(make_source("url", args.url, source_name_from_url(args.url)))
    elif args.urls_file:
        urls_path = Path(args.urls_file).expanduser().resolve()
        if not urls_path.is_file():
            raise MinerUError(f"URL file not found: {urls_path}")
        for line in urls_path.read_text(encoding="utf-8").splitlines():
            url = line.strip()
            if not url or url.startswith("#"):
                continue
            sources.append(make_source("url", url, source_name_from_url(url)))

    if not sources:
        raise MinerUError("No supported PDF or HTML inputs found.")
    return dedupe_output_stems(sources)


def dedupe_output_stems(sources: list[SourceItem]) -> list[SourceItem]:
    counts: dict[str, int] = {}
    for source in sources:
        counts[source.output_stem] = counts.get(source.output_stem, 0) + 1
    if all(count == 1 for count in counts.values()):
        return sources

    deduped: list[SourceItem] = []
    for source in sources:
        if counts[source.output_stem] == 1:
            deduped.append(source)
            continue
        deduped.append(
            SourceItem(
                kind=source.kind,
                source=source.source,
                name=source.name,
                suffix=source.suffix,
                output_stem=f"{source.output_stem}-{sha8(source.source)}",
                data_id=source.data_id,
            )
        )
    return deduped


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert PDF and HTML files or URLs to Markdown with MinerU v4.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--file", help="Single local .pdf/.html/.htm file")
    input_group.add_argument("--dir", help="Directory containing .pdf/.html/.htm files")
    input_group.add_argument("--url", help="Single remote .pdf/.html/.htm URL")
    input_group.add_argument("--urls-file", help="Text file containing one URL per line")

    parser.add_argument("--output", default="./mineru-output", help="Output directory")
    parser.add_argument("--workers", type=int, default=3, help="Concurrent sources to process")
    parser.add_argument("--resume", action="store_true", help="Skip completed outputs")
    parser.add_argument("--recursive", action="store_true", help="Recursively scan --dir")
    parser.add_argument("--timeout", type=int, default=1800, help="Seconds to wait per source")
    parser.add_argument("--poll-interval", type=int, default=5, help="Polling interval in seconds")
    parser.add_argument("--model", choices=sorted(PDF_MODELS), default="vlm", help="PDF model")
    parser.add_argument("--ocr", action="store_true", help="Enable OCR for PDF")
    parser.add_argument("--language", choices=sorted(LANGUAGE_OPTIONS), default="auto", help="PDF language")
    parser.add_argument("--pages", help='PDF page ranges, for example "1-5,8"')
    parser.add_argument("--no-formula", action="store_true", help="Disable formula extraction")
    parser.add_argument("--no-table", action="store_true", help="Disable table extraction")
    parser.add_argument("--token", help="MinerU API token")
    parser.add_argument("--keep-zip", action="store_true", help="Keep downloaded result ZIP")
    args = parser.parse_args(argv)

    if args.workers < 1:
        parser.error("--workers must be >= 1")
    if args.timeout < 1:
        parser.error("--timeout must be >= 1")
    if args.poll_interval < 1:
        parser.error("--poll-interval must be >= 1")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        token = resolve_token(args.token)
        sources = collect_sources(args)
    except MinerUError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    output_root = Path(args.output).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    print(f"Processing {len(sources)} source(s) into {output_root}")

    outcomes: list[ProcessOutcome] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_map = {
            executor.submit(process_item, source, args, token, output_root): source
            for source in sources
        }
        for future in concurrent.futures.as_completed(future_map):
            source = future_map[future]
            try:
                outcome = future.result()
            except Exception as exc:
                outcome = ProcessOutcome(source.source, str(output_root / source.output_stem), "failed", error=str(exc))
            outcomes.append(outcome)
            if outcome.skipped:
                print(f"SKIP {source.name} -> {outcome.output_dir}")
            elif outcome.status == "done":
                print(f"OK   {source.name} -> {outcome.output_dir}")
            else:
                print(f"FAIL {source.name}: {outcome.error}", file=sys.stderr)

    failed = [outcome for outcome in outcomes if outcome.status != "done"]
    skipped = [outcome for outcome in outcomes if outcome.skipped]
    print(f"Done: {len(outcomes) - len(failed)} succeeded ({len(skipped)} skipped), {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
