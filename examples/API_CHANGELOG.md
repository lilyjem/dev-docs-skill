# API Changelog

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

## [1.2.0] - 2026-01-15

### 新增接口
- `POST /files/upload` - 文件上传接口
- `POST /files/convert` - PDF 转换接口
- `GET /files/{id}` - 获取文件信息
- `DELETE /files/{id}` - 删除文件
- `PUT /users/{id}/avatar` - 更新用户头像
- `DELETE /users/{id}/avatar` - 删除用户头像

### 接口变更
- `GET /users/{id}` - 响应新增 `avatar` 和 `last_login` 字段

---

## [1.1.0] - 2025-12-20

### 新增接口
- `GET /users` - 获取用户列表（分页）
- `GET /users/{id}` - 获取用户详情
- `PUT /users/{id}` - 更新用户信息
- `DELETE /users/{id}` - 删除用户
- `GET /audit-logs` - 获取操作日志

### 接口变更
- `POST /auth/login` - 响应新增 `user` 对象，包含用户基本信息
- `GET /users` - 新增 `keyword` 查询参数支持搜索

### 废弃接口
- `GET /user/info` - 将在 v2.0 移除，请使用 `GET /users/{id}`

---

## [1.0.0] - 2025-11-01

### 新增接口
- `POST /auth/login` - 用户登录
- `POST /auth/register` - 用户注册
- `POST /auth/logout` - 用户登出
- `POST /auth/refresh` - 刷新 Token
- `GET /user/info` - 获取当前用户信息

---

## 版本号说明

- **主版本号（Major）**：不兼容的 API 修改
- **次版本号（Minor）**：向下兼容的新增功能
- **修订号（Patch）**：向下兼容的问题修正

## 废弃接口说明

被标记为「废弃」的接口仍可使用，但建议迁移到新接口。废弃接口将在指定版本移除。
