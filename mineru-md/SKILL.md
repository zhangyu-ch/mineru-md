---
name: mineru-md
description: Convert PDF and HTML files or URLs to high-quality Markdown with images using the MinerU v4 Precision Extract API. Use when Codex needs to parse, read, summarize, extract tables/formulas, or batch-convert local or remote .pdf/.html documents into Markdown while preserving figures and structured content.
---

# MinerU Markdown

Use this skill to convert PDF or HTML documents to Markdown through MinerU's v4 Precision Extract API before answering questions about those documents.

## Workflow

1. Locate the input document or URL. Supported inputs are `.pdf`, `.html`, and `.htm`.
2. Locate this skill's converter script at `scripts/mineru_md.py`.
3. Run the script with Python:

```bash
python scripts/mineru_md.py --file ./paper.pdf --output ./mineru-output --resume
python scripts/mineru_md.py --url https://example.com/page.html --output ./mineru-output
python scripts/mineru_md.py --dir ./docs --recursive --workers 3 --resume
```

4. Read `<output>/<document-stem>/manifest.json` first to confirm `status` is `done`.
5. Read the Markdown file named in `manifest.json` under `markdown_path`.
6. List the output directory and inspect referenced image assets when figures, scanned pages, visual tables, charts, or diagrams matter. Do not answer from Markdown alone if the user's request depends on visual content.

## Token

The script requires a MinerU API token. It resolves credentials in this order:

1. `--token`
2. `MINERU_TOKEN`
3. `MINERU_API_TOKEN`
4. `~/.config/mineru/token`

If no token is available, stop and ask the user to configure one. Do not fall back to the lightweight no-token API because this skill prioritizes quality and stability.

## Defaults

- Local files use `/api/v4/file-urls/batch`; URLs use `/api/v4/extract/task`.
- PDF defaults to `vlm`; `--model pipeline` can be used for faster PDF extraction.
- HTML always uses `MinerU-HTML`.
- Output is one directory per source, with the main Markdown normalized to `<safe-input-stem>.md`.
- `manifest.json` records the source, selected model, task or batch id, status, timing, main Markdown path, and any error.

## Options

Use `python scripts/mineru_md.py --help` for the complete CLI. Common options:

- `--file`, `--dir`, `--url`, or `--urls-file` for input.
- `--output ./mineru-output` for destination.
- `--workers 3`, `--resume`, and `--recursive` for batch runs.
- `--ocr`, `--language ch`, `--pages "1-5,8"`, `--no-formula`, and `--no-table` for extraction settings.
- `--keep-zip` to retain the downloaded MinerU result archive.

## Reference

Read `references/mineru-api.md` only when API behavior, request fields, limits, or failure handling need clarification.
