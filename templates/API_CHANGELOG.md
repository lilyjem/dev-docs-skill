# API Changelog

<!--
  API 变更日志模板
  作用：单独追踪 API 接口的演进，区别于项目级 CHANGELOG
  原则：
    1. 任何 API 路径、参数、响应结构、行为的变更都必须记录
    2. Breaking Change 必须显式标注 ⚠️ Breaking
    3. 废弃接口需提前一个版本通知，并给出迁移路径
-->

本文件记录 API 接口的所有变更（包括新增、修改、废弃、移除）。

---

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

## [1.0.0] - {YYYY-MM-DD}

### 新增接口
- `POST /api/auth/login` - 用户登录获取 Token
- `GET /api/users/{id}` - 获取用户详情

---

<!-- 变更条目格式参考 -->
<!--
### 新增接口
- `POST /api/users` - 创建用户

### 接口变更
- `GET /api/users` - 新增 status 筛选参数
- ⚠️ Breaking `PUT /api/users/{id}` - 响应字段 `name` 改为 `fullName`

### 废弃接口
- `GET /api/v1/users` - 将在 v2.0 移除，请使用 `GET /api/v2/users`，迁移指南：[链接]

### 移除接口
- `DELETE /api/legacy` - 已于 v1.0 废弃，本版本正式移除
-->
