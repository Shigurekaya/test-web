# 智慧企业知识财富库系统 V2.0
## REST API 接口设计说明书

| 项目 | 内容 |
|---|---|
| 系统名称 | 智慧企业知识财富库系统（Enterprise Knowledge Wealth Base） |
| 文档版本 | V2.0 |
| 文档日期 | 2026-10-29 |
| 接口风格 | REST + JSON over HTTP |
| 后端框架 | Flask 3 |
| 数据访问 | SQLAlchemy + SQLite |
| 认证方式 | Flask-Login 服务端会话 Cookie |
| 前端调用 | Vue 3 + Vite，同源 `/api`；开发环境由 Vite 代理到 Flask |
| 主要实现 | `app/api.py`、`app/models.py`、`app/services/rag.py`、`app/services/graph.py` |
| 前端客户端 | `frontend/src/api/client.js` |

> 本文以当前仓库中的 Flask 实现为准，描述 V2.0 前后端分离后的 JSON API。接口路径均以 `/api` 为前缀；所有业务页面通过 `frontend/src/api/client.js` 调用，请求默认携带 `credentials: 'include'`，以便浏览器发送会话 Cookie。

---

## 1. 概述

### 1.1 设计目标

1. **前后端分离**：Vue 3 单页应用负责页面与交互，Flask 负责认证、权限、业务规则与数据持久化。
2. **统一资源命名**：以 `/api` 为前缀，按认证、工作台、文档、收藏、分类、问答、图谱、管理、关于/健康分组。
3. **服务端权威鉴权**：前端隐藏按钮只是体验优化，真正的角色与密级判断在 API/服务层完成。
4. **可追溯**：登录、文档查看/编辑、问答等关键动作写入 `audit_logs`；问答结果保存来源。
5. **可演示、可测试**：接口返回结构稳定，便于 Vue 前端、pytest 契约测试与课程答辩演示。

### 1.2 基础地址与传输

| 项目 | 约定 |
|---|---|
| 基础路径 | `/api` |
| 本地服务地址 | `http://127.0.0.1:5000/api` |
| 前端开发地址 | `http://127.0.0.1:5173`，Vite 将 `/api` 代理到 `http://127.0.0.1:5000` |
| 生产/演示入口 | `start.ps1` 启动后访问 `http://127.0.0.1:5000/ui/` |
| 协议 | HTTP（本机演示）；公网部署应使用 HTTPS |
| 请求编码 | UTF-8 |
| 请求/响应格式 | `application/json`；登录/写接口也兼容表单体，但 Vue 客户端统一发送 JSON |
| 时间格式 | `YYYY-MM-DD HH:MM:SS`，服务端本地时间，不带时区后缀 |
| 字符集 | `app.json.ensure_ascii = False`，中文直接输出，不转义为 `\uXXXX` |

### 1.3 同源、跨域与客户端约定

- 当前 Flask 未单独配置 CORS，Vue 生产构建作为同源静态资源提供服务；开发环境由 Vite 代理 `/api`。
- 前端客户端默认请求头：
  - `Accept: application/json`
  - 有请求体时：`Content-Type: application/json`
  - `credentials: 'include'`
- 因认证依赖会话 Cookie，跨域调用必须同时配置 CORS 凭据与 `SameSite`/Secure Cookie，本项目当前不提供跨域 SDK。
- 所有需要登录的接口在未认证时返回 **401 JSON**，不会重定向到 HTML 登录页。

### 1.4 版本与兼容性

| 项目 | 说明 |
|---|---|
| 当前 API 版本 | V2.0（与 `app/meta.py` 中 `APP_VERSION = "2.0"` 一致） |
| 兼容页面 | 旧 Jinja 页面仍保留；V2.0 Vue 前端以 `/api` 为主边界 |
| 旧接口对照 | UML 图中 `/auth/login`、`/qa/` 为早期页面路由；REST 对应为 `/api/auth/login`、`/api/qa/ask` |
| 健康检查 | 主接口 `/api/health`；兼容入口 `/health`（返回结构略有差异） |
| 版本演进 | 新增字段应保持向后兼容；破坏性变更需提升版本并同步本文与前端客户端 |

### 1.5 接口分组与端点总览

本系统 V2.0 共有 **27 个主要方法/路径组合**（`GET /api` 与 `GET /api/` 视为同一端点别名；兼容 `/health` 不计入 27 个 REST 端点）。

| 分组 | 方法 | 路径 | 用途 | 权限 |
|---|---|---|---|---|
| 系统 | GET | `/api` | API 根信息 | 公开 |
| 系统 | GET | `/api/health` | 健康检查 | 公开 |
| 系统 | GET | `/api/meta` | 元信息、演示账号、枚举标签 | 公开 |
| 认证 | POST | `/api/auth/login` | 登录 | 公开 |
| 认证 | GET | `/api/auth/session` | 查询当前会话 | 公开（匿名返回 null） |
| 认证 | GET | `/api/auth/me` | 当前用户资料 | 已登录 |
| 认证 | POST | `/api/auth/logout` | 退出 | 已登录 |
| 工作台 | GET | `/api/dashboard` | 工作台统计与摘要 | 已登录 |
| 文档 | GET | `/api/documents` | 文档列表/检索/筛选/分页 | 已登录 |
| 文档 | GET | `/api/documents/favorites` | 我的收藏 | 已登录 |
| 文档 | GET | `/api/documents/{id}` | 文档详情 | 已登录且可查看 |
| 文档 | POST | `/api/documents` | 新建文档 | 已登录 |
| 文档 | PUT | `/api/documents/{id}` | 编辑文档 | 作者或管理员 |
| 文档 | DELETE | `/api/documents/{id}` | 删除文档 | 作者或管理员 |
| 收藏 | POST | `/api/documents/{id}/favorite` | 收藏/取消收藏切换 | 已登录且可查看 |
| 分类 | GET | `/api/categories` | 分类列表 | 已登录 |
| 分类 | POST | `/api/categories` | 新增分类 | 管理员 |
| 问答 | GET | `/api/qa` | 问答页初始化、建议与历史 | 已登录 |
| 问答 | POST | `/api/qa/ask` | 提交问题并生成回答 | 已登录 |
| 问答 | GET | `/api/qa/history/{id}` | 问答历史详情 | 本人或管理员 |
| 图谱 | GET | `/api/graph` | 权限裁剪后的图谱数据 | 已登录 |
| 图谱 | GET | `/api/graph/manage` | 图谱维护面板数据 | 管理员 |
| 图谱 | POST | `/api/graph/nodes` | 新增/复用节点 | 管理员 |
| 图谱 | POST | `/api/graph/edges` | 新增关系 | 管理员 |
| 管理 | GET | `/api/admin/users` | 用户列表与文档贡献 | 管理员 |
| 管理 | GET | `/api/admin/audits` | 审计日志列表 | 管理员 |
| 关于 | GET | `/api/about` | 关于页数据与可见范围统计 | 已登录 |

---

## 2. 认证方式

### 2.1 会话认证

系统使用 **Flask-Login 服务端会话**：

1. 客户端调用 `POST /api/auth/login` 提交用户名和密码。
2. 校验通过后，Flask-Login 在响应中设置会话 Cookie。
3. 浏览器后续请求自动携带 Cookie；前端 `fetch` 使用 `credentials: 'include'`。
4. 受保护接口通过 `api_login_required` 检查 `current_user.is_authenticated`。
5. 管理员接口再通过 `api_admin_required` 检查 `current_user.is_admin`。
6. 退出调用 `POST /api/auth/logout`，清除当前会话并写审计。

**认证不是 Bearer Token**：V2.0 未提供 JWT/OAuth Access Token，也不从 `Authorization` 头读取凭证。课程演示依赖同源 Cookie 会话。

### 2.2 登录请求与安全约束

`POST /api/auth/login` 请求体：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `username` | string | 是 | 用户名，首尾空白会被去除 |
| `password` | string | 是 | 密码，不能为空 |
| `remember` | boolean | 否 | 是否启用 Flask-Login 的 remember 机制；缺省为 false |

安全约束：

- 密码使用 Werkzeug 带盐慢哈希存储，数据库中不保存明文（`User.password_hash`）。
- 同一来源 IP 在默认 300 秒窗口内失败达到 8 次后，后续登录请求返回 429 和 `retry_after`；成功登录清零计数。
- 失败登录写入 `audit_logs(action="login_failed")`，成功登录写入 `action="login"`。
- 会话 Cookie 配置为 `HttpOnly=True`、`SameSite=Lax`；生产配置可设置 `SESSION_COOKIE_SECURE`。
- 当前版本未引入独立 CSRF Token；同源部署与 `SameSite=Lax` 是现有边界，若改为跨域或高安全场景应补充 CSRF 防护。

### 2.3 认证相关响应

| 场景 | HTTP | 响应 |
|---|---:|---|
| 登录成功 | 200 | `{"user": UserPayload, "message": "登录成功"}` |
| 用户名或密码错误 | 401 | `{"error": "用户名或密码错误", "code": "INVALID_CREDENTIALS"}` |
| 登录锁定 | 429 | `{"error": "登录失败次数过多，请 N 秒后再试", "retry_after": N}` |
| 未登录访问受保护接口 | 401 | `{"error": "请先登录后再访问", "code": "AUTH_REQUIRED"}` |
| 非管理员访问管理接口 | 403 | `{"error": "需要管理员权限", "code": "FORBIDDEN"}` |
| 会话查询（匿名） | 200 | `{"user": null}` |

---

## 3. 统一响应与错误码

### 3.1 成功响应风格

API 不使用统一的 `{code, data}` 外层，而是按资源返回有语义的对象，例如：

- `{"items": [...], "pagination": {...}}`
- `{"document": {...}, "related": [...], "can_edit": true}`
- `{"answer": "...", "sources": [...], "fragments": [...]}`
- `{"message": "..."}`

这样做的目的是让前端直接读取资源字段；失败时统一使用 `error` 与 `code`（部分限流响应额外包含 `retry_after`）。

### 3.2 错误结构

常规业务错误：

```json
{
  "error": "人类可读错误信息",
  "code": "ERROR_CODE"
}
```

字段校验错误可附加 `fields`：

```json
{
  "error": "参数校验失败",
  "code": "VALIDATION_ERROR",
  "fields": {
    "title": "不能为空"
  }
}
```

### 3.3 错误码表

| `code` | HTTP | 触发条件 | 典型接口 |
|---|---:|---|---|
| `AUTH_REQUIRED` | 401 | 未登录访问受保护接口 | `/api/dashboard`、`/api/documents`、`/api/about` |
| `INVALID_CREDENTIALS` | 401 | 用户名不存在或密码错误 | `POST /api/auth/login` |
| `FORBIDDEN` | 403 | 已登录但无角色/数据权限 | 管理接口、隐藏文档、他人文档编辑 |
| `NOT_FOUND` | 404 | 文档/问答记录/资源不存在 | 文档详情、问答历史 |
| `VALIDATION_ERROR` | 400 | 必填项缺失、分类不存在、分类重名等 | 登录之外的写接口 |
| 无 `code` + `retry_after` | 429 | 登录失败限流锁定 | `POST /api/auth/login` |

### 3.4 HTTP 状态码约定

| 状态码 | 含义 | 本系统用法 |
|---:|---|---|
| 200 | OK | 查询成功、登录成功、更新成功、收藏切换成功 |
| 201 | Created | 新建文档、新建分类、新增图谱节点/边 |
| 400 | Bad Request | 参数/业务校验失败 |
| 401 | Unauthorized | 未登录或凭据错误 |
| 403 | Forbidden | 角色不足或文档/问答越权 |
| 404 | Not Found | 资源不存在 |
| 429 | Too Many Requests | 登录窗口内失败过多 |
| 500 | Internal Server Error | 未预期异常；当前全局错误页主要服务于旧页面，业务 API 正常路径不返回裸堆栈 |

> 说明：未命中路由时 Flask 的全局 404 处理器可能返回旧的 HTML 错误页，这不属于本文定义的业务 API 错误契约；调用已定义接口时，业务错误按上表返回 JSON。

### 3.5 错误示例

**未登录**

```http
GET /api/documents
```

```json
{
  "error": "请先登录后再访问",
  "code": "AUTH_REQUIRED"
}
```

**无权查看机密文档**

```http
GET /api/documents/42
```

```json
{
  "error": "无权查看该文档",
  "code": "FORBIDDEN"
}
```

---

## 4. 分页与筛选约定

### 4.1 文档分页

`GET /api/documents`：

| 参数 | 类型 | 默认 | 约束 | 说明 |
|---|---|---:|---|---|
| `page` | integer | 1 | 最小 1；超过总页数时钳制到最后页 | 页码 |
| `per_page` | integer | 9 | 1～50 | 每页数量 |
| `q` | string | 空 | — | 标题/摘要/正文/标签关键词 |
| `category_id` | integer | 空 | 必须是有效分类才参与过滤 | 分类 |
| `department` | string | 空 | 与文档部门精确匹配 | 部门 |
| `visibility` | string | 空 | `public/internal/secret` | 密级 |
| `sort` | string | `updated` | `updated/title/department` | 排序；存在 `q` 时按相关度排序，`sort` 被忽略 |

`pagination` 对象：

```json
{
  "page": 1,
  "pages": 3,
  "total": 22,
  "per_page": 9
}
```

约定：

- 即使总数为 0，`pages` 也返回 1（后端使用 `max(..., 1)`）；
- `page` 超出范围时自动回退到最后一页；
- 列表只返回当前用户可见的 **已发布** 文档；
- 有关键词时，`rank_documents()` 按标题、标签、摘要、正文和分词重叠加权排序。

### 4.2 审计分页

`GET /api/admin/audits` 固定每页 **25** 条，不提供 `per_page` 参数：

| 参数 | 类型 | 说明 |
|---|---|---|
| `action` | string | 仅接受合法动作代码；非法值忽略 |
| `user` | string | 按用户名模糊匹配 |
| `detail` | string | 按明细模糊匹配 |
| `page` | integer | 最小 1，超出时钳制到最后页 |

### 4.3 非分页列表

以下接口返回完整或固定上限列表，不使用 `pagination`：

- `GET /api/documents/favorites`：当前用户全部可见收藏；
- `GET /api/categories`：全部分类；
- `GET /api/admin/users`：全部用户；
- `GET /api/qa`：最近 20 条本人问答；
- `GET /api/graph/manage`：最近 60 个节点和最近 60 条边；
- `GET /api/graph`：权限裁剪后的完整图谱。

---

## 5. 公共数据结构

### 5.1 UserPayload

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | integer | 用户编号 |
| `username` | string | 登录名 |
| `display_name` | string | 展示姓名 |
| `role` | string | `admin` 或 `employee` |
| `role_label` | string | 中文角色名 |
| `department` | string | 所属部门 |
| `is_admin` | boolean | 是否管理员 |
| `created_at` | string | 创建时间 |

**注意**：响应不包含 `password_hash`。

### 5.2 DocumentPayload

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | integer | 文档编号 |
| `title` | string | 标题 |
| `summary` | string | 摘要；为空时由正文自动截取 |
| `department` | string | 所属部门 |
| `visibility` | string | `public/internal/secret` |
| `visibility_label` | string | 中文密级 |
| `status` | string | `draft/published/archived` |
| `status_label` | string | 中文状态 |
| `version` | string | 版本号 |
| `tags` | string[] | 标签数组 |
| `category_id` | integer/null | 分类编号 |
| `category` | string | 分类名；无分类为“未分类” |
| `author_id` | integer/null | 作者编号 |
| `author` | string | 作者展示名；未知为“未知作者” |
| `created_at` | string | 创建时间 |
| `updated_at` | string | 更新时间 |
| `char_count` | integer | 正文字符数 |
| `chunk_count` | integer | 知识片段数 |
| `is_favorite` | boolean | 当前用户是否已收藏 |
| `content` | string | **仅详情/创建/更新响应包含**，正文 |

### 5.3 QAItemPayload

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | integer | 问答历史编号 |
| `question` | string | 问题 |
| `answer` | string | 回答 |
| `mode` | string | `local` 或 `llm` |
| `mode_label` | string | 中文模式名 |
| `created_at` | string | 提问时间 |
| `sources` | array | 仅历史详情接口包含，解析后的来源数组；解析失败为空数组 |

### 5.4 AuditPayload

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | integer | 审计编号 |
| `user_id` | integer/null | 用户编号 |
| `username` | string | 用户名；未知为“匿名/未知” |
| `action` | string | 动作代码 |
| `action_label` | string | 中文动作名 |
| `detail` | string | 统一明细 |
| `created_at` | string | 操作时间 |

### 5.5 GraphPayload

**普通图谱 `GET /api/graph`**

| 字段 | 类型 | 说明 |
|---|---|---|
| `nodes` | array | 节点数组 |
| `nodes[].id` | integer | 节点编号 |
| `nodes[].name` | string | 节点名 |
| `nodes[].category` | string | 节点类型 |
| `nodes[].symbolSize` | number | ECharts 节点大小 |
| `nodes[].itemStyle` | object | `{"color": "#..."}` |
| `nodes[].document_id` | integer/null | 关联文档 id；非文档节点为 null |
| `links` | array | 边数组 |
| `links[].source` | integer | 起点节点 id |
| `links[].target` | integer | 终点节点 id |
| `links[].relation` | string | 关系名 |
| `categories` | array | `[{"name":"document"}, ...]` |

**管理图谱 `GET /api/graph/manage`**

- `nodes`：`id/name/node_type/description`；
- `edges`：`id/source/target/relation`，其中 `source`、`target` 为节点名称；
- `node_types`：`["document","department","project","keyword","concept"]`。

### 5.6 PaginationPayload

| 字段 | 类型 | 说明 |
|---|---|---|
| `page` | integer | 当前页 |
| `pages` | integer | 总页数，至少 1 |
| `total` | integer | 总记录数 |
| `per_page` | integer | 每页条数 |

---
## 6. 系统、认证与工作台接口

### 6.1 系统接口

#### 6.1.1 `GET /api`（别名 `/api/`）

| 项目 | 说明 |
|---|---|
| 用途 | 返回 API 根信息与健康检查入口 |
| 权限 | 公开 |
| 请求参数 | 无 |
| 成功响应 | `name`、`version`、`description`、`health` |
| 错误 | 正常无业务错误 |

**响应示例**

```json
{
  "name": "智慧企业知识财富库",
  "version": "2.0",
  "description": "企业知识管理、检索问答与关系图 REST API",
  "health": "/api/health"
}
```

#### 6.1.2 `GET /api/health`

| 项目 | 说明 |
|---|---|
| 用途 | 检查 Flask 应用与 SQLite 连通性 |
| 权限 | 公开 |
| 请求参数 | 无 |
| 成功响应 | `status`（`ok`/`degraded`）、`database`（boolean）、`version` |
| 状态码 | 始终按当前实现返回 200；数据库失败时 `status="degraded"`、`database=false` |
| 错误 | 不抛出业务错误 |

**响应示例**

```json
{
  "status": "ok",
  "database": true,
  "version": "2.0"
}
```

#### 6.1.3 `GET /api/meta`

| 项目 | 说明 |
|---|---|
| 用途 | 前端启动时读取系统名称、版本、技术栈、演示账号与枚举标签 |
| 权限 | 公开 |
| 请求参数 | 无 |
| 成功响应字段 | `name`、`name_en`、`version`、`tagline`、`tech_stack`、`features`、`scenarios`、`demo_accounts`、`departments`、`visibility_labels`、`status_labels`、`role_labels` |
| 错误 | 正常无业务错误 |

**主要字段结构**

| 字段 | 类型 | 说明 |
|---|---|---|
| `demo_accounts` | array | `{username,password,label,hint}`，用于登录页演示账号快捷填充 |
| `departments` | string[] | 九个部门 |
| `visibility_labels` | object | `public/internal/secret` 到中文 |
| `status_labels` | object | `draft/published/archived` 到中文 |
| `role_labels` | object | `admin/employee` 到中文 |

#### 6.1.4 兼容健康检查 `GET /health`

| 项目 | 说明 |
|---|---|
| 用途 | 旧页面/启动脚本兼容的健康检查 |
| 权限 | 公开 |
| 成功响应 | `status`、`app`、`version`、`database` |
| 与 `/api/health` 差异 | 多返回 `app` 字段；两者都执行 `SELECT 1` |

```json
{
  "status": "ok",
  "app": "智慧企业知识财富库",
  "version": "2.0",
  "database": true
}
```

### 6.2 认证接口

#### 6.2.1 `POST /api/auth/login`

| 项目 | 说明 |
|---|---|
| 用途 | 登录并建立服务端会话 |
| 权限 | 公开 |
| 请求体 | `username`（必填）、`password`（必填）、`remember`（可选 boolean） |
| 成功响应 | 200：`user`（UserPayload）、`message` |
| 失败响应 | 401 `INVALID_CREDENTIALS`；429 带 `retry_after` |
| 审计 | 成功写 `login`，失败写 `login_failed` |
| 限流 | 默认同 IP 300 秒内 8 次失败后锁定，成功清零 |

**请求示例**

```json
{
  "username": "admin",
  "password": "admin123",
  "remember": false
}
```

**成功响应示例**

```json
{
  "user": {
    "id": 1,
    "username": "admin",
    "display_name": "系统管理员",
    "role": "admin",
    "role_label": "管理员",
    "department": "综合部",
    "is_admin": true,
    "created_at": "2026-09-15 10:00:00"
  },
  "message": "登录成功"
}
```

**失败响应示例**

```json
{
  "error": "用户名或密码错误",
  "code": "INVALID_CREDENTIALS"
}
```

**锁定响应示例**

```json
{
  "error": "登录失败次数过多，请 183 秒后再试",
  "retry_after": 183
}
```

#### 6.2.2 `GET /api/auth/session`

| 项目 | 说明 |
|---|---|
| 用途 | 页面启动时查询当前登录用户；匿名不是错误 |
| 权限 | 公开 |
| 请求参数 | 无 |
| 成功响应 | `{"user": UserPayload}` 或 `{"user": null}` |
| 错误 | 正常无业务错误 |

#### 6.2.3 `GET /api/auth/me`

| 项目 | 说明 |
|---|---|
| 用途 | 获取当前登录用户资料 |
| 权限 | 已登录 |
| 请求参数 | 无 |
| 成功响应 | `{"user": UserPayload}` |
| 错误 | 401 `AUTH_REQUIRED` |

#### 6.2.4 `POST /api/auth/logout`

| 项目 | 说明 |
|---|---|
| 用途 | 写退出审计、清除当前会话 |
| 权限 | 已登录 |
| 请求体 | 无 |
| 成功响应 | `{"message": "已退出登录"}` |
| 错误 | 401 `AUTH_REQUIRED` |
| 副作用 | 新增 `logout` 审计 |

### 6.3 工作台接口

#### 6.3.1 `GET /api/dashboard`

| 项目 | 说明 |
|---|---|
| 用途 | 返回当前用户工作台统计、图表、最近文档、最近问答、快捷问题和管理员审计摘要 |
| 权限 | 已登录 |
| 请求参数 | 无 |
| 数据范围 | 文档/收藏/问答/图表按当前用户权限；图谱节点/边为结构总量；审计摘要仅管理员 |
| 错误 | 401 `AUTH_REQUIRED` |

**响应结构**

| 字段 | 类型 | 说明 |
|---|---|---|
| `stats.visible_documents` | integer | 当前用户可见且已发布的文档数 |
| `stats.favorites` | integer | 当前用户收藏数（数据库收藏总数） |
| `stats.qa_total` | integer | 当前用户问答总数 |
| `stats.qa_week` | integer | 当前用户近 7 天问答数 |
| `stats.nodes` | integer | 图谱节点总数 |
| `stats.edges` | integer | 图谱边总数 |
| `charts.departments` | array | `[{"name":"人事部","value":3}]`，按可见文档统计 |
| `charts.categories` | array | `[{"name":"人事制度","value":3}]`，最多 8 类 |
| `recent_documents` | array | 最近 6 篇可见文档（DocumentPayload） |
| `recent_qa` | array | 当前用户最近 6 条问答（不含 sources） |
| `recent_logs` | array | 管理员最近 8 条审计；普通员工为空数组 |
| `quick_questions` | string[] | 4 个快捷问题 |

**响应示例**

```json
{
  "stats": {
    "visible_documents": 35,
    "favorites": 4,
    "qa_total": 46,
    "qa_week": 0,
    "nodes": 154,
    "edges": 222
  },
  "charts": {
    "departments": [
      {"name": "人事部", "value": 4},
      {"name": "财务部", "value": 3}
    ],
    "categories": [
      {"name": "人事制度", "value": 4}
    ]
  },
  "recent_documents": [],
  "recent_qa": [],
  "recent_logs": [],
  "quick_questions": [
    "员工年假有几天？",
    "差旅住宿标准是多少？",
    "加班怎么补偿？",
    "采购超过两万元要找谁审批？"
  ]
}
```

---
## 7. 文档接口

### 7.1 权限规则总表

| 操作 | 普通员工 | 管理员 | 数据/状态限制 |
|---|---|---|---|
| 列表/检索 | 可 | 可 | 只返回已发布且可见文档 |
| 查看详情 | 可 | 可 | 密级权限；草稿/归档仅作者或管理员 |
| 新建 | 可 | 可 | 标题和正文必填 |
| 编辑 | 仅本人文档 | 全部文档 | 标题和正文必填 |
| 删除 | 仅本人文档 | 全部文档 | 删除后不可恢复，并清理图谱 |
| 收藏 | 可 | 可 | 只能收藏通过 `can_view_document()` 密级判定的文档；接口不额外校验发布状态 |

**密级规则**：

- `public`：所有已登录用户可查看；
- `internal`：所有已登录用户可查看；
- `secret`：仅管理员、同部门用户或文档作者可查看；
- 列表与问答只使用 `published` 文档；
- 详情允许作者/管理员查看草稿或归档，但必须先通过密级判断。

### 7.2 `GET /api/documents`

| 项目 | 说明 |
|---|---|
| 用途 | 文档列表、关键词检索、筛选、排序与分页 |
| 权限 | 已登录 |
| 查询参数 | `q`、`category_id`、`department`、`visibility`、`sort`、`page`、`per_page` |
| 成功响应 | `items`、`categories`、`pagination`、`filters`、`departments` |
| 失败 | 401 `AUTH_REQUIRED` |

**查询参数**

| 参数 | 类型 | 默认 | 说明 |
|---|---|---:|---|
| `q` | string | 空 | 关键词；使用 jieba 与加权规则排序 |
| `category_id` | integer | 空 | 分类过滤 |
| `department` | string | 空 | 部门精确过滤 |
| `visibility` | string | 空 | `public/internal/secret` |
| `sort` | string | `updated` | `updated/title/department`；有 `q` 时忽略 |
| `page` | integer | 1 | 页码，最小 1 |
| `per_page` | integer | 9 | 1～50 |

**响应字段**

| 字段 | 类型 | 说明 |
|---|---|---|
| `items` | DocumentPayload[] | 当前页文档，不含正文 |
| `categories` | array | 全部分类：`id/name/description` |
| `pagination` | PaginationPayload | 分页信息 |
| `filters` | object | 回显 `q/category_id/department/visibility/sort` |
| `departments` | string[] | 九个部门常量 |

**响应示例**

```json
{
  "items": [
    {
      "id": 12,
      "title": "员工年休假管理办法",
      "summary": "员工依法享有年休假……",
      "department": "人事部",
      "visibility": "internal",
      "visibility_label": "内部",
      "status": "published",
      "status_label": "已发布",
      "version": "1.0",
      "tags": ["年假", "人事", "制度"],
      "category_id": 2,
      "category": "人事制度",
      "author_id": 2,
      "author": "人事专员",
      "created_at": "2026-09-15 10:00:00",
      "updated_at": "2026-09-20 15:30:00",
      "char_count": 1280,
      "chunk_count": 4,
      "is_favorite": false
    }
  ],
  "categories": [
    {"id": 2, "name": "人事制度", "description": "员工关系与假期"}
  ],
  "pagination": {"page": 1, "pages": 1, "total": 1, "per_page": 9},
  "filters": {"q": "年假", "category_id": null, "department": "", "visibility": "", "sort": "updated"},
  "departments": ["综合部", "人事部", "财务部", "信息部", "产品部", "运营部", "市场部", "法务部", "技术部"]
}
```

### 7.3 `GET /api/documents/favorites`

| 项目 | 说明 |
|---|---|
| 用途 | 返回当前用户收藏的、且密级判定仍可查看的文档 |
| 权限 | 已登录 |
| 请求参数 | 无 |
| 成功响应 | `items`：DocumentPayload[]，`is_favorite=true`；按收藏时间倒序 |
| 分页 | 不分页 |
| 失败 | 401 `AUTH_REQUIRED` |

**说明**：如果文档后来变为不可见或作者/管理员删除，收藏记录可能由 ORM 级联清理；接口还会用 `can_view_document()` 二次过滤，避免返回当前已无权查看的文档。收藏列表当前**不额外过滤** `draft/archived` 状态：若用户已收藏某草稿/归档文档，它仍可能出现在收藏列表中。

### 7.4 `GET /api/documents/{id}`

| 项目 | 说明 |
|---|---|
| 用途 | 获取文档详情、正文、相关文档和编辑权限标记 |
| 权限 | 已登录；密级判定通过，且文档已发布或当前用户为作者/管理员 |
| 路径参数 | `id`：integer 文档编号 |
| 成功响应 | `document`（DocumentPayload + `content`）、`related`、`can_edit` |
| 失败 | 401；403 `FORBIDDEN`；404 `NOT_FOUND` |
| 副作用 | 首次/2 分钟内未记录时写入 `view_document` 审计（相同用户、同一文档 2 分钟内去重） |

**响应字段**

| 字段 | 类型 | 说明 |
|---|---|---|
| `document` | object | 文档详情，包含 `content` 与 `is_favorite` |
| `related` | DocumentPayload[] | 最多 4 篇相关文档，按同分类/同部门/标签重叠评分 |
| `can_edit` | boolean | 当前用户是否作者或管理员 |

**错误顺序**：先判断文档是否存在（404），再判断密级可见性（403），最后判断草稿/归档状态（403）。

### 7.5 `POST /api/documents`

| 项目 | 说明 |
|---|---|
| 用途 | 新建文档，并自动建立知识片段与图谱关系 |
| 权限 | 已登录 |
| 请求体 | JSON（也兼容表单） |
| 成功响应 | 201：`document`（含 content）、`message="文档已创建"` |
| 失败 | 400 `VALIDATION_ERROR`；401 `AUTH_REQUIRED` |

**请求字段**

| 字段 | 类型 | 必填 | 默认/约束 | 说明 |
|---|---|---|---|---|
| `title` | string | 是 | 非空、最长 200 | 标题 |
| `content` | string | 是 | 非空 | 正文 |
| `summary` | string | 否 | 空则自动截取，最多 500 | 摘要 |
| `category_id` | integer/null | 否 | 必须存在 | 分类 |
| `department` | string | 否 | 必须是九部门之一，否则使用当前账号部门 | 所属部门 |
| `visibility` | string | 否 | 默认 `internal`；非法值回退 | 密级 |
| `status` | string | 否 | 默认 `published`；非法值回退 | 状态 |
| `version` | string | 否 | 默认 `1.0` | 版本 |
| `tags` | string[] 或 string | 否 | 数组或逗号分隔字符串 | 标签 |

**请求示例**

```json
{
  "title": "API 自动化测试文档",
  "content": "这是通过 REST API 创建的测试正文。\n\n第二段用于验证知识切分。",
  "summary": "API 测试摘要",
  "category_id": 1,
  "department": "综合部",
  "visibility": "internal",
  "status": "published",
  "version": "1.0",
  "tags": ["API", "测试"]
}
```

**后置处理顺序**：

1. 写入 `documents`；
2. `rebuild_chunks_for_document()` 重建 `knowledge_chunks`；
3. `sync_document_graph()` 创建/更新文档节点、部门节点、分类节点、关键词节点与边；
4. 写入 `create_document` 审计；
5. 返回带正文的文档对象。

### 7.6 `PUT /api/documents/{id}`

| 项目 | 说明 |
|---|---|
| 用途 | 编辑文档；保存后重建片段与图谱 |
| 权限 | 作者或管理员 |
| 路径参数 | `id`：文档编号 |
| 请求体 | 与新建相同；`title`、`content` 必填 |
| 成功响应 | 200：`document`（含 content）、`message="文档已更新"` |
| 失败 | 401；403 `FORBIDDEN`；404 `NOT_FOUND`；400 `VALIDATION_ERROR` |
| 审计 | `edit_document` |

**说明**：

- 本接口为**全量更新语义**：`title`、`content` 必须重新提交，未提交的密级、状态等字段按服务端默认规则处理；Vue 编辑器会提交完整表单。
- 非作者且非管理员返回 403“只能编辑自己创建的文档”；
- 字段未提供时，部门使用原值/当前账号部门，密级/状态非法值回退；
- 标签支持数组或逗号字符串；数组会被拼接为逗号分隔存储；
- 更新后 `updated_at` 由 ORM 自动刷新；
- 片段重建先删除旧片段，再生成新片段。

### 7.7 `DELETE /api/documents/{id}`

| 项目 | 说明 |
|---|---|
| 用途 | 删除文档及关联图谱节点/边 |
| 权限 | 作者或管理员 |
| 路径参数 | `id`：文档编号 |
| 请求体 | 无 |
| 成功响应 | `{"message": "文档已删除"}` |
| 失败 | 401；403 `FORBIDDEN`；404 `NOT_FOUND` |
| 审计 | `delete_document` |

**说明**：删除前调用 `remove_document_graph(doc)` 清理文档节点及连接边；SQLAlchemy 关系级联删除知识片段和收藏。操作不可恢复。

### 7.8 `POST /api/documents/{id}/favorite`

| 项目 | 说明 |
|---|---|
| 用途 | 切换收藏状态 |
| 权限 | 已登录且通过密级判定（`can_view_document`） |
| 路径参数 | `id`：文档编号 |
| 请求体 | 无 |
| 成功响应 | `{"is_favorite": true/false, "message": "已收藏"/"已取消收藏"}` |
| 失败 | 401；403 `FORBIDDEN`；404 `NOT_FOUND` |
| 约束 | `(user_id, document_id)` 唯一，防止重复收藏 |

**响应示例**

```json
{
  "is_favorite": true,
  "message": "已收藏"
}
```

### 7.9 收藏接口汇总

| 接口 | 方法 | 权限 | 请求 | 响应 |
|---|---|---|---|---|
| `/api/documents/favorites` | GET | 已登录 | 无 | `{"items": DocumentPayload[]}`，按收藏时间倒序，仅返回 `can_view_document()` 为真的文档；不额外过滤状态 |
| `/api/documents/{id}/favorite` | POST | 已登录且通过密级判定 | 无 | `{"is_favorite": boolean, "message": string}`，切换收藏状态；不额外校验状态 |

> 收藏以当前用户为隔离边界；管理员也不能代替其他用户收藏。表 `favorites` 对 `(user_id, document_id)` 有唯一约束。

---

## 8. 分类接口

### 8.1 `GET /api/categories`

| 项目 | 说明 |
|---|---|
| 用途 | 获取分类列表，供文档筛选和编辑表单使用 |
| 权限 | 已登录 |
| 请求参数 | 无 |
| 成功响应 | `items`：`id`、`name`、`description`、`document_count` |
| 失败 | 401 `AUTH_REQUIRED` |

**统计口径**：`document_count` 按 `documents.category_id` 全库计数，包含草稿/归档和当前用户不可见文档；它用于分类管理语境，不等同于工作台的“可见文档”统计。前端若不需要该口径，应只展示分类名称。

**响应示例**

```json
{
  "items": [
    {
      "id": 1,
      "name": "人事制度",
      "description": "考勤、假期、入离职",
      "document_count": 5
    }
  ]
}
```

### 8.2 `POST /api/categories`

| 项目 | 说明 |
|---|---|
| 用途 | 新增文档分类 |
| 权限 | 管理员 |
| 请求体 | `name`（必填，唯一）、`description`（可选） |
| 成功响应 | 201：`id`、`name`、`message="分类已添加"` |
| 失败 | 400 `VALIDATION_ERROR`（名称为空/重名）；401；403 `FORBIDDEN` |

**请求示例**

```json
{
  "name": "客户服务",
  "description": "客服话术与服务标准"
}
```

**响应示例**

```json
{
  "id": 7,
  "name": "客户服务",
  "message": "分类已添加"
}
```

> 当前 API 未提供分类删除/改名端点；文档的 `category_id` 可为空表示“未分类”。

---
## 9. 智能问答接口

### 9.1 问答数据流

1. 前端 `POST /api/qa/ask` 提交问题；
2. 服务端通过 `searchable_documents(current_user)` 取可见且已发布的文档；
3. 只加载这些文档的 `knowledge_chunks`；
4. jieba 分词 + 关键词 + 标题/短语评分，取 Top-K；同一文档最多 2 个片段；
5. 无 API Key 时 `build_local_answer()` 生成本地摘要；有 Key 时 `call_llm_answer()` 调用 OpenAI 兼容 Chat Completions；
6. 保存 `qa_history`，写入 `audit_logs(action="ask_qa")`；
7. 返回 `answer`、`mode`、`sources`、`fragments`、`history_id`。

### 9.2 `GET /api/qa`

| 项目 | 说明 |
|---|---|
| 用途 | 问答页初始化：建议问题、快捷问题、LLM 模式标记、最近历史 |
| 权限 | 已登录 |
| 请求参数 | 无 |
| 成功响应 | `suggestions`、`quick_questions`、`llm_enabled`、`history` |
| 失败 | 401 `AUTH_REQUIRED` |
| 历史数量 | 当前用户最近 20 条 |

**响应字段**

| 字段 | 类型 | 说明 |
|---|---|---|
| `suggestions` | string[] | 12 个建议问题 |
| `quick_questions` | string[] | 4 个快捷问题 |
| `llm_enabled` | boolean | 是否配置 `OPENAI_API_KEY` |
| `history` | QAItemPayload[] | 不含 `sources`，用于侧栏历史列表 |

### 9.3 `POST /api/qa/ask`

| 项目 | 说明 |
|---|---|
| 用途 | 提交问题并生成带来源的回答 |
| 权限 | 已登录；检索范围由当前用户权限决定 |
| 请求体 | `question`（必填，非空） |
| 成功响应 | 200：`answer`、`mode`、`mode_label`、`history_id`、`sources`、`fragments` |
| 失败 | 400 `VALIDATION_ERROR`“问题不能为空”；401 `AUTH_REQUIRED` |
| 副作用 | 新增 `qa_history`；新增 `ask_qa` 审计 |

**请求示例**

```json
{
  "question": "员工年假有几天？"
}
```

**响应结构**

| 字段 | 类型 | 说明 |
|---|---|---|
| `answer` | string | 回答正文 |
| `mode` | string | `local` 或 `llm` |
| `mode_label` | string | “本地检索”/“大模型生成” |
| `history_id` | integer | 新增问答历史编号 |
| `sources` | array | 按文档合并的来源 |
| `fragments` | array | 原始命中片段 |

**`sources[]` 结构**

| 字段 | 类型 | 说明 |
|---|---|---|
| `document_id` | integer | 来源文档编号 |
| `title` | string | 文档标题 |
| `department` | string | 部门 |
| `score` | number | 本文档最高相关度 |
| `fragments` | array | 本文件命中的片段对象 |

**`fragments[]` 结构**

| 字段 | 类型 | 说明 |
|---|---|---|
| `score` | number | 片段相关度 |
| `chunk_id` | integer | 片段编号 |
| `document_id` | integer | 文档编号 |
| `title` | string | 文档标题 |
| `content` | string | 片段正文摘要/片段原文 |
| `department` | string | 部门 |
| `fragment_no` | integer | 在结果中的第几个片段 |
| `fragment_total` | integer | 该文档命中片段总数 |

**响应示例**

```json
{
  "answer": "根据企业知识库检索，针对「员工年假有几天？」整理如下：……",
  "mode": "local",
  "mode_label": "本地检索",
  "history_id": 15,
  "sources": [
    {
      "document_id": 12,
      "title": "员工年休假管理办法",
      "department": "人事部",
      "score": 18.6,
      "fragments": [
        {
          "score": 18.6,
          "chunk_id": 44,
          "document_id": 12,
          "title": "员工年休假管理办法",
          "content": "工作满一年不满十年的员工，年休假为 5 天……",
          "department": "人事部",
          "fragment_no": 1,
          "fragment_total": 1
        }
      ]
    }
  ],
  "fragments": [
    {
      "score": 18.6,
      "chunk_id": 44,
      "document_id": 12,
      "title": "员工年休假管理办法",
      "content": "工作满一年不满十年的员工，年休假为 5 天……",
      "department": "人事部",
      "fragment_no": 1,
      "fragment_total": 1
    }
  ]
}
```

> 示例为展示结构，实际 `fragments` 与 `sources[].fragments` 均包含命中片段。若没有命中，`sources` 与 `fragments` 为空数组，`answer` 会明确说明未检索到相关内容。

### 9.4 `GET /api/qa/history/{id}`

| 项目 | 说明 |
|---|---|
| 用途 | 查看单条问答历史详情及来源 |
| 权限 | 记录本人或管理员 |
| 路径参数 | `id`：问答历史编号 |
| 成功响应 | `item`：QAItemPayload，包含解析后的 `sources` |
| 失败 | 401；403 `FORBIDDEN`“无权查看该问答记录”；404 `NOT_FOUND` |
| 来源结构 | `qa_history.sources` 保存的是 `[{document_id,title,score}]`；历史详情只返回这些字段，不返回当时片段全文 |

**响应示例**

```json
{
  "item": {
    "id": 15,
    "question": "员工年假有几天？",
    "answer": "根据企业知识库检索……",
    "mode": "local",
    "mode_label": "本地检索",
    "created_at": "2026-10-29 10:20:00",
    "sources": [
      {"document_id": 12, "title": "员工年休假管理办法", "score": 18.6}
    ]
  }
}
```

> 实时问答响应（`POST /api/qa/ask`）和历史详情（`GET /api/qa/history/{id}`）的 `sources` 结构不同：前者包含 `department` 与 `fragments`，后者是持久化的精简来源。

---

## 10. 知识图谱接口

### 10.1 图谱权限与裁剪规则

- 普通图谱从当前用户可见文档节点出发；
- 只把与这些文档直接相连的节点/边纳入结果；
- 不展示仅由当前用户不可见文档连接的概念/关键词节点；
- 管理员维护接口不受普通图谱裁剪限制，可查看最近 60 个节点/边；
- 文档新增/更新时由 `sync_document_graph()` 自动同步；删除时由 `remove_document_graph()` 清理。

### 10.2 `GET /api/graph`

| 项目 | 说明 |
|---|---|
| 用途 | 普通用户浏览权限裁剪后的 ECharts 力导向图数据 |
| 权限 | 已登录 |
| 请求参数 | 无 |
| 成功响应 | `nodes`、`links`、`categories` |
| 失败 | 401 `AUTH_REQUIRED` |
| 节点类型 | document、department、project、keyword、concept |

**节点/边结构**：见 5.5 GraphPayload。`links.source` 与 `links.target` 是节点 id，不是名称。

### 10.3 `GET /api/graph/manage`

| 项目 | 说明 |
|---|---|
| 用途 | 管理员打开“维护图谱”弹窗，读取最近节点、边和可选节点类型 |
| 权限 | 管理员 |
| 请求参数 | 无 |
| 成功响应 | `nodes`（最近 60）、`edges`（最近 60）、`node_types` |
| 失败 | 401；403 `FORBIDDEN`“需要管理员权限” |

**响应示例**

```json
{
  "nodes": [
    {"id": 1, "name": "文档:员工年休假管理办法", "node_type": "document", "description": "员工休假制度"}
  ],
  "edges": [
    {"id": 1, "source": "文档:员工年休假管理办法", "target": "人事部", "relation": "属于"}
  ],
  "node_types": ["document", "department", "project", "keyword", "concept"]
}
```

### 10.4 `POST /api/graph/nodes`

| 项目 | 说明 |
|---|---|
| 用途 | 新增或复用概念/项目等节点 |
| 权限 | 管理员 |
| 请求体 | `name`（必填）、`node_type`（可选，默认 `concept`）、`description`（可选） |
| 成功响应 | 201：`id`、`name`、`message="节点已添加"` |
| 失败 | 400 `VALIDATION_ERROR`“节点名称不能为空”；401；403 |
| 去重 | 按节点名称复用，已存在时返回已有节点 id，不新增重复名称 |

**请求示例**

```json
{
  "name": "数字化转型",
  "node_type": "concept",
  "description": "企业数字化相关概念"
}
```

**响应示例**

```json
{
  "id": 22,
  "name": "数字化转型",
  "message": "节点已添加"
}
```

### 10.5 `POST /api/graph/edges`

| 项目 | 说明 |
|---|---|
| 用途 | 新增节点关系；若起点/终点不存在则按 `concept` 类型自动创建 |
| 权限 | 管理员 |
| 请求体 | `source_name`（必填）、`target_name`（必填）、`relation`（可选，默认“关联”） |
| 成功响应 | 201：`{"message": "关系已添加"}` |
| 失败 | 400 `VALIDATION_ERROR`“起点和终点名称不能为空”；401；403 |
| 去重 | 同起点、终点、关系名的边不重复插入 |

**请求示例**

```json
{
  "source_name": "数字化转型",
  "target_name": "信息部",
  "relation": "由部门推进"
}
```

**响应示例**

```json
{
  "message": "关系已添加"
}
```

> 当前 API 未提供图谱节点/边的删除与编辑端点；管理员可新增，自动同步负责文档相关节点和边。

---
## 11. 管理接口

### 11.1 `GET /api/admin/users`

| 项目 | 说明 |
|---|---|
| 用途 | 管理员查看全部账号、角色、部门、创建时间与文档贡献 |
| 权限 | 管理员 |
| 请求参数 | 无 |
| 成功响应 | `items`、`summary` |
| 失败 | 401 `AUTH_REQUIRED`；403 `FORBIDDEN`“需要管理员权限” |

**`items[]` 字段**

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | integer | 用户编号 |
| `username` | string | 登录名 |
| `display_name` | string | 展示姓名 |
| `role` | string | `admin`/`employee` |
| `role_label` | string | 中文角色 |
| `department` | string | 部门 |
| `is_admin` | boolean | 是否管理员 |
| `created_at` | string | 创建时间 |
| `document_count` | integer | 该用户作为作者的文档总数（全库口径） |

**`summary` 字段**

| 字段 | 类型 | 说明 |
|---|---|---|
| `total` | integer | 全部账号数 |
| `admins` | integer | 管理员数 |
| `employees` | integer | 普通员工数 |

**响应示例**

```json
{
  "items": [
    {
      "id": 1,
      "username": "admin",
      "display_name": "系统管理员",
      "role": "admin",
      "role_label": "管理员",
      "department": "综合部",
      "is_admin": true,
      "created_at": "2026-09-15 10:00:00",
      "document_count": 7
    }
  ],
  "summary": {"total": 22, "admins": 1, "employees": 21}
}
```

### 11.2 `GET /api/admin/audits`

| 项目 | 说明 |
|---|---|
| 用途 | 管理员按动作/用户/明细筛选审计日志，按时间倒序分页 |
| 权限 | 管理员 |
| 查询参数 | `action`、`user`、`detail`、`page` |
| 成功响应 | `items`、`pagination`、`action_stats`、`actions` |
| 失败 | 401 `AUTH_REQUIRED`；403 `FORBIDDEN`“需要管理员权限” |
| 每页 | 固定 25 条 |

**查询参数**

| 参数 | 类型 | 说明 |
|---|---|---|
| `action` | string | 仅合法动作代码参与过滤；非法值忽略 |
| `user` | string | 用户名模糊匹配，联表 `users` |
| `detail` | string | 明细模糊匹配 |
| `page` | integer | 最小 1；超出时钳制到最后页 |

**响应字段**

| 字段 | 类型 | 说明 |
|---|---|---|
| `items` | AuditPayload[] | 当前页日志 |
| `pagination` | PaginationPayload | `per_page` 固定 25 |
| `action_stats` | object | 全库按动作代码计数，不受当前筛选影响 |
| `actions` | array | `[{value,label}]`，合法动作筛选项 |

**动作代码与中文**

| `action` | 中文 |
|---|---|
| `login` | 登录 |
| `login_failed` | 登录失败 |
| `logout` | 退出 |
| `view_document` | 查看文档 |
| `create_document` | 创建文档 |
| `edit_document` | 编辑文档 |
| `delete_document` | 删除文档 |
| `ask_qa` | 智能问答 |

**响应示例**

```json
{
  "items": [
    {
      "id": 88,
      "user_id": 3,
      "username": "hr",
      "action": "view_document",
      "action_label": "查看文档",
      "detail": "查看文档 #12 《员工年休假管理办法》",
      "created_at": "2026-10-29 10:30:00"
    }
  ],
  "pagination": {"page": 1, "pages": 4, "total": 88, "per_page": 25},
  "action_stats": {"login": 20, "login_failed": 2, "view_document": 45, "ask_qa": 21},
  "actions": [
    {"value": "login", "label": "登录"},
    {"value": "login_failed", "label": "登录失败"}
  ]
}
```

> `action_stats` 是管理页顶部的全量统计，不会随当前筛选条件改变；分页列表本身才受筛选影响。

---

## 12. 关于与健康接口表

### 12.1 `GET /api/about`

| 项目 | 说明 |
|---|---|
| 用途 | 关于页展示应用元信息、技术栈、核心能力、典型场景和统计 |
| 权限 | 已登录 |
| 请求参数 | 无 |
| 成功响应 | `app`、`stats`、`scope` |
| 失败 | 401 `AUTH_REQUIRED` |
| 统计口径 | 文档/片段为当前用户可见范围；节点/边为结构全量；问答为本人 |

**`app` 字段**

| 字段 | 类型 | 说明 |
|---|---|---|
| `name` | string | 系统中文名 |
| `name_en` | string | 英文名 |
| `version` | string | V2.0 |
| `tagline` | string | 一句话定位 |
| `tech_stack` | string | 技术栈文本 |
| `features` | string[] | 核心能力列表 |
| `scenarios` | string[] | 典型场景列表 |

**`stats` 字段**

| 字段 | 类型 | 说明 |
|---|---|---|
| `documents` | integer | 当前用户可见已发布文档数 |
| `chunks` | integer | 可见文档对应的片段数 |
| `nodes` | integer | 全量图谱节点数 |
| `edges` | integer | 全量图谱边数 |
| `qa` | integer | 当前用户问答总数 |

**响应示例**

```json
{
  "app": {
    "name": "智慧企业知识财富库",
    "name_en": "Enterprise Knowledge Wealth Base",
    "version": "2.0",
    "tagline": "企业知识管理 · 检索问答 · 关系图",
    "tech_stack": "Vue 3 · Vite · Flask REST API · SQLAlchemy · SQLite · ECharts · jieba",
    "features": ["按部门与密级管控的制度/手册归档"],
    "scenarios": ["人事：查年假天数、加班补偿、入职首周事项"]
  },
  "stats": {
    "documents": 35,
    "chunks": 38,
    "nodes": 154,
    "edges": 222,
    "qa": 46
  },
  "scope": "本人可见范围"
}
```

### 12.2 关于/健康接口速查表

| 接口 | 方法 | 权限 | 主要响应 | 说明 |
|---|---|---|---|---|
| `/api/about` | GET | 已登录 | `app/stats/scope` | 关于页数据，统计口径随权限 |
| `/api/health` | GET | 公开 | `status/database/version` | REST 健康检查 |
| `/health` | GET | 公开 | `status/app/version/database` | 兼容旧页面/启动脚本 |

### 12.3 健康检查语义

| `status` | `database` | 含义 |
|---|---|---|
| `ok` | true | 应用可响应，数据库 `SELECT 1` 成功 |
| `degraded` | false | 应用可响应，但数据库检查失败 |

> 当前实现无论数据库是否成功都返回 HTTP 200，以响应体区分 `ok/degraded`。监控系统应读取 `database` 字段，而不是只看 HTTP 状态码。

---

## 13. 权限矩阵

### 13.1 角色级权限

| 能力 | 匿名 | 普通员工 | 管理员 |
|---|---|---|---|
| 查看元信息/健康 | 可 | 可 | 可 |
| 登录/查询会话 | 可 | 可 | 可 |
| 退出 | 不可 | 可 | 可 |
| 工作台 | 不可 | 可 | 可 |
| 文档列表/检索 | 不可 | 可 | 可 |
| 文档详情 | 不可 | 可见文档 | 全部文档 |
| 新建文档 | 不可 | 可 | 可 |
| 编辑/删除文档 | 不可 | 仅本人 | 全部 |
| 收藏/取消收藏 | 不可 | 可（通过密级判定） | 可（通过密级判定） |
| 分类列表 | 不可 | 可 | 可 |
| 新增分类 | 不可 | 不可 | 可 |
| 问答 | 不可 | 可 | 可 |
| 问答历史 | 不可 | 仅本人 | 全部 |
| 浏览图谱 | 不可 | 可（裁剪） | 可（裁剪） |
| 维护图谱 | 不可 | 不可 | 可 |
| 用户列表 | 不可 | 不可 | 可 |
| 审计日志 | 不可 | 不可 | 可 |
| 关于页 | 不可 | 可 | 可 |

### 13.2 文档数据级权限

| 文档密级/状态 | 普通员工 | 管理员 | 说明 |
|---|---|---|---|
| `public` + `published` | 可查看 | 可查看 | 所有登录用户 |
| `internal` + `published` | 可查看 | 可查看 | 所有登录用户 |
| `secret` + `published` | 同部门或作者可查看 | 可查看 | 部门隔离 |
| `draft` | 仅作者 | 可查看 | 列表不返回，详情需作者 |
| `archived` | 仅作者 | 可查看 | 不进入普通检索/问答 |

### 13.3 关键权限实现位置

| 权限点 | 实现 |
|---|---|
| 登录校验 | `app/api.py::api_login_required` |
| 管理员校验 | `app/api.py::api_admin_required` |
| 密级/部门判断 | `app/services/rag.py::can_view_document` |
| 可见已发布文档集合 | `app/services/rag.py::searchable_documents` |
| 文档编辑/删除所有权 | `app/api.py::update_document`、`delete_document` |
| 问答历史归属 | `app/api.py::qa_history_detail` |
| 图谱裁剪 | `app/api.py::_visible_graph_payload` |

---

> 本文 JSON 示例中的 id、计数、时间、用户名等为便于阅读的示意值，实际值以运行中的数据库和当前账号权限为准；字段名、类型、嵌套结构以本文与 `app/api.py` 为准。

## 14. 调用流程与示例

### 14.1 浏览器会话流程

```text
1. GET  /api/meta                 获取版本/演示账号/枚举
2. GET  /api/auth/session         匿名返回 {"user": null}
3. POST /api/auth/login           建立会话，返回 user
4. GET  /api/dashboard            加载工作台
5. GET  /api/documents?q=年假     检索文档
6. GET  /api/documents/12         读取详情（写查看审计）
7. POST /api/qa/ask               提问并保存历史
8. GET  /api/graph                读取权限裁剪图谱
9. POST /api/auth/logout          退出并写审计
```

### 14.2 cURL 示例

**登录并保存 Cookie**

```bash
curl -c cookies.txt -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  http://127.0.0.1:5000/api/auth/login
```

**携带 Cookie 查询文档**

```bash
curl -b cookies.txt "http://127.0.0.1:5000/api/documents?q=年假&page=1&per_page=9"
```

**提问**

```bash
curl -b cookies.txt -H "Content-Type: application/json" \
  -d '{"question":"员工年假有几天？"}' \
  http://127.0.0.1:5000/api/qa/ask
```

### 14.3 PowerShell 示例

```powershell
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
Invoke-RestMethod -WebSession $session -Method Post `
  -Uri 'http://127.0.0.1:5000/api/auth/login' `
  -ContentType 'application/json' `
  -Body '{"username":"admin","password":"admin123"}'

Invoke-RestMethod -WebSession $session `
  -Uri 'http://127.0.0.1:5000/api/documents?q=年假'
```

---

## 15. 接口—需求—测试追踪

| 接口组 | 主要需求 | 主要测试文件 | 重点验证 |
|---|---|---|---|
| `/api/auth/*` | UR-AUTH-01/02/05/06/07；SR-AUTH-001～009 | `tests/test_api.py`、`tests/test_login_security.py` | 登录/退出、限流、失败审计、密码哈希 |
| `/api/dashboard` | SR-OPS-001 | `tests/test_api.py`、`tests/test_security.py` | 统计范围与结构 |
| `/api/documents*` | UR-DOC-01～05；SR-DOC-001～007 | `tests/test_api.py`、`tests/test_security.py` | CRUD、检索、分页、密级、片段重建 |
| `/api/documents/favorites`、收藏切换 | UR-FAV-01；SR-FAV-001～003 | `tests/test_api.py` | 收藏切换与唯一性 |
| `/api/categories` | UR-DOC-06；SR-DOC-008 | `tests/test_api.py`、`tests/test_security.py` | 管理员新增、重名、列表 |
| `/api/qa*` | UR-QA-01～04；SR-QA-001～009 | `tests/test_api.py`、`tests/test_rag.py` | 来源、权限、Top-K、模式、历史 |
| `/api/graph*` | UR-KG-01/02；SR-KG-001～005 | `tests/test_api.py`、`tests/test_security.py` | 裁剪、维护权限、节点/边 |
| `/api/admin/*` | UR-AUD-01；SR-AUD-001/002 | `tests/test_api.py`、`tests/test_login_security.py` | 管理员权限、分页、审计 |
| `/api/about`、`/api/health` | SR-OPS-002/003 | `tests/test_system.py`、`tests/test_api.py` | 统计口径、健康响应 |

---

## 16. 实现边界与维护约定

### 16.1 当前边界

1. **认证**：仅会话 Cookie，不提供 JWT/OAuth、API Key 或开放平台鉴权。
2. **跨域**：未配置 CORS；Vue 开发环境依赖 Vite 代理，生产环境依赖同源部署。
3. **CSRF**：未实现独立 CSRF Token；当前依赖 `SameSite=Lax` 与同源调用，跨域/高安全部署需补充。
4. **限流**：登录限流为单进程内存滑动窗口，多进程部署需 Redis 等共享存储。
5. **文档体**：文档写接口接收 JSON 正文，不提供 multipart 文件上传端点。
6. **删除**：分类、用户、图谱节点/边没有删除 API；文档删除会联动清理图谱。
7. **分页**：仅文档列表和审计列表分页；收藏、分类、用户、问答历史、图谱管理列表使用固定上限或全量返回。\n8. **收藏状态**：收藏切换和收藏列表按 `can_view_document()` 密级判定过滤，当前未额外检查 `status`；若产品要求收藏列表只含已发布文档，应补充状态条件与测试。

### 16.2 变更维护规则

- 修改 `app/api.py` 的字段或状态码时，必须同步更新本文第 5～13 章和前端 `frontend/src/api/client.js` 的调用；
- 修改数据库字段时，必须同步更新 `app/models.py`、`docs/uml/07-ER图.puml` 并重新渲染；
- 修改权限规则时，必须同步更新 `docs/03-系统需求说明书.md` 与安全测试；
- 新增 API 时，应补充端点总览、请求/响应字段、权限、错误码和测试追踪；
- 提交前建议执行：
  - `.\run_tests.ps1`
  - `.\.venv\Scripts\python.exe -m ruff check app tests`
  - 手工验证“登录 → 文档检索 → 问答 → 图谱 → 审计”主路径。

---

*文档结束 · 2026-10-29 · V2.0*
