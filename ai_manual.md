# AI Manual for mineru-md

This file is for AI agents that need to help a user install, deploy, verify, or use the `mineru-md` Codex skill.

## Purpose

`mineru-md` converts PDF and HTML files or URLs into Markdown and image assets through MinerU v4 before the agent answers questions about those documents.

Prefer the skill workflow over asking the user to run the internal Python script manually. Direct script execution is appropriate only for troubleshooting, testing, or environments that cannot load Codex skills.

## Project Layout

```text
mineru-md/
|-- SKILL.md
|-- agents/openai.yaml
|-- references/mineru-api.md
`-- scripts/mineru_md.py
```

Repository-level files:

```text
README.md       Chinese user documentation
README.en.md    English user documentation
ai_manual.md    This file
requirements.txt
tests/test_mineru_md.py
```

## Installation Checklist

When helping a user deploy the project:

1. Confirm Python 3.10+ is available.
2. Install Python dependencies from the repository root:

```bash
python -m pip install -r requirements.txt
```

3. Copy the `mineru-md/` folder into the user's Codex skills directory.

Default paths:

```text
Windows: %USERPROFILE%\.codex\skills\mineru-md
Linux/macOS: ~/.codex/skills/mineru-md
```

4. Verify that the deployed skill contains:

```text
SKILL.md
scripts/mineru_md.py
references/mineru-api.md
```

5. Restart or refresh the agent environment if it does not detect newly installed skills automatically.

## Credential Requirements

The skill requires a MinerU API token. It resolves credentials in this order:

Token management URL: [https://mineru.net/apiManage/token](https://mineru.net/apiManage/token)

1. `--token`
2. `MINERU_TOKEN`
3. `MINERU_API_TOKEN`
4. `~/.config/mineru/token`

Recommended user-facing guidance:

- Prefer `MINERU_TOKEN` or `~/.config/mineru/token`.
- Do not ask the user to paste a real token into a public issue, README, repository file, or shared chat.
- If using environment variables, remind the user that already-running agent processes may need to be restarted to see the new value.

## How an Agent Should Invoke the Skill

Use `mineru-md` when the user asks to read, parse, summarize, inspect, or extract information from PDF or HTML files/URLs.

Typical user requests:

- "Use `$mineru-md` to read this PDF."
- "Parse this HTML API document before summarizing it."
- "Extract tables and formulas from this report."
- "This document contains charts; inspect the images too."

Expected agent workflow:

1. Locate the input file or URL.
2. Use the `mineru-md` skill instructions from `SKILL.md`.
3. Run conversion through the skill's converter.
4. Read the generated `manifest.json` first and continue only when `status` is `done`.
5. Read the Markdown path recorded in `manifest.json`.
6. Inspect image assets whenever the question depends on charts, scanned pages, visual tables, diagrams, figures, or layout.

Do not answer visual questions from Markdown alone if the converted output includes relevant images.

## User-Facing Guidance Style

For normal usage, tell the user:

- Install the skill folder.
- Configure the MinerU token.
- Ask the agent to use `$mineru-md`.

Avoid exposing internal converter commands as the primary workflow. The script is an implementation detail of the skill.

Use internal script details only when:

- Verifying the deployment works.
- Debugging missing dependencies.
- Debugging token resolution.
- Running tests or maintaining the repository.
- Supporting a non-Codex environment that cannot load skills.

## Troubleshooting

### Skill Not Detected

Check:

- `mineru-md/SKILL.md` exists under the active skills directory.
- The folder name is `mineru-md`.
- The agent environment has been restarted or refreshed.
- The user is not confusing the repository root with the deployed skill folder.

### Missing Token

Check:

- `MINERU_TOKEN` is available to the agent process.
- `MINERU_API_TOKEN` is available if used instead.
- `~/.config/mineru/token` exists and is readable.
- The token file contains only the token value, not labels or quotes.

### Dependency Failure

Check:

- Python version is 3.10+.
- `requests` is installed in the Python environment used by the agent.
- The agent and terminal are using the same Python environment when troubleshooting.

### API or Conversion Failure

Check:

- Token validity.
- Network access to `https://mineru.net/api/v4`.
- File type is `.pdf`, `.html`, or `.htm`.
- File size and page count are within MinerU API limits.
- For URL failures, suggest using a local file upload if possible.

### Output Seems Incomplete

Check:

- `manifest.json` status is `done`.
- The Markdown path exists.
- Image assets are present and inspected when the question depends on visual content.
- The user did not ask about pages or sections excluded from conversion.

## Validation Commands for Maintainers

From the repository root:

```bash
python -m unittest discover -s tests
```

Before publishing:

- Confirm `git ls-files` contains only intended project files.
- Run a secret scan for real tokens or private keys.
- Ensure generated outputs, caches, `.env`, and token files are not tracked.

## Safety Rules

- Never commit or display real MinerU tokens.
- Do not upload conversion outputs if source documents may be private.
- Do not remove or weaken the instruction that visual questions require image asset inspection.
- Do not replace the high-quality MinerU API workflow with a no-token fallback unless the user explicitly asks for a different skill design.
