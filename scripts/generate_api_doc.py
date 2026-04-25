#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从代码或 OpenAPI 规范生成完整的 API.md 文档

支持来源：
    1. OpenAPI 3.x 规范文件（YAML/JSON）—— 最完整，推荐
    2. 源码扫描 + docstring/JSDoc/Javadoc/Go doc 提取 —— 适合无 OpenAPI 的项目

用法:
    # 从 OpenAPI 规范生成（推荐）
    python generate_api_doc.py --openapi docs/api/openapi.yaml --output docs/api/API.md

    # 从源码扫描生成
    python generate_api_doc.py --source ./src --output docs/api/API.md

    # 同时使用：以源码扫描结果补全 OpenAPI 缺失的端点
    python generate_api_doc.py --openapi docs/api/openapi.yaml --source ./src --output docs/api/API.md

    # 指定项目元信息
    python generate_api_doc.py --source ./src --project-name "我的项目" --base-url "https://api.example.com"
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent))
from api_patterns import (  # noqa: E402
    Endpoint,
    extract_endpoints_from_content,
    parse_openapi_file,
    file_matches,
)


# ==================== 数据结构 ====================

@dataclass
class EndpointDoc:
    """带描述的端点信息（用于渲染 API.md）"""
    endpoint: Endpoint
    summary: str = ""           # 一句话描述
    description: str = ""       # 详细描述
    parameters: List[Dict] = field(default_factory=list)
    request_body: Optional[Dict] = None
    responses: Dict[str, Dict] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


# ==================== 源码扫描 + docstring 提取 ====================

# 跳过这些目录（性能 + 减少噪音）
SKIP_DIRS = {
    "node_modules", "venv", ".venv", "__pycache__",
    ".git", ".idea", ".vscode", "dist", "build", "target",
    "vendor",  # Go vendor
    ".pytest_cache", ".mypy_cache",
}


def scan_source(root: str) -> List[EndpointDoc]:
    """递归扫描源码目录，返回带 docstring 的端点列表"""
    docs: List[EndpointDoc] = []
    root_path = Path(root)
    if not root_path.exists():
        print(f"[警告] 源码目录不存在: {root}", file=sys.stderr)
        return docs

    for path in _walk_source_files(root_path):
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        # 转为相对路径，便于在文档中显示
        try:
            rel = path.relative_to(root_path)
        except ValueError:
            rel = path
        rel_str = str(rel)
        endpoints = extract_endpoints_from_content(content, rel_str)
        for ep in endpoints:
            doc_text = _extract_docstring_for_endpoint(content, ep)
            summary, description = _split_summary(doc_text)
            docs.append(EndpointDoc(
                endpoint=ep,
                summary=summary,
                description=description,
            ))
    return docs


def _walk_source_files(root: Path):
    """生成器：递归 yield 所有源码文件，跳过 SKIP_DIRS"""
    if root.is_file():
        yield root
        return
    for child in root.iterdir():
        if child.name in SKIP_DIRS or child.name.startswith("."):
            continue
        if child.is_dir():
            yield from _walk_source_files(child)
        else:
            # 仅扫描有意义的源码后缀
            if child.suffix in {".py", ".js", ".ts", ".tsx", ".jsx",
                                 ".java", ".go", ".kt"}:
                yield child


def _extract_docstring_for_endpoint(content: str, ep: Endpoint) -> str:
    """根据端点行号尝试抓取上下文的注释/docstring。

    策略：
        1. 装饰器之后的下一段 docstring（Python：函数体内的三引号）
        2. 装饰器之前的连续注释行（JS/TS/Java/Go：// 或 /** */）
    """
    lines = content.split("\n")
    line_no = max(ep.line - 1, 0)

    # 1. 向下找 Python docstring
    py_doc = _python_docstring_after(lines, line_no)
    if py_doc:
        return py_doc

    # 2. 向上找块/单行注释（JSDoc / Javadoc / Go doc）
    block_doc = _block_comment_before(lines, line_no)
    if block_doc:
        return block_doc

    return ""


def _python_docstring_after(lines: List[str], start: int, max_look: int = 10) -> str:
    """从装饰器行向下找 def，再尝试抓 docstring"""
    pat_def = re.compile(r"^\s*(?:async\s+)?def\s+\w+\s*\(")
    def_line = -1
    for i in range(start + 1, min(start + 1 + max_look, len(lines))):
        if pat_def.match(lines[i]):
            def_line = i
            break
    if def_line < 0:
        return ""

    # def 行可能跨多行（参数过多），找到第一个 ":" 收尾
    body_start = def_line + 1
    for i in range(def_line, min(def_line + 5, len(lines))):
        if lines[i].rstrip().endswith(":"):
            body_start = i + 1
            break

    if body_start >= len(lines):
        return ""

    first = lines[body_start].strip()
    quote: Optional[str] = None
    if first.startswith('"""') or first.startswith("'''"):
        quote = first[:3]
    else:
        return ""

    # 单行 docstring
    if first.endswith(quote) and len(first) > 6:
        return first[3:-3].strip()

    # 多行 docstring
    parts: List[str] = [first[3:]]
    for j in range(body_start + 1, min(body_start + 30, len(lines))):
        line = lines[j]
        if quote in line:
            parts.append(line.split(quote)[0])
            break
        parts.append(line)
    return "\n".join(part.strip() for part in parts).strip()


def _block_comment_before(lines: List[str], start: int) -> str:
    """从装饰器行向上找连续的注释块（含 JSDoc/Javadoc/Go doc）"""
    collected: List[str] = []
    i = start - 1
    in_block = False
    while i >= 0:
        stripped = lines[i].strip()

        # 单行块注释：/** ... */ 同行（JSDoc 简写）
        single_block = re.match(r"^/\*+\s*(.*?)\s*\*+/\s*$", stripped)
        if single_block:
            text = single_block.group(1).strip()
            if text:
                collected.insert(0, text)
            i -= 1
            continue

        # 多行块注释结尾 */
        if stripped.endswith("*/"):
            in_block = True
            # 该行可能含内容（如 ` * description */`）
            inner = stripped[:-2].lstrip("*").strip()
            if inner:
                collected.insert(0, inner)
            i -= 1
            continue

        if in_block:
            # 块开始 /** 或 /*
            if stripped.startswith("/**") or stripped.startswith("/*"):
                # 该行可能含内容
                inner = stripped.lstrip("/").lstrip("*").strip()
                if inner:
                    collected.insert(0, inner)
                in_block = False
                i -= 1
                continue
            cleaned = stripped.lstrip("*").strip()
            collected.insert(0, cleaned)
            i -= 1
            continue

        # 单行注释 //
        if stripped.startswith("//"):
            collected.insert(0, stripped[2:].strip())
            i -= 1
            continue

        # 装饰器/空行：继续往上看（同一注解组）
        if stripped.startswith("@") or stripped == "":
            i -= 1
            continue
        break

    # 过滤掉 JSDoc tag 行（@param 等），保留正文
    cleaned = [line for line in collected if not line.startswith("@")]
    return "\n".join(cleaned).strip()


def _split_summary(doc_text: str) -> Tuple[str, str]:
    """把 docstring 拆成 (summary, description)：第一行为 summary"""
    if not doc_text:
        return "", ""
    lines = [line.strip() for line in doc_text.split("\n")]
    summary = lines[0]
    rest = "\n".join(lines[1:]).strip()
    return summary, rest


# ==================== OpenAPI 转 EndpointDoc ====================

def from_openapi(path: str) -> List[EndpointDoc]:
    """OpenAPI → EndpointDoc，保留参数与响应结构"""
    docs: List[EndpointDoc] = []
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        print(f"[警告] OpenAPI 文件读取失败: {path}", file=sys.stderr)
        return docs

    spec: Optional[dict] = None
    if path.endswith((".yaml", ".yml")):
        try:
            import yaml  # type: ignore
            spec = yaml.safe_load(text)
        except ImportError:
            print("[警告] 解析 YAML 需要 PyYAML，请运行 pip install pyyaml", file=sys.stderr)
            return docs
        except yaml.YAMLError as exc:
            print(f"[警告] YAML 解析失败: {exc}", file=sys.stderr)
            return docs
    elif path.endswith(".json"):
        import json
        try:
            spec = json.loads(text)
        except json.JSONDecodeError as exc:
            print(f"[警告] JSON 解析失败: {exc}", file=sys.stderr)
            return docs

    if not isinstance(spec, dict):
        return docs

    paths = spec.get("paths", {})
    for path_str, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, op in path_item.items():
            if method.upper() not in {"GET", "POST", "PUT", "DELETE", "PATCH",
                                       "OPTIONS", "HEAD"}:
                continue
            if not isinstance(op, dict):
                continue
            ep = Endpoint(
                method=method.upper(),
                path=path_str,
                function=op.get("operationId", ""),
                framework="OpenAPI",
                file=path,
            )
            docs.append(EndpointDoc(
                endpoint=ep,
                summary=op.get("summary", "").strip(),
                description=op.get("description", "").strip(),
                parameters=op.get("parameters", []),
                request_body=op.get("requestBody"),
                responses=op.get("responses", {}),
                tags=op.get("tags", []),
            ))
    return docs


# ==================== 合并去重 ====================

def merge_docs(*sources: List[EndpointDoc]) -> List[EndpointDoc]:
    """按 (method, path) 去重，OpenAPI 优先（信息更完整）"""
    by_key: Dict[Tuple[str, str], EndpointDoc] = {}
    for source in sources:
        for doc in source:
            key = (doc.endpoint.method, doc.endpoint.path)
            existing = by_key.get(key)
            if not existing:
                by_key[key] = doc
                continue
            # 如果新条目来自 OpenAPI 且现有不是，则覆盖
            if doc.endpoint.framework == "OpenAPI" and existing.endpoint.framework != "OpenAPI":
                by_key[key] = doc
            # 否则保留更早遇到的
    return list(by_key.values())


# ==================== Markdown 渲染 ====================

def render_api_md(
    docs: List[EndpointDoc],
    project_name: str = "项目",
    version: str = "1.0.0",
    base_url: str = "https://api.example.com",
) -> str:
    """渲染完整 API.md 内容"""
    today = datetime.now().strftime("%Y-%m-%d")
    by_tag: Dict[str, List[EndpointDoc]] = {}

    for doc in docs:
        tag = (doc.tags[0] if doc.tags else _infer_tag_from_path(doc.endpoint.path))
        by_tag.setdefault(tag, []).append(doc)

    lines: List[str] = [
        f"# {project_name} API 接口文档",
        "",
        "## 文档信息",
        "",
        "| 属性 | 值 |",
        "|------|-----|",
        f"| 版本 | v{version} |",
        f"| 最后更新 | {today} |",
        f"| 基础 URL | `{base_url}` |",
        f"| 接口总数 | {len(docs)} |",
        "",
        "---",
        "",
        "## 1. 概述",
        "",
        "本文档由 `dev-docs-skill` 自动生成，覆盖项目所有公开 HTTP 接口。",
        "",
        "**约定**：",
        "- 协议：HTTPS",
        "- 数据格式：JSON（UTF-8）",
        "- 时间格式：ISO 8601",
        "",
        "---",
        "",
        "## 2. 接口列表",
        "",
    ]

    section_idx = 0
    for tag in sorted(by_tag.keys()):
        section_idx += 1
        endpoints = sorted(by_tag[tag], key=lambda d: (d.endpoint.path, d.endpoint.method))
        lines.append(f"### 2.{section_idx} {tag}")
        lines.append("")
        for doc in endpoints:
            lines.extend(_render_endpoint(doc))
            lines.append("")

    lines.extend([
        "---",
        "",
        "## 3. 错误码说明",
        "",
        "| HTTP | 含义 |",
        "|------|------|",
        "| 200 | 成功 |",
        "| 400 | 请求参数错误 |",
        "| 401 | 未认证 |",
        "| 403 | 无权限 |",
        "| 404 | 资源不存在 |",
        "| 429 | 触发限流 |",
        "| 500 | 服务器错误 |",
        "",
        "---",
        "",
        "## 附录",
        "",
        "- [API 变更日志](./API_CHANGELOG.md)",
        f"- 生成方式：`python scripts/generate_api_doc.py`（{today}）",
        "",
    ])

    return "\n".join(lines)


def _infer_tag_from_path(path: str) -> str:
    """从路径推断分组：/api/users/... → users"""
    parts = [p for p in path.split("/") if p and not p.startswith("{") and not p.startswith(":")]
    if not parts:
        return "Default"
    # 跳过常见前缀
    skip = {"api", "v1", "v2", "v3", "rest"}
    for p in parts:
        if p.lower() not in skip:
            return p.capitalize()
    return parts[0].capitalize()


def _render_endpoint(doc: EndpointDoc) -> List[str]:
    """渲染单个端点的 Markdown 段落"""
    ep = doc.endpoint
    summary = doc.summary or doc.endpoint.function or "（无描述）"
    out: List[str] = [
        f"#### `{ep.method} {ep.path}` — {summary}",
        "",
    ]

    # 元信息表
    out.append("| 属性 | 值 |")
    out.append("|------|-----|")
    if ep.framework:
        out.append(f"| 框架 | {ep.framework} |")
    if ep.function:
        out.append(f"| 处理函数 | `{ep.function}` |")
    if ep.file:
        out.append(f"| 来源 | `{ep.file}`{':' + str(ep.line) if ep.line else ''} |")
    if doc.tags:
        out.append(f"| 分组 | {', '.join(doc.tags)} |")
    out.append("")

    # 详细描述
    if doc.description:
        out.append("**描述**")
        out.append("")
        out.append(doc.description)
        out.append("")

    # 参数
    if doc.parameters:
        out.append("**请求参数**")
        out.append("")
        out.append("| 参数 | 位置 | 类型 | 必填 | 描述 |")
        out.append("|------|------|------|------|------|")
        for p in doc.parameters:
            if not isinstance(p, dict):
                continue
            schema = p.get("schema", {}) or {}
            out.append(
                f"| `{p.get('name', '?')}` | {p.get('in', '?')} | "
                f"{schema.get('type', '?')} | {'是' if p.get('required') else '否'} | "
                f"{(p.get('description') or '').strip() or '-'} |"
            )
        out.append("")

    # 请求体
    if doc.request_body:
        out.append("**请求体**")
        out.append("")
        out.append("```json")
        out.append(_pretty_request_body(doc.request_body))
        out.append("```")
        out.append("")

    # 响应
    if doc.responses:
        out.append("**响应**")
        out.append("")
        out.append("| 状态码 | 描述 |")
        out.append("|--------|------|")
        for code, resp in doc.responses.items():
            if isinstance(resp, dict):
                desc = (resp.get("description") or "").strip() or "-"
                out.append(f"| {code} | {desc} |")
        out.append("")

    return out


def _pretty_request_body(rb: Dict) -> str:
    """从 OpenAPI requestBody 提取一个示例 JSON"""
    content = rb.get("content", {}) or {}
    json_section = content.get("application/json", {})
    if "example" in json_section:
        import json
        return json.dumps(json_section["example"], ensure_ascii=False, indent=2)
    schema = json_section.get("schema", {})
    if schema:
        import json
        return json.dumps(_schema_to_example(schema), ensure_ascii=False, indent=2)
    return "{}"


def _schema_to_example(schema: Dict) -> object:
    """根据 schema 生成简单示例（不解析 $ref）"""
    if not isinstance(schema, dict):
        return None
    if "example" in schema:
        return schema["example"]
    typ = schema.get("type")
    if typ == "string":
        return schema.get("default", "string")
    if typ == "integer":
        return schema.get("default", 0)
    if typ == "number":
        return schema.get("default", 0.0)
    if typ == "boolean":
        return schema.get("default", False)
    if typ == "array":
        return [_schema_to_example(schema.get("items", {}))]
    if typ == "object" or "properties" in schema:
        result = {}
        for name, prop_schema in (schema.get("properties") or {}).items():
            result[name] = _schema_to_example(prop_schema)
        return result
    return None


# ==================== 主流程 ====================

def main() -> None:
    parser = argparse.ArgumentParser(description="从 OpenAPI 或源码生成完整 API.md")
    parser.add_argument("--openapi", help="OpenAPI 规范文件（.yaml/.json）")
    parser.add_argument("--source", help="源码根目录")
    parser.add_argument("--output", default="docs/api/API.md", help="输出路径")
    parser.add_argument("--project-name", default="项目", help="项目名称")
    parser.add_argument("--version", default="1.0.0", help="API 版本")
    parser.add_argument("--base-url", default="https://api.example.com", help="基础 URL")
    args = parser.parse_args()

    if not args.openapi and not args.source:
        parser.error("至少指定 --openapi 或 --source 之一")

    sources: List[List[EndpointDoc]] = []

    if args.openapi:
        print(f"解析 OpenAPI: {args.openapi}", file=sys.stderr)
        openapi_docs = from_openapi(args.openapi)
        print(f"  → {len(openapi_docs)} 个端点", file=sys.stderr)
        sources.append(openapi_docs)

    if args.source:
        print(f"扫描源码: {args.source}", file=sys.stderr)
        source_docs = scan_source(args.source)
        print(f"  → {len(source_docs)} 个端点", file=sys.stderr)
        sources.append(source_docs)

    merged = merge_docs(*sources)
    if not merged:
        print("[警告] 未识别到任何端点，输出空文档", file=sys.stderr)

    output = render_api_md(
        merged,
        project_name=args.project_name,
        version=args.version,
        base_url=args.base_url,
    )

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(output, encoding="utf-8")
    print(f"✅ 已生成 API 文档: {args.output}（{len(merged)} 个端点）", file=sys.stderr)


if __name__ == "__main__":
    main()
