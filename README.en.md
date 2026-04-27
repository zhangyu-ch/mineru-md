# mineru-md

[中文](README.md) | English | [AI Manual](ai_manual.md)

`mineru-md` is a Codex skill that lets an agent convert PDF and HTML files or URLs into high-quality Markdown through the MinerU v4 Precision Extract API before reading, summarizing, or extracting information from those documents.

This repository is written for people who want to install and use the skill. In normal use, you do not need to learn how the internal converter script works. Install the skill, configure a MinerU token, and ask your agent to use `$mineru-md`.

## Who This Is For

- Users who want Codex or another skill-aware agent to read PDF, HTML, exported web docs, papers, contracts, reports, or technical documentation.
- Users who want the agent to convert documents before answering, reducing information loss from direct PDF/HTML reading.
- Users who need figures, scanned pages, charts, tables, formulas, and image assets preserved for better document understanding.
- Users who want to deploy a reusable document parsing capability into their Codex skills directory.

## What It Provides

- Supports PDF, HTML, local files, and remote URLs.
- Uses the MinerU v4 Precision Extract API. PDF uses the high-quality `vlm` model by default.
- Produces Markdown plus image and structured output assets.
- Supports batch inputs, resumable conversion, and conversion status records.
- Provides a skill-level workflow so the agent can run conversion and read the result when needed.

## Repository Layout

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
|-- README.en.md
|-- ai_manual.md
|-- LICENSE
|-- requirements.txt
`-- .gitignore
```

For normal installation, deploy the `mineru-md/` skill folder to your Codex skills directory. The tests and repository-level docs are for maintenance and validation.

## Requirements

- Python 3.10 or later.
- Network access to the MinerU API.
- A valid MinerU API token.
- A Codex or agent environment that supports local skills.

Install Python dependencies:

```bash
python -m pip install -r requirements.txt
```

## Install Into Codex Skills

1. Clone the repository:

```bash
git clone https://github.com/zhangyu-ch/mineru-md.git
cd mineru-md
```

2. Copy the skill folder.

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.codex\skills" | Out-Null
Copy-Item -Recurse -Force ".\mineru-md" "$env:USERPROFILE\.codex\skills\mineru-md"
```

Linux/macOS:

```bash
mkdir -p ~/.codex/skills
cp -R ./mineru-md ~/.codex/skills/mineru-md
```

3. Confirm that these files exist after deployment:

```text
~/.codex/skills/mineru-md/SKILL.md
~/.codex/skills/mineru-md/scripts/mineru_md.py
~/.codex/skills/mineru-md/references/mineru-api.md
```

If your Codex environment uses a different skills directory, place `mineru-md/` in the directory your environment actually loads.

## Configure the MinerU Token

`mineru-md` requires a MinerU API token. Use an environment variable or a local token file. Do not commit real tokens to git, README files, chat logs, or shared scripts.

The skill resolves credentials in this order:

1. `--token`
2. `MINERU_TOKEN`
3. `MINERU_API_TOKEN`
4. `~/.config/mineru/token`

Recommended option: environment variable.

Windows PowerShell:

```powershell
$env:MINERU_TOKEN = "your-mineru-token"
```

Linux/macOS:

```bash
export MINERU_TOKEN="your-mineru-token"
```

Recommended option: local token file.

Linux/macOS:

```bash
mkdir -p ~/.config/mineru
printf '%s\n' 'your-mineru-token' > ~/.config/mineru/token
chmod 600 ~/.config/mineru/token
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.config\mineru" | Out-Null
Set-Content -Path "$env:USERPROFILE\.config\mineru\token" -Value "your-mineru-token"
```

## Ask an Agent to Use It

After installation and token setup, explicitly ask your agent to use `$mineru-md` for PDF or HTML documents. Examples:

```text
Please use $mineru-md to read this PDF and extract the summary, key conclusions, and table data.
```

```text
Please use $mineru-md to convert this HTML document to Markdown first, then summarize the API documentation.
```

```text
This folder contains several PDFs. Please use $mineru-md to parse them in batch and group the findings by topic.
```

When the agent uses the skill correctly, it should:

- Locate the PDF/HTML file or URL you provided.
- Run the `mineru-md` skill conversion.
- Check the conversion result status first.
- Read the generated Markdown.
- Inspect output image assets as well when the question depends on charts, scanned pages, diagrams, visual tables, or image details.

You do not need to provide internal script arguments unless you are troubleshooting deployment or using an environment that cannot load skills automatically.

## Good Prompt Examples

- "Use `$mineru-md` to read this paper and produce a Chinese summary."
- "Use `$mineru-md` to parse this PDF contract, then extract parties, amount, term, and risk clauses."
- "Use `$mineru-md` to read this HTML API documentation and generate an endpoint list."
- "This report contains charts. Use `$mineru-md`, inspect image assets, and then answer my questions."

## How the Agent Uses the Output

The conversion output usually includes:

- A main Markdown file.
- A `manifest.json` status file.
- Images, layout data, and other MinerU assets.

As a human user, you usually only need to confirm that the agent completed conversion and answered from the converted content. For visual questions, remind the agent to inspect image assets instead of relying only on Markdown.

## FAQ

### The agent cannot find `$mineru-md`

Check that the `mineru-md/` folder was copied into the skills directory your Codex environment actually loads, and that this file exists:

```text
~/.codex/skills/mineru-md/SKILL.md
```

If your environment uses a custom skills path, use that configured path instead.

### The agent says there is no MinerU token

Configure `MINERU_TOKEN`, `MINERU_API_TOKEN`, or create `~/.config/mineru/token`. Restart the agent session if needed so the new environment variable is visible to the agent process.

### The PDF is too large or has too many pages

MinerU API has file size and page limits. Split the document or ask the agent to process only the relevant part.

### The parsed result misses chart details

Ask the agent to inspect the image assets in the conversion output and answer using both Markdown and images.

### Do I need to run the Python script manually?

Not in normal skill usage. The agent invokes the underlying script based on `SKILL.md`. Direct script execution is only useful for troubleshooting installation, token, network, or non-Codex integrations.

## Manual for AI/Agents

If you want another AI to deploy or troubleshoot this project, ask it to read [ai_manual.md](ai_manual.md). It explains how an agent should check installation paths, dependencies, token setup, invocation behavior, and common failure modes.

## Maintenance and Tests

When developing or modifying the skill, run:

```bash
python -m unittest discover -s tests
```

Tests are for repository maintenance. Normal users usually do not need to run them to use the skill.

## Security

- Do not commit real MinerU tokens.
- Do not upload `.env` files, local credential files, conversion outputs, or parsed content containing private information.
- Converted Markdown and image assets may contain sensitive source document content. Review them before sharing.

## License

MIT License. See [LICENSE](LICENSE).
