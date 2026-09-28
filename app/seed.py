"""初始化 / 增量补充演示数据（展示站用，虚构数据，勿当真实业务）。"""
from __future__ import annotations

import json
import random
from datetime import datetime, timedelta

from app.extensions import db
from app.models import (
    AuditLog,
    Category,
    Document,
    Favorite,
    QAHistory,
    User,
)
from app.services.graph import ensure_edge, get_or_create_node, sync_document_graph
from app.services.rag import rebuild_chunks_for_document

DEMO_DOCS = [
    {
        "title": "员工年休假管理办法",
        "department": "人事部",
        "category": "制度规范",
        "visibility": "internal",
        "tags": "年假,休假,人事",
        "summary": "规定正式员工年休假天数与申请流程。",
        "content": """一、适用范围
本办法适用于公司全体正式员工。

二、年休假天数
1. 连续工作满1年不满10年的，年休假5天。
2. 连续工作满10年不满20年的，年休假10天。
3. 连续工作满20年的，年休假15天。

三、申请流程
员工应提前至少3个工作日在OA系统提交年假申请，经直属主管与人事部审批后方可休假。
突发情况可事后补办手续，但须在返岗后2个工作日内完成。

四、其他说明
年休假原则上不跨年累计，确因工作原因未休完的，可延期至次年3月31日前使用。
国家法定节假日、休息日不计入年休假假期。
""",
    },
    {
        "title": "差旅报销制度（节选）",
        "department": "财务部",
        "category": "制度规范",
        "visibility": "internal",
        "tags": "差旅,报销,财务",
        "summary": "出差交通、住宿与餐补报销标准。",
        "content": """一、交通
市内交通优先地铁与网约车公务单；跨城出差可报销高铁二等座或经济舱机票。
未经批准的头等舱、商务座不予报销。

二、住宿
一线城市住宿标准上限为每晚500元；其他城市上限为每晚350元。
超标准部分需说明原因并由分管领导签字。

三、餐补
出差期间餐补标准为每人每天100元，已由接待方安排用餐的当日不再发放餐补。

四、报销时限
差旅结束后15个自然日内提交报销单，逾期需说明原因。
""",
    },
    {
        "title": "加班与调休管理办法",
        "department": "人事部",
        "category": "制度规范",
        "visibility": "internal",
        "tags": "加班,调休,补偿",
        "summary": "明确加班审批、调休与法定节假日加班补偿规则。",
        "content": """一、加班原则
加班应以完成紧急任务为前提，须事先在OA提交加班申请并由主管审批。

二、补偿方式
1. 工作日加班：优先安排调休，无法调休的按正常工资150%计发。
2. 休息日加班：优先调休；不能调休的按200%计发。
3. 法定节假日加班：按300%计发，一般不安排调休替代。

三、调休有效期
调休须在加班发生后90日内使用完毕，逾期视同放弃，特殊情况由人事部备案延期。
""",
    },
    {
        "title": "产品A 用户手册（摘要）",
        "department": "产品部",
        "category": "产品知识",
        "visibility": "public",
        "tags": "产品A,手册,FAQ",
        "summary": "产品A 登录、重置密码与常见问题。",
        "content": """产品A 是面向中小企业的协同办公工具。

登录说明
默认使用企业邮箱登录。首次登录需完成手机号绑定。

重置密码
在登录页点击「忘记密码」，输入邮箱后将收到重置链接，链接15分钟内有效。

常见问题
Q：能否同时登录多台设备？
A：同一账号最多同时在线3台设备，超出后最早登录的设备会被踢下线。

Q：数据保存在哪里？
A：默认保存在企业专属空间，管理员可配置本地备份策略。
""",
    },
    {
        "title": "产品B 发版说明 v2.3",
        "department": "产品部",
        "category": "产品知识",
        "visibility": "public",
        "tags": "产品B,发版,更新",
        "summary": "产品B v2.3 新增知识检索与权限改进说明。",
        "content": """版本号：v2.3
发布日期：2026-09-01

新增功能
1. 支持知识库问答入口，可按权限检索企业文档。
2. 文档可见性新增「机密」级别，仅同部门可见。
3. 导出报表支持按部门筛选。

修复问题
1. 修复搜索结果偶发重复的问题。
2. 修复移动端表格横向滚动条遮挡按钮的问题。

升级注意
升级前请备份数据库；升级后首次登录将触发索引重建，预计耗时 3～10 分钟。
""",
    },
    {
        "title": "信息安全分级与访问控制规范",
        "department": "信息部",
        "category": "制度规范",
        "visibility": "secret",
        "tags": "安全,保密,分级",
        "summary": "公开、内部、机密三级文档访问规则。",
        "content": """一、分级定义
公开：可对企业外部合作伙伴展示。
内部：仅限在职员工访问。
机密：仅限归属部门与管理员访问。

二、访问控制
系统应根据文档可见性与用户部门进行鉴权。机密文档的下载与转发需留存审计日志。

三、违规处理
擅自传播机密信息的，按公司奖惩条例处理，情节严重者解除劳动合同并追究法律责任。
""",
    },
    {
        "title": "VPN与远程办公安全指南",
        "department": "信息部",
        "category": "培训资料",
        "visibility": "secret",
        "tags": "VPN,远程办公,安全",
        "summary": "远程接入、双因素认证与终端安全要求。",
        "content": """一、接入方式
远程办公必须通过公司 VPN，禁止将业务系统直接暴露公网。

二、认证要求
启用双因素认证（密码 + 动态口令）。公用电脑禁止保存密码。

三、终端要求
1. 系统需保持自动更新。
2. 安装公司指定终端安全软件。
3. 离开座位立即锁屏。

四、数据外发
通过即时通讯发送含客户隐私的文件前，须脱敏或加密，并在工作群留存说明。
""",
    },
    {
        "title": "智慧知识库建设指引",
        "department": "综合部",
        "category": "培训资料",
        "visibility": "internal",
        "tags": "RAG,知识图谱,知识库",
        "summary": "介绍企业知识财富库的建设目标与使用方式。",
        "content": """建设目标
沉淀企业制度、产品与项目经验，形成可检索、可问答、可关联的知识财富库。

核心能力
1. 知识文档管理：分类、版本、权限。
2. RAG 智能问答：先检索相关片段，再生成回答，并标注来源。
3. 知识图谱：展示文档、部门、关键词之间的关系。

使用建议
提问尽量包含业务关键词，例如「年假几天」「差旅住宿标准」。
上传新文档后系统会自动切分知识片段并同步图谱关系。
""",
    },
    {
        "title": "新员工入职培训手册",
        "department": "人事部",
        "category": "培训资料",
        "visibility": "internal",
        "tags": "入职,培训,新人",
        "summary": "入职首周需要完成的事项与常见问题。",
        "content": """入职首日
1. 领取工牌、电脑与办公用品。
2. 完成账号开通：邮箱、OA、知识库。
3. 阅读《员工手册》并签署确认。

入职首周
1. 参加部门业务宣讲。
2. 完成信息安全在线测验（及格线 80 分）。
3. 与导师确认试用期目标。

常见问题
Q：通勤补贴如何申请？
A：入职满一个月后，在OA「福利申请」提交，次月随工资发放。
""",
    },
    {
        "title": "会议室与办公资源使用规范",
        "department": "综合部",
        "category": "制度规范",
        "visibility": "internal",
        "tags": "会议室,预约,行政",
        "summary": "会议室预约、取消与设备使用规则。",
        "content": """一、预约
通过OA「会议室」模块预约，单次最长2小时；跨半天需部门负责人批准。

二、取消
开始前30分钟仍可取消；连续三次未取消且未使用，将限制预约权限一周。

三、设备
投影、视频会议设备使用后请复位；损坏及时报修综合部。

四、卫生
会议结束带走垃圾，白板擦拭干净。
""",
    },
    {
        "title": "采购申请与审批流程",
        "department": "财务部",
        "category": "制度规范",
        "visibility": "internal",
        "tags": "采购,审批,预算",
        "summary": "物资与服务采购的金额分级审批规则。",
        "content": """一、适用范围
办公物资、软件订阅、外包服务等采购。

二、审批权限
1. 金额 ≤ 2000 元：部门负责人审批。
2. 2000～20000 元：部门负责人 + 财务审批。
3. 超过 20000 元：分管领导审批，并需三方比价材料。

三、票据
发票抬头必须与公司全称一致；电子发票需在报销系统上传原件 PDF。
""",
    },
    {
        "title": "客户服务标准话术手册",
        "department": "产品部",
        "category": "产品知识",
        "visibility": "internal",
        "tags": "客服,话术,投诉",
        "summary": "接待、投诉升级与回访的标准话术。",
        "content": """开场
您好，这里是客服中心，工号××，很高兴为您服务。

投诉处理
1. 先致歉并复述问题，确认理解一致。
2. 能当场解决的当场解决；不能的明确时限并建单。
3. 涉及资金纠纷须升级主管，禁止私自承诺赔付金额。

回访
处理完成后24小时内回访，记录满意度（1～5分）。低于3分进入复盘清单。
""",
    },
    {
        "title": "项目里程碑与周报模板",
        "department": "综合部",
        "category": "项目资料",
        "visibility": "internal",
        "tags": "项目,里程碑,周报",
        "summary": "项目立项后的里程碑划分与周报填写说明。",
        "content": """里程碑建议
1. 需求冻结
2. 设计评审通过
3. 开发完成（含联调）
4. 测试通过
5. 上线与验收

周报结构
1. 本周完成
2. 风险与阻塞
3. 下周计划
4. 需要的支持

要求
每周五 17:00 前提交至项目空间；重大风险需当日同步项目经理。
""",
    },
    {
        "title": "绩效考核与目标管理说明",
        "department": "人事部",
        "category": "制度规范",
        "visibility": "internal",
        "tags": "绩效,OKR,考核",
        "summary": "季度目标制定、评分构成与结果应用。",
        "content": """一、周期
按自然季度考核，目标须在季度首两周内确认。

二、评分构成
业绩结果 70% + 过程行为 20% + 协作评价 10%。

三、结果应用
1. 优秀：优先培训与晋升提名。
2. 合格：正常调薪池。
3. 待改进：制定30天改进计划并由导师辅导。

四、申诉
对结果有异议可在公布后5个工作日内向人事部书面申诉。
""",
    },
    # —— 以下为补充文档：丰富展示密度（虚构）——
    {
        "title": "劳动合同续签与转正流程",
        "department": "人事部",
        "category": "制度规范",
        "visibility": "internal",
        "tags": "合同,转正,续签",
        "summary": "试用期转正材料与合同续签节点说明。",
        "content": """一、试用期转正
试用期满前15个工作日，员工提交《转正申请表》与阶段性总结；直属主管与人事联合评审。

二、续签节点
合同到期前60天系统自动提醒；到期前30天完成续签审批。不续签的，按劳动法规办理离职交接。

三、材料清单
身份证复印件、学历证明、保密协议、岗位说明书确认页。
""",
    },
    {
        "title": "社保公积金缴纳与基数调整须知",
        "department": "人事部",
        "category": "制度规范",
        "visibility": "internal",
        "tags": "社保,公积金,福利",
        "summary": "参保范围、缴费基数与年度调整窗口。",
        "content": """一、参保范围
正式员工入职当月起缴纳五险一金；实习/兼职按当地政策执行。

二、基数调整
每年7月根据上年度月均工资调整一次；员工可在OA查询个人缴费明细。

三、异地缴纳
确需异地缴纳的，须人事与财务双签确认，并在备注中写明原因。
""",
    },
    {
        "title": "发票验真与费用报销常见驳回原因",
        "department": "财务部",
        "category": "培训资料",
        "visibility": "internal",
        "tags": "发票,报销,驳回",
        "summary": "财务驳回高频原因与自查清单。",
        "content": """高频驳回原因
1. 发票抬头或税号错误。
2. 报销事由与科目不匹配。
3. 缺少审批流截图或合同附件。
4. 跨月超期未说明原因。

自查清单
提交前核对：抬头、金额、附件清晰度、审批节点是否齐全。
""",
    },
    {
        "title": "预算编制与季度滚动预测指引",
        "department": "财务部",
        "category": "制度规范",
        "visibility": "secret",
        "tags": "预算,预测,财务",
        "summary": "年度预算拆解与季度滚动更新节奏。",
        "content": """一、编制节奏
每年11月启动下一年度预算；各部门按成本中心填报，财务汇总后报管理层。

二、滚动预测
每季度末更新一次剩余季度预测，偏差超过10%须附原因说明。

三、冻结规则
预算一经批准，单项超支须走追加申请，禁止先斩后奏。
""",
    },
    {
        "title": "产品C 渠道伙伴入驻手册",
        "department": "市场部",
        "category": "产品知识",
        "visibility": "public",
        "tags": "产品C,渠道,伙伴",
        "summary": "渠道申请、资质审核与返点结算说明。",
        "content": """申请条件
具备本地服务能力与基础技术支持团队；提交营业执照与案例材料。

审核周期
资料齐全后5个工作日内完成初审，通过后开通伙伴门户。

返点结算
按季度结算，以已回款订单为准；争议订单进入复核队列。
""",
    },
    {
        "title": "官网与活动页内容发布规范",
        "department": "市场部",
        "category": "运营规范",
        "visibility": "internal",
        "tags": "官网,发布,内容",
        "summary": "文案口径、素材规格与上线检查清单。",
        "content": """文案口径
对外承诺须与产品事实一致；涉及价格、SLA 的表述需产品与法务双确认。

素材规格
主视觉 ≥ 1920×1080；Logo 保留透明底；禁止拉伸变形。

上线检查
链接可点、表单可提交、移动端折行正常、备案号显示完整。
""",
    },
    {
        "title": "品牌视觉识别（VI）使用简册",
        "department": "市场部",
        "category": "市场物料",
        "visibility": "internal",
        "tags": "VI,品牌,物料",
        "summary": "Logo 安全区、主色与禁用示例。",
        "content": """Logo
保持安全留白不少于字标高度的 1/2；禁止改色、加阴影、旋转。

主色
深蓝 #0B3D5C、辅绿 #1A6B5C、点缀金 #C9852D。

禁用
不得与竞品色混用；印刷品需打样确认。
""",
    },
    {
        "title": "线索跟进与商机阶段定义",
        "department": "运营部",
        "category": "运营规范",
        "visibility": "internal",
        "tags": "线索,商机,CRM",
        "summary": "线索分级、跟进时限与商机阶段口径。",
        "content": """线索分级
A：48小时内必须首触；B：3个工作日；C：进入培育池。

商机阶段
线索确认 → 需求调研 → 方案报价 → 商务谈判 → 赢单/丢单。

记录要求
每次跟进须在 CRM 留下纪要与下次动作，禁止只改阶段不写说明。
""",
    },
    {
        "title": "客成交接与续费预警机制",
        "department": "运营部",
        "category": "运营规范",
        "visibility": "internal",
        "tags": "客成,续费,预警",
        "summary": "交付转客成材料包与到期前预警节奏。",
        "content": """交接材料
合同摘要、开通账号清单、培训记录、未结工单。

续费预警
到期前 90/60/30 天分别触发提醒；高价值客户由客成经理人工跟进。

风险标记
连续 14 天无登录或关键投诉未闭环的，进入风险清单周会。
""",
    },
    {
        "title": "数据备份与灾难恢复演练计划",
        "department": "信息部",
        "category": "技术文档",
        "visibility": "secret",
        "tags": "备份,容灾,演练",
        "summary": "备份策略、恢复目标与年度演练安排。",
        "content": """备份策略
核心库每日全量 + 每小时增量；对象存储异地冗余。

恢复目标
RPO ≤ 1 小时；关键业务 RTO ≤ 4 小时。

演练
每半年至少一次桌面推演 + 一次受限恢复演练，结果归档至知识库。
""",
    },
    {
        "title": "API 网关限流与密钥轮换规范",
        "department": "技术部",
        "category": "技术文档",
        "visibility": "secret",
        "tags": "API,限流,密钥",
        "summary": "对外 API 调用配额与密钥有效期管理。",
        "content": """限流
默认 60 QPS / 应用；突发允许短时 2 倍，超限返回 429。

密钥轮换
生产密钥最长 90 天；轮换前后保留 7 天双钥并行窗口。

审计
密钥创建、禁用、调用异常须写入审计日志。
""",
    },
    {
        "title": "代码评审与发布窗口约定",
        "department": "技术部",
        "category": "技术文档",
        "visibility": "internal",
        "tags": "评审,发布,研发",
        "summary": "MR 评审门槛与工作日发布窗口。",
        "content": """评审门槛
至少 1 名同组同事 Approve；涉及权限/计费需额外 Reviewer。

发布窗口
工作日 10:00–11:30、14:00–17:00；周五 16:00 后与节假日前一天原则上冻结。

回滚
发布后 30 分钟内保持值守；异常优先回滚再排查。
""",
    },
    {
        "title": "合同模板选用与印章管理规定",
        "department": "法务部",
        "category": "法务合规",
        "visibility": "internal",
        "tags": "合同,印章,法务",
        "summary": "标准模板优先原则与用印审批路径。",
        "content": """模板选用
优先使用法务发布的现行模板；改条款须法务批注后方可外发。

用印
电子章走 OA；实体章须双人在场并登记用印事由、份数、去向。

归档
签约完成后 3 个工作日内上传扫描件至合同档案库。
""",
    },
    {
        "title": "个人信息保护与客户数据脱敏指引",
        "department": "法务部",
        "category": "法务合规",
        "visibility": "secret",
        "tags": "隐私,脱敏,合规",
        "summary": "处理客户个人信息时的最小必要与脱敏要求。",
        "content": """最小必要
仅收集业务必需字段；禁止为「以后也许用得上」囤积数据。

脱敏
日志、截图、演示环境中的手机号、证件号须打码；导出前走审批。

对外提供
向第三方提供数据须签署协议并完成影响评估。
""",
    },
    {
        "title": "季度述职与项目复盘模板",
        "department": "综合部",
        "category": "项目资料",
        "visibility": "internal",
        "tags": "述职,复盘,模板",
        "summary": "述职结构与复盘「做得好/待改进/行动项」。",
        "content": """述职结构
目标回顾 → 关键成果 → 数据证据 → 问题与改进 → 下季计划。

复盘三问
1. 预期与实际差在哪里？
2. 根因是过程还是判断？
3. 下周可落地的一条行动是什么？
""",
    },
    {
        "title": "跨部门协作与需求提单规范",
        "department": "综合部",
        "category": "运营规范",
        "visibility": "internal",
        "tags": "协作,需求,提单",
        "summary": "需求单必填字段与优先级定义。",
        "content": """必填字段
背景、目标、验收标准、期望上线时间、影响范围、对接人。

优先级
P0 故障/合规；P1 影响营收；P2 体验优化；P3 探索项。

拒绝条件
缺少验收标准或无法明确负责人的需求，可退回补充。
""",
    },
    {
        "title": "产品A 权限模型与角色说明",
        "department": "产品部",
        "category": "产品知识",
        "visibility": "internal",
        "tags": "产品A,权限,角色",
        "summary": "管理员、部门负责人、普通成员能力边界。",
        "content": """角色
管理员：用户与权限、全局配置。
部门负责人：本部门文档与成员。
普通成员：按可见性读写。

注意
机密文档不可通过分享链接对外；需临时开放时走审批并设过期时间。
""",
    },
    {
        "title": "内部培训积分与选修课目录（2026）",
        "department": "人事部",
        "category": "培训资料",
        "visibility": "internal",
        "tags": "培训,积分,选修",
        "summary": "年度必修学分与选修课清单。",
        "content": """学分要求
正式员工每年至少完成 8 学分；新员工入职当年另加安全必修 2 学分。

选修方向
项目管理、数据分析入门、客户沟通、信息安全进阶。

记录
课后测评 ≥ 80 分记入学分；缺勤两次取消当季选修资格。
""",
    },
    {
        "title": "办公用品领用与固定资产盘点",
        "department": "综合部",
        "category": "制度规范",
        "visibility": "internal",
        "tags": "办公用品,资产,盘点",
        "summary": "低值易耗品领用额度与年度盘点安排。",
        "content": """领用
按岗位配置标准发放；超额领用需部门负责人批准。

盘点
每年 11 月开展固定资产盘点；账实不符须当周完成差异说明。

报废
设备报废须信息部确认数据已清除，再移交综合部处置。
""",
    },
    {
        "title": "客服值班排班与升级矩阵",
        "department": "运营部",
        "category": "运营规范",
        "visibility": "internal",
        "tags": "客服,值班,升级",
        "summary": "工作日/节假日值班与问题升级路径。",
        "content": """排班
工作日双班；节假日单人值守 + 经理待命。

升级矩阵
L1 一线处理；L2 产品/技术；L3 管理层（资金/舆情）。

时效
L1 首次响应 ≤ 5 分钟；L2 接手 ≤ 30 分钟。
""",
    },
    {
        "title": "对外演示环境申请与数据刷新流程",
        "department": "技术部",
        "category": "技术文档",
        "visibility": "internal",
        "tags": "演示,环境,脱敏",
        "summary": "Demo 环境申请、账号发放与周刷新。",
        "content": """申请
提前 2 个工作日在工单系统提交；写明客户名、时段、演示功能点。

数据
仅使用脱敏样本；禁止导入生产真实客户数据。

刷新
每周一凌晨自动重置；演示前可申请临时加锁。
""",
    },
]

CAT_DESC = {
    "制度规范": "公司制度与管理办法",
    "产品知识": "产品说明、发版与 FAQ",
    "培训资料": "入职与专题培训",
    "项目资料": "项目过程与模板",
    "运营规范": "线索、客成、客服与协作流程",
    "市场物料": "品牌视觉与对外物料规范",
    "法务合规": "合同、印章与隐私合规",
    "技术文档": "研发、发布、备份与 API 规范",
}

USER_SPECS = [
    ("admin", "系统管理员", "admin", "综合部", "admin123"),
    ("hr", "人事小王", "employee", "人事部", "hr123"),
    ("finance", "财务小李", "employee", "财务部", "fin123"),
    ("it", "信息小张", "employee", "信息部", "it123"),
    ("product", "产品小陈", "employee", "产品部", "prod123"),
    ("ops_liu", "运营刘倩", "employee", "运营部", "ops123"),
    ("ops_zhou", "运营周航", "employee", "运营部", "ops123"),
    ("mkt_sun", "市场孙悦", "employee", "市场部", "mkt123"),
    ("mkt_wu", "市场吴桐", "employee", "市场部", "mkt123"),
    ("legal_zhao", "法务赵敏", "employee", "法务部", "leg123"),
    ("tech_gao", "研发高远", "employee", "技术部", "tech123"),
    ("tech_lin", "研发林溪", "employee", "技术部", "tech123"),
    ("tech_xu", "研发徐晨", "employee", "技术部", "tech123"),
    ("hr_fang", "人事方圆", "employee", "人事部", "hr123"),
    ("fin_he", "财务何洁", "employee", "财务部", "fin123"),
    ("it_deng", "信息邓凯", "employee", "信息部", "it123"),
    ("prod_jiang", "产品蒋宁", "employee", "产品部", "prod123"),
    ("admin_assist", "行政助理小叶", "employee", "综合部", "adm123"),
    ("pm_cui", "项目经理崔然", "employee", "综合部", "pm123"),
    ("cs_yuan", "客成袁可", "employee", "运营部", "cs123"),
    ("qa_shi", "测试施雯", "employee", "技术部", "qa123"),
    ("design_pan", "设计潘夏", "employee", "市场部", "des123"),
]

DEMO_QA = [
    (
        "员工年假有几天？",
        "根据《员工年休假管理办法》：连续工作满1年不满10年的年休假5天；满10年不满20年的10天；满20年的15天。申请须提前至少3个工作日在OA提交。",
        "员工年休假管理办法",
    ),
    (
        "差旅住宿标准是多少？",
        "一线城市住宿上限每晚500元，其他城市每晚350元；超标准须说明原因并由分管领导签字。餐补为每人每天100元。",
        "差旅报销制度（节选）",
    ),
    (
        "加班怎么补偿？",
        "工作日加班优先调休，否则按150%计发；休息日优先调休否则200%；法定节假日按300%计发。调休须在加班后90日内使用。",
        "加班与调休管理办法",
    ),
    (
        "采购超过两万元要找谁审批？",
        "超过20000元须分管领导审批，并准备三方比价材料；2000～20000元为部门负责人+财务审批。",
        "采购申请与审批流程",
    ),
    (
        "如何重置产品A密码？",
        "在登录页点击「忘记密码」，输入企业邮箱后收取重置链接，链接15分钟内有效。同一账号最多同时在线3台设备。",
        "产品A 用户手册（摘要）",
    ),
    (
        "知识库怎么用？",
        "可在知识文档中按分类/部门/密级筛选；智能问答会先检索相关片段再生成回答并标注来源；关系图可查看文档与部门、关键词关联。",
        "智慧知识库建设指引",
    ),
    (
        "VPN 远程办公要注意什么？",
        "必须通过公司 VPN；启用双因素认证；公用电脑禁止保存密码；离开座位立即锁屏；外发涉密文件须脱敏并留痕。",
        "VPN与远程办公安全指南",
    ),
    (
        "合同用印怎么走？",
        "优先使用法务现行模板；电子章走 OA；实体章须双人在场并登记。签约后3个工作日内上传扫描件归档。",
        "合同模板选用与印章管理规定",
    ),
    (
        "线索 A 级要多久首触？",
        "A 级线索须 48 小时内完成首次触达；B 级 3 个工作日；C 级进入培育池。跟进须在 CRM 留下纪要。",
        "线索跟进与商机阶段定义",
    ),
    (
        "续费预警什么时候发？",
        "到期前 90/60/30 天分别触发提醒；高价值客户由客成经理人工跟进。连续 14 天无登录会进入风险清单。",
        "客成交接与续费预警机制",
    ),
    (
        "API 密钥多久轮换一次？",
        "生产密钥最长 90 天轮换一次；轮换前后保留 7 天双钥并行。默认限流 60 QPS，超限返回 429。",
        "API 网关限流与密钥轮换规范",
    ),
    (
        "发布窗口是哪段时间？",
        "工作日 10:00–11:30 与 14:00–17:00；周五 16:00 后及节假日前一天原则上冻结发布。",
        "代码评审与发布窗口约定",
    ),
    (
        "演示环境能导生产数据吗？",
        "不可以。仅允许脱敏样本；演示环境申请须提前 2 个工作日提单，每周一凌晨自动重置。",
        "对外演示环境申请与数据刷新流程",
    ),
    (
        "培训学分怎么算？",
        "正式员工每年至少 8 学分；新员工另加安全必修 2 学分。课后测评 ≥80 分记入学分。",
        "内部培训积分与选修课目录（2026）",
    ),
    (
        "发票被驳回常见原因？",
        "抬头/税号错误、科目不匹配、缺审批附件、跨月超期未说明。提交前请按自查清单核对。",
        "发票验真与费用报销常见驳回原因",
    ),
]


def _ensure_users():
    for username, display_name, role, department, password in USER_SPECS:
        user = User.query.filter_by(username=username).first()
        if user:
            # 保持展示名/部门与 seed 一致（不覆盖已改密码）
            user.display_name = display_name
            user.role = role
            user.department = department
            continue
        user = User(
            username=username,
            display_name=display_name,
            role=role,
            department=department,
        )
        user.set_password(password)
        db.session.add(user)
    db.session.flush()


def _ensure_categories():
    cats = {}
    for name, desc in CAT_DESC.items():
        c = Category.query.filter_by(name=name).first()
        if not c:
            c = Category(name=name, description=desc)
            db.session.add(c)
            db.session.flush()
        else:
            c.description = desc
        cats[name] = c
    return cats


def _author_for(department: str, admin: User) -> User:
    mapping = {
        "人事部": "hr",
        "财务部": "finance",
        "信息部": "it",
        "产品部": "product",
        "综合部": "admin",
        "运营部": "ops_liu",
        "市场部": "mkt_sun",
        "法务部": "legal_zhao",
        "技术部": "tech_gao",
    }
    username = mapping.get(department, "admin")
    return User.query.filter_by(username=username).first() or admin


def _purge_test_docs(app):
    """清理调试产生的测试稿，避免污染展示。"""
    junk = Document.query.filter(Document.title.like("%测试稿%")).all()
    for doc in junk:
        db.session.delete(doc)
    if junk:
        db.session.flush()
        app.logger.info("seed: purged %s test documents", len(junk))


def _upsert_docs(cats, admin, app):
    project = get_or_create_node("知识财富库项目", "project", "综合项目实践大作业")
    for dept_name in (
        "综合部",
        "人事部",
        "财务部",
        "信息部",
        "产品部",
        "运营部",
        "市场部",
        "法务部",
        "技术部",
    ):
        dept = get_or_create_node(dept_name, "department", f"{dept_name}组织节点")
        ensure_edge(project, dept, "归属")

    added = 0
    for item in DEMO_DOCS:
        exists = Document.query.filter_by(title=item["title"]).first()
        if exists:
            continue
        cat = cats.get(item["category"])
        if not cat:
            continue
        doc = Document(
            title=item["title"],
            content=item["content"],
            summary=item["summary"],
            department=item["department"],
            visibility=item["visibility"],
            status="published",
            version="1.0",
            tags=item["tags"],
            category_id=cat.id,
            author_id=_author_for(item["department"], admin).id,
        )
        db.session.add(doc)
        db.session.flush()
        rebuild_chunks_for_document(
            doc,
            chunk_size=app.config["CHUNK_SIZE"],
            overlap=app.config["CHUNK_OVERLAP"],
        )
        sync_document_graph(doc)
        ensure_edge(
            get_or_create_node(f"文档:{doc.title}", "document", document_id=doc.id),
            project,
            "支撑",
        )
        added += 1
    return added


def _seed_activity(admin: User, app):
    """补充问答、收藏、审计，让工作台/审计页看起来像真实在用。"""
    users = User.query.order_by(User.id).all()
    docs = Document.query.filter_by(status="published").all()
    if not users or not docs:
        return

    # 收藏：管理员 + 若干员工各收藏几篇
    fav_targets = {
        "admin": ["智慧知识库建设指引", "信息安全分级与访问控制规范", "项目里程碑与周报模板", "API 网关限流与密钥轮换规范"],
        "hr": ["员工年休假管理办法", "绩效考核与目标管理说明", "新员工入职培训手册"],
        "ops_liu": ["线索跟进与商机阶段定义", "客成交接与续费预警机制", "客服值班排班与升级矩阵"],
        "tech_gao": ["代码评审与发布窗口约定", "数据备份与灾难恢复演练计划"],
        "mkt_sun": ["品牌视觉识别（VI）使用简册", "官网与活动页内容发布规范"],
    }
    title_map = {d.title: d for d in docs}
    for uname, titles in fav_targets.items():
        u = User.query.filter_by(username=uname).first()
        if not u:
            continue
        for t in titles:
            d = title_map.get(t)
            if not d:
                continue
            if Favorite.query.filter_by(user_id=u.id, document_id=d.id).first():
                continue
            db.session.add(Favorite(user_id=u.id, document_id=d.id))

    # 问答历史：按用户分散写入（去重 question+user）
    rng = random.Random(20260928)
    base = datetime(2026, 9, 1, 9, 0, 0)
    if QAHistory.query.count() < 40:
        for i, (q, a, src_title) in enumerate(DEMO_QA):
            asker = users[i % len(users)]
            if QAHistory.query.filter_by(user_id=asker.id, question=q).first():
                continue
            src_doc = title_map.get(src_title)
            sources = []
            if src_doc:
                sources = [
                    {
                        "document_id": src_doc.id,
                        "title": src_doc.title,
                        "score": round(0.72 + (i % 5) * 0.04, 2),
                    }
                ]
            created = base + timedelta(days=rng.randint(0, 26), hours=rng.randint(0, 10), minutes=rng.randint(0, 50))
            db.session.add(
                QAHistory(
                    user_id=asker.id,
                    question=q,
                    answer=a,
                    sources=json.dumps(sources, ensure_ascii=False),
                    mode="local",
                    created_at=created,
                )
            )
        # 再补一批变体提问，避免历史全是同一句
        variants = [
            ("年假能跨年吗？", "原则上不跨年累计，确因工作原因未休完的可延期至次年3月31日前使用。"),
            ("会议室最长约多久？", "单次最长2小时；跨半天需部门负责人批准。"),
            ("产品B v2.3 有什么新功能？", "新增知识库问答入口、机密可见性、按部门导出报表等。"),
            ("客服投诉怎么升级？", "先致歉复述；当场不能解决则建单并明确时限；资金纠纷须升级主管。"),
            ("预算超支怎么办？", "须走追加申请，禁止先斩后奏；季度滚动预测偏差超10%需说明。"),
            ("个人信息能不能截图发群？", "日志与截图中的手机号、证件号须打码；对外提供须协议与评估。"),
            ("固定资产什么时候盘点？", "每年11月盘点；账实不符须当周完成差异说明。"),
            ("P0 需求怎么定义？", "故障或合规类为 P0；影响营收为 P1；体验优化 P2；探索项 P3。"),
        ]
        for i, (q, a) in enumerate(variants):
            asker = users[(i + 3) % len(users)]
            if QAHistory.query.filter_by(user_id=asker.id, question=q).first():
                continue
            created = base + timedelta(days=rng.randint(0, 26), hours=rng.randint(8, 18))
            db.session.add(
                QAHistory(
                    user_id=asker.id,
                    question=q,
                    answer=a,
                    sources="[]",
                    mode="local",
                    created_at=created,
                )
            )

    # 审计日志：若偏少则批量补齐多样化动作
    if AuditLog.query.count() < 120:
        actions = [
            ("login", "登录系统"),
            ("logout", "退出系统"),
            ("view_document", None),
            ("create_document", None),
            ("edit_document", None),
            ("ask_qa", None),
        ]
        for i in range(160):
            u = users[i % len(users)]
            action, detail = actions[i % len(actions)]
            doc = docs[i % len(docs)]
            if action == "view_document":
                detail = f"查看文档 #{doc.id} {doc.title}"
            elif action == "create_document":
                detail = f"创建文档 #{doc.id} {doc.title}"
            elif action == "edit_document":
                detail = f"编辑文档 #{doc.id} {doc.title}"
            elif action == "ask_qa":
                detail = f"提问：{DEMO_QA[i % len(DEMO_QA)][0]}"
            created = base + timedelta(days=rng.randint(0, 27), hours=rng.randint(0, 23), minutes=rng.randint(0, 59))
            db.session.add(
                AuditLog(
                    user_id=u.id,
                    action=action,
                    detail=detail,
                    created_at=created,
                )
            )

    db.session.flush()
    app.logger.info(
        "seed activity: users=%s docs=%s qa=%s audits=%s favs=%s",
        User.query.count(),
        Document.query.count(),
        QAHistory.query.count(),
        AuditLog.query.count(),
        Favorite.query.count(),
    )


def seed_all(app) -> None:
    with app.app_context():
        db.create_all()
        _ensure_users()
        cats = _ensure_categories()
        admin = User.query.filter_by(username="admin").first()
        _purge_test_docs(app)
        added = _upsert_docs(cats, admin, app)
        _seed_activity(admin, app)
        db.session.commit()
        if added:
            app.logger.info("seed: added %s demo documents", added)
