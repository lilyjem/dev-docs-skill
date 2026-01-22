# 示例项目 API 接口文档

## 文档信息

| 属性 | 值 |
|------|-----|
| 版本 | v1.2.0 |
| 最后更新 | 2026-01-15 |
| 基础URL | `https://api.example.com/v1` |

---

## 1. 概述

### 1.1 简介

本文档描述了示例项目的 RESTful API 接口，提供用户管理、文件处理等功能。

### 1.2 基础信息

- **协议**: HTTPS
- **数据格式**: JSON
- **字符编码**: UTF-8

---

## 2. 认证方式

### 2.1 认证类型

JWT (JSON Web Token) Bearer 认证

### 2.2 认证方式

```
Authorization: Bearer {token}
```

### 2.3 获取 Token

调用登录接口 `POST /auth/login` 获取 Token，有效期 24 小时。

---

## 3. 接口列表

### 3.1 用户认证模块

#### 用户登录

| 属性 | 值 |
|------|-----|
| 路径 | `POST /auth/login` |
| 认证 | 否 |
| 描述 | 用户登录并获取访问令牌 |

**请求参数**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| username | body | string | 是 | 用户名 |
| password | body | string | 是 | 密码 |

**请求示例**

```json
{
  "username": "admin",
  "password": "password123"
}
```

**响应参数**

| 参数名 | 类型 | 描述 |
|--------|------|------|
| code | integer | 响应码，0 表示成功 |
| message | string | 响应消息 |
| data.token | string | 访问令牌 |
| data.expires_in | integer | 令牌有效期（秒） |
| data.user | object | 用户信息 |

**响应示例**

```json
{
  "code": 0,
  "message": "登录成功",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 86400,
    "user": {
      "id": 1,
      "username": "admin",
      "role": "admin"
    }
  }
}
```

---

#### 用户注册

| 属性 | 值 |
|------|-----|
| 路径 | `POST /auth/register` |
| 认证 | 否 |
| 描述 | 新用户注册 |

**请求参数**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| username | body | string | 是 | 用户名（3-20字符） |
| password | body | string | 是 | 密码（至少8字符） |
| email | body | string | 是 | 邮箱地址 |

**请求示例**

```json
{
  "username": "newuser",
  "password": "securepass123",
  "email": "user@example.com"
}
```

**响应示例**

```json
{
  "code": 0,
  "message": "注册成功",
  "data": {
    "id": 2,
    "username": "newuser",
    "email": "user@example.com"
  }
}
```

---

### 3.2 用户管理模块

#### 获取用户列表

| 属性 | 值 |
|------|-----|
| 路径 | `GET /users` |
| 认证 | 是 |
| 描述 | 获取用户列表（分页） |

**请求参数**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| page | query | integer | 否 | 页码（默认 1） |
| page_size | query | integer | 否 | 每页数量（默认 20，最大 100） |
| keyword | query | string | 否 | 搜索关键词 |

**响应示例**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 1,
        "username": "admin",
        "email": "admin@example.com",
        "role": "admin",
        "created_at": "2025-01-01T00:00:00Z"
      }
    ],
    "total": 50,
    "page": 1,
    "page_size": 20
  }
}
```

---

#### 获取用户详情

| 属性 | 值 |
|------|-----|
| 路径 | `GET /users/{id}` |
| 认证 | 是 |
| 描述 | 获取指定用户的详细信息 |

**请求参数**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| id | path | integer | 是 | 用户 ID |

**响应示例**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "role": "admin",
    "avatar": "https://example.com/avatar.jpg",
    "created_at": "2025-01-01T00:00:00Z",
    "last_login": "2026-01-15T10:30:00Z"
  }
}
```

---

### 3.3 文件处理模块

#### 上传文件

| 属性 | 值 |
|------|-----|
| 路径 | `POST /files/upload` |
| 认证 | 是 |
| 描述 | 上传文件（支持 PDF、图片） |

**请求参数**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| file | body | file | 是 | 文件（最大 10MB） |
| type | body | string | 是 | 文件类型（pdf/image） |

**响应示例**

```json
{
  "code": 0,
  "message": "上传成功",
  "data": {
    "file_id": "abc123",
    "filename": "document.pdf",
    "size": 1024000,
    "url": "https://cdn.example.com/files/abc123.pdf"
  }
}
```

---

#### 转换 PDF

| 属性 | 值 |
|------|-----|
| 路径 | `POST /files/convert` |
| 认证 | 是 |
| 描述 | 将银行 PDF 对账单转换为结构化数据 |

**请求参数**

| 参数名 | 位置 | 类型 | 必填 | 描述 |
|--------|------|------|------|------|
| file_id | body | string | 是 | 文件 ID |
| bank_type | body | string | 是 | 银行类型（cmb/icbc/ccb/boc） |
| output_format | body | string | 否 | 输出格式（json/excel，默认 json） |

**请求示例**

```json
{
  "file_id": "abc123",
  "bank_type": "cmb",
  "output_format": "excel"
}
```

**响应示例**

```json
{
  "code": 0,
  "message": "转换成功",
  "data": {
    "task_id": "task_xyz789",
    "status": "completed",
    "result_url": "https://cdn.example.com/results/xyz789.xlsx",
    "transactions_count": 150
  }
}
```

---

## 4. 数据模型

### 4.1 User（用户）

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| id | integer | 是 | 用户唯一标识 |
| username | string | 是 | 用户名 |
| email | string | 是 | 邮箱地址 |
| role | string | 是 | 角色（admin/user） |
| avatar | string | 否 | 头像 URL |
| created_at | datetime | 是 | 创建时间 |
| last_login | datetime | 否 | 最后登录时间 |

### 4.2 File（文件）

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| file_id | string | 是 | 文件唯一标识 |
| filename | string | 是 | 原始文件名 |
| size | integer | 是 | 文件大小（字节） |
| type | string | 是 | 文件类型 |
| url | string | 是 | 文件访问 URL |
| uploaded_by | integer | 是 | 上传者用户 ID |
| uploaded_at | datetime | 是 | 上传时间 |

---

## 5. 错误码说明

| 错误码 | HTTP状态码 | 描述 | 解决方案 |
|--------|------------|------|----------|
| 0 | 200 | 成功 | - |
| 10001 | 400 | 请求参数错误 | 检查请求参数格式和取值 |
| 10002 | 401 | 未授权 | 检查 Token 是否有效 |
| 10003 | 403 | 禁止访问 | 检查用户权限 |
| 10004 | 404 | 资源不存在 | 检查请求的资源 ID |
| 10005 | 500 | 服务器内部错误 | 联系技术支持 |
| 20001 | 400 | 用户名已存在 | 更换用户名 |
| 20002 | 400 | 密码格式不正确 | 密码至少8位 |
| 30001 | 400 | 文件格式不支持 | 检查文件格式 |
| 30002 | 400 | 文件大小超限 | 文件不超过10MB |
| 30003 | 400 | 不支持的银行类型 | 检查 bank_type 参数 |

---

## 6. 调用示例

### 6.1 cURL

```bash
# 登录获取 Token
curl -X POST "https://api.example.com/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password123"}'

# 获取用户列表（需要认证）
curl -X GET "https://api.example.com/v1/users?page=1&page_size=20" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 上传文件
curl -X POST "https://api.example.com/v1/files/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@document.pdf" \
  -F "type=pdf"
```

### 6.2 Python

```python
import requests

BASE_URL = "https://api.example.com/v1"

# 登录
response = requests.post(
    f"{BASE_URL}/auth/login",
    json={"username": "admin", "password": "password123"}
)
token = response.json()["data"]["token"]

# 获取用户列表
headers = {"Authorization": f"Bearer {token}"}
response = requests.get(
    f"{BASE_URL}/users",
    headers=headers,
    params={"page": 1, "page_size": 20}
)
users = response.json()["data"]["items"]
print(f"共有 {len(users)} 个用户")

# 上传并转换文件
with open("statement.pdf", "rb") as f:
    response = requests.post(
        f"{BASE_URL}/files/upload",
        headers=headers,
        files={"file": f},
        data={"type": "pdf"}
    )
file_id = response.json()["data"]["file_id"]

# 转换 PDF
response = requests.post(
    f"{BASE_URL}/files/convert",
    headers=headers,
    json={
        "file_id": file_id,
        "bank_type": "cmb",
        "output_format": "excel"
    }
)
result = response.json()["data"]
print(f"转换完成，共 {result['transactions_count']} 条交易记录")
```

### 6.3 JavaScript

```javascript
const BASE_URL = "https://api.example.com/v1";

// 登录
async function login(username, password) {
  const response = await fetch(`${BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password })
  });
  const data = await response.json();
  return data.data.token;
}

// 获取用户列表
async function getUsers(token, page = 1) {
  const response = await fetch(
    `${BASE_URL}/users?page=${page}&page_size=20`,
    {
      headers: { "Authorization": `Bearer ${token}` }
    }
  );
  const data = await response.json();
  return data.data.items;
}

// 使用示例
async function main() {
  const token = await login("admin", "password123");
  const users = await getUsers(token);
  console.log(`共有 ${users.length} 个用户`);
}

main();
```

---

## 附录

### A. 相关文档

- [架构文档](../architecture.md)
- [API 变更日志](./API_CHANGELOG.md)

### B. 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.2.0 | 2026-01-15 | 新增文件上传和转换接口 |
| v1.1.0 | 2025-12-20 | 新增用户管理接口 |
| v1.0.0 | 2025-11-01 | 初始版本 |
