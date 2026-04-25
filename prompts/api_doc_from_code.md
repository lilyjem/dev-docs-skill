# Prompt：从代码生成 API 文档段落

> **如何使用**：把整篇内容发给 LLM，附上目标接口的源码与配套类型/数据模型。LLM 将输出符合 `templates/API.md` 风格的接口文档段落。

---

## 角色

你是一名 API 技术文档专家，擅长把代码与 docstring/注释 转化为面向调用方的清晰文档。

## 上下文

**项目语言/框架**：<LANGUAGE_AND_FRAMEWORK>（例：Python / FastAPI、Node.js / NestJS）

**目标接口源码**（必填）：
```<语言>
<把接口的源码贴到这里，包含装饰器、函数签名、docstring、参数模型、响应模型>
```

**关联类型/模型**（可选）：
```<语言>
<把请求体/响应体的数据类、Pydantic 模型、TypeScript interface、Java DTO 等贴到这里>
```

**业务背景**（可选但推荐）：
<本接口在业务流程中的位置、调用方、上下游依赖>

## 任务

输出一段可直接插入 `docs/api/API.md` 的 Markdown，描述这个接口。

## 必须遵循的规则

1. **使用以下结构**（与 `templates/API.md` 一致）：
   ```
   #### `METHOD /path` — 一句话描述

   | 属性 | 值 |
   |------|-----|
   | 路径 | `METHOD /path` |
   | 认证 | 是/否/可选 |
   | 权限 | xxx |
   | 幂等 | 是/否 |
   | 描述 | xxx |

   **请求参数**
   <表格>

   **请求示例**
   <bash 或 json>

   **响应参数**
   <表格>

   **响应示例（成功）**
   <json>

   **响应示例（失败）**
   <json>
   ```
2. **类型尽量具体**：写 `string (UUID)`、`integer (>=1, <=100)`、`enum: active / inactive` 等，不要只写 `string`。
3. **必填用「是/否」**，不要混用 true/false/Y/N。
4. **路径参数与 query 参数分开**：`位置` 列写 `path` / `query` / `header` / `body`。
5. **请求示例用 cURL**；如代码中能识别到 JSON 请求体，提供完整的请求体 JSON。
6. **响应示例双份**：成功（HTTP 200）+ 一个常见失败（如 400/404/401）。
7. **错误码引用**：如果代码抛出了具体业务码，仅引用错误码（不要重复定义），格式：`详见错误码 10001`。
8. **不要编造**：源码没体现的字段不要写；不知道就写 `（待补充）` 而不是猜测。

## 输出格式

只输出 Markdown，不要外部说明。示例：

```markdown
#### `POST /api/auth/login` — 邮箱密码登录

| 属性 | 值 |
|------|-----|
| 路径 | `POST /api/auth/login` |
| 认证 | 否 |
| 权限 | 公开 |
| 幂等 | 否 |
| 描述 | 邮箱与密码校验通过后，返回 access/refresh token |

**请求参数**

| 参数 | 位置 | 类型 | 必填 | 描述 |
|------|------|------|------|------|
| `email` | body | string (Email) | 是 | 用户邮箱 |
| `password` | body | string (≥ 8 字符) | 是 | 用户密码 |

**请求示例**
```bash
curl -X POST "https://api.example.com/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"jem@example.com","password":"secret123"}'
```

**响应参数**

| 字段 | 类型 | 描述 |
|------|------|------|
| `code` | integer | 业务码，0 表示成功 |
| `data.accessToken` | string | 访问令牌（JWT） |
| `data.refreshToken` | string | 刷新令牌 |
| `data.expiresIn` | integer | 访问令牌有效期（秒） |

**响应示例（成功）**
```json
{
  "code": 0,
  "data": {
    "accessToken": "eyJhbGc...",
    "refreshToken": "eyJhbGc...",
    "expiresIn": 7200
  }
}
```

**响应示例（失败）**
```json
{
  "code": 10001,
  "message": "邮箱或密码错误",
  "data": null
}
```
```

## 现在开始
请基于上述源码生成接口文档段落。
