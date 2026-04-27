# mineru-md

中文 | [English](README.en.md) | [AI Manual](ai_manual.md)

`mineru-md` 是一个 Codex Skill，用于让 Agent 在阅读、总结、抽取 PDF/HTML 文档前，先通过 MinerU v4 精准解析 API 将文件或 URL 转换为高质量 Markdown，并保留图片等结构化资产。

这个仓库面向“想安装并使用 Skill 的人”。如果你只是希望 Agent 帮你读 PDF 或 HTML，通常不需要了解内部脚本怎么运行，只需要完成安装、Token 配置，并在对话中明确让 Agent 使用 `$mineru-md`。

## 适合谁使用

- 想让 Codex/Agent 读取 PDF、HTML、网页导出的技术文档、论文、合同、报告。
- 希望 Agent 在回答前先转换文档，减少直接读取 PDF/HTML 时的信息丢失。
- 需要保留图片、扫描页、图表、表格、公式等结构化内容，方便 Agent 结合 Markdown 和图片资产分析。
- 希望把一个可复用的文档解析能力部署到自己的 Codex skills 目录中。

## 功能概览

- 支持 PDF、HTML、本地文件和远程 URL。
- 使用 MinerU v4 Precision Extract API，PDF 默认使用高质量 `vlm` 模型。
- 转换结果包含 Markdown、图片和相关结构化文件。
- 支持批量输入、断点续跑和转换状态记录。
- Skill 已封装调用流程，Agent 可按需自动运行转换并读取结果。

## 仓库结构

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

日常安装时，只需要把 `mineru-md/` 这个 Skill 文件夹部署到 Codex skills 目录；仓库里的测试和文档用于维护与验证。

## 安装要求

- Python 3.10 或更高版本。
- 可以访问 MinerU API 的网络环境。
- 一个有效的 MinerU API Token。
- 支持本地 Skill 的 Codex/Agent 环境。

安装 Python 依赖：

```bash
python -m pip install -r requirements.txt
```

## 安装到 Codex skills 目录

1. 克隆仓库：

```bash
git clone https://github.com/zhangyu-ch/mineru-md.git
cd mineru-md
```

2. 复制 Skill 文件夹。

Windows PowerShell：

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.codex\skills" | Out-Null
Copy-Item -Recurse -Force ".\mineru-md" "$env:USERPROFILE\.codex\skills\mineru-md"
```

Linux/macOS：

```bash
mkdir -p ~/.codex/skills
cp -R ./mineru-md ~/.codex/skills/mineru-md
```

3. 确认部署后的文件存在：

```text
~/.codex/skills/mineru-md/SKILL.md
~/.codex/skills/mineru-md/scripts/mineru_md.py
~/.codex/skills/mineru-md/references/mineru-api.md
```

如果你的 Codex 环境使用不同的 skills 目录，请把 `mineru-md/` 放到该环境实际读取的 skills 路径下。

## 配置 MinerU Token

`mineru-md` 需要 MinerU API Token。推荐使用环境变量或本地 token 文件，不要把真实 Token 写入 Git 仓库、README、对话记录或共享脚本。

Token 获取地址：[https://mineru.net/apiManage/token](https://mineru.net/apiManage/token)

Skill 会按以下顺序读取凭据：

1. `--token`
2. `MINERU_TOKEN`
3. `MINERU_API_TOKEN`
4. `~/.config/mineru/token`

推荐方式一：环境变量。

Windows PowerShell：

```powershell
$env:MINERU_TOKEN = "your-mineru-token"
```

Linux/macOS：

```bash
export MINERU_TOKEN="your-mineru-token"
```

推荐方式二：本地 token 文件。

Linux/macOS：

```bash
mkdir -p ~/.config/mineru
printf '%s\n' 'your-mineru-token' > ~/.config/mineru/token
chmod 600 ~/.config/mineru/token
```

Windows PowerShell：

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.config\mineru" | Out-Null
Set-Content -Path "$env:USERPROFILE\.config\mineru\token" -Value "your-mineru-token"
```

## 如何让 Agent 调用

安装并配置 Token 后，在对话中直接说明要使用 `$mineru-md` 处理 PDF 或 HTML。示例：

```text
请使用 $mineru-md 读取这个 PDF，提炼摘要、关键结论和表格数据。
```

```text
请先用 $mineru-md 把这个 HTML 文档转换为 Markdown，再帮我整理接口说明。
```

```text
这个文件夹里有多份 PDF，请用 $mineru-md 批量解析，然后按主题归纳。
```

Agent 正确使用时通常会：

- 找到你提供的 PDF/HTML 文件或 URL。
- 调用 `mineru-md` Skill 完成转换。
- 先检查转换结果状态。
- 读取生成的 Markdown。
- 当问题涉及图表、扫描页、流程图、视觉表格或图片细节时，同时检查输出图片资产。

你不需要告诉 Agent 底层脚本参数，除非你是在排查部署问题，或你的运行环境不支持自动加载 Skill。

## 适合的用户提示词

- “请使用 `$mineru-md` 阅读这篇论文，并输出中文摘要。”
- “请先用 `$mineru-md` 解析这份 PDF 合同，再提取甲乙方、金额、期限和风险条款。”
- “请用 `$mineru-md` 读取这个 HTML API 文档，生成接口清单。”
- “这份报告里有图表，请用 `$mineru-md` 转换后同时检查图片资产，再回答问题。”

## 输出结果如何被 Agent 使用

转换结果一般会包含：

- Markdown 主文件。
- `manifest.json` 状态文件。
- 图片、布局和其他 MinerU 资产。

对人类用户来说，通常只需要确认 Agent 已成功完成转换并基于转换结果回答。对依赖视觉信息的问题，应提醒 Agent 不要只看 Markdown，还要检查图片资产。

## 常见问题

### Agent 说找不到 `$mineru-md`

检查 `mineru-md/` 是否复制到了 Codex 实际读取的 skills 目录，并确认 `SKILL.md` 位于：

```text
~/.codex/skills/mineru-md/SKILL.md
```

如果你使用的是自定义 skills 路径，请以你的环境配置为准。

### Agent 提示没有 MinerU Token

配置 `MINERU_TOKEN`、`MINERU_API_TOKEN`，或创建 `~/.config/mineru/token`。完成后重新打开 Agent 会话，或确保新环境变量对当前 Agent 进程可见。

### PDF 很大或页数很多

MinerU API 对文件大小和页数有限制。请拆分文档，或让 Agent 只处理你关心的部分。

### 解析结果缺少图表信息

让 Agent 同时检查转换输出目录中的图片资产，并基于图片和 Markdown 一起回答。

### 是否必须手动运行 Python 脚本

正常使用 Skill 时不需要。底层脚本由 Agent 根据 `SKILL.md` 调用。只有在排查安装、Token、网络或非 Codex 环境集成时，才需要直接运行脚本。

## 给 AI/Agent 的说明

如果你希望把这个仓库交给另一个 AI 来部署或排障，请让它阅读 [ai_manual.md](ai_manual.md)。该文件说明了 Agent 应如何检查安装路径、依赖、Token、调用方式和常见失败场景。

## 维护与测试

开发或修改 Skill 时可以运行测试：

```bash
python -m unittest discover -s tests
```

测试用于维护仓库质量；普通用户安装和调用 Skill 时通常不需要运行测试。

## 安全提醒

- 不要提交真实 MinerU Token。
- 不要上传 `.env`、本地凭据文件、转换输出目录或包含隐私内容的解析结果。
- 转换后的 Markdown 和图片资产可能包含原文档敏感信息，分享前请单独审查。

## 许可证

MIT License. See [LICENSE](LICENSE).
