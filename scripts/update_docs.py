#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
开发文档自动更新工具（多语言版）

用法:
    python update_docs.py <action> [options]

Actions:
    init        初始化文档目录与 CHANGELOG / API_CHANGELOG 骨架
    changelog   往 CHANGELOG.md 追加条目
    api         往 API_CHANGELOG.md 追加条目
    req         按 templates/PRD.md 模板创建需求文档
    release     把 [Unreleased] 段落转换为正式版本

Examples:
    python update_docs.py init
    python update_docs.py changelog -t added -m "支持邮箱登录"
    python update_docs.py api -t add -e "POST /api/login" -d "邮箱密码登录"
    python update_docs.py req -n "user-auth" -t "用户认证" -a "Jem"
    python update_docs.py release --version 1.2.0
    python update_docs.py release --version 1.2.0 --target api    # 处理 API_CHANGELOG
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


# ==================== 路径约定 ====================

DOCS_DIR = "docs"
API_DOCS_DIR = "docs/api"
REQUIREMENTS_DIR = "docs/requirements"

# templates/ 与 update_docs.py 同级（脚本所在目录的 ../templates）
SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = SCRIPT_DIR.parent / "templates"


# ==================== 工具函数 ====================

def ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def read_file(path: str) -> Optional[str]:
    try:
        return Path(path).read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return None


def write_file(path: str, content: str) -> None:
    """写入文件（必要时自动创建父目录）"""
    target = Path(path)
    ensure_dir(str(target.parent))
    target.write_text(content, encoding="utf-8")
    print(f"已写入: {path}")


def load_template(name: str) -> str:
    """从 templates/ 目录加载指定模板。失败时返回 fallback 最小模板。"""
    template_path = TEMPLATES_DIR / name
    content = read_file(str(template_path))
    if content is not None:
        return content
    print(f"[警告] 找不到模板 {template_path}，将使用内置最小模板", file=sys.stderr)
    return _fallback_template(name)


def _fallback_template(name: str) -> str:
    """templates/ 不可用时的最小可用骨架"""
    today = datetime.now().strftime("%Y-%m-%d")
    if name == "CHANGELOG.md":
        return (
            "# Changelog\n\n"
            "本文件记录项目的所有重要变更。\n\n"
            "## [Unreleased]\n\n"
            "### Added\n- 无\n\n### Changed\n- 无\n\n### Fixed\n- 无\n\n### Removed\n- 无\n"
        )
    if name == "API_CHANGELOG.md":
        return (
            "# API Changelog\n\n"
            "## [Unreleased]\n\n"
            "### 新增接口\n- 无\n\n### 接口变更\n- 无\n\n### 废弃接口\n- 无\n\n### 移除接口\n- 无\n"
        )
    return f"# {name}\n\n（模板缺失）\n"


def get_next_req_number() -> str:
    """扫描已有 REQ-*.md，返回下一个 3 位编号"""
    req_dir = Path(REQUIREMENTS_DIR)
    if not req_dir.exists():
        return "001"
    numbers = []
    for f in req_dir.glob("REQ-*.md"):
        content = read_file(str(f)) or ""
        m = re.search(r"文档编号\s*\|\s*REQ-(\d+)", content)
        if m:
            numbers.append(int(m.group(1)))
    nxt = (max(numbers) + 1) if numbers else len(list(req_dir.glob("REQ-*.md"))) + 1
    return f"{nxt:03d}"


# ==================== 命令实现 ====================

def cmd_init(_args) -> None:
    """初始化文档目录"""
    print("正在初始化文档目录...")
    ensure_dir(DOCS_DIR)
    ensure_dir(API_DOCS_DIR)
    ensure_dir(REQUIREMENTS_DIR)

    targets = [
        (f"{DOCS_DIR}/CHANGELOG.md", "CHANGELOG.md"),
        (f"{API_DOCS_DIR}/API_CHANGELOG.md", "API_CHANGELOG.md"),
        (f"{API_DOCS_DIR}/API.md", "API.md"),
    ]
    for dest, template_name in targets:
        if Path(dest).exists():
            print(f"跳过（已存在）: {dest}")
            continue
        content = load_template(template_name)
        write_file(dest, content)

    print("\n✅ 文档目录初始化完成。")
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


def _insert_into_section(
    content: str,
    section_header: str,
    new_entry: str,
) -> Optional[str]:
    """把 new_entry 插入到 `### {section_header}` 标题下的第一个 - 项之前。

    支持「无」占位符替换。返回 None 表示找不到段落。
    """
    # 注意：lookahead 允许 section 后面跟空行 / `---` 分隔符 / 下一个 `##` 或 `###`
    # 这样最后一个 section 后紧跟 `---\n## [1.0.0]` 也能正确闭合
    pattern = re.compile(
        rf"(### {re.escape(section_header)}\s*\n)((?:- .*\n|无\s*\n)*?)(?=\s*(?:###|##|---|\Z))",
        re.MULTILINE,
    )

    def replace(match: re.Match) -> str:
        header = match.group(1)
        body = match.group(2)
        # 如果是占位「无」则整体替换
        if body.strip() in ("无", "- 无"):
            return f"{header}- {new_entry}\n"
        return f"{header}- {new_entry}\n{body}"

    new_content, count = pattern.subn(replace, content, count=1)
    return new_content if count else None


def cmd_changelog(args) -> None:
    """追加 CHANGELOG 条目"""
    path = f"{DOCS_DIR}/CHANGELOG.md"
    content = read_file(path)
    if content is None:
        print(f"[错误] {path} 不存在，请先运行 init 命令")
        sys.exit(1)

    section = args.type.capitalize()
    valid = {"Added", "Changed", "Fixed", "Removed", "Deprecated", "Security"}
    if section not in valid:
        print(f"[错误] type 必须是 {valid} 之一")
        sys.exit(1)

    updated = _insert_into_section(content, section, args.message)
    if updated is None:
        print(f"[警告] 未找到 [Unreleased] 中的 '### {section}' 段落，请检查格式")
        sys.exit(1)
    write_file(path, updated)
    print(f"✅ CHANGELOG 已追加 [{section}] {args.message}")


def cmd_api(args) -> None:
    """追加 API CHANGELOG 条目"""
    path = f"{API_DOCS_DIR}/API_CHANGELOG.md"
    content = read_file(path)
    if content is None:
        print(f"[错误] {path} 不存在，请先运行 init 命令")
        sys.exit(1)

    type_map = {
        "add": "新增接口",
        "change": "接口变更",
        "deprecate": "废弃接口",
        "remove": "移除接口",
    }
    section_name = type_map.get(args.type)
    if not section_name:
        print(f"[错误] type 必须是 {list(type_map.keys())} 之一")
        sys.exit(1)

    entry = f"`{args.endpoint}` - {args.description}"
    if args.breaking:
        entry = f"⚠️ Breaking {entry}"

    updated = _insert_into_section(content, section_name, entry)
    if updated is None:
        print(f"[警告] 未找到 [Unreleased] 中的 '### {section_name}' 段落，请检查格式")
        sys.exit(1)
    write_file(path, updated)
    print(f"✅ API CHANGELOG 已追加 [{section_name}] {args.endpoint}")


def cmd_req(args) -> None:
    """创建需求文档"""
    name = args.name
    title = args.title or name.replace("-", " ").title()
    author = args.author or "Unknown"
    today = datetime.now().strftime("%Y-%m-%d")

    target = f"{REQUIREMENTS_DIR}/REQ-{name}.md"
    if Path(target).exists() and not args.force:
        print(f"[错误] {target} 已存在，使用 --force 覆盖")
        sys.exit(1)

    template = load_template("PRD.md")
    number = get_next_req_number()
    rendered = (
        template
        .replace("{功能名称}", title)
        .replace("{编号}", number)
        .replace("{YYYY-MM-DD}", today, 2)
        .replace("{作者}", author)
        .replace("{日期}", today)
    )

    write_file(target, rendered)
    print(f"✅ 已创建需求文档: {target}（编号 REQ-{number}）")


def cmd_release(args) -> None:
    """把 [Unreleased] 段落转换为正式版本

    步骤：
        1. 把 `## [Unreleased]` 改为 `## [{version}] - {date}`
        2. 在文件顶部插入新的空 `## [Unreleased]` 段
        3. 维护底部链接定义（如有）
    """
    target = (
        f"{API_DOCS_DIR}/API_CHANGELOG.md"
        if args.target == "api"
        else f"{DOCS_DIR}/CHANGELOG.md"
    )
    content = read_file(target)
    if content is None:
        print(f"[错误] {target} 不存在")
        sys.exit(1)

    version = args.version.lstrip("v")
    today = datetime.now().strftime("%Y-%m-%d")

    # 用 [ \t]*$ 避免吞掉换行符（保留段落间空行）
    if not re.search(r"^## \[Unreleased\][ \t]*$", content, flags=re.MULTILINE):
        print(f"[错误] 文档中找不到 `## [Unreleased]` 段落，无法发版")
        sys.exit(1)

    # 1. 把 [Unreleased] 替换为 [version] - date
    new_unreleased_block = _build_empty_unreleased(args.target)
    versioned_header = f"## [{version}] - {today}"
    content_after = re.sub(
        r"^## \[Unreleased\][ \t]*$",
        new_unreleased_block + "\n\n" + versioned_header,
        content,
        count=1,
        flags=re.MULTILINE,
    )

    # 2. 维护链接定义（仅 CHANGELOG 才用语义化版本链接）
    if args.target != "api":
        content_after = _refresh_changelog_links(content_after, version)

    write_file(target, content_after)
    print(f"✅ 已发布版本 {version}（{today}）→ {target}")


def _build_empty_unreleased(target: str) -> str:
    """生成空的 [Unreleased] 段落"""
    if target == "api":
        return (
            "## [Unreleased]\n\n"
            "### 新增接口\n- 无\n\n"
            "### 接口变更\n- 无\n\n"
            "### 废弃接口\n- 无\n\n"
            "### 移除接口\n- 无"
        )
    return (
        "## [Unreleased]\n\n"
        "### Added\n- 无\n\n"
        "### Changed\n- 无\n\n"
        "### Deprecated\n- 无\n\n"
        "### Removed\n- 无\n\n"
        "### Fixed\n- 无\n\n"
        "### Security\n- 无"
    )


def _refresh_changelog_links(content: str, new_version: str) -> str:
    """维护 CHANGELOG 底部的版本对比链接"""
    # 找到 [Unreleased] 链接定义
    pattern = re.compile(
        r"\[Unreleased\]:\s*(.+?)/compare/(?:v)?([\w.+-]+)\.\.\.HEAD",
        re.MULTILINE,
    )
    m = pattern.search(content)
    if not m:
        # 没有链接定义则不强制添加
        return content
    repo_url = m.group(1)
    last_version = m.group(2)

    new_unreleased_link = f"[Unreleased]: {repo_url}/compare/v{new_version}...HEAD"
    new_version_link = f"[{new_version}]: {repo_url}/compare/v{last_version}...v{new_version}"

    content = pattern.sub(new_unreleased_link, content, count=1)
    # 在 [Unreleased] 链接行后追加新版本链接（避免重复）
    if f"[{new_version}]:" not in content:
        content = re.sub(
            r"(\[Unreleased\]:.+\n)",
            r"\1" + new_version_link + "\n",
            content,
            count=1,
        )
    return content


# ==================== CLI ====================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="开发文档自动更新工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=False)

    sub.add_parser("init", help="初始化文档目录")

    p_cl = sub.add_parser("changelog", help="追加 CHANGELOG 条目")
    p_cl.add_argument("--type", "-t", required=True,
                      choices=["added", "changed", "fixed", "removed", "deprecated", "security"])
    p_cl.add_argument("--message", "-m", required=True, help="变更描述（用户视角）")

    p_api = sub.add_parser("api", help="追加 API CHANGELOG 条目")
    p_api.add_argument("--type", "-t", required=True,
                       choices=["add", "change", "deprecate", "remove"])
    p_api.add_argument("--endpoint", "-e", required=True, help="例：'POST /api/users'")
    p_api.add_argument("--description", "-d", required=True, help="变更说明")
    p_api.add_argument("--breaking", action="store_true",
                       help="标注为 Breaking Change（前置 ⚠️ 标志）")

    p_req = sub.add_parser("req", help="创建需求文档")
    p_req.add_argument("--name", "-n", required=True, help="功能短名（用于文件名）")
    p_req.add_argument("--title", "-t", help="文档标题")
    p_req.add_argument("--author", "-a", help="作者")
    p_req.add_argument("--force", "-f", action="store_true", help="覆盖已存在文件")

    p_rel = sub.add_parser("release", help="把 [Unreleased] 段落转为正式版本")
    p_rel.add_argument("--version", "-v", required=True, help="新版本号，如 1.2.0")
    p_rel.add_argument("--target", choices=["changelog", "api"], default="changelog",
                       help="处理 CHANGELOG 还是 API_CHANGELOG（默认 changelog）")

    args = parser.parse_args()

    handlers = {
        "init": cmd_init,
        "changelog": cmd_changelog,
        "api": cmd_api,
        "req": cmd_req,
        "release": cmd_release,
    }

    if not args.command:
        parser.print_help()
        return
    handlers[args.command](args)


if __name__ == "__main__":
    main()
