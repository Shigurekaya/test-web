# 页面原型截图

本目录是 V2.0 Vue 前端在临时隔离 Flask API 环境下的运行截图，用于课程文档中的页面原型与验收证据。

| 文件 | 页面 | 说明 |
|---|---|---|
| `01-login.png` | 登录页 | 品牌展示、演示账号与登录表单 |
| `02-dashboard.png` | 工作台 | 权限内统计、部门/分类图表、最近文档、快捷提问与审计 |
| `03-documents.png` | 知识文档列表 | 检索、筛选、分页、密级与收藏 |
| `04-document-detail.png` | 文档详情 | 正文、元数据、收藏、编辑/删除与相关阅读 |
| `05-document-editor.png` | 文档编辑 | 标题、摘要、正文、分类、部门、密级、状态和标签 |
| `06-qa.png` | 智能问答首页 | 建议问题、问答历史与检索流程说明 |
| `07-graph.png` | 知识关系图 | ECharts 力导向图、节点类型、操作说明与权限过滤 |
| `08-users.png` | 用户管理 | 账号、角色、部门和文档贡献 |
| `09-audits.png` | 审计日志 | 操作统计、服务端筛选与分页 |
| `10-about.png` | 关于系统 | 项目定位、技术架构、能力与课程交付信息 |
| `11-qa-answer.png` | 问答结果 | 回答、模式、来源文档和命中片段 |
| `12-mobile-dashboard.png` | 移动端工作台 | 390 × 844 响应式布局 |

桌面截图统一为 1440 × 950，移动截图为 390 × 844。截图由 `scripts/capture_ui.py` 调用 Playwright 生成；服务运行在 `127.0.0.1:5099`，使用临时数据库，不会修改 `instance/knowledge.db`。

重新生成：

```powershell
cd frontend
npm run build
cd ..
.\.venv\Scripts\python.exe scripts\capture_ui.py
```

截图任务会同时检查浏览器控制台错误和外部网络请求。界面字体使用 Windows 本地字体栈，不依赖 Google Fonts。
