# 智慧企业知识财富库系统

企业内部知识管理 Web 应用（软件工程课程大作业）。
以**可鉴权的文档库**为底座，叠加**检索增强问答（RAG）**与**知识关系图**，
并配套完整的竞品调研、需求、设计、UML 与测试文档。

> 技术栈：Python · Flask · SQLAlchemy · SQLite · Bootstrap · ECharts · jieba
> 当前版本：v1.2

---

## 1. 快速开始

```powershell
# 1) 建虚拟环境（装到项目内，不污染全局）
python -m venv .venv

# 2) 装依赖
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt

# 3) 启动
.\.venv\Scripts\python.exe run.py
# 浏览器打开 http://127.0.0.1:5000
```

首次启动会自动建表并写入演示数据，账号 `admin / admin123`。
后台启动用 `.\start.ps1`，停止用 `.\stop.ps1`，双击 `start.bat` 亦可。

### 演示账号

| 用户 | 密码 | 部门 | 说明 |
|------|------|------|------|
| admin | admin123 | 综合部 | 管理员，可看全部 + 审计/用户/分类/图谱维护 |
| hr | hr123 | 人事部 | 普通员工（演示机密拒绝） |
| finance | fin123 | 财务部 | 差旅 / 采购 / 预算 |
| it | it123 | 信息部 | **可看本部门机密**（演示机密放行） |
| product | prod123 | 产品部 | 产品 FAQ / 话术 |

### 建议演示路线

1. `admin` 登录 → 工作台看规模统计与部门分布；
2. 「知识文档」搜「年假」→ 打开《员工年休假管理办法》；
3. 「站内问答」问「员工年假有几天」→ 查看带来源的摘要回答；
4. 「关系图」拖拽查看 文档—部门—关键词 连线；
5. 退出后用 `hr` 登录 → 打开信息部机密文档**返回 403**；改用 `it` → 正常打开。

---

## 2. 功能概览

| 模块 | 能力 |
|------|------|
| 账户与权限 | 登录/退出、角色菜单、文档三级密级（公开/内部/机密）+ 同部门隔离、登录防爆破、失败登录审计 |
| 知识文档 | 新建/编辑/删除、分类与标签、按关键词/分类/部门/密级筛选、分页、发布状态 |
| 站内问答（RAG） | 文档切分建索引 → 权限内检索打分 Top-K → 本地摘要回答（可配大模型）→ 带来源与历史 |
| 知识关系图 | 文档—部门—分类—关键词自动建图，ECharts 力导向可视化，管理员可手工补节点/关系 |
| 收藏与审计 | 个人收藏夹、关键操作（含登录失败）审计查询与统计 |
| 运维 | 工作台、关于页、`/health` 健康检查、启停脚本、自动化测试 |

---

## 3. 目录结构

```
大作业/
├── run.py                     启动入口
├── requirements.txt           运行依赖
├── requirements-dev.txt       开发/测试依赖（pytest、ruff、渲染 UML 用的 jdk4py）
├── pyproject.toml             pytest / ruff / coverage 配置
├── start.ps1 stop.ps1         后台启停
├── run_tests.ps1              跑测试（透传参数给 pytest）
│
├── app/
│   ├── __init__.py            应用工厂：配置、蓝图注册、错误页、模板过滤器
│   ├── config.py              默认 / 测试 / 生产三套配置
│   ├── models.py               ORM：users / documents / knowledge_chunks / graph_* / favorites / audit_logs / qa_history
│   ├── utils.py               鉴权辅助、密级标签、安全 next URL、登录限流器
│   ├── seed.py                演示账号与制度文本、活动记录
│   ├── blueprints/            auth / main / knowledge / qa / graph / admin
│   ├── services/              rag（切分检索问答）、graph（图谱同步）
│   ├── templates/             Jinja2 页面
│   └── static/                CSS / JS
│
├── tests/                     自动化测试（99 条）
│   ├── conftest.py            独立数据库夹具
│   ├── test_system.py         系统冒烟与回归
│   ├── test_security.py       权限矩阵、检索范围、open redirect、统计口径
│   ├── test_rag.py            切分、打分、检索、去重、降级
│   └── test_login_security.py 防爆破、失败审计、密码存储
│
├── docs/                      项目文档（见下）
├── scripts/
│   ├── render_uml.py          渲染 UML（本地，中文正常）
│   ├── setup_uml.py           准备渲染环境（字体 + jar + JRE）
│   └── plantuml_local.py      本地 PlantUML 渲染封装
└── instance/                  SQLite 库与运行日志（不入库）
```

---

## 4. 项目文档

按软件工程过程组织，入口 [`docs/README.md`](docs/README.md)：

| 文档 | 内容 |
|------|------|
| [docs/01-竞品调研报告.md](docs/01-竞品调研报告.md) | 竞品对比、痛点归纳、差异化定位与范围冻结 |
| [docs/02-用户需求说明书.md](docs/02-用户需求说明书.md) | 业务需求 BR-*、用户需求 UR-*、非功能需求 NFR-* |
| [docs/03-系统需求说明书.md](docs/03-系统需求说明书.md) | 系统需求 SR-*、业务流程、非功能指标、路由附录 |
| [docs/04-软件设计说明书.md](docs/04-软件设计说明书.md) | 三层架构、RAG/图谱/权限设计、数据库设计、需求追踪 |
| [docs/05-测试报告.md](docs/05-测试报告.md) | 测试环境、手工与自动化用例、缺陷与结论 |
| [docs/06-项目管理.md](docs/06-项目管理.md) | 角色分工、计划与风险 |
| [docs/uml/](docs/uml/README.md) | **10 张 UML 图**（含渲染好的 PNG/SVG） |
| [docs/用例描述/](docs/用例描述/README.md) | 登录、文档管理、智能问答的详细用例 |

---

## 5. 测试

```powershell
.\run_tests.ps1                 # 全部 99 条
.\run_tests.ps1 -- -q -k security   # 只跑某个子集
```

测试全部跑在**独立的临时数据库**上，不会读写 `instance/knowledge.db`（演示库），
可反复执行且互不影响。覆盖：权限矩阵、检索范围、问答算法、防爆破、失败审计、
新建后可检索、全新库自建、演示故事线等。

代码检查：

```powershell
.\.venv\Scripts\python.exe -m ruff check app scripts tests run.py
```

---

## 6. UML 图渲染

`docs/uml/rendered/` 里已经是渲染好的图片。如需重新生成：

```powershell
.\.venv\Scripts\python.exe scripts\setup_uml.py     # 首次：准备字体 + jar + JRE
.\.venv\Scripts\python.exe scripts\render_uml.py    # 渲染 svg + png
.\.venv\Scripts\python.exe scripts\render_uml.py --check   # 只校验语法
```

采用**本地渲染**而非 PlantText / kroki.io：这些在线服务的 PlantUML 服务器
不带中文字体，中文标签会全部变成空白方框。

---

## 7. 配置项

通过环境变量或 `.env` 注入（见 [`.env.example`](.env.example)）：

| 变量 | 默认 | 说明 |
|------|------|------|
| `SECRET_KEY` | 开发默认值 | 会话签名密钥，生产必须修改 |
| `DATABASE_URL` | `sqlite:///instance/knowledge.db` | 数据库连接 |
| `OPENAI_API_KEY` | 空 | 配置后问答切换为大模型生成；留空用本地摘要 |
| `OPENAI_BASE_URL` / `OPENAI_MODEL` | OpenAI 默认 | 兼容协议接口（如豆包 Ark） |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` / `TOP_K` | 400 / 50 / 5 | RAG 切分与检索参数 |
| `LOGIN_MAX_ATTEMPTS` / `LOGIN_WINDOW_SECONDS` | 8 / 300 | 登录防爆破阈值与窗口 |
| `AUTO_SEED` | 1 | 是否自动建表并灌演示数据；生产建议置 0 |
| `FLASK_ENV` / `APP_ENV` | default | `testing` / `production` 切换配置类 |

---

## 8. 说明

- 演示制度正文均为**虚构**，不代表任何真实企业规定。
- 问答默认是「权限内分词检索 + 摘要拼接」，配置 `OPENAI_API_KEY` 后可在命中片段上调用大模型；
  调用失败会自动回退本地摘要，且不会伪装成已调用大模型。
- 登录限流为**进程内**实现，适合单机/单进程演示；多进程部署需换成共享存储。
