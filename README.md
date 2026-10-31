# 智慧企业知识财富库系统

[![CI](https://github.com/Shigurekaya/test-web/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Shigurekaya/test-web/actions/workflows/ci.yml)
![Vue 3](https://img.shields.io/badge/Vue-3-42b883)
![Flask](https://img.shields.io/badge/Flask-3-000000?logo=flask&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Tests](https://img.shields.io/badge/tests-136%20passed-brightgreen)

V2.0 课程大作业。一个采用前后端分离架构的企业知识管理 Web 应用，覆盖需求分析、系统设计、编码实现、自动化测试、UML 建模、项目管理和最终文档交付。

> 供后续开发者和 AI Agent 使用的完整文件地图：[项目文件说明.md](./项目文件说明.md)

> 前端：Vue 3 + Vite + Vue Router + ECharts
> 后端：Flask 3 REST API + SQLAlchemy + SQLite + jieba
> 测试：pytest，当前 **136 条自动化测试全部通过**

## 交付物直达

| 交付物 | 入口 |
|---|---|
| 完整 Word 报告 | [智慧企业知识财富库系统-课程大作业完整报告.docx](./deliverables/智慧企业知识财富库系统-课程大作业完整报告.docx) |
| 完整 PDF 报告 | [智慧企业知识财富库系统-课程大作业完整报告.pdf](./deliverables/pdf/智慧企业知识财富库系统-课程大作业完整报告.pdf) |
| 完整提交包 | [智慧企业知识财富库系统-课程大作业完整提交包.zip](./deliverables/智慧企业知识财富库系统-课程大作业完整提交包.zip) |
| 提交与运行说明 | [00-提交说明.md](./00-提交说明.md) |
| 实现说明 | [实现说明](./docs/guides/实现说明.md) |
| 正式文档索引 | [docs/course/README.md](./docs/course/README.md) |
| 精简阅读文档 | [需求 / 设计 / 开发计划](./docs/short/) |
| 交付验收记录 | [交付验收记录.md](./deliverables/交付验收记录.md) |

## 1. 系统能力

| 模块 | 主要能力 |
|------|----------|
| 认证与权限 | 登录/退出、密码哈希、登录失败限流、管理员/员工角色 |
| 知识文档 | 新建、编辑、删除、分类、标签、版本、发布状态、收藏 |
| 文档权限 | 公开/内部/机密三级密级，机密文档仅同部门或作者可访问 |
| 检索 | 关键词、标题、摘要、正文与标签检索 |
| 智能问答 | 权限内 RAG 检索、来源片段展示、可选 OpenAI 兼容大模型、失败回退本地摘要 |
| 知识图谱 | 文档—部门—分类—关键词关系图、管理员节点与关系维护 |
| 审计 | 登录、登录失败、退出、查看/创建/编辑/删除文档、问答记录 |
| 管理 | 用户列表、分类维护、审计日志服务端筛选与分页、健康检查 |

## 2. 快速启动

### 2.1 准备后端

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

### 2.2 构建前端

```powershell
cd frontend
npm install
npm run build
cd ..
```

生产构建会输出到 `frontend/dist/`，由 Flask 在 `/ui/` 提供。

### 2.3 启动

```powershell
.\.venv\Scripts\python.exe run.py
```

浏览器打开：

- 主界面：`http://127.0.0.1:5000/ui/`
- 根地址会自动跳转：`http://127.0.0.1:5000/`
- API 健康检查：`http://127.0.0.1:5000/api/health`

也可以双击 `start.bat`，或运行 `.\start.ps1` 后台启动。`start.ps1` 会在前端未构建时自动执行 `npm install` 与 `npm run build`。

### 2.4 前端开发模式

分别启动后端和 Vite：

```powershell
.\.venv\Scripts\python.exe run.py
cd frontend
npm run dev
```

打开 `http://127.0.0.1:5173/`。Vite 会将 `/api` 代理到 `http://127.0.0.1:5000`。

## 3. 演示账号

| 用户 | 密码 | 部门 | 说明 |
|------|------|------|------|
| admin | admin123 | 综合部 | 管理员，可查看全部、审计、用户、分类与图谱维护 |
| hr | hr123 | 人事部 | 普通员工，可验证机密文档拒绝访问 |
| finance | fin123 | 财务部 | 财务制度、差旅与采购 |
| it | it123 | 信息部 | 可查看信息部机密文档 |
| product | prod123 | 产品部 | 产品 FAQ 与客服话术 |

## 4. 目录结构

```text
大作业/
├── app/
│   ├── api.py                    REST API
│   ├── spa.py                    Vue 生产构建托管
│   ├── blueprints/               兼容的 Jinja 页面路由
│   ├── services/                 RAG 与知识图谱服务
│   ├── models.py                 SQLAlchemy 数据模型
│   ├── seed.py                   演示数据
│   └── templates/                兼容页面
├── frontend/
│   ├── src/views/                Vue 页面
│   ├── src/components/           通用组件
│   ├── src/api/                  前端 API 客户端
│   ├── src/stores/               会话与提示状态
│   └── dist/                     已构建生产文件
├── tests/                        pytest 自动化测试
├── docs/
│   ├── course/                   课程作业正式文档
│   ├── guides/                   提交说明与实现说明
│   ├── screenshots/              页面截图
│   ├── uml/                      PlantUML 源文件与渲染图
│   └── 用例描述/                 详细用例说明
├── deliverables/                 Word、PDF、验收记录与完整提交包
├── scripts/                      UML、文档生成与导出一致性脚本
├── run.py
├── start.ps1 / stop.ps1
├── 00-提交说明.md
└── README.md
```

## 5. 自动化测试

```powershell
.\run_tests.ps1
# 或
.\.venv\Scripts\python.exe -m pytest -q
```

测试使用独立内存数据库，不会修改 `instance/knowledge.db`。覆盖：

- 登录成功、失败、防爆破与审计；
- 管理员/员工权限矩阵；
- 公开/内部/机密文档访问隔离；
- 文档 CRUD、收藏、检索、知识切分与图谱同步；
- RAG 打分、来源合并、权限过滤与大模型失败降级；
- 图谱数据范围、审计日志分页和筛选；
- Flask REST API 契约；
- 全新数据库自动建表与演示数据初始化；
- 时间口径与前后端联调。

代码检查：

```powershell
.\.venv\Scripts\python.exe -m ruff check app scripts tests run.py
```

GitHub Actions 会同时执行 Ruff 检查与格式校验、136 条 pytest、前端生产依赖审计和 Vue 构建，避免只通过后端检查却遗漏前端编译或依赖安全问题。

## 6. REST API

主要接口：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 登录 |
| POST | `/api/auth/logout` | 退出 |
| GET | `/api/dashboard` | 工作台数据 |
| GET/POST | `/api/documents` | 文档列表/新建 |
| GET/PUT/DELETE | `/api/documents/<id>` | 文档详情/更新/删除 |
| POST | `/api/documents/<id>/favorite` | 切换收藏 |
| POST | `/api/qa/ask` | 智能问答 |
| GET | `/api/graph` | 权限过滤后的图谱数据 |
| GET | `/api/admin/users` | 用户列表 |
| GET | `/api/admin/audits` | 审计分页查询 |
| GET | `/api/health` | 健康检查 |

完整接口说明见 `docs/course/08-REST-API接口设计说明书.md`。

## 7. UML 与课程文档

UML 源文件位于 `docs/uml/`，已渲染 PNG/SVG 到 `docs/uml/rendered/`。课程正式文档位于 `docs/course/`，包括：

1. 项目开发计划
2. 软件需求规格说明书
3. 软件设计规格说明书
4. 项目测试计划
5. 测试用例说明书
6. 项目总结
7. 个人项目小结与考核材料
8. REST API 接口设计说明书

最终 Word 合并版和单独文档输出到 `deliverables/`。

### 7.1 重新生成页面截图

先构建前端，再启动临时隔离数据库并生成 1440 × 950 桌面截图和 390 × 844 移动截图：

```powershell
cd frontend
npm run build
cd ..
.\.venv\Scripts\python.exe scripts\capture_ui.py
```

脚本使用 `127.0.0.1:5099` 的临时 Flask 服务，不会修改演示数据库；会检查浏览器控制台错误和外部网络请求。前端字体使用 Windows 本地字体栈，不依赖 Google Fonts。

## 8. 配置项

通过环境变量或 `.env` 注入，详见 `.env.example`：

| 变量 | 默认 | 说明 |
|------|------|------|
| `SECRET_KEY` | 开发默认值 | 会话签名密钥，生产必须修改 |
| `DATABASE_URL` | `sqlite:///instance/knowledge.db` | 数据库连接 |
| `OPENAI_API_KEY` | 空 | 配置后启用大模型回答 |
| `OPENAI_BASE_URL` / `OPENAI_MODEL` | OpenAI 默认 | OpenAI 兼容接口 |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` / `TOP_K` | 400 / 50 / 5 | RAG 参数 |
| `LOGIN_MAX_ATTEMPTS` / `LOGIN_WINDOW_SECONDS` | 8 / 300 | 登录限流 |
| `AUTO_SEED` | 1 | 是否自动写入演示数据 |

## 9. 说明

- 演示制度、账号和业务数据均为课程作业虚构内容。
- 未配置大模型密钥时，问答使用可解释的本地检索摘要，不会伪装成大模型生成。
- 登录限流为进程内实现，适用于单机课程演示；多进程部署需改用共享存储。
- 原 Flask/Jinja 页面保留在 `/dashboard`、`/knowledge`、`/qa` 等旧路径，作为兼容层。
