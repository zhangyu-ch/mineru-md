# MinerU v4 API Notes

This skill uses the MinerU v4 Precision Extract API at `https://mineru.net/api/v4`.

## Supported Scope

- Supported inputs: PDF and HTML files or URLs.
- PDF model: `vlm` by default, or `pipeline` when the user asks for speed.
- HTML model: always `MinerU-HTML`.
- Limits: 200 MB per file, 200 pages per file, 50 files/URLs per batch request.
- Authentication: `Authorization: Bearer <token>`.

## Local File Upload

Use `POST /file-urls/batch` with one local file per task for predictable per-file retries and manifests.

Request body for PDF:

```json
{
  "files": [
    {
      "name": "paper.pdf",
      "data_id": "paper",
      "is_ocr": false,
      "page_ranges": "1-5"
    }
  ],
  "model_version": "vlm",
  "enable_formula": true,
  "enable_table": true,
  "language": "ch"
}
```

Request body for HTML:

```json
{
  "files": [
    {
      "name": "page.html",
      "data_id": "page"
    }
  ],
  "model_version": "MinerU-HTML"
}
```

Upload the file to the returned signed URL with `PUT` and the raw file bytes. Do not set a multipart upload body.

Poll `GET /extract-results/batch/{batch_id}` until the first `extract_result` state is `done` or `failed`.

## URL Extraction

Use `POST /extract/task` for a single URL.

Request body for PDF:

```json
{
  "url": "https://example.com/paper.pdf",
  "data_id": "paper",
  "model_version": "vlm",
  "is_ocr": false,
  "enable_formula": true,
  "enable_table": true,
  "language": "ch",
  "page_ranges": "1-5"
}
```

Request body for HTML:

```json
{
  "url": "https://example.com/page.html",
  "data_id": "page",
  "model_version": "MinerU-HTML"
}
```

Poll `GET /extract/task/{task_id}` until `state` is `done` or `failed`.

## Result Handling

- Successful v4 responses contain `full_zip_url`.
- Download the ZIP, validate all ZIP member paths before extraction, then extract into the per-document output directory.
- Rename `full.md` to `<safe-input-stem>.md`.
- Keep other extracted files, including images, JSON, HTML, and layout artifacts.
- Write `manifest.json` for every run, including failed runs.

## Common Failures

- Invalid or expired token: ask the user to refresh the MinerU token.
- File too large or too many pages: ask the user to split the document.
- URL fetch timeout: ask for a local file upload instead.
- Result ZIP download issues from `cdn-mineru.openxlab.org.cn`: retry, then try the equivalent `mineru.oss-cn-shanghai.aliyuncs.com` host without disabling TLS verification.
