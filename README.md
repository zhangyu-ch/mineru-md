# mineru-md

`mineru-md` is a Codex skill for converting PDF and HTML files or URLs into high-quality Markdown with image assets through the MinerU v4 Precision Extract API.

`mineru-md` 是一个面向 Codex 的 Skill，用于通过 MinerU v4 精准解析 API 将 PDF、HTML 文件或 URL 转换为高质量 Markdown，并保留图片等结构化资产。

> This project is a community skill wrapper around the MinerU API. You need your own MinerU API token. Do not commit real tokens to this repository.
>
> 本项目是围绕 MinerU API 的社区 Skill 封装。你需要自行准备 MinerU API Token。不要把真实 Token 提交到仓库中。

## 中文说明

### 功能特性

- 支持本地 `.pdf`、`.html`、`.htm` 文件转换为 Markdown。
- 支持远程 PDF/HTML URL 转换为 Markdown。
- 支持目录批处理、递归扫描、并发处理和断点续跑。
- PDF 默认使用 MinerU `vlm` 模型，必要时可切换到 `pipeline` 以提升速度。
- HTML 自动使用 `MinerU-HTML` 模型。
- 支持 OCR、语言提示、页码范围、公式解析和表格解析开关。
- 每个输入生成独立输出目录，并写入 `manifest.json`，便于确认状态和定位 Markdown 文件。
- 下载并安全解压 MinerU 结果包，防止 ZIP 路径穿越。
- 保留 MinerU 输出中的图片、布局、JSON、HTML 等辅助文件，便于进一步核查视觉内容。

### 适用场景

- 在回答 PDF/HTML 文档问题前，先把原文转换为 Markdown。
- 解析论文、报告、合同、产品文档、API 文档中的正文、标题、表格、公式和图片说明。
- 批量转换一个目录中的 PDF/HTML 文件。
- 对扫描页、图表、流程图、复杂表格等视觉信息进行二次检查。

### 仓库结构

```text
.
|-- mineru-md/
|   |-- SKILL.md
|   |-- agents/
|   |   `-- openai.yaml
|   |-- references/
|   |   `-- mineru-api.md
|   `-- scripts/
|       `-- mineru_md.py
|-- tests/
|   `-- test_mineru_md.py
|-- README.md
|-- LICENSE
|-- requirements.txt
`-- .gitignore
```

### 安装

1. 克隆仓库：

```bash
git clone https://github.com/zhangyu-ch/mineru-md.git
cd mineru-md
```

2. 安装 Python 依赖：

```bash
python -m pip install -r requirements.txt
```

3. 将 `mineru-md/` 文件夹放到你的 Codex skills 目录中，或在支持本地 skill 的工作区中直接引用该文件夹。

常见位置示例：

```text
~/.codex/skills/mineru-md
```

Windows PowerShell 示例：

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.codex\skills" | Out-Null
Copy-Item -Recurse -Force ".\mineru-md" "$env:USERPROFILE\.codex\skills\mineru-md"
```

### Token 配置

转换脚本需要 MinerU API Token。脚本按以下优先级读取凭据：

1. 命令行参数：`--token`
2. 环境变量：`MINERU_TOKEN`
3. 环境变量：`MINERU_API_TOKEN`
4. 文件：`~/.config/mineru/token`

推荐使用环境变量或本地 token 文件，不推荐把 token 写入命令历史或提交到仓库。

Linux/macOS:

```bash
export MINERU_TOKEN="your-mineru-token"
```

Windows PowerShell:

```powershell
$env:MINERU_TOKEN = "your-mineru-token"
```

本地 token 文件：

```bash
mkdir -p ~/.config/mineru
printf '%s\n' 'your-mineru-token' > ~/.config/mineru/token
chmod 600 ~/.config/mineru/token
```

### 使用方法

转换单个 PDF：

```bash
python mineru-md/scripts/mineru_md.py --file ./paper.pdf --output ./mineru-output --resume
```

转换单个 HTML：

```bash
python mineru-md/scripts/mineru_md.py --file ./page.html --output ./mineru-output --resume
```

转换远程 URL：

```bash
python mineru-md/scripts/mineru_md.py --url https://example.com/paper.pdf --output ./mineru-output
```

批量转换目录：

```bash
python mineru-md/scripts/mineru_md.py --dir ./docs --recursive --workers 3 --resume
```

从 URL 列表批量转换：

```bash
python mineru-md/scripts/mineru_md.py --urls-file ./urls.txt --output ./mineru-output --workers 3
```

只解析 PDF 的部分页码：

```bash
python mineru-md/scripts/mineru_md.py --file ./paper.pdf --pages "1-5,8" --output ./mineru-output
```

开启 OCR 并指定中文：

```bash
python mineru-md/scripts/mineru_md.py --file ./scan.pdf --ocr --language ch --output ./mineru-output
```

切换 PDF 模型为 `pipeline`：

```bash
python mineru-md/scripts/mineru_md.py --file ./paper.pdf --model pipeline --output ./mineru-output
```

### 输出说明

每个输入会生成一个独立目录：

```text
mineru-output/
`-- paper/
    |-- manifest.json
    |-- paper.md
    |-- images/
    |-- layout.json
    `-- other-mineru-assets
```

读取转换结果时，应先打开 `manifest.json`：

```json
{
  "source": "...",
  "source_kind": "file",
  "name": "paper.pdf",
  "model": "vlm",
  "status": "done",
  "markdown_path": "/absolute/path/to/mineru-output/paper/paper.md",
  "error": null
}
```

只有当 `status` 为 `done` 时，才应继续读取 `markdown_path` 指向的 Markdown 文件。若用户问题依赖图片、扫描页、图表、流程图或复杂表格，应同时检查输出目录中的图片和相关资产，不要只依赖 Markdown 文本。

### CLI 参数

输入来源，四选一：

- `--file`：单个本地 `.pdf`、`.html` 或 `.htm` 文件。
- `--dir`：包含 PDF/HTML 文件的目录。
- `--url`：单个远程 PDF/HTML URL。
- `--urls-file`：每行一个 URL 的文本文件，空行和 `#` 注释行会被忽略。

常用参数：

- `--output`：输出目录，默认 `./mineru-output`。
- `--workers`：并发处理数量，默认 `3`。
- `--resume`：跳过已完成的输出。
- `--recursive`：配合 `--dir` 递归扫描。
- `--timeout`：单个任务等待秒数，默认 `1800`。
- `--poll-interval`：轮询间隔秒数，默认 `5`。
- `--model`：PDF 模型，可选 `vlm` 或 `pipeline`，默认 `vlm`。
- `--ocr`：启用 PDF OCR。
- `--language`：PDF 语言提示，默认 `auto`。
- `--pages`：PDF 页码范围，例如 `"1-5,8"`。
- `--no-formula`：关闭公式解析。
- `--no-table`：关闭表格解析。
- `--token`：直接传入 MinerU API Token。
- `--keep-zip`：保留下载的 MinerU 结果 ZIP。

查看完整帮助：

```bash
python mineru-md/scripts/mineru_md.py --help
```

### API 与限制

- API 基址：`https://mineru.net/api/v4`
- 本地文件上传：`POST /file-urls/batch`
- URL 抽取：`POST /extract/task`
- 本地文件上传限制：单文件最大 200 MB。
- 页数限制：单文件最大 200 页。
- 批量请求限制：最多 50 个文件或 URL。
- 认证方式：`Authorization: Bearer <token>`。

更多接口行为、请求字段和常见失败处理见 `mineru-md/references/mineru-api.md`。

### 错误处理建议

- Token 无效或过期：刷新 MinerU Token 后重试。
- 文件过大或页数过多：拆分文档后重试。
- URL 下载超时：改用本地文件上传。
- 任务超时：调大 `--timeout`，并配合 `--resume` 续跑。
- ZIP 下载失败：脚本会重试，并在必要时尝试 MinerU CDN 的等价 OSS 域名。

### 安全注意事项

- 不要提交真实 API Token、`.env`、本地凭据文件或转换输出目录。
- `--token` 会出现在命令历史中，建议优先使用环境变量或 `~/.config/mineru/token`。
- 转换结果可能包含原文档中的敏感信息，发布或分享前请单独审查 `mineru-output/`。
- 脚本会校验 ZIP 成员路径，防止结果包解压到目标目录之外。

### 测试

```bash
python -m unittest discover -s tests
```

当前测试覆盖：

- Token 读取优先级。
- PDF/HTML 模型选择。
- 支持语言参数解析。
- 本地文件和 URL 请求载荷构造。
- ZIP 安全解压。
- Markdown 文件归一化与断点续跑判断。
- 批量任务轮询成功、失败和超时场景。

### 贡献

欢迎提交 Issue 或 Pull Request。建议变更前后运行测试，并在 PR 中说明：

- 解决的问题或新增能力。
- 行为变化和兼容性影响。
- 验证方式。
- 是否涉及 API 字段、输出结构或 Token 处理逻辑。

## English

### Features

- Converts local `.pdf`, `.html`, and `.htm` files to Markdown.
- Converts remote PDF/HTML URLs to Markdown.
- Supports directory batch conversion, recursive scanning, concurrency, and resumable runs.
- Uses MinerU `vlm` for PDF by default, with optional `pipeline` for faster PDF extraction.
- Uses `MinerU-HTML` automatically for HTML inputs.
- Supports OCR, language hints, page ranges, formula extraction, and table extraction switches.
- Writes one output directory per input, including a `manifest.json` file for status and Markdown discovery.
- Downloads and safely extracts MinerU result archives with ZIP path validation.
- Preserves image, layout, JSON, HTML, and other MinerU assets for visual review.

### Use Cases

- Convert PDF/HTML documents to Markdown before answering questions about them.
- Extract content from papers, reports, contracts, product docs, API docs, tables, formulas, and figures.
- Batch-convert a directory of PDF/HTML documents.
- Review visual content such as scanned pages, charts, diagrams, and complex tables alongside Markdown.

### Repository Layout

```text
.
|-- mineru-md/
|   |-- SKILL.md
|   |-- agents/
|   |   `-- openai.yaml
|   |-- references/
|   |   `-- mineru-api.md
|   `-- scripts/
|       `-- mineru_md.py
|-- tests/
|   `-- test_mineru_md.py
|-- README.md
|-- LICENSE
|-- requirements.txt
`-- .gitignore
```

### Installation

1. Clone the repository:

```bash
git clone https://github.com/zhangyu-ch/mineru-md.git
cd mineru-md
```

2. Install Python dependencies:

```bash
python -m pip install -r requirements.txt
```

3. Place the `mineru-md/` folder in your Codex skills directory, or reference it directly from a workspace that supports local skills.

Typical location:

```text
~/.codex/skills/mineru-md
```

Windows PowerShell example:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.codex\skills" | Out-Null
Copy-Item -Recurse -Force ".\mineru-md" "$env:USERPROFILE\.codex\skills\mineru-md"
```

### Token Configuration

The converter requires a MinerU API token. Credentials are resolved in this order:

1. CLI argument: `--token`
2. Environment variable: `MINERU_TOKEN`
3. Environment variable: `MINERU_API_TOKEN`
4. File: `~/.config/mineru/token`

Environment variables or a local token file are recommended. Avoid storing tokens in shell history or committing them to git.

Linux/macOS:

```bash
export MINERU_TOKEN="your-mineru-token"
```

Windows PowerShell:

```powershell
$env:MINERU_TOKEN = "your-mineru-token"
```

Local token file:

```bash
mkdir -p ~/.config/mineru
printf '%s\n' 'your-mineru-token' > ~/.config/mineru/token
chmod 600 ~/.config/mineru/token
```

### Usage

Convert one PDF:

```bash
python mineru-md/scripts/mineru_md.py --file ./paper.pdf --output ./mineru-output --resume
```

Convert one HTML file:

```bash
python mineru-md/scripts/mineru_md.py --file ./page.html --output ./mineru-output --resume
```

Convert a remote URL:

```bash
python mineru-md/scripts/mineru_md.py --url https://example.com/paper.pdf --output ./mineru-output
```

Batch-convert a directory:

```bash
python mineru-md/scripts/mineru_md.py --dir ./docs --recursive --workers 3 --resume
```

Batch-convert from a URL list:

```bash
python mineru-md/scripts/mineru_md.py --urls-file ./urls.txt --output ./mineru-output --workers 3
```

Convert selected PDF pages only:

```bash
python mineru-md/scripts/mineru_md.py --file ./paper.pdf --pages "1-5,8" --output ./mineru-output
```

Enable OCR with a Chinese language hint:

```bash
python mineru-md/scripts/mineru_md.py --file ./scan.pdf --ocr --language ch --output ./mineru-output
```

Use the faster PDF `pipeline` model:

```bash
python mineru-md/scripts/mineru_md.py --file ./paper.pdf --model pipeline --output ./mineru-output
```

### Output

Each input gets its own output directory:

```text
mineru-output/
`-- paper/
    |-- manifest.json
    |-- paper.md
    |-- images/
    |-- layout.json
    `-- other-mineru-assets
```

Always inspect `manifest.json` first:

```json
{
  "source": "...",
  "source_kind": "file",
  "name": "paper.pdf",
  "model": "vlm",
  "status": "done",
  "markdown_path": "/absolute/path/to/mineru-output/paper/paper.md",
  "error": null
}
```

Only read the Markdown file when `status` is `done`. If the task depends on images, scanned pages, charts, diagrams, or complex visual tables, inspect the extracted image assets as well. Do not rely on Markdown alone for visual questions.

### CLI Options

Input source, choose exactly one:

- `--file`: one local `.pdf`, `.html`, or `.htm` file.
- `--dir`: a directory containing PDF/HTML files.
- `--url`: one remote PDF/HTML URL.
- `--urls-file`: a text file with one URL per line. Blank lines and `#` comments are ignored.

Common options:

- `--output`: output directory, default `./mineru-output`.
- `--workers`: number of concurrent sources, default `3`.
- `--resume`: skip completed outputs.
- `--recursive`: recursively scan `--dir`.
- `--timeout`: seconds to wait per source, default `1800`.
- `--poll-interval`: polling interval in seconds, default `5`.
- `--model`: PDF model, `vlm` or `pipeline`, default `vlm`.
- `--ocr`: enable OCR for PDF.
- `--language`: PDF language hint, default `auto`.
- `--pages`: PDF page ranges, for example `"1-5,8"`.
- `--no-formula`: disable formula extraction.
- `--no-table`: disable table extraction.
- `--token`: pass a MinerU API token directly.
- `--keep-zip`: keep the downloaded MinerU result ZIP.

Full help:

```bash
python mineru-md/scripts/mineru_md.py --help
```

### API and Limits

- API base: `https://mineru.net/api/v4`
- Local file upload: `POST /file-urls/batch`
- URL extraction: `POST /extract/task`
- Local file size limit: 200 MB per file.
- Page limit: 200 pages per file.
- Batch request limit: 50 files or URLs.
- Authentication: `Authorization: Bearer <token>`.

See `mineru-md/references/mineru-api.md` for request fields, API behavior, and common failure handling.

### Error Handling

- Invalid or expired token: refresh the MinerU token and retry.
- File too large or too many pages: split the document and retry.
- URL fetch timeout: use a local file upload instead.
- Task timeout: increase `--timeout` and rerun with `--resume`.
- ZIP download failure: the script retries and may switch from the MinerU CDN host to the equivalent OSS host.

### Security Notes

- Do not commit real API tokens, `.env` files, local credential files, or conversion outputs.
- `--token` can appear in shell history. Prefer environment variables or `~/.config/mineru/token`.
- Converted output may contain sensitive source document content. Review `mineru-output/` before sharing it.
- ZIP member paths are validated before extraction to prevent writing outside the output directory.

### Testing

```bash
python -m unittest discover -s tests
```

The current tests cover:

- Token resolution priority.
- PDF/HTML model selection.
- Documented language argument parsing.
- Local file and URL payload construction.
- Safe ZIP extraction.
- Markdown file normalization and resumable run detection.
- Batch polling success, failure, and timeout cases.

### Contributing

Issues and pull requests are welcome. Before submitting a change, run the tests and describe:

- The problem fixed or capability added.
- Behavior changes and compatibility impact.
- Validation performed.
- Whether the change affects API fields, output structure, or token handling.
