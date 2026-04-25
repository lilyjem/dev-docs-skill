#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析 Git 变更并生成文档更新建议（多语言版）

支持识别的框架/语言：
    - Python：FastAPI、Flask、Django
    - Node.js / TypeScript：Express / Koa / NestJS
    - Java：Spring Boot
    - Go：Gin、Echo、net/http
    - 通用：OpenAPI 3.x（YAML/JSON）

用法:
    python analyze_changes.py                          # 分析当前未提交变更
    python analyze_changes.py --since HEAD~5           # 分析最近 5 次提交
    python analyze_changes.py --since v1.0.0           # 分析自某 tag 以来的变更
    python analyze_changes.py --json                   # JSON 格式输出
    python analyze_changes.py --output report.txt      # 写入文件

输出内容:
    - 变更文件清单（含分类）
    - 多语言 API 端点变更检测
    - CHANGELOG 候选条目（按 Conventional Commits 启发式分类）
    - API CHANGELOG 候选条目
    - 建议更新的文档列表
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# 引入多语言模式库
sys.path.insert(0, str(Path(__file__).parent))
from api_patterns import (  # noqa: E402
    Endpoint,
    extract_endpoints_from_content,
    parse_openapi_file,
    file_matches,
)


# ==================== 配置 ====================

# 文档目录约定
DOCS_DIR = "docs"
API_DOCS_DIR = "docs/api"
REQUIREMENTS_DIR = "docs/requirements"

# 视为「功能性代码」的文件 glob（用于建议是否需要新建 PRD）
FEATURE_GLOBS: Tuple[str, ...] = (
    "**/*.py", "**/*.js", "**/*.ts", "**/*.tsx", "**/*.jsx",
    "**/*.vue", "**/*.svelte",
    "**/*.java", "**/*.kt",
    "**/*.go", "**/*.rs",
)

# 视为「文档/配置」类文件，不计入 PRD 触发
SKIP_GLOBS: Tuple[str, ...] = (
    "**/*.md", "**/*.txt",
    "**/test_*.py", "**/*_test.py", "**/*.test.js", "**/*.test.ts",
    "**/__tests__/**",
    "docs/**", ".github/**",
)


# ==================== 数据结构 ====================

@dataclass
class FileChange:
    """单个文件的变更记录"""
    status: str  # "A" / "M" / "D" / "R" 单字符
    file: str

    @property
    def status_name(self) -> str:
        return {
            "A": "Added",
            "M": "Modified",
            "D": "Deleted",
            "R": "Renamed",
        }.get(self.status, "Changed")


@dataclass
class ApiChangeReport:
    """API 变更对比报告"""
    added: List[Endpoint] = field(default_factory=list)
    removed: List[Endpoint] = field(default_factory=list)
    modified: List[Endpoint] = field(default_factory=list)  # 同 signature 但 file/line 不同

    def is_empty(self) -> bool:
        return not (self.added or self.removed or self.modified)


# ==================== Git 辅助 ====================

def run_git(args: List[str], cwd: Optional[str] = None) -> str:
    """执行 git 命令，失败时返回空串"""
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            check=True,
            cwd=cwd,
        )
        return result.stdout
    except subprocess.CalledProcessError as exc:
        # 不是致命错误时静默；致命错误会在主流程报错
        if "not a git repository" in (exc.stderr or "").lower():
            print("[错误] 当前目录不是 Git 仓库", file=sys.stderr)
            sys.exit(2)
        return ""


def get_changed_files(since: Optional[str]) -> List[FileChange]:
    """获取变更文件列表。"""
    raw_lines: List[str] = []
    if since:
        out = run_git(["diff", "--name-status", since, "HEAD"])
        raw_lines.extend(out.splitlines())
    else:
        raw_lines.extend(run_git(["diff", "--name-status", "--cached"]).splitlines())
        raw_lines.extend(run_git(["diff", "--name-status"]).splitlines())
        # 也包括未跟踪文件（用 ls-files）
        untracked = run_git(["ls-files", "--others", "--exclude-standard"]).splitlines()
        for f in untracked:
            if f.strip():
                raw_lines.append(f"A\t{f.strip()}")

    seen: Set[str] = set()
    changes: List[FileChange] = []
    for line in raw_lines:
        line = line.rstrip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status = parts[0][0].upper()
        file_path = parts[-1]  # 重命名时取新名
        if file_path in seen:
            continue
        seen.add(file_path)
        changes.append(FileChange(status=status, file=file_path))
    return changes


def get_file_content_at(ref: str, file: str) -> str:
    """获取某 ref 下文件的内容；失败返回空串"""
    try:
        result = subprocess.run(
            ["git", "show", f"{ref}:{file}"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return ""


def get_current_content(file: str) -> str:
    """读取工作区当前文件内容（不存在返回空串）"""
    try:
        return Path(file).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def get_commit_messages(since: Optional[str]) -> List[str]:
    """获取 commit messages，便于按 Conventional Commits 启发式分类"""
    if since:
        out = run_git(["log", "--pretty=%s", f"{since}..HEAD"])
    else:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


# ==================== 文件过滤 ====================

def is_skipped(file_path: str) -> bool:
    """是否为应跳过的文件（文档/测试等）"""
    return file_matches(file_path, SKIP_GLOBS)


def is_feature_code(file_path: str) -> bool:
    """是否为功能性代码（用于触发 PRD 建议）"""
    if is_skipped(file_path):
        return False
    return file_matches(file_path, FEATURE_GLOBS)


# ==================== API 变更比对 ====================

def collect_endpoints(file: str, content: str) -> List[Endpoint]:
    """对单个文件提取所有端点"""
    if not content:
        return []
    return extract_endpoints_from_content(content, file)


def diff_endpoints(
    before: List[Endpoint],
    after: List[Endpoint],
) -> ApiChangeReport:
    """比对两个端点列表，识别新增/移除/修改"""
    before_keys = {(e.method, e.path): e for e in before}
    after_keys = {(e.method, e.path): e for e in after}

    added = [e for k, e in after_keys.items() if k not in before_keys]
    removed = [e for k, e in before_keys.items() if k not in after_keys]
    # 修改：键存在于双方，但 function/line 变化（粗略判定）
    modified: List[Endpoint] = []
    for k, after_e in after_keys.items():
        before_e = before_keys.get(k)
        if before_e and (before_e.function != after_e.function):
            modified.append(after_e)

    return ApiChangeReport(added=added, removed=removed, modified=modified)


def analyze_api_changes(
    changed_files: List[FileChange],
    since: Optional[str],
) -> ApiChangeReport:
    """跨所有变更文件汇总 API 变更"""
    overall = ApiChangeReport()
    base_ref = since or "HEAD"

    for change in changed_files:
        if is_skipped(change.file):
            continue

        # 获取「之前」与「之后」内容
        if change.status == "A":
            before_content = ""
            after_content = get_current_content(change.file)
        elif change.status == "D":
            before_content = get_file_content_at(base_ref, change.file)
            after_content = ""
        else:
            before_content = get_file_content_at(base_ref, change.file)
            after_content = get_current_content(change.file)

        before_eps = collect_endpoints(change.file, before_content)
        after_eps = collect_endpoints(change.file, after_content)
        report = diff_endpoints(before_eps, after_eps)

        overall.added.extend(report.added)
        overall.removed.extend(report.removed)
        overall.modified.extend(report.modified)

    # 单独扫描 OpenAPI 文件
    for change in changed_files:
        path = Path(change.file)
        if path.name in {"openapi.yaml", "openapi.yml", "openapi.json", "swagger.yaml", "swagger.json"}:
            current = parse_openapi_file(change.file) if change.status != "D" else []
            previous = []
            if change.status != "A":
                # 把 git show 的内容写入临时文件再解析
                prev_text = get_file_content_at(base_ref, change.file)
                if prev_text:
                    tmp = Path(".dev-docs-tmp-openapi" + path.suffix)
                    try:
                        tmp.write_text(prev_text, encoding="utf-8")
                        previous = parse_openapi_file(str(tmp))
                    finally:
                        if tmp.exists():
                            tmp.unlink()
            report = diff_endpoints(previous, current)
            overall.added.extend(report.added)
            overall.removed.extend(report.removed)
            overall.modified.extend(report.modified)

    return overall


# ==================== 启发式分类（Conventional Commits） ====================

# 前缀 → CHANGELOG 段名
CC_PREFIX_MAP: Dict[str, str] = {
    "feat": "Added",
    "feature": "Added",
    "add": "Added",
    "fix": "Fixed",
    "bugfix": "Fixed",
    "perf": "Changed",
    "refactor": "Changed",
    "change": "Changed",
    "update": "Changed",
    "remove": "Removed",
    "delete": "Removed",
    "deprecate": "Deprecated",
    "security": "Security",
    "sec": "Security",
}


def classify_commits(messages: List[str]) -> Dict[str, List[str]]:
    """按 Conventional Commits 前缀分类"""
    buckets: Dict[str, List[str]] = {
        "Added": [], "Changed": [], "Fixed": [],
        "Deprecated": [], "Removed": [], "Security": [],
        "Other": [],
    }
    for msg in messages:
        # 解析 type(scope)?: subject
        match = _parse_cc(msg)
        if not match:
            buckets["Other"].append(msg)
            continue
        cc_type, _scope, subject = match
        bucket = CC_PREFIX_MAP.get(cc_type.lower(), "Other")
        buckets[bucket].append(subject)
    return buckets


def _parse_cc(msg: str) -> Optional[Tuple[str, str, str]]:
    """解析 'feat(scope): subject' / 'fix: subject' 等"""
    import re
    m = re.match(r"^(\w+)(?:\(([^)]+)\))?!?:\s*(.+)$", msg)
    if not m:
        return None
    return m.group(1), m.group(2) or "", m.group(3).strip()


# ==================== 报告渲染 ====================

def _categorize_files(changes: List[FileChange]) -> Dict[str, List[str]]:
    """把文件按 git 状态分组"""
    buckets: Dict[str, List[str]] = {"Added": [], "Modified": [], "Deleted": [], "Renamed": []}
    for c in changes:
        buckets.setdefault(c.status_name, []).append(c.file)
    return buckets


def render_changelog_section(commit_buckets: Dict[str, List[str]]) -> str:
    """渲染 CHANGELOG 候选段落（基于 commit 信息）"""
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"## [Unreleased] - {today}", ""]
    section_order = ["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"]
    for section in section_order:
        items = commit_buckets.get(section) or []
        if not items:
            continue
        lines.append(f"### {section}")
        for item in items:
            lines.append(f"- {item}")
        lines.append("")
    others = commit_buckets.get("Other") or []
    if others:
        lines.append("### Other (未识别 Conventional Commits 前缀，请手动归类)")
        for item in others:
            lines.append(f"- {item}")
        lines.append("")
    return "\n".join(lines)


def render_api_changelog_section(report: ApiChangeReport) -> str:
    """渲染 API CHANGELOG 候选段落"""
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"## [Unreleased] - {today}", ""]
    if report.added:
        lines.append("### 新增接口")
        for e in report.added:
            lines.append(f"- `{e.signature()}` - {e.function or e.framework}（来源：{e.file}）")
        lines.append("")
    if report.modified:
        lines.append("### 接口变更")
        for e in report.modified:
            lines.append(f"- `{e.signature()}` - 处理函数已变更（来源：{e.file}）")
        lines.append("")
    if report.removed:
        lines.append("### 移除接口")
        for e in report.removed:
            lines.append(f"- `{e.signature()}` - {e.function or e.framework}")
        lines.append("")
    return "\n".join(lines)


def update_suggestions(
    has_feature_changes: bool,
    api_report: ApiChangeReport,
    has_any_change: bool,
) -> List[str]:
    docs: List[str] = []
    if has_any_change:
        docs.append(f"{DOCS_DIR}/CHANGELOG.md")
    if not api_report.is_empty():
        docs.append(f"{API_DOCS_DIR}/API.md")
        docs.append(f"{API_DOCS_DIR}/API_CHANGELOG.md")
    if has_feature_changes:
        docs.append(f"{REQUIREMENTS_DIR}/REQ-<feature>.md（建议新建或更新）")
    return docs


# ==================== 主流程 ====================

def main() -> None:
    parser = argparse.ArgumentParser(description="分析 Git 变更并生成文档更新建议（多语言）")
    parser.add_argument("--since", help="起始 ref（commit/tag/分支），不填则比较工作区与暂存区")
    parser.add_argument("--output", help="将报告写入文件")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    args = parser.parse_args()

    print("正在分析 Git 变更...", file=sys.stderr)
    changes = get_changed_files(args.since)
    if not changes:
        print("没有检测到任何变更")
        return

    api_report = analyze_api_changes(changes, args.since)
    commits = get_commit_messages(args.since)
    commit_buckets = classify_commits(commits) if commits else {}

    has_feature_changes = any(is_feature_code(c.file) for c in changes)
    suggestions = update_suggestions(
        has_feature_changes=has_feature_changes,
        api_report=api_report,
        has_any_change=bool(changes),
    )

    if args.json:
        result = {
            "changed_files": [
                {"status": c.status_name, "file": c.file} for c in changes
            ],
            "api_changes": {
                "added": [_endpoint_to_dict(e) for e in api_report.added],
                "modified": [_endpoint_to_dict(e) for e in api_report.modified],
                "removed": [_endpoint_to_dict(e) for e in api_report.removed],
            },
            "commit_classification": commit_buckets,
            "documents_to_update": suggestions,
            "changelog_section": render_changelog_section(commit_buckets),
            "api_changelog_section": render_api_changelog_section(api_report),
        }
        output = json.dumps(result, ensure_ascii=False, indent=2)
    else:
        output = _render_text_report(
            changes=changes,
            api_report=api_report,
            commit_buckets=commit_buckets,
            suggestions=suggestions,
        )

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"分析报告已写入: {args.output}", file=sys.stderr)
    else:
        print(output)


def _endpoint_to_dict(e: Endpoint) -> Dict:
    return {
        "method": e.method,
        "path": e.path,
        "function": e.function,
        "framework": e.framework,
        "file": e.file,
        "line": e.line,
    }


def _render_text_report(
    changes: List[FileChange],
    api_report: ApiChangeReport,
    commit_buckets: Dict[str, List[str]],
    suggestions: List[str],
) -> str:
    lines = ["=" * 60, "Git 变更分析报告（多语言）", "=" * 60, ""]
    file_buckets = _categorize_files(changes)

    lines.append("## 1. 变更文件")
    for status in ("Added", "Modified", "Renamed", "Deleted"):
        files = file_buckets.get(status) or []
        if not files:
            continue
        lines.append(f"\n### {status} ({len(files)})")
        for f in files:
            lines.append(f"  - {f}")

    lines.append("\n## 2. API 端点变更")
    if api_report.is_empty():
        lines.append("\n  未检测到 API 端点变更")
    else:
        if api_report.added:
            lines.append("\n### 新增 (Added)")
            for e in api_report.added:
                lines.append(f"  + [{e.framework}] {e.signature()} → {e.function or '?'}  ({e.file}:{e.line})")
        if api_report.modified:
            lines.append("\n### 变更 (Modified)")
            for e in api_report.modified:
                lines.append(f"  ~ [{e.framework}] {e.signature()} → {e.function or '?'}  ({e.file}:{e.line})")
        if api_report.removed:
            lines.append("\n### 移除 (Removed)")
            for e in api_report.removed:
                lines.append(f"  - [{e.framework}] {e.signature()} → {e.function or '?'}  ({e.file})")

    lines.append("\n## 3. 建议更新的文档")
    if not suggestions:
        lines.append("\n  无需更新文档")
    else:
        for doc in suggestions:
            lines.append(f"  - {doc}")

    if commit_buckets:
        lines.append("\n## 4. CHANGELOG 候选条目")
        lines.append("")
        lines.append(render_changelog_section(commit_buckets))

    if not api_report.is_empty():
        lines.append("\n## 5. API CHANGELOG 候选条目")
        lines.append("")
        lines.append(render_api_changelog_section(api_report))

    return "\n".join(lines)


if __name__ == "__main__":
    main()
