---
name: dev-docs
description: Use when finishing a feature, fixing a bug, or changing an API and need to write/update PRD, API docs, CHANGELOG, or API CHANGELOG. Triggers include phrases like "生成文档"、"写文档"、"更新文档"、"补充 PRD"、"维护 changelog"、"接口文档"、"release notes"，or after completing development tasks that affect users or API consumers.
---

# 开发文档自动化 Skill

## Overview

把"开发完成"和"文档完成"绑定。本 Skill 提供：

- 4 套标准模板（PRD、API、CHANGELOG、API CHANGELOG）位于 `templates/`
- 3 个自动化脚本（变更分析、文档更新、文档校验）位于 `scripts/`
- 3 个 AI prompt 模板（让 LLM 根据 git diff 生成更智能的文档描述）位于 `prompts/`
- 多语言 API 识别能力：Python（FastAPI/Flask/Django）、Node.js（Express/Koa/NestJS）、Java（Spring）、Go（Gin/Echo/net-http），以及通用 OpenAPI/Swagger 解析

**核心原则**：每次代码变更都应有对应文档变更——CHANGELOG 是必填项，PRD 在新功能时创建，API 文档在接口变更时同步。

---

## When to Use

**应当使用的场景：**
- 完成新功能开发，需要补 PRD 和 CHANGELOG
- 修改/新增/废弃 API 接口
- 修复 bug 后需要追加 CHANGELOG（Fixed 段）
- 准备发版，需要把 `[Unreleased]` 转为正式版本
- 收到"生成文档"、"更新文档"、"维护 changelog"、"补充 API 文档"等请求
- 代码 review 时发现文档与代码不同步

**不应使用的场景：**
- 临时探索性脚本、一次性实验代码（不需要文档化）
- 仅修改注释、格式化、重命名（无用户可见变化）
- 内部重构且不影响外部接口（除非影响显著，仅在 CHANGELOG `Changed` 段记录）
- 项目尚未初始化文档目录（先运行 `python scripts/update_docs.py init`）

---

## Quick Reference

| 场景 | 必更文档 | 命令入口 |
|------|----------|----------|
| 新功能 | PRD + CHANGELOG（Added）+ API 文档（如有接口） | `req` → `changelog -t added` → `api -t add` |
| 接口变更 | API.md + API_CHANGELOG + CHANGELOG | `api -t change` → 手动改 API.md |
| Bug 修复 | CHANGELOG（Fixed） | `changelog -t fixed` |
| 废弃接口 | API_CHANGELOG（标注迁移路径） | `api -t deprecate` |
| 移除接口 | API_CHANGELOG + CHANGELOG（Breaking） | `api -t remove` → `changelog -t removed` |
| 发版 | 把 [Unreleased] 转正 + 打 tag | `release --version x.y.z` |
| 文档校验 | 校验格式/链接/版本 | `validate` |

| 文件 | 路径 | 作用 |
|------|------|------|
| PRD 模板 | `templates/PRD.md` | 需求文档结构 |
| API 模板 | `templates/API.md` | 接口文档结构 |
| CHANGELOG 模板 | `templates/CHANGELOG.md` | Keep a Changelog 格式 |
| API CHANGELOG 模板 | `templates/API_CHANGELOG.md` | 接口变更追踪 |
| 变更分析 | `scripts/analyze_changes.py` | 解析 git diff，识别 API 改动 |
| 文档更新 | `scripts/update_docs.py` | 维护 CHANGELOG / API CHANGELOG / PRD |
| 文档校验 | `scripts/validate_docs.py` | 校验格式、链接、版本一致性 |
| API 文档生成 | `scripts/generate_api_doc.py` | 从代码/OpenAPI 生成完整 API.md |
| AI Prompt 模板 | `prompts/*.md` | 让 LLM 写更智能的描述 |

---

## Core Workflow

### 决策流：来了变更，该走哪条路？

```
变更类型？
├─ 新功能 ──────────► [W1: 新功能流程]
├─ 接口变更 ────────► [W2: 接口流程]
├─ Bug 修复 ────────► [W3: 修复流程]
└─ 准备发版 ────────► [W4: 发版流程]
```

### W1：新功能流程

```bash
# 1. 分析变更，识别 API 改动（多语言自动识别）
python scripts/analyze_changes.py

# 2. 创建需求文档
python scripts/update_docs.py req -n "feature-name" -t "功能标题" -a "Jem"
#   → 生成 docs/requirements/REQ-feature-name.md，按 templates/PRD.md 结构

# 3. 追加 CHANGELOG
python scripts/update_docs.py changelog -t added -m "支持邮箱登录"

# 4. 如有新接口
python scripts/update_docs.py api -t add -e "POST /api/auth/login" -d "邮箱密码登录"

# 5.（可选）从代码自动生成 API.md
python scripts/generate_api_doc.py --source ./src --output docs/api/API.md

# 6. 校验文档
python scripts/validate_docs.py
```

### W2：接口变更流程

```bash
python scripts/update_docs.py api -t change -e "GET /api/users" -d "新增 status 筛选参数"
# 手动同步 docs/api/API.md 中该接口的参数表与示例
python scripts/update_docs.py changelog -t changed -m "用户列表接口支持按状态筛选"
```

> **Breaking Change** 必须在 API_CHANGELOG 条目前加 `⚠️ Breaking` 并在 CHANGELOG 中独立成段。

### W3：Bug 修复流程

```bash
python scripts/update_docs.py changelog -t fixed -m "修复日期跨时区解析错误"
```

### W4：发版流程

```bash
# 把 [Unreleased] 段落转换为正式版本，自动注入日期与对比链接
python scripts/update_docs.py release --version 1.2.0

# 同时处理 API_CHANGELOG（如有变更）
python scripts/update_docs.py release --version 1.2.0 --target api

# 打 tag（手动）
git tag -a v1.2.0 -m "Release 1.2.0"
```

---

## Documentation Structure

每次启动新项目，先运行：

```bash
python scripts/update_docs.py init
```

生成的目录结构：

```
docs/
├── CHANGELOG.md              # 项目变更日志
├── architecture.md            # 架构文档（已有则跳过）
├── api/
│   ├── API.md                # API 接口详细文档
│   ├── API_CHANGELOG.md      # API 变更日志
│   └── openapi.yaml          # （可选）OpenAPI 规范
└── requirements/
    └── REQ-{feature}.md      # 各功能的需求文档
```

---

## Multi-Language API Recognition

`analyze_changes.py` 自动识别以下框架的接口定义。所有模式集中在 `scripts/api_patterns.py`，方便扩展。

| 语言 | 框架 | 识别模式 |
|------|------|----------|
| Python | FastAPI | `@app.get(...)`、`@router.post(...)` |
| Python | Flask | `@app.route("/path", methods=["POST"])` |
| Python | Django | `path("...", view)`、`url(r"...")` |
| Node.js | Express/Koa | `app.get("/path", ...)`、`router.post(...)` |
| Node.js | NestJS | `@Get(...)`、`@Post(...)` 控制器装饰器 |
| Java | Spring | `@GetMapping`、`@PostMapping`、`@RequestMapping` |
| Go | Gin | `r.GET("/path", handler)`、`r.POST(...)` |
| Go | Echo | `e.GET(...)`、`e.POST(...)` |
| Go | net/http | `http.HandleFunc("/path", ...)`、`mux.Handle(...)` |
| 通用 | OpenAPI 3.0 | 解析 `openapi.yaml` / `openapi.json` |

---

## AI Prompt Templates

当 git diff 信息丰富时，仅靠正则无法生成高质量描述。`prompts/` 提供了三个为 LLM 设计的 prompt 模板：

| 模板 | 用途 |
|------|------|
| `prompts/changelog_from_diff.md` | 把 git diff + commit messages → CHANGELOG 用户视角条目 |
| `prompts/api_doc_from_code.md` | 从代码 + docstring → 完整接口文档段落 |
| `prompts/prd_from_feature.md` | 从功能描述 + 代码改动 → PRD 草稿 |

在 Cursor / Claude Code 中使用：

```
用户：帮我用 prompts/changelog_from_diff.md 模板，根据当前 git diff 生成 CHANGELOG
```

AI 会读取模板、注入 diff、产出符合 Keep a Changelog 风格的条目。

---

## Common Mistakes

| 错误做法 | 正确做法 |
|----------|----------|
| CHANGELOG 写"修改 auth.py" | 写"支持邮箱密码登录"（用户视角） |
| 废弃接口直接删除 | 先用 `api -t deprecate` 标注迁移路径，下个大版本再删 |
| Breaking Change 不显式标注 | API_CHANGELOG 条目前必须加 `⚠️ Breaking` |
| PRD 占位符不替换就交付 | 用 `validate_docs.py` 检查残留的 `{xxx}` 与 `[待填写：]` |
| API 路径硬编码到 PRD | PRD 只列接口清单，详情链接到 API.md |
| 多人同一天编辑 [Unreleased] 冲突 | 让脚本插入新条目（自动避免格式破坏） |
| 一次发版混入未发布的实验功能 | 发版前 review [Unreleased] 段落，移除未发布特性 |

---

## Red Flags - STOP

如果你有这些念头，停下来检查：

- "改动很小，不用更新 CHANGELOG" → 任何用户可见变更都要记录
- "改完代码再补文档" → 代码合并 = 文档同步合并，否则永远不会补
- "API 变了但只改了实现" → 任何外部可观察的行为都是 API 的一部分
- "直接编辑 docs/CHANGELOG.md 更快" → 用脚本以保证格式与链接正确
- "PRD 模板太重，简化几节吧" → 删占位符可，但保留 8 个一级章节框架

---

## Validation Checklist

提交前自检（也可用 `python scripts/validate_docs.py`）：

- [ ] CHANGELOG 中所有变更条目都从用户视角描述
- [ ] 每个新接口都同时出现在 API.md（详情）和 API_CHANGELOG.md（条目）
- [ ] Breaking Change 已显式标注 `⚠️ Breaking`
- [ ] PRD 已无 `{占位符}` 与 `[待填写：]`
- [ ] CHANGELOG 版本号与 `package.json` / `pyproject.toml` 等一致
- [ ] 文档内的相对链接均可访问
- [ ] 发版条目包含日期，且日期格式为 `YYYY-MM-DD`

---

## Best Practices

1. **频率优先于完美**：每次提交都顺手补一行 CHANGELOG，胜过一周后回忆。
2. **用户视角描述**：CHANGELOG 写"用户能感知的变化"，不是"哪个文件改了"。
3. **PRD 与代码互链**：PRD 链 API.md，API.md 顶部链 PRD，便于追溯。
4. **中文注释、中文文档**：与代码注释保持一致语种。
5. **脚本优先于手改**：能用 `update_docs.py` 完成就别手改 Markdown，避免破坏链接定义与格式。
6. **校验进 CI**：把 `validate_docs.py` 接入 CI，未通过禁止合并。

---

## Cross-References

- 写 SKILL 本身：参见 `superpowers:writing-skills`
- TDD 实现：参见 `superpowers:test-driven-development`
- 验证完成：参见 `superpowers:verification-before-completion`
