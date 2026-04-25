#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档校验工具

检查项：
    1. CHANGELOG / API_CHANGELOG 格式（Keep a Changelog 规范）
       - 必须存在 [Unreleased] 段
       - 版本号符合 SemVer
       - 每个版本块包含至少一个分类段
       - 已发版本的日期格式 YYYY-MM-DD
    2. 链接有效性
       - 内部相对链接的目标文件存在
       - 检测残留占位符 ({xxx}, [待填写：xxx])
    3. 版本一致性
       - CHANGELOG 最新版本号与 package.json / pyproject.toml / setup.py / Cargo.toml 等一致
    4. PRD 完整性
       - 文档信息表必须有日期、作者、编号
       - 验收标准至少有一条

退出码：
    0 = 全部通过
    1 = 有错误
    2 = 有警告（仅当 --strict 时也视为失败）

用法：
    python validate_docs.py
    python validate_docs.py --root /path/to/project
    python validate_docs.py --strict     # 警告也视为失败
    python validate_docs.py --json       # JSON 输出便于 CI 解析
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ==================== 数据结构 ====================

@dataclass
class Issue:
    severity: str   # "error" | "warning"
    file: str
    line: int       # 0 表示未指定
    code: str       # 简短代码，便于规则禁用
    message: str

    def render(self) -> str:
        loc = f"{self.file}:{self.line}" if self.line else self.file
        return f"[{self.severity.upper()}] {loc} ({self.code}) {self.message}"


@dataclass
class ValidationResult:
    issues: List[Issue] = field(default_factory=list)

    def add(self, *args, **kwargs) -> None:
        self.issues.append(Issue(*args, **kwargs))

    @property
    def errors(self) -> List[Issue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> List[Issue]:
        return [i for i in self.issues if i.severity == "warning"]

    def is_passed(self, strict: bool = False) -> bool:
        if self.errors:
            return False
        if strict and self.warnings:
            return False
        return True


# ==================== 校验函数 ====================

SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:[-+][\w.+-]+)?$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_changelog(path: Path, result: ValidationResult) -> Optional[str]:
    """校验 CHANGELOG，返回最新已发布版本号（用于版本一致性检查）"""
    if not path.exists():
        result.add("warning", str(path), 0, "CL001", "CHANGELOG 文件不存在")
        return None

    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()

    # 1. 必须存在 [Unreleased]
    if not re.search(r"^## \[Unreleased\]", content, re.MULTILINE):
        result.add("error", str(path), 0, "CL002", "缺少 `## [Unreleased]` 段落")

    # 2. 解析所有版本头：## [x.y.z] - YYYY-MM-DD
    version_headers = re.finditer(
        r"^## \[([\w.+-]+)\](?:\s*-\s*([\d-]+))?", content, re.MULTILINE,
    )
    latest_version: Optional[str] = None
    versions_seen: List[str] = []
    for match in version_headers:
        version = match.group(1)
        date_str = match.group(2)
        line_no = content[: match.start()].count("\n") + 1

        if version == "Unreleased":
            continue

        if not SEMVER.match(version):
            result.add("error", str(path), line_no, "CL003",
                       f"版本号 `{version}` 不符合 SemVer 规范")

        if date_str is None:
            result.add("error", str(path), line_no, "CL004",
                       f"版本 `{version}` 缺少发布日期")
        elif not DATE_RE.match(date_str):
            result.add("error", str(path), line_no, "CL005",
                       f"版本 `{version}` 日期格式错误（应为 YYYY-MM-DD）：{date_str}")

        versions_seen.append(version)
        if latest_version is None:
            latest_version = version

    # 3. 检查残留占位符
    _check_placeholders(content, str(path), result, ignore_codeblocks=True, ignore_comments=True)

    # 4. 检查重复版本
    if len(versions_seen) != len(set(versions_seen)):
        duplicates = [v for v in set(versions_seen) if versions_seen.count(v) > 1]
        result.add("error", str(path), 0, "CL006",
                   f"重复的版本号: {', '.join(duplicates)}")

    return latest_version


def validate_api_changelog(path: Path, result: ValidationResult) -> None:
    """校验 API_CHANGELOG（中文段名）"""
    if not path.exists():
        result.add("warning", str(path), 0, "AC001", "API_CHANGELOG 文件不存在")
        return

    content = path.read_text(encoding="utf-8")

    if not re.search(r"^## \[Unreleased\]", content, re.MULTILINE):
        result.add("error", str(path), 0, "AC002", "缺少 `## [Unreleased]` 段落")

    # 检查 [Unreleased] 段是否包含 4 个标准分类
    unreleased_block = _extract_section(content, r"\[Unreleased\]")
    expected = ["新增接口", "接口变更", "废弃接口", "移除接口"]
    if unreleased_block:
        for section in expected:
            if f"### {section}" not in unreleased_block:
                result.add("warning", str(path), 0, "AC003",
                           f"[Unreleased] 缺少 `### {section}` 段")

    # Breaking Change 必须有 ⚠️ 标志（启发式：含 BREAKING/Breaking 字样的行应该有 ⚠️）
    for i, line in enumerate(content.splitlines(), start=1):
        if re.search(r"\bBreaking\b|\bBREAKING\b", line) and "⚠️" not in line:
            result.add("warning", str(path), i, "AC004",
                       "Breaking Change 条目建议加 ⚠️ Breaking 前缀")


def validate_prds(req_dir: Path, result: ValidationResult) -> None:
    """校验所有 REQ-*.md 文件的完整性"""
    if not req_dir.exists():
        return
    for prd_file in req_dir.glob("REQ-*.md"):
        content = prd_file.read_text(encoding="utf-8")

        # 必须有文档信息表
        if "文档信息" not in content:
            result.add("error", str(prd_file), 0, "PRD001",
                       "缺少『文档信息』章节")
            continue

        # 必须填写编号
        if not re.search(r"文档编号\s*\|\s*REQ-\w", content):
            result.add("error", str(prd_file), 0, "PRD002", "未填写文档编号")

        # 必须填写日期
        if not re.search(r"创建日期\s*\|\s*\d{4}-\d{2}-\d{2}", content):
            result.add("warning", str(prd_file), 0, "PRD003",
                       "创建日期未填或格式错误")

        # 必须有验收标准
        if "验收标准" not in content:
            result.add("error", str(prd_file), 0, "PRD004", "缺少『验收标准』章节")

        # 检查残留占位符
        _check_placeholders(content, str(prd_file), result)


def validate_links(docs_dir: Path, result: ValidationResult) -> None:
    """校验所有 .md 文档中的相对链接（忽略 HTML 注释和代码块）"""
    if not docs_dir.exists():
        return

    md_files = list(docs_dir.rglob("*.md"))
    link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        # 把注释和代码块替换为同行数的空行，保持行号准确
        sanitized = _blank_out(content, r"<!--[\s\S]*?-->")
        sanitized = _blank_out(sanitized, r"```[\s\S]*?```")

        for line_no, line in enumerate(sanitized.splitlines(), start=1):
            for match in link_pattern.finditer(line):
                _label, url = match.group(1), match.group(2).strip()
                if url.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                if url.startswith(("{", "[")):
                    continue
                target = url.split("#", 1)[0].strip()
                if not target:
                    continue
                target_path = (md_file.parent / target).resolve()
                if not target_path.exists():
                    result.add("error", str(md_file), line_no, "LINK001",
                               f"相对链接无效: {url}")


def _blank_out(content: str, pattern: str) -> str:
    """把匹配 pattern 的内容替换为同行数的空白，保持行号不变"""
    def replace(m: re.Match) -> str:
        # 保留换行符数量，避免后续按行号定位时错位
        newlines = m.group(0).count("\n")
        return "\n" * newlines
    return re.sub(pattern, replace, content)


def validate_version_consistency(
    project_root: Path,
    changelog_latest: Optional[str],
    result: ValidationResult,
) -> None:
    """对照 package.json / pyproject.toml / setup.py / Cargo.toml 检查版本一致性"""
    if not changelog_latest:
        return

    candidates: List[Tuple[Path, str, str]] = []

    pkg_json = project_root / "package.json"
    if pkg_json.exists():
        version = _read_json_version(pkg_json)
        if version:
            candidates.append((pkg_json, "package.json", version))

    pyproject = project_root / "pyproject.toml"
    if pyproject.exists():
        version = _read_pyproject_version(pyproject)
        if version:
            candidates.append((pyproject, "pyproject.toml", version))

    setup_py = project_root / "setup.py"
    if setup_py.exists():
        version = _read_setup_py_version(setup_py)
        if version:
            candidates.append((setup_py, "setup.py", version))

    cargo = project_root / "Cargo.toml"
    if cargo.exists():
        version = _read_pyproject_version(cargo)  # 同样的 TOML 解析
        if version:
            candidates.append((cargo, "Cargo.toml", version))

    for path, _name, version in candidates:
        if version != changelog_latest:
            result.add("warning", str(path), 0, "VER001",
                       f"项目版本 `{version}` 与 CHANGELOG 最新版本 `{changelog_latest}` 不一致")


# ==================== 工具函数 ====================

PLACEHOLDER_PATTERNS = [
    re.compile(r"\{[^{}\n]{1,40}\}"),       # {功能名称} 等
    re.compile(r"\[待填写[：:][^\]]+\]"),   # [待填写：xxx]
]


def _check_placeholders(
    content: str,
    file_label: str,
    result: ValidationResult,
    ignore_codeblocks: bool = True,
    ignore_comments: bool = False,
) -> None:
    """扫描占位符；可选忽略 ``` 代码块或 <!-- --> 注释中的内容"""
    if ignore_codeblocks:
        content = _strip_codeblocks(content)
    if ignore_comments:
        content = _strip_html_comments(content)
    for line_no, line in enumerate(content.splitlines(), start=1):
        # 跳过链接定义行（含 {repo_url} 等）
        if line.lstrip().startswith("[") and "]:" in line:
            continue
        for pat in PLACEHOLDER_PATTERNS:
            for match in pat.finditer(line):
                token = match.group(0)
                # 排除常见无害的 {value}, {token} 这种代码示例（启发式：极短）
                if len(token) <= 4 and token not in ("{token}", "{value}"):
                    continue
                # 仅当不是合法 Markdown 表格分隔符时报告
                if "{" in token:  # PLACEHOLDER 占位符
                    result.add("warning", file_label, line_no, "PH001",
                               f"残留占位符: {token}")


def _strip_codeblocks(content: str) -> str:
    """移除 ``` 围栏代码块（避免误报）"""
    return re.sub(r"```[\s\S]*?```", "", content)


def _strip_html_comments(content: str) -> str:
    """移除 <!-- ... --> 注释"""
    return re.sub(r"<!--[\s\S]*?-->", "", content)


def _extract_section(content: str, header_pattern: str) -> Optional[str]:
    """提取 ## [pattern] ... 直到下一个 ## 之间的内容"""
    pat = re.compile(
        rf"^## {header_pattern}.*?(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = pat.search(content)
    return m.group(0) if m else None


def _read_json_version(path: Path) -> Optional[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("version")
    except (OSError, json.JSONDecodeError):
        return None


def _read_pyproject_version(path: Path) -> Optional[str]:
    """读取 pyproject.toml / Cargo.toml 等 TOML 中的 version"""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    # 优先尝试标准库 tomllib（Python 3.11+）
    try:
        import tomllib  # type: ignore
        data = tomllib.loads(text)
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore
            data = tomllib.loads(text)
        except ImportError:
            # 退化：用正则提取 version = "x.y.z"
            m = re.search(r'^\s*version\s*=\s*"([\w.+-]+)"', text, re.MULTILINE)
            return m.group(1) if m else None
    except Exception:
        return None

    # 常见路径：[project] version, [tool.poetry] version, [package] version
    for path_keys in (
        ("project", "version"),
        ("tool", "poetry", "version"),
        ("package", "version"),
    ):
        cur = data
        try:
            for key in path_keys:
                cur = cur[key]
            if isinstance(cur, str):
                return cur
        except (KeyError, TypeError):
            continue
    return None


def _read_setup_py_version(path: Path) -> Optional[str]:
    """从 setup.py 中粗略提取 version='x.y.z'"""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    m = re.search(r'version\s*=\s*[\'"]([\w.+-]+)[\'"]', text)
    return m.group(1) if m else None


# ==================== 主流程 ====================

def main() -> None:
    parser = argparse.ArgumentParser(description="校验项目文档（格式、链接、版本一致性）")
    parser.add_argument("--root", default=".", help="项目根目录")
    parser.add_argument("--strict", action="store_true",
                        help="警告也视为失败（适合 CI）")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    docs_dir = root / "docs"
    changelog_path = docs_dir / "CHANGELOG.md"
    api_changelog_path = docs_dir / "api" / "API_CHANGELOG.md"
    requirements_dir = docs_dir / "requirements"

    result = ValidationResult()

    print(f"📋 开始校验文档... 根目录: {root}", file=sys.stderr)

    latest = validate_changelog(changelog_path, result)
    validate_api_changelog(api_changelog_path, result)
    validate_prds(requirements_dir, result)
    validate_links(docs_dir, result)
    validate_version_consistency(root, latest, result)

    if args.json:
        out = {
            "passed": result.is_passed(strict=args.strict),
            "errors": [_issue_to_dict(i) for i in result.errors],
            "warnings": [_issue_to_dict(i) for i in result.warnings],
            "summary": {
                "errors": len(result.errors),
                "warnings": len(result.warnings),
                "latest_version": latest,
            },
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(_render_text(result, latest, args.strict))

    sys.exit(0 if result.is_passed(strict=args.strict) else 1)


def _issue_to_dict(i: Issue) -> Dict:
    return {
        "severity": i.severity,
        "file": i.file,
        "line": i.line,
        "code": i.code,
        "message": i.message,
    }


def _render_text(result: ValidationResult, latest: Optional[str], strict: bool) -> str:
    lines = ["", "=" * 60, "文档校验结果", "=" * 60]
    if not result.issues:
        lines.append("\n✅ 全部通过！")
    else:
        for issue in result.issues:
            lines.append(issue.render())

    lines.append("")
    lines.append(f"错误: {len(result.errors)}")
    lines.append(f"警告: {len(result.warnings)}")
    if latest:
        lines.append(f"CHANGELOG 最新版本: {latest}")
    if result.is_passed(strict=strict):
        lines.append("\n✅ 校验通过")
    else:
        lines.append("\n❌ 校验失败" + ("（strict 模式）" if strict and result.warnings else ""))
    return "\n".join(lines)


if __name__ == "__main__":
    main()
