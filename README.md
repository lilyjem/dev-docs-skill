# dev-docs - 开发文档自动化工具

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.7+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/Cursor-Agent%20Skill-purple.svg" alt="Cursor">
  <img src="https://img.shields.io/badge/Claude%20Code-AGENTS.md-orange.svg" alt="Claude Code">
</p>

**dev-docs** 是一个为 AI 编程助手设计的 Agent Skill，支持 [Cursor IDE](https://cursor.sh) 和 [Claude Code](https://docs.anthropic.com/en/docs/claude-code)，用于自动化生成和维护项目开发文档。它可以帮助开发者在完成功能开发后自动生成需求文档（PRD）、API接口文档，并在代码更新时自动维护 CHANGELOG。

## ✨ 功能特性

- 📝 **需求文档自动生成** - 使用标准化模板自动创建 PRD 文档
- 📚 **API 文档维护** - 自动检测 API 变更并更新文档
- 📋 **CHANGELOG 管理** - 遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/) 规范
- 🔍 **Git 变更分析** - 自动分析代码变更并生成文档更新建议
- 🤖 **多平台支持** - 同时支持 Cursor IDE 和 Claude Code

## 📦 安装

### 方式一：作为 Cursor Skill 安装

1. 将整个 `dev-docs` 文件夹复制到 Cursor skills 目录：
   
   ```bash
   # Windows
   cp -r dev-docs-skill ~/.cursor/skills/dev-docs
   
   # macOS/Linux
   cp -r dev-docs-skill ~/.cursor/skills/dev-docs
   ```

2. 在 Cursor 中使用时，AI 会自动识别并使用此 Skill

### 方式二：作为 Claude Code AGENTS.md 安装

1. 将 `SKILL.md` 的内容复制到项目根目录的 `AGENTS.md` 文件中：
   
   ```bash
   # 克隆仓库
   git clone https://github.com/lilyjem/dev-docs-skill.git
   
   # 复制到你的项目
   cp dev-docs-skill/SKILL.md your-project/AGENTS.md
   ```

2. 或者直接在项目中创建 `AGENTS.md`，将 `SKILL.md` 内容粘贴进去

3. Claude Code 会自动读取 `AGENTS.md` 并遵循其中的指导

### 方式三：独立使用脚本

1. 克隆仓库：
   
   ```bash
   git clone https://github.com/lilyjem/dev-docs-skill.git
   cd dev-docs-skill
   ```

2. 将 `scripts` 目录复制到你的项目中：
   
   ```bash
   cp -r scripts your-project/
   ```

## 🚀 快速开始

### 初始化文档结构

在项目根目录运行以下命令，创建标准化的文档目录结构：

```bash
python scripts/update_docs.py init
```

这将创建：
```
docs/
├── CHANGELOG.md           # 项目变更日志
├── api/
│   ├── API.md            # API 接口文档
│   └── API_CHANGELOG.md  # API 变更日志
└── requirements/
    └── REQ-<feature>.md  # 各功能的需求文档
```

### 分析 Git 变更

```bash
# 分析当前未提交的变更
python scripts/analyze_changes.py

# 分析从指定 commit 到 HEAD 的变更
python scripts/analyze_changes.py --since HEAD~5

# 输出为 JSON 格式
python scripts/analyze_changes.py --json

# 保存到文件
python scripts/analyze_changes.py --output changes_report.txt
```

### 更新 CHANGELOG

```bash
# 记录新增功能
python scripts/update_docs.py changelog -t added -m "新增用户认证功能"

# 记录功能变更
python scripts/update_docs.py changelog -t changed -m "优化PDF解析性能"

# 记录Bug修复
python scripts/update_docs.py changelog -t fixed -m "修复日期格式解析错误"

# 记录移除的功能
python scripts/update_docs.py changelog -t removed -m "移除旧版API支持"
```

### 更新 API CHANGELOG

```bash
# 新增接口
python scripts/update_docs.py api -t add -e "POST /api/users" -d "创建用户"

# 接口变更
python scripts/update_docs.py api -t change -e "GET /api/users" -d "新增分页参数"

# 废弃接口
python scripts/update_docs.py api -t deprecate -e "GET /api/old" -d "将在v2.0移除"

# 移除接口
python scripts/update_docs.py api -t remove -e "DELETE /api/legacy" -d "已废弃"
```

### 创建需求文档

```bash
# 创建新的需求文档
python scripts/update_docs.py req -n "user-auth" -t "用户认证功能" -a "Jem"

# 强制覆盖已存在的文档
python scripts/update_docs.py req -n "user-auth" --force
```

## 📖 文档模板

### 需求文档 (PRD)

每个功能模块都有独立的需求文档，包含以下章节：

| 章节 | 内容 |
|------|------|
| 文档信息 | 编号、版本、日期、状态 |
| 功能概述 | 简要描述、关键词 |
| 背景和目标 | 为什么做、目标是什么 |
| 功能需求 | 用户故事、功能清单、业务规则 |
| 非功能需求 | 性能、安全、兼容性 |
| UI/交互设计 | 页面布局、交互流程 |
| 数据模型 | 表结构、字段说明 |
| 验收标准 | 验收条件、测试用例 |
| 时间节点 | 里程碑计划 |

### API 文档

标准化的 API 文档格式：

- 接口基础信息（版本、Base URL）
- 认证方式说明
- 接口详细列表（路径、参数、示例）
- 数据模型定义
- 错误码说明
- 多语言调用示例（cURL、Python、JavaScript）

### CHANGELOG

遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/) 规范：

- **Added**: 新增功能
- **Changed**: 功能变更
- **Deprecated**: 即将废弃
- **Removed**: 已移除
- **Fixed**: Bug 修复
- **Security**: 安全相关

## 🔧 典型工作流

### 工作流 1：新功能开发

```bash
# 1. 开发完成后，分析代码变更
python scripts/analyze_changes.py

# 2. 创建需求文档
python scripts/update_docs.py req -n "feature-name" -t "功能标题"
# 编辑生成的需求文档，填写详细内容

# 3. 更新 CHANGELOG
python scripts/update_docs.py changelog -t added -m "新增XX功能"

# 4. 如果有新 API，更新 API 文档
python scripts/update_docs.py api -t add -e "POST /api/xxx" -d "接口描述"

# 5. 提交代码和文档
git add .
git commit -m "feat: 新增XX功能"
```

### 工作流 2：Bug 修复

```bash
# 1. 修复完成后，更新 CHANGELOG
python scripts/update_docs.py changelog -t fixed -m "修复XX问题"

# 2. 提交
git add .
git commit -m "fix: 修复XX问题"
```

### 工作流 3：API 变更

```bash
# 1. 更新 API CHANGELOG
python scripts/update_docs.py api -t change -e "GET /api/xxx" -d "变更说明"

# 2. 手动更新 API.md 中的接口详情

# 3. 更新 CHANGELOG
python scripts/update_docs.py changelog -t changed -m "更新XX接口"
```

## 🤖 在 AI 编程助手中使用

### Cursor IDE

当此 Skill 安装到 Cursor 后，AI 助手会在以下场景自动触发：

1. **用户说"生成文档"、"写文档"、"更新文档"时**
2. **完成一个功能开发后**
3. **更新了代码需要同步文档时**
4. **用户提到 PRD、API文档、changelog、需求文档时**

### Claude Code

将 `SKILL.md` 内容放入项目根目录的 `AGENTS.md` 文件后，Claude Code 会：

1. **自动识别文档生成需求** - 当你完成功能开发并请求生成文档时
2. **遵循标准化模板** - 使用预定义的 PRD、API 文档模板
3. **维护变更日志** - 自动更新 CHANGELOG 和 API CHANGELOG

### 示例对话

```
用户: 我刚完成了用户认证功能的开发，帮我生成相关文档

AI: 好的，我来帮你生成用户认证功能的相关文档...
    1. 首先分析代码变更...
    2. 创建需求文档 REQ-user-auth.md...
    3. 更新 API 文档...
    4. 追加 CHANGELOG 条目...
```

## 📁 项目结构

```
dev-docs-skill/
├── SKILL.md              # Skill 定义文件 (Cursor / Claude Code AGENTS.md)
├── README.md             # 本文件
├── LICENSE               # MIT 许可证
├── CONTRIBUTING.md       # 贡献指南
├── requirements.txt      # Python 依赖
├── scripts/
│   ├── analyze_changes.py    # Git 变更分析脚本
│   └── update_docs.py        # 文档更新脚本
└── examples/
    ├── CHANGELOG.md          # CHANGELOG 示例
    ├── API.md                # API 文档示例
    └── REQ-example.md        # 需求文档示例
```

## 🔄 平台兼容性

| 平台 | 安装方式 | 说明 |
|------|----------|------|
| **Cursor IDE** | 复制到 `~/.cursor/skills/` | 作为 Agent Skill 自动加载 |
| **Claude Code** | 复制到项目 `AGENTS.md` | 作为项目级指导文件 |
| **其他 AI 工具** | 直接使用 `scripts/` | 命令行工具独立使用 |

## 🤝 贡献

欢迎贡献代码！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [Keep a Changelog](https://keepachangelog.com/) - CHANGELOG 格式规范
- [Semantic Versioning](https://semver.org/) - 语义化版本规范
- [Cursor IDE](https://cursor.sh) - AI 驱动的代码编辑器
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) - Anthropic 的 AI 编程助手

---

<p align="center">
  Made with ❤️ for better documentation<br>
  Supporting Cursor IDE & Claude Code
</p>
