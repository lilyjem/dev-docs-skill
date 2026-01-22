#!/usr/bin/env python3
"""
分析 Git 变更并生成文档更新建议

使用方法:
    python analyze_changes.py [--since <commit>] [--output <file>]
    
参数:
    --since: 从指定 commit 开始分析（默认为最近一次提交）
    --output: 输出文件路径（默认输出到控制台）
    
输出:
    - 变更文件列表
    - API 变更检测
    - 建议更新的文档
    - CHANGELOG 条目建议
"""

import subprocess
import re
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set, Tuple, Optional


# ==================== 配置区域 ====================

# API 文件路径模式（用于检测 API 变更）
API_FILE_PATTERNS = [
    r".*api.*\.py$",
    r".*routes?.*\.py$",
    r".*endpoints?.*\.py$",
    r".*controllers?.*\.py$",
    r".*views?.*\.py$",
]

# 需求相关文件路径模式
FEATURE_FILE_PATTERNS = [
    r".*\.vue$",
    r".*\.tsx?$",
    r".*\.jsx?$",
    r".*models?.*\.py$",
    r".*services?.*\.py$",
    r".*core.*\.py$",
]

# API 方法装饰器模式（FastAPI）
API_DECORATOR_PATTERNS = [
    r"@(app|router)\.(get|post|put|delete|patch|options|head)\s*\(",
    r"@api_router\.(get|post|put|delete|patch|options|head)\s*\(",
]

# 文档目录结构
DOCS_DIR = "docs"
API_DOCS_DIR = "docs/api"
REQUIREMENTS_DIR = "docs/requirements"


# ==================== 工具函数 ====================

def run_git_command(args: List[str]) -> str:
    """执行 Git 命令并返回输出"""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Git 命令执行失败: {e.stderr}")
        return ""


def get_changed_files(since: Optional[str] = None) -> List[Dict]:
    """
    获取变更的文件列表
    
    Args:
        since: 起始 commit，如果为 None 则比较工作区与 HEAD
        
    Returns:
        变更文件列表，每个元素包含 status 和 file 字段
    """
    if since:
        # 比较指定 commit 到 HEAD 的变更
        output = run_git_command(["diff", "--name-status", since, "HEAD"])
    else:
        # 获取暂存区和工作区的变更
        staged = run_git_command(["diff", "--name-status", "--cached"])
        unstaged = run_git_command(["diff", "--name-status"])
        output = staged + "\n" + unstaged
    
    changes = []
    for line in output.strip().split("\n"):
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            status = parts[0][0]  # 取第一个字符 (A/M/D/R)
            file_path = parts[-1]  # 重命名时取新文件名
            changes.append({
                "status": status,
                "file": file_path,
                "status_name": {
                    "A": "Added",
                    "M": "Modified", 
                    "D": "Deleted",
                    "R": "Renamed"
                }.get(status, "Changed")
            })
    
    # 去重
    seen = set()
    unique_changes = []
    for change in changes:
        if change["file"] not in seen:
            seen.add(change["file"])
            unique_changes.append(change)
    
    return unique_changes


def match_patterns(file_path: str, patterns: List[str]) -> bool:
    """检查文件路径是否匹配任一模式"""
    for pattern in patterns:
        if re.match(pattern, file_path, re.IGNORECASE):
            return True
    return False


def analyze_api_changes(changed_files: List[Dict]) -> List[Dict]:
    """
    分析 API 变更
    
    Args:
        changed_files: 变更文件列表
        
    Returns:
        API 变更详情列表
    """
    api_changes = []
    
    for change in changed_files:
        file_path = change["file"]
        
        # 检查是否是 API 相关文件
        if not match_patterns(file_path, API_FILE_PATTERNS):
            continue
            
        # 获取文件内容（如果文件存在）
        if change["status"] == "D":
            # 删除的文件，获取上一个版本的内容
            content = run_git_command(["show", f"HEAD~1:{file_path}"])
        else:
            # 新增或修改的文件，读取当前内容
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except FileNotFoundError:
                continue
        
        # 提取 API 端点
        endpoints = extract_api_endpoints(content)
        
        if endpoints:
            api_changes.append({
                "file": file_path,
                "status": change["status_name"],
                "endpoints": endpoints
            })
    
    return api_changes


def extract_api_endpoints(content: str) -> List[Dict]:
    """
    从代码中提取 API 端点信息
    
    Args:
        content: 文件内容
        
    Returns:
        API 端点列表
    """
    endpoints = []
    lines = content.split("\n")
    
    for i, line in enumerate(lines):
        for pattern in API_DECORATOR_PATTERNS:
            match = re.search(pattern, line)
            if match:
                method = match.group(2).upper()
                
                # 尝试提取路径
                path_match = re.search(r'["\']([^"\']+)["\']', line)
                path = path_match.group(1) if path_match else "未知路径"
                
                # 尝试提取函数名作为描述
                for j in range(i + 1, min(i + 5, len(lines))):
                    func_match = re.match(r"^(?:async\s+)?def\s+(\w+)", lines[j])
                    if func_match:
                        func_name = func_match.group(1)
                        endpoints.append({
                            "method": method,
                            "path": path,
                            "function": func_name
                        })
                        break
    
    return endpoints


def categorize_changes(changed_files: List[Dict]) -> Dict[str, List[str]]:
    """
    将变更分类
    
    Args:
        changed_files: 变更文件列表
        
    Returns:
        分类后的变更，按 Added/Changed/Fixed/Removed 分组
    """
    categories = {
        "Added": [],
        "Changed": [],
        "Fixed": [],
        "Removed": []
    }
    
    for change in changed_files:
        status = change["status"]
        file_path = change["file"]
        
        if status == "A":
            categories["Added"].append(file_path)
        elif status == "D":
            categories["Removed"].append(file_path)
        else:
            # M, R 等都归为 Changed
            # 如果文件名包含 fix/bug 关键字，归为 Fixed
            if any(kw in file_path.lower() for kw in ["fix", "bug", "patch"]):
                categories["Fixed"].append(file_path)
            else:
                categories["Changed"].append(file_path)
    
    return categories


def generate_changelog_suggestions(
    categories: Dict[str, List[str]],
    api_changes: List[Dict]
) -> str:
    """
    生成 CHANGELOG 建议
    
    Args:
        categories: 分类后的变更
        api_changes: API 变更
        
    Returns:
        CHANGELOG 条目建议文本
    """
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"## [Unreleased] - {today}",
        ""
    ]
    
    if categories["Added"]:
        lines.append("### Added")
        for file in categories["Added"]:
            lines.append(f"- {describe_file_change(file, 'added')}")
        lines.append("")
    
    if categories["Changed"]:
        lines.append("### Changed")
        for file in categories["Changed"]:
            lines.append(f"- {describe_file_change(file, 'changed')}")
        lines.append("")
    
    if categories["Fixed"]:
        lines.append("### Fixed")
        for file in categories["Fixed"]:
            lines.append(f"- {describe_file_change(file, 'fixed')}")
        lines.append("")
    
    if categories["Removed"]:
        lines.append("### Removed")
        for file in categories["Removed"]:
            lines.append(f"- {describe_file_change(file, 'removed')}")
        lines.append("")
    
    return "\n".join(lines)


def generate_api_changelog_suggestions(api_changes: List[Dict]) -> str:
    """
    生成 API CHANGELOG 建议
    
    Args:
        api_changes: API 变更
        
    Returns:
        API CHANGELOG 条目建议文本
    """
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"## [Unreleased] - {today}",
        ""
    ]
    
    added = []
    changed = []
    removed = []
    
    for change in api_changes:
        status = change["status"]
        for endpoint in change["endpoints"]:
            entry = f"`{endpoint['method']} {endpoint['path']}` - {endpoint['function']}"
            
            if status == "Added":
                added.append(entry)
            elif status == "Deleted":
                removed.append(entry)
            else:
                changed.append(entry)
    
    if added:
        lines.append("### 新增接口")
        for entry in added:
            lines.append(f"- {entry}")
        lines.append("")
    
    if changed:
        lines.append("### 接口变更")
        for entry in changed:
            lines.append(f"- {entry}")
        lines.append("")
    
    if removed:
        lines.append("### 移除接口")
        for entry in removed:
            lines.append(f"- {entry}")
        lines.append("")
    
    return "\n".join(lines)


def describe_file_change(file_path: str, change_type: str) -> str:
    """
    根据文件路径生成变更描述
    
    Args:
        file_path: 文件路径
        change_type: 变更类型 (added/changed/fixed/removed)
        
    Returns:
        变更描述
    """
    # 从文件路径提取有意义的描述
    path = Path(file_path)
    name = path.stem
    
    # 根据目录和文件名推断功能
    if "api" in str(path).lower():
        module = "API接口"
    elif "component" in str(path).lower():
        module = "组件"
    elif "view" in str(path).lower():
        module = "页面"
    elif "service" in str(path).lower():
        module = "服务"
    elif "model" in str(path).lower():
        module = "数据模型"
    elif "test" in str(path).lower():
        module = "测试"
    else:
        module = "模块"
    
    # 生成描述
    verbs = {
        "added": "新增",
        "changed": "更新",
        "fixed": "修复",
        "removed": "移除"
    }
    verb = verbs.get(change_type, "修改")
    
    return f"{verb} {name} {module} (`{file_path}`)"


def get_update_suggestions(
    changed_files: List[Dict],
    api_changes: List[Dict]
) -> List[str]:
    """
    生成需要更新的文档建议
    
    Args:
        changed_files: 变更文件列表
        api_changes: API 变更
        
    Returns:
        需要更新的文档列表
    """
    suggestions = []
    
    # 总是建议更新 CHANGELOG
    if changed_files:
        suggestions.append(f"{DOCS_DIR}/CHANGELOG.md")
    
    # 如果有 API 变更，建议更新 API 文档
    if api_changes:
        suggestions.append(f"{API_DOCS_DIR}/API.md")
        suggestions.append(f"{API_DOCS_DIR}/API_CHANGELOG.md")
    
    # 检查是否需要创建/更新需求文档
    feature_files = [
        f for f in changed_files 
        if match_patterns(f["file"], FEATURE_FILE_PATTERNS)
    ]
    if feature_files:
        suggestions.append(f"{REQUIREMENTS_DIR}/REQ-<feature_name>.md (建议创建或更新)")
    
    return suggestions


def main():
    parser = argparse.ArgumentParser(description="分析 Git 变更并生成文档更新建议")
    parser.add_argument(
        "--since", 
        help="从指定 commit 开始分析",
        default=None
    )
    parser.add_argument(
        "--output",
        help="输出文件路径",
        default=None
    )
    parser.add_argument(
        "--json",
        help="以 JSON 格式输出",
        action="store_true"
    )
    
    args = parser.parse_args()
    
    # 分析变更
    print("正在分析 Git 变更...")
    changed_files = get_changed_files(args.since)
    
    if not changed_files:
        print("没有检测到文件变更")
        return
    
    # 分析 API 变更
    api_changes = analyze_api_changes(changed_files)
    
    # 分类变更
    categories = categorize_changes(changed_files)
    
    # 生成建议
    changelog_suggestion = generate_changelog_suggestions(categories, api_changes)
    api_changelog_suggestion = generate_api_changelog_suggestions(api_changes)
    update_suggestions = get_update_suggestions(changed_files, api_changes)
    
    # 输出结果
    if args.json:
        result = {
            "changed_files": changed_files,
            "api_changes": api_changes,
            "categories": categories,
            "suggestions": {
                "changelog": changelog_suggestion,
                "api_changelog": api_changelog_suggestion,
                "documents_to_update": update_suggestions
            }
        }
        output = json.dumps(result, ensure_ascii=False, indent=2)
    else:
        output_lines = [
            "=" * 60,
            "Git 变更分析报告",
            "=" * 60,
            "",
            "## 变更文件列表",
            ""
        ]
        
        for change in changed_files:
            output_lines.append(f"  [{change['status_name']:8}] {change['file']}")
        
        output_lines.extend([
            "",
            "## API 变更检测",
            ""
        ])
        
        if api_changes:
            for change in api_changes:
                output_lines.append(f"  文件: {change['file']} ({change['status']})")
                for endpoint in change["endpoints"]:
                    output_lines.append(
                        f"    - {endpoint['method']} {endpoint['path']} "
                        f"-> {endpoint['function']}()"
                    )
        else:
            output_lines.append("  未检测到 API 变更")
        
        output_lines.extend([
            "",
            "## 建议更新的文档",
            ""
        ])
        
        for doc in update_suggestions:
            output_lines.append(f"  - {doc}")
        
        output_lines.extend([
            "",
            "## CHANGELOG 建议条目",
            "",
            changelog_suggestion,
        ])
        
        if api_changes:
            output_lines.extend([
                "",
                "## API CHANGELOG 建议条目",
                "",
                api_changelog_suggestion,
            ])
        
        output = "\n".join(output_lines)
    
    # 输出
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"分析结果已保存到: {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
