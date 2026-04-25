# Prompt：从 git diff 生成 CHANGELOG 条目

> **如何使用**：把整篇内容（含尖括号变量）发给 LLM（Cursor、Claude Code 等），并提供 git diff 与 commit messages 作为上下文。LLM 将输出符合 Keep a Changelog 规范的条目。

---

## 角色

你是一名熟悉「Keep a Changelog」规范与「语义化版本」原则的资深技术作家，正在为代码仓库维护 `docs/CHANGELOG.md`。

## 上下文

**项目名称**：<PROJECT_NAME>

**目标版本**：<TARGET_VERSION>（如 1.2.0；填 `Unreleased` 表示尚未发版）

**git diff 摘要**（必填）：
```diff
<把 git diff 或 git diff --stat 的输出粘到这里>
```

**commit messages**（可选但强烈推荐）：
```
<把 git log --pretty=%s SINCE..HEAD 的输出粘到这里>
```

## 任务

阅读上下文，产出一段可直接追加到 `docs/CHANGELOG.md` 中 `[<TARGET_VERSION>]` 段落的 Markdown 内容。

## 必须遵循的规则

1. **使用六个标准段落**：`Added` / `Changed` / `Deprecated` / `Removed` / `Fixed` / `Security`，每个段落使用 `### 段落名` 三级标题。无内容的段落直接省略。
2. **每条目一行**，以 `- ` 开头；语言风格保持一致（中文）。
3. **用户视角描述**：写「用户能感知的变化」，不要写「改动了哪个文件」。
   - ✅ 好：`新增邮箱密码登录方式`
   - ❌ 差：`修改 auth.py 增加 EmailLogin 类`
4. **聚合同义条目**：多个 commit 描述同一件事时合并为一条；不要把 `feat:` 和后续的 `refactor:` 重复列。
5. **明确标注 Breaking Change**：如果某条目改变了已发布的对外行为，前置 `⚠️ Breaking ` 文本。
6. **保持简洁**：单条目 ≤ 80 字。
7. **不要写日期**、不要写版本号链接定义、不要重复声明文件名。

## 启发式映射（从 commit 类型到段落）

| commit 前缀 | 通常归类到 |
|-------------|-----------|
| `feat`, `feature`, `add` | `Added` |
| `fix`, `bugfix` | `Fixed` |
| `perf`, `refactor`, `change`, `update`, `improve` | `Changed` |
| `deprecate` | `Deprecated` |
| `remove`, `delete` | `Removed` |
| `security`, `sec`, CVE-相关 | `Security` |
| `chore`, `style`, `test`, `docs`, `ci`, `build` | 通常忽略，除非影响外部 |

## 输出格式

直接输出 Markdown，不要外部任何说明。示例：

```markdown
### Added
- 新增邮箱密码登录方式（POST /api/auth/login）
- 用户列表支持按状态筛选

### Changed
- ⚠️ Breaking 用户列表响应字段 `name` 重命名为 `fullName`
- 默认每页数量从 10 提升至 20

### Fixed
- 修复跨时区订单创建时间显示错误
- 修复在 Safari 中文件上传偶尔失败的问题

### Security
- 升级 jsonwebtoken 至 9.0.2 修复 CVE-2024-0001
```

## 现在开始
请基于上述 diff 和 commit messages 生成 CHANGELOG 内容。
