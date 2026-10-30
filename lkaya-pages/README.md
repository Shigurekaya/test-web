# lkaya.com 静态演示站

这是「智慧企业知识财富库」的独立 Cloudflare Pages 演示项目。它使用原 Vue 生产构建，配合浏览器内 Mock API 和 `localStorage` 假数据，完整展示 11 个页面与主要交互。

**不修改、不依赖、不连接主 Flask 项目。**

## 部署方式

### Cloudflare Pages 控制台

- Git 仓库：`Shigurekaya/test-web`
- 根目录：`lkaya-pages`
- 框架预设：`None`
- 构建命令：留空
- 构建输出目录：`.`

### Wrangler

```powershell
npx wrangler pages deploy lkaya-pages --project-name lkaya-com
```

然后在 Cloudflare Pages 项目中绑定自定义域名 `lkaya.com`。

## 演示账号

| 账号 | 密码 | 权限 |
|---|---|---|
| admin | admin123 | 管理员 |
| hr | hr123 | 人事部员工 |
| finance | fin123 | 财务部员工 |
| it | it123 | 信息部员工 |
| product | prod123 | 产品部员工 |

## 功能范围

- 登录、退出与角色权限演示
- 工作台统计与图表
- 文档搜索、筛选、分页、收藏、新建、编辑、删除
- 文档详情与相关推荐
- 带来源片段的本地检索式问答
- 知识关系图与管理员图谱维护
- 用户列表、审计日志筛选与分页
- 关于系统

演示数据保存在当前浏览器的 `localStorage`。右下角“重置数据”可以恢复初始状态。清除浏览器数据、更换浏览器或设备后不会同步。

## 边界

该版本不包含真实认证、服务器端权限、跨设备数据同步、真实文件上传或大模型调用。它用于课程展示，不应作为生产系统使用。