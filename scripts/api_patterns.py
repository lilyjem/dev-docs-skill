#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多语言 API 识别模式库

为 analyze_changes.py 和 generate_api_doc.py 提供统一的接口识别能力。
覆盖 Python（FastAPI/Flask/Django）、Node.js（Express/Koa/NestJS）、
Java（Spring）、Go（Gin/Echo/net-http），并支持 OpenAPI 规范解析。

设计原则：
    1. 每种框架对应一个 FrameworkPattern，包含文件类型、装饰器/调用模式、提取规则
    2. 使用统一的 Endpoint 数据结构表达识别结果
    3. 支持上下文感知（例如 Spring @RequestMapping 类级前缀）
    4. 易于扩展：新增框架只需追加 FrameworkPattern，无需改动调用方
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Pattern, Tuple


# ==================== 数据结构 ====================

@dataclass
class Endpoint:
    """统一的接口表示。

    Attributes:
        method: HTTP 方法（GET/POST/PUT/DELETE/PATCH/...）
        path: 接口路径
        function: 处理函数/控制器方法名
        framework: 识别到的框架名
        file: 来源文件路径（相对项目根）
        line: 起始行号（1-indexed）
        description: 从 docstring/注释提取的接口描述（可选）
    """

    method: str
    path: str
    function: str = ""
    framework: str = ""
    file: str = ""
    line: int = 0
    description: str = ""

    def signature(self) -> str:
        """生成可读签名，例：'POST /api/users'"""
        return f"{self.method.upper()} {self.path}"


@dataclass
class FrameworkPattern:
    """一种框架的识别配置。

    Attributes:
        name: 框架名（用于诊断）
        language: 编程语言
        file_globs: 适用的文件 glob 模式列表
        decorator_regex: 用于在源码中匹配接口声明的正则
        method_group: 在 decorator_regex 中 HTTP 方法的捕获组索引（None = 由 method_resolver 处理）
        path_group: 路径的捕获组索引（None = 由 path_resolver 处理）
        method_resolver: 自定义方法解析回调（用于装饰器名即方法的场景，如 @Get）
        path_resolver: 自定义路径解析回调
        function_finder: 在装饰器之后查找处理函数名的策略
    """

    name: str
    language: str
    file_globs: Tuple[str, ...]
    decorator_regex: Pattern[str]
    method_group: Optional[int] = None
    path_group: Optional[int] = None
    method_resolver: Optional[Callable] = None
    path_resolver: Optional[Callable] = None
    function_finder: Optional[Callable] = None
    class_prefix_regex: Optional[Pattern[str]] = None  # Spring/NestJS 类级路径前缀


# ==================== 通用辅助 ====================

# HTTP 方法白名单，用于 @Get / @Post 这类「方法即装饰器名」的场景
HTTP_METHODS = {
    "GET", "POST", "PUT", "DELETE", "PATCH",
    "OPTIONS", "HEAD", "TRACE", "CONNECT",
}


def _next_function_python(lines: List[str], start: int, max_look: int = 8) -> str:
    """Python: 在装饰器之后向下查找 def / async def"""
    pat = re.compile(r"^\s*(?:async\s+)?def\s+(\w+)\s*\(")
    for i in range(start + 1, min(start + 1 + max_look, len(lines))):
        m = pat.match(lines[i])
        if m:
            return m.group(1)
    return ""


def _next_function_typescript(lines: List[str], start: int, max_look: int = 8) -> str:
    """TS/JS: 装饰器后向下查找方法或函数名"""
    patterns = [
        re.compile(r"^\s*(?:async\s+)?(\w+)\s*\([^)]*\)\s*[:{]"),  # 类方法
        re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\("),  # 函数
        re.compile(r"^\s*const\s+(\w+)\s*=\s*(?:async\s*)?\("),  # 箭头函数
    ]
    for i in range(start + 1, min(start + 1 + max_look, len(lines))):
        for pat in patterns:
            m = pat.match(lines[i])
            if m:
                return m.group(1)
    return ""


def _next_function_java(lines: List[str], start: int, max_look: int = 12) -> str:
    """Java: 装饰器后查找方法签名"""
    pat = re.compile(r"^\s*(?:public|private|protected)?\s*(?:static\s+)?[\w<>\[\],\s]+\s+(\w+)\s*\(")
    for i in range(start + 1, min(start + 1 + max_look, len(lines))):
        m = pat.match(lines[i])
        if m and not lines[i].lstrip().startswith("@"):
            return m.group(1)
    return ""


def _next_function_go(lines: List[str], start: int, max_look: int = 5) -> str:
    """Go: r.GET("/path", handler) 中提取 handler 名（同行处理）"""
    return ""


# ==================== 各语言 / 框架模式 ====================

# ---------- Python ----------

# FastAPI: @app.get("/users")  /  @router.post("/users")
FASTAPI_PATTERN = FrameworkPattern(
    name="FastAPI",
    language="python",
    file_globs=("**/*.py",),
    decorator_regex=re.compile(
        r"@(?:app|router|api_router)\.(get|post|put|delete|patch|options|head)\s*\(\s*['\"]([^'\"]+)['\"]"
    ),
    method_group=1,
    path_group=2,
    function_finder=_next_function_python,
)

# Flask: @app.route("/users", methods=["GET", "POST"])  /  @bp.route(...)
# 注意 methods 参数可选，默认 GET
FLASK_PATTERN = FrameworkPattern(
    name="Flask",
    language="python",
    file_globs=("**/*.py",),
    decorator_regex=re.compile(
        r"@(?:\w+)\.route\s*\(\s*['\"]([^'\"]+)['\"](?:\s*,\s*methods\s*=\s*\[([^\]]+)\])?"
    ),
    method_group=None,
    path_group=1,
    method_resolver=lambda m: _flask_methods(m.group(2)),
    function_finder=_next_function_python,
)


def _flask_methods(methods_str: Optional[str]) -> str:
    """Flask methods=["GET","POST"] → 'GET,POST'，缺省时返回 GET"""
    if not methods_str:
        return "GET"
    methods = re.findall(r"['\"](\w+)['\"]", methods_str)
    return ",".join(m.upper() for m in methods) if methods else "GET"


# Django URL: path("users/", views.list_users, name="users")
DJANGO_PATTERN = FrameworkPattern(
    name="Django",
    language="python",
    file_globs=("**/urls.py",),
    decorator_regex=re.compile(
        r"(?:path|re_path|url)\s*\(\s*r?['\"]([^'\"]*)['\"]\s*,\s*([\w.]+)"
    ),
    method_group=None,
    path_group=1,
    method_resolver=lambda m: "ANY",
    path_resolver=None,
    function_finder=lambda lines, start, _max=0: "",
)


# ---------- Node.js / TypeScript ----------

# Express / Koa: app.get("/users", handler)  /  router.post("/users", ...)
EXPRESS_PATTERN = FrameworkPattern(
    name="Express/Koa",
    language="javascript",
    file_globs=("**/*.js", "**/*.ts", "**/*.mjs", "**/*.cjs"),
    decorator_regex=re.compile(
        r"\b(?:app|router|api|server)\.(get|post|put|delete|patch|options|head|all)\s*\(\s*['\"`]([^'\"`]+)['\"`]"
    ),
    method_group=1,
    path_group=2,
    function_finder=_next_function_typescript,
)

# NestJS: @Get('users')  /  @Post()  装饰器
# 注意：路径可省略（默认 ''），并依赖类级 @Controller('users')
NEST_PATTERN = FrameworkPattern(
    name="NestJS",
    language="typescript",
    file_globs=("**/*.controller.ts", "**/*.controller.js"),
    decorator_regex=re.compile(
        r"@(Get|Post|Put|Delete|Patch|Options|Head|All)\s*\(\s*['\"`]?([^'\"`)]*)['\"`]?\s*\)"
    ),
    method_group=1,
    path_group=2,
    function_finder=_next_function_typescript,
    class_prefix_regex=re.compile(
        r"@Controller\s*\(\s*['\"`]([^'\"`]+)['\"`]"
    ),
)


# ---------- Java / Spring ----------

# Spring: @GetMapping("/users")  /  @RequestMapping(value="/users", method=RequestMethod.POST)
SPRING_MAPPING_PATTERN = FrameworkPattern(
    name="Spring",
    language="java",
    file_globs=("**/*.java",),
    decorator_regex=re.compile(
        r"@(GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping)\s*\(\s*(?:value\s*=\s*)?['\"]([^'\"]+)['\"]"
    ),
    method_group=1,
    path_group=2,
    method_resolver=lambda m: m.group(1).replace("Mapping", "").upper(),
    function_finder=_next_function_java,
    class_prefix_regex=re.compile(
        r"@RequestMapping\s*\(\s*(?:value\s*=\s*)?['\"]([^'\"]+)['\"]"
    ),
)

# Spring 通用 @RequestMapping(method = RequestMethod.GET, value = "/users")
SPRING_REQUEST_MAPPING_PATTERN = FrameworkPattern(
    name="Spring",
    language="java",
    file_globs=("**/*.java",),
    decorator_regex=re.compile(
        r"@RequestMapping\s*\([^)]*method\s*=\s*RequestMethod\.(\w+)[^)]*value\s*=\s*['\"]([^'\"]+)['\"]"
    ),
    method_group=1,
    path_group=2,
    function_finder=_next_function_java,
)


# ---------- Go ----------

# Gin: r.GET("/users", handler)  /  group.POST(...)
GIN_PATTERN = FrameworkPattern(
    name="Gin",
    language="go",
    file_globs=("**/*.go",),
    decorator_regex=re.compile(
        r"\b\w+\.(GET|POST|PUT|DELETE|PATCH|OPTIONS|HEAD|Any)\s*\(\s*\"([^\"]+)\"\s*,\s*([\w.]+)"
    ),
    method_group=1,
    path_group=2,
    function_finder=lambda lines, start, _max=0: "",
)

# Echo: e.GET("/users", handler)
ECHO_PATTERN = FrameworkPattern(
    name="Echo",
    language="go",
    file_globs=("**/*.go",),
    decorator_regex=re.compile(
        r"\b(?:e|echo|app|router|group)\.(GET|POST|PUT|DELETE|PATCH|OPTIONS|HEAD)\s*\(\s*\"([^\"]+)\""
    ),
    method_group=1,
    path_group=2,
    function_finder=lambda lines, start, _max=0: "",
)

# net/http: http.HandleFunc("/users", handler)  /  mux.Handle("/users", ...)
NETHTTP_PATTERN = FrameworkPattern(
    name="net/http",
    language="go",
    file_globs=("**/*.go",),
    decorator_regex=re.compile(
        r"(?:http|mux|router)\.(?:HandleFunc|Handle)\s*\(\s*\"([^\"]+)\"\s*,\s*([\w.]+)"
    ),
    method_group=None,
    path_group=1,
    method_resolver=lambda m: "ANY",
    function_finder=lambda lines, start, _max=0: "",
)


# 所有模式集合，按优先级排序（特定的优先于通用的）
ALL_PATTERNS: Tuple[FrameworkPattern, ...] = (
    NEST_PATTERN,                  # NestJS 装饰器最具特征性
    SPRING_MAPPING_PATTERN,
    SPRING_REQUEST_MAPPING_PATTERN,
    FASTAPI_PATTERN,
    FLASK_PATTERN,
    DJANGO_PATTERN,
    EXPRESS_PATTERN,
    GIN_PATTERN,
    ECHO_PATTERN,
    NETHTTP_PATTERN,
)


# ==================== 主入口 ====================

def file_matches(file_path: str, patterns: Iterable[str]) -> bool:
    """检查文件路径是否匹配任一 glob。

    特别处理 `**/x` 形式：兼容根目录下的文件（Path.match 在 Python < 3.13 中对根目录
    文件用 `**/` 前缀会返回 False），需要单独处理。
    """
    p = Path(file_path)
    name_only = Path(p.name)
    for pattern in patterns:
        # 直接 Path.match 试一次
        if p.match(pattern):
            return True
        # 若以 **/ 开头，则脱掉前缀再尝试匹配（支持根目录文件）
        if pattern.startswith("**/"):
            stripped = pattern[3:]
            if p.match(stripped) or name_only.match(stripped):
                return True
    return False


def extract_class_prefix(content: str, pattern: FrameworkPattern) -> str:
    """提取类级路径前缀（用于 Spring @RequestMapping、NestJS @Controller）"""
    if not pattern.class_prefix_regex:
        return ""
    m = pattern.class_prefix_regex.search(content)
    return m.group(1) if m else ""


def normalize_path(prefix: str, path: str) -> str:
    """合并类级前缀与方法级路径，确保前导 / 与中间 / 正确处理"""
    if not prefix:
        # 无前缀：仅确保以 / 开头
        if not path:
            return "/"
        return path if path.startswith("/") else "/" + path
    # 规范化 prefix：去尾 /，若缺前导 / 则补
    prefix = prefix.rstrip("/")
    if not prefix.startswith("/"):
        prefix = "/" + prefix
    if not path:
        return prefix or "/"
    if not path.startswith("/"):
        path = "/" + path
    return prefix + path


def extract_endpoints_from_content(
    content: str,
    file_path: str = "",
) -> List[Endpoint]:
    """从单个文件内容中识别所有端点。

    Args:
        content: 文件文本内容
        file_path: 用于框架匹配与回填 Endpoint.file

    Returns:
        识别到的端点列表（已去重）
    """
    if not content:
        return []

    lines = content.split("\n")
    endpoints: List[Endpoint] = []
    seen: set = set()

    for pattern in ALL_PATTERNS:
        if file_path and not file_matches(file_path, pattern.file_globs):
            continue

        prefix = extract_class_prefix(content, pattern)

        for line_no, line in enumerate(lines):
            for match in pattern.decorator_regex.finditer(line):
                method = _resolve_method(pattern, match)
                path = _resolve_path(pattern, match, line)
                if not method or not path:
                    continue

                full_path = normalize_path(prefix, path)
                func_name = ""
                if pattern.function_finder:
                    func_name = pattern.function_finder(lines, line_no)

                # 优先尝试同行抓 handler（Gin/Echo/net-http 的常见写法）
                if not func_name and match.lastindex and match.lastindex >= 3:
                    try:
                        func_name = match.group(3) or ""
                    except IndexError:
                        func_name = ""

                # 处理 Flask 多方法（'GET,POST' → 拆为多条）
                for single_method in method.split(","):
                    single_method = single_method.strip().upper()
                    if not single_method:
                        continue
                    key = (single_method, full_path, file_path)
                    if key in seen:
                        continue
                    seen.add(key)
                    endpoints.append(
                        Endpoint(
                            method=single_method,
                            path=full_path,
                            function=func_name,
                            framework=pattern.name,
                            file=file_path,
                            line=line_no + 1,
                        )
                    )

    return endpoints


def _resolve_method(pattern: FrameworkPattern, match: re.Match) -> str:
    """根据 FrameworkPattern 配置解析 HTTP 方法"""
    if pattern.method_resolver:
        return pattern.method_resolver(match)
    if pattern.method_group is not None:
        try:
            raw = match.group(pattern.method_group)
        except IndexError:
            return ""
        return raw.upper() if raw else ""
    return ""


def _resolve_path(pattern: FrameworkPattern, match: re.Match, line: str) -> str:
    """根据 FrameworkPattern 配置解析路径"""
    if pattern.path_resolver:
        return pattern.path_resolver(match, line)
    if pattern.path_group is not None:
        try:
            return match.group(pattern.path_group) or ""
        except IndexError:
            return ""
    return ""


# ==================== OpenAPI 解析 ====================

def parse_openapi_file(path: str) -> List[Endpoint]:
    """解析 OpenAPI 3.x（YAML 或 JSON）文件，提取所有端点。

    依赖：PyYAML（yaml 模块）。若未安装则降级跳过 YAML 文件。
    """
    file_path = Path(path)
    if not file_path.exists():
        return []

    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError:
        return []

    spec: Optional[dict] = None
    if file_path.suffix in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore
            spec = yaml.safe_load(text)
        except ImportError:
            print(f"[警告] 解析 {path} 需要 PyYAML，请运行 pip install pyyaml")
            return []
        except yaml.YAMLError as exc:
            print(f"[警告] OpenAPI YAML 解析失败：{exc}")
            return []
    elif file_path.suffix == ".json":
        import json
        try:
            spec = json.loads(text)
        except json.JSONDecodeError as exc:
            print(f"[警告] OpenAPI JSON 解析失败：{exc}")
            return []

    if not isinstance(spec, dict):
        return []

    endpoints: List[Endpoint] = []
    paths = spec.get("paths") or {}
    for path_str, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, op in path_item.items():
            if method.upper() not in HTTP_METHODS:
                continue
            if not isinstance(op, dict):
                continue
            description = op.get("summary") or op.get("description") or ""
            endpoints.append(
                Endpoint(
                    method=method.upper(),
                    path=path_str,
                    function=op.get("operationId", ""),
                    framework="OpenAPI",
                    file=str(file_path),
                    description=description.strip(),
                )
            )
    return endpoints


# ==================== CLI 自检 ====================

def _self_test() -> None:
    """快速自检：传入若干样例，验证识别结果"""
    samples = [
        ("app/api.py", '@app.get("/users")\nasync def list_users():\n    return []\n'),
        ("flask_app.py", '@app.route("/login", methods=["POST"])\ndef login():\n    pass\n'),
        ("user.controller.ts",
         '@Controller("users")\nclass UC {\n  @Get(":id")\n  findOne() {}\n}\n'),
        ("UserController.java",
         '@RequestMapping("/api")\nclass UC {\n  @GetMapping("/users")\n  public List<User> list() { return null; }\n}\n'),
        ("server.go",
         'r.GET("/users", listUsers)\nr.POST("/users", createUser)\n'),
        ("express.js",
         'router.get("/health", (req, res) => res.json({ok: true}))\n'),
    ]
    print("=" * 60)
    print("api_patterns 自检")
    print("=" * 60)
    for file_path, content in samples:
        endpoints = extract_endpoints_from_content(content, file_path)
        print(f"\n📄 {file_path}")
        if not endpoints:
            print("   （未识别到端点）")
            continue
        for e in endpoints:
            print(f"   [{e.framework:10}] {e.signature():30} → {e.function or '?'}")


if __name__ == "__main__":
    _self_test()
