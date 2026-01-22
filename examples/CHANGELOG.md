# Changelog

本文件记录项目的所有重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Added
- 无

### Changed
- 无

### Fixed
- 无

### Removed
- 无

---

## [1.2.0] - 2026-01-15

### Added
- 新增用户头像上传功能
- 新增批量导出 Excel 功能
- 新增邮件通知服务

### Changed
- 优化 PDF 解析性能，速度提升 30%
- 重构用户认证模块，支持 OAuth2.0

### Fixed
- 修复分页组件在移动端显示异常的问题
- 修复文件上传进度条偶尔卡住的问题

---

## [1.1.0] - 2025-12-20

### Added
- 新增多租户支持
- 新增操作日志审计功能
- 新增数据备份与恢复功能

### Changed
- 升级 Vue 到 3.4 版本
- 优化数据库查询，减少 N+1 查询问题

### Fixed
- 修复登录超时后未正确跳转的问题
- 修复删除用户时关联数据未清理的问题

### Security
- 修复 XSS 漏洞
- 升级依赖库以修复已知安全问题

---

## [1.0.0] - 2025-11-01

### Added
- 初始版本发布
- 用户管理模块（注册、登录、权限）
- PDF 转换功能（支持招商银行、工商银行）
- 管理后台界面
- API 接口文档

---

[Unreleased]: https://github.com/example/project/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/example/project/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/example/project/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/example/project/releases/tag/v1.0.0
