# dev-docs - 开发文档自动化工具

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/Cursor-Skill-purple.svg" alt="Cursor">
  <img src="https://img.shields.io/badge/Claude%20Code-Skill-orange.svg" alt="Claude Code">
</p>

**dev-docs** 是一个为 AI 编程助手设计的 Skill，支持 [Cursor IDE](https://cursor.sh) 和 [Claude Code](https://code.claude.com)，用于自动化生成、维护与校验项目开发文档（PRD、API 文档、CHANGELOG、API CHANGELOG）。

> 1.x 是逆向式整理工具：先有代码改动，再回头让 LLM + 脚本把功能落到文档上。它**不是**正向需求规划工具。

---

## ✨ 功能特性

- 📝 **PRD 自动生成** — 标准化模板（背景/SMART 目标/验收标准/上线计划/回滚方案）
- 📚 **API 文档双通道生成** — OpenAPI 规范文件 **或** 源码 docstring/注释扫描，统一渲染成 `API.md`
- 🌐 **多语言/多框架** — Python (FastAPI / Flask / Django) · Node.js (Express / Koa / NestJS) · Java (Spring) · Go (Gin / Echo / net-http)
- 🔍 **Git 变更智能分析** — 对比前后两个 ref 的接口差异，启发式分类 Conventional Commits 推荐 CHANGELOG 条目
- 📋 **CHANGELOG 全自动维护** — 写入条目 / 自动 release 当前版本 / 校验格式 / 标注 ⚠️ Breaking
- 🛡️ **文档校验器** — Keep a Changelog 格式、SemVer、相对链接、占位符、版本一致性
- 🤖 **AI Prompt 模板** — 给 LLM 喂 git diff / 源码 / 功能描述，输出符合本仓库风格的 CHANGELOG / API / PRD 段落
- 🪶 **零依赖** — 纯 Python 标准库，开箱即用

---

## 📦 安装

### 方式一：作为 Cursor Skill 安装

```bash
# macOS / Linux
mkdir -p ~/.cursor/skills/dev-docs
cp -r dev-docs-skill/* ~/.cursor/skills/dev-docs/
```

Cursor 会通过 `agent_skills` 自动发现并按需加载。

### 方式二：作为 Claude Code Skill 安装

**个人级别（推荐）：**

```bash
mkdir -p ~/.claude/skills/dev-docs
cp -r dev-docs-skill/{SKILL.md,scripts,templates,prompts} ~/.claude/skills/dev-docs/
```

**项目级别（团队共享）：**

```bash
mkdir -p .claude/skills/dev-docs
cp -r dev-docs-skill/{SKILL.md,scripts,templates,prompts} .claude/skills/dev-docs/
git add .claude/skills/ && git commit -m "chore: add dev-docs skill"
```

调用方式：
- **自动触发**：说「生成文档」「写 PRD」「更新 changelog」「维护 API 文档」时
- **手动调用**：`/dev-docs <任务描述>`（Claude Code）

### 方式三：仅使用脚本

```bash
git clone https://github.com/lilyjem/dev-docs-skill.git
cp -r dev-docs-skill/scripts dev-docs-skill/templates dev-docs-skill/prompts your-project/
```

---

## 🚀 快速开始

### 1. 初始化文档结构

在项目根目录运行：

```bash
python scripts/update_docs.py init
```

生成：

```
docs/
├── CHANGELOG.md             # 项目变更日志（Keep a Changelog）
├── api/
│   ├── API.md               # API 接口文档
│   └── API_CHANGELOG.md     # API 变更日志（含 ⚠️ Breaking 标注）
└── requirements/
    └── README.md            # 需求文档索引
```

### 2. 一句话工作流（推荐）

```bash
# A. 提交前 / PR 前：分析 Git 变更，得到文档更新建议
python scripts/analyze_changes.py --since HEAD~5

# B. 写入条目（按建议填写）
python scripts/update_docs.py changelog -t added -m "新增订单导出 CSV"
python scripts/update_docs.py api -t add -e "POST /api/orders/export" -d "导出订单 CSV"

# C. 校验文档
python scripts/validate_docs.py

# D. 发版时一键 release
python scripts/update_docs.py release -v 1.4.0
```

---

## 📜 命令参考

### `analyze_changes.py` — Git 变更分析

```bash
# 分析当前未提交变更
python scripts/analyze_changes.py

# 分析自指定 ref 起的变更
python scripts/analyze_changes.py --since HEAD~10
python scripts/analyze_changes.py --since v1.3.0 --until HEAD

# JSON 输出（便于 CI / LLM 二次处理）
python scripts/analyze_changes.py --json --output changes.json
```

输出包含：变更文件分类（功能代码/测试/配置/文档）、API endpoint diff（新增/修改/移除，带框架与行号）、按 Conventional Commits 分组的提交 message。

### `generate_api_doc.py` — 生成 API.md

```bash
# 从 OpenAPI 规范生成（YAML 需安装 PyYAML，JSON 用标准库）
python scripts/generate_api_doc.py --openapi openapi.yaml --output docs/api/API.md
python scripts/generate_api_doc.py --openapi openapi.json --output docs/api/API.md

# 扫描源码（自动识别 6 框架的装饰器/路由）
python scripts/generate_api_doc.py --source src/ --output docs/api/API.md

# 双通道合并（OpenAPI 优先，源码补缺）
python scripts/generate_api_doc.py --openapi openapi.yaml --source src/ --output docs/api/API.md
```

提取规则：Python docstring、JSDoc（含单行 `/** ... */`）、Javadoc、Go doc。

### `update_docs.py` — 文档维护

```bash
# 项目 CHANGELOG
python scripts/update_docs.py changelog -t added   -m "新增功能描述"
python scripts/update_docs.py changelog -t changed -m "修改说明"
python scripts/update_docs.py changelog -t fixed   -m "修复说明"
python scripts/update_docs.py changelog -t deprecated -m "废弃说明"
python scripts/update_docs.py changelog -t removed -m "移除说明"
python scripts/update_docs.py changelog -t security -m "安全补丁说明"

# API CHANGELOG（--breaking 自动加 ⚠️ Breaking 标注）
python scripts/update_docs.py api -t add        -e "POST /api/users" -d "创建用户"
python scripts/update_docs.py api -t change     -e "GET /api/users"  -d "新增分页参数"
python scripts/update_docs.py api -t deprecate  -e "GET /api/old"    -d "v2.0 移除"
python scripts/update_docs.py api -t remove     -e "DELETE /api/legacy" -d "已废弃" --breaking

# 创建 PRD
python scripts/update_docs.py req -n user-auth -t "用户认证功能" -a Jem
python scripts/update_docs.py req -n user-auth --force   # 强制覆盖

# 一键发版（把 Unreleased 区块提升为 v1.4.0 - 2026-04-25，并补 compare 链接）
python scripts/update_docs.py release -v 1.4.0
python scripts/update_docs.py release -v 1.4.0 --target api   # 只 release API CHANGELOG
```

### `validate_docs.py` — 文档校验

```bash
# 全量校验（默认 docs/ 目录）
python scripts/validate_docs.py

# 严格模式：警告也视为失败（CI 推荐）
python scripts/validate_docs.py --strict

# JSON 输出（便于 CI / GitHub Actions）
python scripts/validate_docs.py --json
```

校验规则码：

| 规则码 | 校验项 |
|--------|--------|
| CL001-006 | CHANGELOG 头/`[Unreleased]`/SemVer/日期/分类章节 |
| AC001-004 | API CHANGELOG 章节/`⚠️ Breaking` 标注完整性 |
| PRD001-004 | PRD 必备章节（文档信息/功能需求/验收标准等） |
| LINK001 | 内部相对链接有效性（自动跳过 HTML 注释与代码块） |
| PH001 | 文档中遗留的 `{占位符}` |
| VER001 | CHANGELOG 顶部版本号与 `package.json`/`pyproject.toml`/`setup.py`/`Cargo.toml` 一致 |

---

## 🤖 AI Prompt 模板

`prompts/` 目录提供三个开箱即用的 LLM prompt，把上下文塞进去即可一次得到符合本仓库风格的输出：

| 模板 | 输入 | 输出 |
|------|------|------|
| `prompts/changelog_from_diff.md` | 项目名 + 目标版本 + git diff + commit messages | Keep a Changelog 风格的版本块 |
| `prompts/api_doc_from_code.md` | 接口源码 + 数据模型 + 业务背景 | 一段可粘贴到 `API.md` 的接口段落 |
| `prompts/prd_from_feature.md` | 功能简述 + 关键代码改动 + 数据表 | 完整的 PRD 草稿（与 `templates/PRD.md` 一致） |

使用方式（在 Cursor / Claude Code 内）：

```
请使用 prompts/changelog_from_diff.md 这个模板，
项目名是 my-app，目标版本 v1.4.0。
diff 见 git diff v1.3.0..HEAD：
<贴 diff>
```

---

## 📖 文档模板

`templates/` 目录是规范化骨架，所有脚本生成的内容都基于它们：

| 模板 | 内容 |
|------|------|
| `templates/PRD.md` | 文档信息、SMART 目标、用户故事、业务规则、边界异常、数据模型、验收标准、上线计划、回滚方案 |
| `templates/API.md` | 基础约定、版本策略、限流、认证、数据模型、错误码、cURL/Python/JS/Go 调用示例 |
| `templates/CHANGELOG.md` | Keep a Changelog 标准格式（Added/Changed/Deprecated/Removed/Fixed/Security） |
| `templates/API_CHANGELOG.md` | API 变更专用，含 `⚠️ Breaking` 标注规范与迁移指引 |

---

## 🔧 典型工作流

### 工作流 1：新功能开发后整理文档

```bash
# 1. 让脚本告诉你哪些接口/文件变了
python scripts/analyze_changes.py --since HEAD~5

# 2. 让 LLM 用 prompts/prd_from_feature.md 生成 PRD 草稿
#    把功能描述 + 关键代码贴给它，得到 docs/requirements/REQ-xxx.md

# 3. 让 LLM 用 prompts/api_doc_from_code.md 补全 API.md 接口段落
#    或：直接 python scripts/generate_api_doc.py --source src/

# 4. 写入 CHANGELOG
python scripts/update_docs.py changelog -t added -m "新增 XX 功能"
python scripts/update_docs.py api -t add -e "POST /api/xxx" -d "..."

# 5. 提交前校验
python scripts/validate_docs.py --strict
```

### 工作流 2：发版

```bash
# 1. 校验
python scripts/validate_docs.py --strict

# 2. 一键 release（自动加日期 + 更新 compare 链接）
python scripts/update_docs.py release -v 1.4.0
python scripts/update_docs.py release -v 1.4.0 --target api

# 3. 提交并打 tag
git add docs/ && git commit -m "chore(release): v1.4.0"
git tag v1.4.0
```

### 工作流 3：CI 集成

```yaml
# .github/workflows/docs.yml
name: Docs validation
on: [pull_request]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.11"}
      - name: Validate documentation
        run: python scripts/validate_docs.py --strict --json > docs-report.json
      - uses: actions/upload-artifact@v4
        with: {name: docs-report, path: docs-report.json}
```

---

## 📁 项目结构

```
dev-docs-skill/
├── SKILL.md                    # Skill 主定义
├── README.md                   # 本文件
├── LICENSE                     # MIT
├── CONTRIBUTING.md             # 贡献指南
├── requirements.txt            # （零依赖；预留可选 dev 依赖）
├── scripts/
│   ├── analyze_changes.py      # Git 变更分析（多语言 endpoint diff）
│   ├── api_patterns.py         # 多语言 API 模式库
│   ├── generate_api_doc.py     # API.md 生成（OpenAPI / 源码扫描）
│   ├── update_docs.py          # 文档维护（init / changelog / api / req / release）
│   └── validate_docs.py        # 文档校验（格式 / 链接 / 版本）
├── templates/
│   ├── PRD.md
│   ├── API.md
│   ├── CHANGELOG.md
│   └── API_CHANGELOG.md
├── prompts/
│   ├── changelog_from_diff.md
│   ├── api_doc_from_code.md
│   └── prd_from_feature.md
└── examples/
    ├── CHANGELOG.md
    ├── API.md
    ├── API_CHANGELOG.md
    └── REQ-example.md
```

---

## 🌐 平台兼容性

| 平台 | 安装位置 | 作用范围 | 调用方式 |
|------|----------|----------|----------|
| **Cursor IDE** | `~/.cursor/skills/dev-docs/` | 所有项目 | 自动触发 |
| **Claude Code（个人）** | `~/.claude/skills/dev-docs/` | 所有项目 | `/dev-docs` 或自动触发 |
| **Claude Code（项目）** | `.claude/skills/dev-docs/` | 当前项目 | `/dev-docs` 或自动触发 |
| **命令行** | 项目 `scripts/` 目录 | 当前项目 | 直接 `python scripts/xxx.py` |

---

## 🤝 贡献

欢迎贡献代码！请查看 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## 📄 许可证

MIT — 详见 [LICENSE](LICENSE)。

---

## 🙏 致谢

- [Keep a Changelog](https://keepachangelog.com/zh-CN/)
- [Semantic Versioning](https://semver.org/)
- [OpenAPI Specification](https://www.openapis.org/)
- [Cursor IDE](https://cursor.sh) · [Claude Code](https://code.claude.com)
- [Agent Skills 标准](https://code.claude.com/docs/en/skills)

---

<p align="center">
  Made with ❤️ for better documentation<br>
  Cursor IDE & Claude Code
</p>
