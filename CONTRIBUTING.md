# 贡献指南

感谢你对 dev-docs 项目的关注！我们欢迎任何形式的贡献，包括但不限于：

- 报告 Bug
- 提交新功能建议
- 改进文档
- 提交代码修复或新功能

## 开始之前

1. 请先查看 [Issues](https://github.com/YOUR_USERNAME/dev-docs-skill/issues) 确认你的问题或想法是否已被讨论
2. 对于较大的改动，建议先开一个 Issue 讨论

## 开发流程

### 1. Fork 并克隆仓库

```bash
# Fork 仓库后克隆到本地
git clone https://github.com/YOUR_USERNAME/dev-docs-skill.git
cd dev-docs-skill
```

### 2. 创建功能分支

```bash
git checkout -b feature/your-feature-name
# 或者
git checkout -b fix/your-fix-name
```

### 3. 进行修改

- 确保代码风格一致
- 添加必要的注释（使用中文）
- 如果添加新功能，请更新相关文档

### 4. 测试你的修改

```bash
# 测试脚本是否正常工作
python scripts/update_docs.py init
python scripts/analyze_changes.py --help
```

### 5. 提交更改

```bash
git add .
git commit -m "feat: 添加新功能描述"
# 或者
git commit -m "fix: 修复问题描述"
```

#### Commit Message 规范

我们使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

| 类型 | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 仅文档更改 |
| `style` | 不影响代码含义的更改（空格、格式化等） |
| `refactor` | 既不修复 bug 也不添加功能的代码更改 |
| `perf` | 提高性能的代码更改 |
| `test` | 添加缺失的测试或修正现有测试 |
| `chore` | 对构建过程或辅助工具的更改 |

示例：
```
feat: 添加对 TypeScript 项目的支持
fix: 修复 Windows 路径解析问题
docs: 更新 README 安装说明
```

### 6. 推送并创建 Pull Request

```bash
git push origin feature/your-feature-name
```

然后在 GitHub 上创建 Pull Request。

## Pull Request 指南

1. **标题清晰**：使用规范的 commit message 格式
2. **描述详细**：说明做了什么改动、为什么要这样做
3. **关联 Issue**：如果相关，请在 PR 描述中引用 Issue（如 `Closes #123`）
4. **保持更新**：如果 main 分支有更新，请 rebase 你的分支

## 代码风格

### Python

- 遵循 [PEP 8](https://www.python.org/dev/peps/pep-0008/) 规范
- 使用 4 空格缩进
- 函数和类添加 docstring
- 注释使用中文

```python
def example_function(param: str) -> bool:
    """
    示例函数
    
    Args:
        param: 参数描述
        
    Returns:
        返回值描述
    """
    # 这是一个注释
    return True
```

### Markdown

- 使用有意义的标题层级
- 代码块指定语言
- 表格对齐

## 报告 Bug

报告 Bug 时，请包含以下信息：

1. **环境信息**
   - Python 版本
   - 操作系统
   - Cursor 版本（如适用）

2. **重现步骤**
   - 清晰的步骤说明如何触发问题

3. **期望行为**
   - 你期望发生什么

4. **实际行为**
   - 实际发生了什么

5. **错误信息**
   - 如果有错误信息，请完整贴出

## 功能建议

提交功能建议时，请说明：

1. **问题背景**：这个功能解决什么问题？
2. **解决方案**：你建议如何实现？
3. **替代方案**：是否考虑过其他解决方案？
4. **附加信息**：任何有助于理解这个建议的信息

## 问题？

如果你有任何问题，欢迎：

- 开一个 Issue 讨论
- 查看现有文档

感谢你的贡献！
