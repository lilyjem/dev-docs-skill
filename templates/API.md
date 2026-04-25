# {项目名称} API 接口文档

<!--
  API 接口文档模板
  适用场景：RESTful API、GraphQL、RPC 接口
  使用说明：
    1. 复制本模板到 docs/api/API.md
    2. 在「3. 接口列表」中按模块组织接口
    3. 每个接口都需要：路径 / 描述 / 请求参数 / 请求示例 / 响应参数 / 响应示例
    4. 所有错误码必须在「5. 错误码说明」中定义
-->

## 文档信息

| 属性 | 值 |
|------|-----|
| 版本 | v{版本号} |
| 最后更新 | {YYYY-MM-DD} |
| 基础 URL（开发） | `https://dev.example.com/api` |
| 基础 URL（生产） | `https://api.example.com` |
| 维护人 | {负责人} |

---

## 1. 概述

### 1.1 简介
{API 的用途、适用对象、设计原则}

### 1.2 基础约定
- **协议**：HTTPS（生产强制）
- **数据格式**：JSON（UTF-8）
- **时间格式**：ISO 8601（`2026-04-25T20:30:00Z`）
- **分页**：`page`（从 1 开始）+ `pageSize`（默认 20，最大 100）
- **排序**：`sortBy=field&order=asc|desc`

### 1.3 版本策略
{URL 版本（/v1/）/ Header 版本 / Accept 版本，及向后兼容承诺}

---

## 2. 认证授权

### 2.1 认证方式
{JWT / API Key / OAuth 2.0 / Basic Auth}

### 2.2 请求头
```http
Authorization: Bearer {token}
X-Request-Id: {唯一请求 ID，用于追踪}
```

### 2.3 获取 Token
| 属性 | 值 |
|------|-----|
| 路径 | `POST /auth/login` |
| 描述 | 用户名密码登录获取 Token |

**请求体**
```json
{
  "username": "admin",
  "password": "******"
}
```

**响应**
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

### 2.4 限流策略
- 单 Token：60 次/分钟
- 单 IP：120 次/分钟
- 超限响应：HTTP 429 + `Retry-After` 响应头

---

## 3. 接口列表

### 3.1 {模块名称}

#### {接口名称}

| 属性 | 值 |
|------|-----|
| 路径 | `{HTTP方法} {路径}` |
| 认证 | 是 / 否 / 可选 |
| 权限 | {所需角色或权限码} |
| 幂等 | 是 / 否 |
| 描述 | {接口功能描述} |

**请求参数**

| 参数名 | 位置 | 类型 | 必填 | 默认值 | 描述 |
|--------|------|------|------|--------|------|
| {参数} | path / query / header / body | {类型} | 是 / 否 | {默认值} | {描述} |

**请求示例**
```bash
curl -X POST "https://api.example.com/users" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Jem",
    "email": "jem@example.com"
  }'
```

**响应参数**

| 参数名 | 类型 | 描述 |
|--------|------|------|
| code | integer | 业务状态码，0 表示成功 |
| message | string | 状态描述 |
| data | object | 业务数据 |
| data.id | string | 资源 ID |

**响应示例（成功）**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "u_001",
    "name": "Jem",
    "email": "jem@example.com",
    "createdAt": "2026-04-25T20:30:00Z"
  }
}
```

**响应示例（失败）**
```json
{
  "code": 10001,
  "message": "邮箱格式不合法",
  "data": null
}
```

---

## 4. 数据模型

### 4.1 通用响应结构

```typescript
interface ApiResponse<T> {
  code: number;        // 业务状态码，0 表示成功
  message: string;     // 状态描述
  data: T | null;      // 业务数据
  timestamp?: string;  // 服务器时间（ISO 8601）
  requestId?: string;  // 请求追踪 ID
}
```

### 4.2 分页响应结构

```typescript
interface PageResponse<T> {
  list: T[];           // 当前页数据
  total: number;       // 总记录数
  page: number;        // 当前页（从 1 开始）
  pageSize: number;    // 每页数量
}
```

### 4.3 业务模型

#### {模型名称}
| 字段名 | 类型 | 必填 | 描述 | 示例 |
|--------|------|------|------|------|
| id | string | 是 | 资源 ID | `u_001` |
| name | string | 是 | 名称 | `Jem` |

---

## 5. 错误码说明

### 5.1 HTTP 状态码

| 状态码 | 含义 | 说明 |
|--------|------|------|
| 200 | OK | 请求成功 |
| 201 | Created | 资源创建成功 |
| 204 | No Content | 操作成功，无返回内容 |
| 400 | Bad Request | 请求参数错误 |
| 401 | Unauthorized | 未认证或 Token 失效 |
| 403 | Forbidden | 无操作权限 |
| 404 | Not Found | 资源不存在 |
| 409 | Conflict | 资源冲突（如重复创建） |
| 422 | Unprocessable Entity | 参数语义错误 |
| 429 | Too Many Requests | 触发限流 |
| 500 | Internal Server Error | 服务器内部错误 |
| 502 | Bad Gateway | 网关错误 |
| 503 | Service Unavailable | 服务不可用 |

### 5.2 业务错误码

| 错误码 | HTTP | 描述 | 解决方案 |
|--------|------|------|----------|
| 0 | 200 | 成功 | - |
| 10001 | 400 | 参数错误 | 检查请求参数格式与必填项 |
| 10002 | 401 | 未授权 | 重新登录获取 Token |
| 10003 | 403 | 权限不足 | 联系管理员申请权限 |
| 10004 | 404 | 资源不存在 | 检查资源 ID 是否正确 |
| 10005 | 409 | 资源已存在 | 检查唯一性约束 |
| 10006 | 429 | 触发限流 | 降低请求频率，等待 `Retry-After` |
| 10500 | 500 | 服务器错误 | 联系运维或查看 requestId |

---

## 6. 调用示例

### 6.1 cURL
```bash
curl -X POST "https://api.example.com/users" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"name": "Jem", "email": "jem@example.com"}'
```

### 6.2 Python（requests）
```python
import requests

response = requests.post(
    "https://api.example.com/users",
    headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    },
    json={"name": "Jem", "email": "jem@example.com"},
    timeout=10,
)
response.raise_for_status()
print(response.json())
```

### 6.3 JavaScript（fetch）
```javascript
const response = await fetch("https://api.example.com/users", {
  method: "POST",
  headers: {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({ name: "Jem", email: "jem@example.com" }),
});
if (!response.ok) {
  throw new Error(`HTTP ${response.status}`);
}
const data = await response.json();
```

### 6.4 Go（net/http）
```go
payload := bytes.NewBufferString(`{"name":"Jem","email":"jem@example.com"}`)
req, _ := http.NewRequest("POST", "https://api.example.com/users", payload)
req.Header.Set("Authorization", "Bearer "+token)
req.Header.Set("Content-Type", "application/json")
resp, err := http.DefaultClient.Do(req)
```

---

## 附录

### A. 相关文档
- [API 变更日志](./API_CHANGELOG.md)

<!--
  在项目实际产出以下文件后，将链接取消注释：
  - [架构文档](../architecture.md)
  - [SDK 仓库](https://github.com/your-org/your-sdk)
-->

### B. 调试工具

<!--
  添加调试相关链接，例如：
  - [Postman Collection](https://example.com/collection.json)
  - [OpenAPI Spec](./openapi.yaml)
  - 在线调试：[Swagger UI](https://example.com/swagger)
-->

