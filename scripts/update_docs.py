#!/usr/bin/env python3
"""
自动更新文档工具

使用方法:
    python update_docs.py <action> [options]
    
Actions:
    init        初始化文档目录结构
    changelog   更新 CHANGELOG.md
    api         更新 API 文档和 API CHANGELOG
    req         创建或更新需求文档
    
Examples:
    python update_docs.py init
    python update_docs.py changelog --type added --message "新增XX功能"
    python update_docs.py api --endpoint "POST /api/xxx" --description "新增接口"
    python update_docs.py req --name "user-auth" --title "用户认证功能"
"""

import os
import re
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional


# ==================== 配置 ====================

DOCS_DIR = "docs"
API_DOCS_DIR = "docs/api"
REQUIREMENTS_DIR = "docs/requirements"


# ==================== 模板 ====================

CHANGELOG_TEMPLATE = '''# Changelog

本文件记录项目的所有重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Added
- 无

### Changed
- 无

### Fixed
- 无

### Removed
- 无

---

[Unreleased]: {repo_url}/compare/v1.0.0...HEAD
'''

API_CHANGELOG_TEMPLATE = '''# API Changelog

本文件记录 API 接口的所有变更。

## [Unreleased]

### 新增接口
- 无

### 接口变更
- 无

### 废弃接口
- 无

### 移除接口
- 无

---
'''

API_DOC_TEMPLATE = '''# {project_name} API 接口文档

## 文档信息

| 属性 | 值 |
|------|-----|
| 版本 | v1.0.0 |
| 最后更新 | {date} |
| 基础URL | `{base_url}` |

---

## 1. 概述

### 1.1 简介

{description}

### 1.2 基础信息

- **协议**: HTTP/HTTPS
- **数据格式**: JSON
- **字符编码**: UTF-8

---

## 2. 认证方式

### 2.1 认证类型

{auth_type}

### 2.2 认证方式

```
Authorization: Bearer {{token}}
```

---

## 3. 接口列表

{endpoints}

---

## 4. 数据模型

{models}

---

## 5. 错误码说明

| 错误码 | HTTP状态码 | 描述 | 解决方案 |
|--------|------------|------|----------|
| - | 200 | 成功 | - |
| - | 400 | 请求参数错误 | 检查请求参数格式 |
| - | 401 | 未授权 | 检查Token是否有效 |
| - | 403 | 禁止访问 | 检查用户权限 |
| - | 404 | 资源不存在 | 检查请求路径 |
| - | 500 | 服务器内部错误 | 联系管理员 |

---

## 附录

### A. 相关文档

- [架构文档](../architecture.md)
- [API变更日志](./API_CHANGELOG.md)
'''

REQUIREMENT_TEMPLATE = '''# {title} - 需求文档

## 文档信息

| 属性 | 值 |
|------|-----|
| 文档编号 | REQ-{number} |
| 版本 | v1.0 |
| 创建日期 | {date} |
| 最后更新 | {date} |
| 作者 | {author} |
| 状态 | 草稿 |

---

## 1. 功能概述

### 1.1 简要描述

{brief_description}

### 1.2 关键词

{keywords}

---

## 2. 背景和目标

### 2.1 背景

{background}

### 2.2 目标

- 目标 1：{goal1}
- 目标 2：{goal2}

### 2.3 非目标

{non_goals}

---

## 3. 功能需求

### 3.1 用户故事

| 编号 | 角色 | 需求 | 价值 |
|------|------|------|------|
| US-01 | 作为{role} | 我希望{want} | 以便{value} |

### 3.2 功能清单

| 编号 | 功能名称 | 优先级 | 描述 |
|------|----------|--------|------|
| F-01 | {feature_name} | P0 | {feature_description} |

### 3.3 业务规则

- BR-01：{business_rule}

---

## 4. 非功能需求

### 4.1 性能要求

- 响应时间：{performance}
- 吞吐量：{throughput}

### 4.2 安全要求

- {security}

### 4.3 兼容性

- {compatibility}

---

## 5. UI/交互设计

### 5.1 页面布局

{ui_layout}

### 5.2 交互流程

{interaction_flow}

### 5.3 状态说明

| 状态 | 显示效果 | 触发条件 |
|------|----------|----------|
| {state} | {display} | {trigger} |

---

## 6. 数据模型

### 6.1 数据表

{data_tables}

### 6.2 数据字段说明

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| {field} | {type} | 是/否 | {field_description} |

---

## 7. 验收标准

### 7.1 功能验收

- [ ] AC-01：{acceptance_criteria}

### 7.2 测试用例

| 用例编号 | 描述 | 预期结果 |
|----------|------|----------|
| TC-01 | {test_case} | {expected_result} |

---

## 8. 时间节点

| 里程碑 | 计划日期 | 实际日期 | 状态 |
|--------|----------|----------|------|
| 需求评审 | {date} | - | 待开始 |
| 开发完成 | {date} | - | 待开始 |
| 测试完成 | {date} | - | 待开始 |
| 上线发布 | {date} | - | 待开始 |

---

## 附录

### A. 相关文档

- [API 文档](../api/API.md)
- [架构文档](../architecture.md)

### B. 变更历史

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|----------|
| v1.0 | {date} | {author} | 初始版本 |
'''


# ==================== 工具函数 ====================

def ensure_dir(path: str) -> None:
    """确保目录存在"""
    Path(path).mkdir(parents=True, exist_ok=True)


def read_file(path: str) -> Optional[str]:
    """读取文件内容"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None


def write_file(path: str, content: str) -> None:
    """写入文件"""
    ensure_dir(str(Path(path).parent))
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"已写入: {path}")


def get_next_req_number() -> str:
    """获取下一个需求文档编号"""
    req_dir = Path(REQUIREMENTS_DIR)
    if not req_dir.exists():
        return "001"
    
    existing = list(req_dir.glob("REQ-*.md"))
    if not existing:
        return "001"
    
    # 从现有文件中提取编号
    numbers = []
    for f in existing:
        content = read_file(str(f))
        if content:
            match = re.search(r"文档编号\s*\|\s*REQ-(\d+)", content)
            if match:
                numbers.append(int(match.group(1)))
    
    if numbers:
        return f"{max(numbers) + 1:03d}"
    return f"{len(existing) + 1:03d}"


# ==================== 命令实现 ====================

def cmd_init(args):
    """初始化文档目录结构"""
    print("正在初始化文档目录结构...")
    
    # 创建目录
    ensure_dir(DOCS_DIR)
    ensure_dir(API_DOCS_DIR)
    ensure_dir(REQUIREMENTS_DIR)
    
    # 创建 CHANGELOG.md（如果不存在）
    changelog_path = f"{DOCS_DIR}/CHANGELOG.md"
    if not Path(changelog_path).exists():
        repo_url = "https://github.com/your-repo/your-project"
        write_file(changelog_path, CHANGELOG_TEMPLATE.format(repo_url=repo_url))
    else:
        print(f"跳过（已存在）: {changelog_path}")
    
    # 创建 API_CHANGELOG.md（如果不存在）
    api_changelog_path = f"{API_DOCS_DIR}/API_CHANGELOG.md"
    if not Path(api_changelog_path).exists():
        write_file(api_changelog_path, API_CHANGELOG_TEMPLATE)
    else:
        print(f"跳过（已存在）: {api_changelog_path}")
    
    print("文档目录初始化完成！")
    print(f"""
目录结构:
{DOCS_DIR}/
├── CHANGELOG.md
├── api/
│   ├── API.md
│   └── API_CHANGELOG.md
└── requirements/
    └── REQ-<feature>.md
""")


def cmd_changelog(args):
    """更新 CHANGELOG.md"""
    changelog_path = f"{DOCS_DIR}/CHANGELOG.md"
    content = read_file(changelog_path)
    
    if not content:
        print(f"错误: {changelog_path} 不存在，请先运行 init 命令")
        return
    
    # 构建新条目
    change_type = args.type.capitalize()
    message = args.message
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 查找对应的分类并插入
    section_pattern = rf"(### {change_type}\n)(- [^\n]+\n|无\n)"
    
    def replace_section(match):
        header = match.group(1)
        existing = match.group(2)
        
        if existing.strip() == "无":
            return f"{header}- {message}\n"
        else:
            return f"{header}- {message}\n{existing}"
    
    new_content = re.sub(section_pattern, replace_section, content, count=1)
    
    if new_content == content:
        print(f"警告: 未找到 '{change_type}' 分类，请检查 CHANGELOG 格式")
        return
    
    write_file(changelog_path, new_content)
    print(f"已更新 CHANGELOG: [{change_type}] {message}")


def cmd_api(args):
    """更新 API 文档和 API CHANGELOG"""
    api_changelog_path = f"{API_DOCS_DIR}/API_CHANGELOG.md"
    content = read_file(api_changelog_path)
    
    if not content:
        print(f"错误: {api_changelog_path} 不存在，请先运行 init 命令")
        return
    
    # 构建新条目
    change_type = args.type
    endpoint = args.endpoint
    description = args.description
    
    # 映射类型到中文
    type_map = {
        "add": "新增接口",
        "change": "接口变更", 
        "deprecate": "废弃接口",
        "remove": "移除接口"
    }
    section_name = type_map.get(change_type, "接口变更")
    
    # 查找对应的分类并插入
    section_pattern = rf"(### {section_name}\n)(- [^\n]+\n|无\n)"
    
    def replace_section(match):
        header = match.group(1)
        existing = match.group(2)
        
        entry = f"`{endpoint}` - {description}"
        
        if existing.strip() == "无":
            return f"{header}- {entry}\n"
        else:
            return f"{header}- {entry}\n{existing}"
    
    new_content = re.sub(section_pattern, replace_section, content, count=1)
    
    if new_content == content:
        print(f"警告: 未找到 '{section_name}' 分类，请检查 API CHANGELOG 格式")
        return
    
    write_file(api_changelog_path, new_content)
    print(f"已更新 API CHANGELOG: [{section_name}] {endpoint}")


def cmd_req(args):
    """创建或更新需求文档"""
    name = args.name
    title = args.title or name.replace("-", " ").title()
    author = args.author or "Unknown"
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 生成文件名
    filename = f"REQ-{name}.md"
    filepath = f"{REQUIREMENTS_DIR}/{filename}"
    
    if Path(filepath).exists() and not args.force:
        print(f"错误: {filepath} 已存在，使用 --force 覆盖")
        return
    
    # 获取编号
    number = get_next_req_number()
    
    # 生成内容（使用占位符）
    content = REQUIREMENT_TEMPLATE.format(
        title=title,
        number=number,
        date=today,
        author=author,
        brief_description="[待填写：一句话描述该功能的核心目的]",
        keywords="[待填写：功能相关的关键术语]",
        background="[待填写：为什么需要这个功能？解决什么问题？]",
        goal1="[待填写：具体可衡量的目标]",
        goal2="[待填写：具体可衡量的目标]",
        non_goals="[待填写：明确声明此功能不做什么]",
        role="[角色]",
        want="[功能]",
        value="[价值]",
        feature_name="[功能名]",
        feature_description="[详细描述]",
        business_rule="[业务规则描述]",
        performance="[具体指标]",
        throughput="[具体指标]",
        security="[安全相关要求]",
        compatibility="[兼容性要求]",
        ui_layout="[描述或引用设计稿]",
        interaction_flow="[用户操作的步骤流程]",
        state="[状态名]",
        display="[效果]",
        trigger="[条件]",
        data_tables="[使用 Mermaid ER 图或表格描述]",
        field="[字段]",
        type="[类型]",
        field_description="[说明]",
        acceptance_criteria="[验收条件]",
        test_case="[测试步骤]",
        expected_result="[预期结果]"
    )
    
    write_file(filepath, content)
    print(f"已创建需求文档: {filepath}")
    print(f"文档编号: REQ-{number}")


def main():
    parser = argparse.ArgumentParser(
        description="自动更新文档工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python update_docs.py init
  python update_docs.py changelog --type added --message "新增XX功能"
  python update_docs.py api --type add --endpoint "POST /api/xxx" --description "新增接口"
  python update_docs.py req --name "user-auth" --title "用户认证功能"
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # init 命令
    init_parser = subparsers.add_parser("init", help="初始化文档目录结构")
    init_parser.set_defaults(func=cmd_init)
    
    # changelog 命令
    cl_parser = subparsers.add_parser("changelog", help="更新 CHANGELOG.md")
    cl_parser.add_argument(
        "--type", "-t",
        required=True,
        choices=["added", "changed", "fixed", "removed"],
        help="变更类型"
    )
    cl_parser.add_argument(
        "--message", "-m",
        required=True,
        help="变更描述"
    )
    cl_parser.set_defaults(func=cmd_changelog)
    
    # api 命令
    api_parser = subparsers.add_parser("api", help="更新 API CHANGELOG")
    api_parser.add_argument(
        "--type", "-t",
        required=True,
        choices=["add", "change", "deprecate", "remove"],
        help="变更类型"
    )
    api_parser.add_argument(
        "--endpoint", "-e",
        required=True,
        help="API 端点 (如 'POST /api/users')"
    )
    api_parser.add_argument(
        "--description", "-d",
        required=True,
        help="接口描述"
    )
    api_parser.set_defaults(func=cmd_api)
    
    # req 命令
    req_parser = subparsers.add_parser("req", help="创建需求文档")
    req_parser.add_argument(
        "--name", "-n",
        required=True,
        help="功能名称（用于文件名，如 'user-auth'）"
    )
    req_parser.add_argument(
        "--title", "-t",
        help="文档标题（如 '用户认证功能'）"
    )
    req_parser.add_argument(
        "--author", "-a",
        help="作者"
    )
    req_parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="强制覆盖已存在的文件"
    )
    req_parser.set_defaults(func=cmd_req)
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return
    
    args.func(args)


if __name__ == "__main__":
    main()
