"""初始化 / 增量补充演示数据。"""
from __future__ import annotations

from app.extensions import db
from app.models import Category, Document, User
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
]


CAT_DESC = {
    "制度规范": "公司制度与管理办法",
    "产品知识": "产品说明、发版与 FAQ",
    "培训资料": "入职与专题培训",
    "项目资料": "项目过程与模板",
}


def _ensure_users():
    specs = [
        ("admin", "系统管理员", "admin", "综合部", "admin123"),
        ("hr", "人事小王", "employee", "人事部", "hr123"),
        ("finance", "财务小李", "employee", "财务部", "fin123"),
        ("it", "信息小张", "employee", "信息部", "it123"),
        ("product", "产品小陈", "employee", "产品部", "prod123"),
    ]
    for username, display_name, role, department, password in specs:
        user = User.query.filter_by(username=username).first()
        if user:
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
        cats[name] = c
    return cats


def _author_for(department: str, admin: User) -> User:
    mapping = {
        "人事部": "hr",
        "财务部": "finance",
        "信息部": "it",
        "产品部": "product",
        "综合部": "admin",
    }
    username = mapping.get(department, "admin")
    return User.query.filter_by(username=username).first() or admin


def _upsert_docs(cats, admin, app):
    project = get_or_create_node("知识财富库项目", "project", "综合项目实践大作业")
    dept = get_or_create_node("综合部", "department", "综合管理部门")
    ensure_edge(project, dept, "归属")

    added = 0
    for item in DEMO_DOCS:
        exists = Document.query.filter_by(title=item["title"]).first()
        if exists:
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
            category_id=cats[item["category"]].id,
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


def seed_all(app) -> None:
    with app.app_context():
        db.create_all()
        _ensure_users()
        cats = _ensure_categories()
        admin = User.query.filter_by(username="admin").first()
        added = _upsert_docs(cats, admin, app)
        db.session.commit()
        if added:
            app.logger.info("seed: added %s demo documents", added)
