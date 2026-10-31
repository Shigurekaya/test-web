"""JSON REST API for the Vue frontend.

The legacy server-rendered pages remain available, while this module provides a
stable frontend/backend boundary for the separated Vue application.
"""

from __future__ import annotations

import json
from datetime import timedelta
from functools import wraps

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_user, logout_user
from sqlalchemy import func, text

from app import meta
from app.extensions import db
from app.models import (
    AuditLog,
    Category,
    Document,
    Favorite,
    GraphEdge,
    GraphNode,
    KnowledgeChunk,
    QAHistory,
    User,
)
from app.qa_content import quick_questions_for, suggestions_for
from app.services.graph import (
    ensure_edge,
    get_or_create_node,
    graph_payload,
    remove_document_graph,
    sync_document_graph,
)
from app.services.qa_history import recent_unique_qa
from app.services.rag import (
    ask,
    can_view_document,
    group_hits_by_document,
    rank_documents,
    rebuild_chunks_for_document,
    related_documents,
    searchable_documents,
)
from app.utils import (
    ACTION_LABELS,
    DEMO_ACCOUNTS,
    DEPARTMENTS,
    MODE_LABELS,
    ROLE_LABELS,
    STATUS_LABELS,
    VISIBILITY_LABELS,
    audit_detail,
    auto_summary,
    format_dt,
    normalize_choice,
    now_naive,
)

bp = Blueprint("api", __name__, url_prefix="/api")


def api_login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"error": "请先登录后再访问", "code": "AUTH_REQUIRED"}), 401
        return view(*args, **kwargs)

    return wrapped


def api_admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"error": "请先登录后再访问", "code": "AUTH_REQUIRED"}), 401
        if not current_user.is_admin:
            return jsonify({"error": "需要管理员权限", "code": "FORBIDDEN"}), 403
        return view(*args, **kwargs)

    return wrapped


def _json_body() -> dict:
    data = request.get_json(silent=True)
    if isinstance(data, dict):
        return data
    return request.form.to_dict()


def _not_found(entity: str = "资源"):
    return jsonify({"error": f"{entity}不存在", "code": "NOT_FOUND"}), 404


def _forbidden(message: str = "无权执行该操作"):
    return jsonify({"error": message, "code": "FORBIDDEN"}), 403


def _validation(message: str, fields: dict | None = None):
    payload = {"error": message, "code": "VALIDATION_ERROR"}
    if fields:
        payload["fields"] = fields
    return jsonify(payload), 400


def _user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role,
        "role_label": ROLE_LABELS.get(user.role, user.role),
        "department": user.department,
        "is_admin": user.is_admin,
        "created_at": format_dt(user.created_at),
    }


def _doc_payload(
    doc: Document, *, include_content: bool = False, is_favorite: bool = False
) -> dict:
    payload = {
        "id": doc.id,
        "title": doc.title,
        "summary": doc.summary or auto_summary(doc.content, limit=140),
        "department": doc.department,
        "visibility": doc.visibility,
        "visibility_label": VISIBILITY_LABELS.get(doc.visibility, doc.visibility),
        "status": doc.status,
        "status_label": STATUS_LABELS.get(doc.status, doc.status),
        "version": doc.version,
        "tags": doc.tag_list,
        "category_id": doc.category_id,
        "category": doc.category.name if doc.category else "未分类",
        "author_id": doc.author_id,
        "author": doc.author.display_name if doc.author else "未知作者",
        "created_at": format_dt(doc.created_at),
        "updated_at": format_dt(doc.updated_at),
        "char_count": len(doc.content or ""),
        "chunk_count": len(doc.chunks or []),
        "is_favorite": is_favorite,
    }
    if include_content:
        payload["content"] = doc.content
    return payload


def _qa_payload(item: QAHistory, *, include_sources: bool = False) -> dict:
    payload = {
        "id": item.id,
        "question": item.question,
        "answer": item.answer,
        "mode": item.mode,
        "mode_label": MODE_LABELS.get(item.mode, item.mode),
        "created_at": format_dt(item.created_at),
    }
    if include_sources:
        try:
            payload["sources"] = json.loads(item.sources or "[]")
        except json.JSONDecodeError:
            payload["sources"] = []
    return payload


def _audit_payload(log: AuditLog) -> dict:
    return {
        "id": log.id,
        "user_id": log.user_id,
        "username": log.user.username if log.user else "匿名/未知",
        "action": log.action,
        "action_label": ACTION_LABELS.get(log.action, log.action),
        "detail": log.detail or "",
        "created_at": format_dt(log.created_at),
    }


@bp.get("")
@bp.get("/")
def index():
    return jsonify(
        {
            "name": meta.APP_NAME,
            "version": meta.APP_VERSION,
            "description": "企业知识管理、检索问答与关系图 REST API",
            "health": "/api/health",
        }
    )


@bp.get("/health")
def health():
    try:
        db.session.execute(text("SELECT 1"))
        ok = True
    except Exception:  # noqa: BLE001
        ok = False
    return jsonify(
        {"status": "ok" if ok else "degraded", "database": ok, "version": meta.APP_VERSION}
    )


@bp.get("/meta")
def public_meta():
    return jsonify(
        {
            "name": meta.APP_NAME,
            "name_en": meta.APP_NAME_EN,
            "version": meta.APP_VERSION,
            "tagline": meta.TAGLINE,
            "tech_stack": meta.TECH_STACK,
            "features": list(meta.FEATURES),
            "scenarios": list(meta.SCENARIOS),
            "demo_accounts": list(DEMO_ACCOUNTS),
            "departments": DEPARTMENTS,
            "visibility_labels": VISIBILITY_LABELS,
            "status_labels": STATUS_LABELS,
            "role_labels": ROLE_LABELS,
        }
    )


@bp.post("/auth/login")
def login():
    from app.blueprints.auth import login_limiter

    if login_limiter.is_locked_from_request():
        retry_after = login_limiter.retry_after_from_request()
        return (
            jsonify(
                {
                    "error": f"登录失败次数过多，请 {retry_after} 秒后再试",
                    "retry_after": retry_after,
                }
            ),
            429,
        )

    data = _json_body()
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    user = User.query.filter_by(username=username).first()

    if not user or not user.check_password(password):
        login_limiter.record_failure_from_request()
        db.session.add(
            AuditLog(
                user_id=user.id if user else None,
                action="login_failed",
                detail=audit_detail("login_failed", username=username or None),
            )
        )
        db.session.commit()
        return jsonify({"error": "用户名或密码错误", "code": "INVALID_CREDENTIALS"}), 401

    login_limiter.clear_from_request()
    login_user(user, remember=bool(data.get("remember")))
    db.session.add(
        AuditLog(
            user_id=user.id, action="login", detail=audit_detail("login", username=user.username)
        )
    )
    db.session.commit()
    return jsonify({"user": _user_payload(user), "message": "登录成功"})


@bp.get("/auth/session")
def session_info():
    """Return the current session without treating anonymous users as an error."""
    user = _user_payload(current_user) if current_user.is_authenticated else None
    return jsonify({"user": user})


@bp.get("/auth/me")
@api_login_required
def me():
    return jsonify({"user": _user_payload(current_user)})


@bp.post("/auth/logout")
@api_login_required
def logout():
    user = current_user
    db.session.add(
        AuditLog(
            user_id=user.id, action="logout", detail=audit_detail("logout", username=user.username)
        )
    )
    db.session.commit()
    logout_user()
    return jsonify({"message": "已退出登录"})


@bp.get("/dashboard")
@api_login_required
def dashboard():
    docs = searchable_documents(current_user)
    favorite_ids = {
        row[0]
        for row in Favorite.query.with_entities(Favorite.document_id)
        .filter(Favorite.user_id == current_user.id)
        .all()
    }
    week_ago = now_naive() - timedelta(days=7)
    qa_total = QAHistory.query.filter_by(user_id=current_user.id).count()
    qa_week = (
        QAHistory.query.filter_by(user_id=current_user.id)
        .filter(QAHistory.created_at >= week_ago)
        .count()
    )

    dept_counter: dict[str, int] = {}
    cat_counter: dict[str, int] = {}
    for doc in docs:
        dept_counter[doc.department] = dept_counter.get(doc.department, 0) + 1
        cat_name = doc.category.name if doc.category else "未分类"
        cat_counter[cat_name] = cat_counter.get(cat_name, 0) + 1

    recent_docs = [_doc_payload(doc, is_favorite=doc.id in favorite_ids) for doc in docs[:6]]
    recent_qa = [_qa_payload(item) for item in recent_unique_qa(current_user.id, limit=6)]
    recent_logs = []
    if current_user.is_admin:
        recent_logs = [
            _audit_payload(log)
            for log in AuditLog.query.order_by(AuditLog.created_at.desc()).limit(8).all()
        ]

    return jsonify(
        {
            "stats": {
                "visible_documents": len(docs),
                "favorites": len(favorite_ids),
                "qa_total": qa_total,
                "qa_week": qa_week,
                "nodes": GraphNode.query.count(),
                "edges": GraphEdge.query.count(),
            },
            "charts": {
                "departments": [
                    {"name": name, "value": count}
                    for name, count in sorted(
                        dept_counter.items(), key=lambda item: (-item[1], item[0])
                    )
                ],
                "categories": [
                    {"name": name, "value": count}
                    for name, count in sorted(
                        cat_counter.items(), key=lambda item: (-item[1], item[0])
                    )[:8]
                ],
            },
            "recent_documents": recent_docs,
            "recent_qa": recent_qa,
            "recent_logs": recent_logs,
            "quick_questions": quick_questions_for(current_user),
        }
    )


@bp.get("/documents")
@api_login_required
def list_documents():
    q = request.args.get("q", "").strip()
    category_id = request.args.get("category_id", type=int)
    department = request.args.get("department", "").strip()
    visibility = request.args.get("visibility", "").strip()
    sort = request.args.get("sort", "updated").strip() or "updated"
    page = max(request.args.get("page", 1, type=int) or 1, 1)
    per_page = min(max(request.args.get("per_page", 9, type=int) or 9, 1), 50)

    docs = searchable_documents(current_user)
    if category_id:
        docs = [doc for doc in docs if doc.category_id == category_id]
    if department:
        docs = [doc for doc in docs if doc.department == department]
    if visibility:
        docs = [doc for doc in docs if doc.visibility == visibility]

    if q:
        docs = rank_documents(docs, q)
    elif sort == "title":
        docs = sorted(docs, key=lambda doc: doc.title or "")
    elif sort == "department":
        docs = sorted(
            docs,
            key=lambda doc: (
                doc.department or "",
                -(doc.updated_at.timestamp() if doc.updated_at else 0),
            ),
        )
    else:
        docs = sorted(docs, key=lambda doc: doc.updated_at or now_naive(), reverse=True)

    total = len(docs)
    pages = max((total + per_page - 1) // per_page, 1)
    page = min(page, pages)
    start = (page - 1) * per_page
    favorite_ids = {
        row[0]
        for row in Favorite.query.with_entities(Favorite.document_id)
        .filter(Favorite.user_id == current_user.id)
        .all()
    }
    return jsonify(
        {
            "items": [
                _doc_payload(doc, is_favorite=doc.id in favorite_ids)
                for doc in docs[start : start + per_page]
            ],
            "categories": [
                {"id": cat.id, "name": cat.name, "description": cat.description or ""}
                for cat in Category.query.order_by(Category.name).all()
            ],
            "pagination": {"page": page, "pages": pages, "total": total, "per_page": per_page},
            "filters": {
                "q": q,
                "category_id": category_id,
                "department": department,
                "visibility": visibility,
                "sort": sort,
            },
            "departments": DEPARTMENTS,
        }
    )


@bp.get("/documents/favorites")
@api_login_required
def favorite_documents():
    items = (
        Favorite.query.filter_by(user_id=current_user.id).order_by(Favorite.created_at.desc()).all()
    )
    return jsonify(
        {
            "items": [
                _doc_payload(item.document, is_favorite=True)
                for item in items
                if item.document and can_view_document(current_user, item.document)
            ]
        }
    )


@bp.get("/documents/<int:doc_id>")
@api_login_required
def document_detail(doc_id: int):
    doc = db.session.get(Document, doc_id)
    if not doc:
        return _not_found("文档")
    if not can_view_document(current_user, doc):
        return _forbidden("无权查看该文档")
    if doc.status != "published" and not (
        current_user.is_admin or doc.author_id == current_user.id
    ):
        return _forbidden("该文档尚未发布")

    fav = Favorite.query.filter_by(user_id=current_user.id, document_id=doc.id).first()
    recent = (
        AuditLog.query.filter_by(user_id=current_user.id, action="view_document")
        .filter(AuditLog.created_at >= now_naive() - timedelta(minutes=2))
        .order_by(AuditLog.created_at.desc())
        .limit(5)
        .all()
    )
    if not any(f"#{doc.id} " in (log.detail or "") for log in recent):
        db.session.add(
            AuditLog(
                user_id=current_user.id,
                action="view_document",
                detail=audit_detail("view_document", doc_id=doc.id, title=doc.title),
            )
        )
        db.session.commit()

    return jsonify(
        {
            "document": _doc_payload(doc, include_content=True, is_favorite=bool(fav)),
            "related": [
                _doc_payload(item) for item in related_documents(doc, current_user, limit=4)
            ],
            "can_edit": bool(current_user.is_admin or doc.author_id == current_user.id),
        }
    )


def _apply_document_payload(doc: Document, data: dict):
    title = (data.get("title") or "").strip()
    content = (data.get("content") or "").strip()
    if not title or not content:
        return None, "标题与正文不能为空"

    category_id = data.get("category_id")
    category_id = int(category_id) if str(category_id or "").isdigit() else None
    if category_id and not db.session.get(Category, category_id):
        return None, "所选分类不存在"

    doc.title = title
    doc.content = content
    doc.summary = (data.get("summary") or "").strip()[:500] or auto_summary(content)
    doc.department = (
        data.get("department")
        if data.get("department") in DEPARTMENTS
        else (doc.department or current_user.department)
    )
    doc.visibility = normalize_choice(data.get("visibility"), VISIBILITY_LABELS, "internal")
    doc.status = normalize_choice(data.get("status"), STATUS_LABELS, "published")
    doc.version = (data.get("version") or "1.0").strip() or "1.0"
    tags = data.get("tags") or []
    if isinstance(tags, list):
        tags = ",".join(str(tag).strip() for tag in tags if str(tag).strip())
    doc.tags = str(tags).strip()
    doc.category_id = category_id
    return doc, None


def _finalize_document(doc: Document, action: str):
    db.session.flush()
    rebuild_chunks_for_document(
        doc,
        chunk_size=current_app.config["CHUNK_SIZE"],
        overlap=current_app.config["CHUNK_OVERLAP"],
    )
    sync_document_graph(doc)
    db.session.add(
        AuditLog(
            user_id=current_user.id,
            action=action,
            detail=audit_detail(action, doc_id=doc.id, title=doc.title),
        )
    )
    db.session.commit()


@bp.post("/documents")
@api_login_required
def create_document():
    data = _json_body()
    doc = Document(author_id=current_user.id)
    doc, error = _apply_document_payload(doc, data)
    if error:
        return _validation(error)
    db.session.add(doc)
    _finalize_document(doc, "create_document")
    return jsonify(
        {"document": _doc_payload(doc, include_content=True), "message": "文档已创建"}
    ), 201


@bp.put("/documents/<int:doc_id>")
@api_login_required
def update_document(doc_id: int):
    doc = db.session.get(Document, doc_id)
    if not doc:
        return _not_found("文档")
    if not (current_user.is_admin or doc.author_id == current_user.id):
        return _forbidden("只能编辑自己创建的文档")
    doc, error = _apply_document_payload(doc, _json_body())
    if error:
        return _validation(error)
    _finalize_document(doc, "edit_document")
    return jsonify({"document": _doc_payload(doc, include_content=True), "message": "文档已更新"})


@bp.delete("/documents/<int:doc_id>")
@api_login_required
def delete_document(doc_id: int):
    doc = db.session.get(Document, doc_id)
    if not doc:
        return _not_found("文档")
    if not (current_user.is_admin or doc.author_id == current_user.id):
        return _forbidden("只能删除自己创建的文档")
    title = doc.title
    remove_document_graph(doc)
    db.session.delete(doc)
    db.session.add(
        AuditLog(
            user_id=current_user.id,
            action="delete_document",
            detail=audit_detail("delete_document", doc_id=doc_id, title=title),
        )
    )
    db.session.commit()
    return jsonify({"message": "文档已删除"})


@bp.post("/documents/<int:doc_id>/favorite")
@api_login_required
def toggle_favorite(doc_id: int):
    doc = db.session.get(Document, doc_id)
    if not doc:
        return _not_found("文档")
    if not can_view_document(current_user, doc):
        return _forbidden("无权收藏该文档")
    fav = Favorite.query.filter_by(user_id=current_user.id, document_id=doc.id).first()
    if fav:
        db.session.delete(fav)
        active = False
    else:
        db.session.add(Favorite(user_id=current_user.id, document_id=doc.id))
        active = True
    db.session.commit()
    return jsonify({"is_favorite": active, "message": "已收藏" if active else "已取消收藏"})


@bp.get("/categories")
@api_login_required
def categories():
    counts = {
        row[0]: row[1]
        for row in db.session.query(Document.category_id, func.count(Document.id))
        .filter(Document.category_id.isnot(None))
        .group_by(Document.category_id)
        .all()
    }
    return jsonify(
        {
            "items": [
                {
                    "id": item.id,
                    "name": item.name,
                    "description": item.description or "",
                    "document_count": counts.get(item.id, 0),
                }
                for item in Category.query.order_by(Category.id).all()
            ]
        }
    )


@bp.post("/categories")
@api_admin_required
def create_category():
    data = _json_body()
    name = (data.get("name") or "").strip()
    if not name:
        return _validation("分类名称不能为空")
    if Category.query.filter_by(name=name).first():
        return _validation("分类名称已存在")
    category = Category(name=name, description=(data.get("description") or "").strip())
    db.session.add(category)
    db.session.commit()
    return jsonify({"id": category.id, "name": category.name, "message": "分类已添加"}), 201


@bp.get("/qa")
@api_login_required
def qa_page():
    history = recent_unique_qa(current_user.id, limit=20)
    return jsonify(
        {
            "suggestions": suggestions_for(current_user),
            "quick_questions": quick_questions_for(current_user),
            "llm_enabled": bool(current_app.config.get("OPENAI_API_KEY")),
            "history": [_qa_payload(item) for item in history],
        }
    )


@bp.post("/qa/ask")
@api_login_required
def ask_question():
    question = (_json_body().get("question") or "").strip()
    if not question:
        return _validation("问题不能为空")
    result = ask(question, current_user, current_app.config)
    db.session.add(
        AuditLog(
            user_id=current_user.id,
            action="ask_qa",
            detail=audit_detail("ask_qa", question=question),
        )
    )
    db.session.commit()
    return jsonify(
        {
            "answer": result["answer"],
            "mode": result["mode"],
            "mode_label": MODE_LABELS.get(result["mode"], result["mode"]),
            "history_id": result["history_id"],
            "sources": group_hits_by_document(result["hits"]),
            "fragments": result["hits"],
        }
    )


@bp.get("/qa/history/<int:history_id>")
@api_login_required
def qa_history_detail(history_id: int):
    item = db.session.get(QAHistory, history_id)
    if not item:
        return _not_found("问答记录")
    if item.user_id != current_user.id and not current_user.is_admin:
        return _forbidden("无权查看该问答记录")
    return jsonify({"item": _qa_payload(item, include_sources=True)})


def _visible_graph_payload() -> dict:
    payload = graph_payload()
    allowed_doc_ids = {doc.id for doc in searchable_documents(current_user)}
    nodes = {node["id"]: node for node in payload["nodes"]}
    visible_doc_nodes = {
        node["id"] for node in payload["nodes"] if node.get("document_id") in allowed_doc_ids
    }
    visible_node_ids = set(visible_doc_nodes)
    links = []
    for link in payload["links"]:
        if link["source"] in visible_doc_nodes or link["target"] in visible_doc_nodes:
            links.append(link)
            visible_node_ids.add(link["source"])
            visible_node_ids.add(link["target"])
    return {
        "nodes": [nodes[node_id] for node_id in visible_node_ids if node_id in nodes],
        "links": [
            link
            for link in links
            if link["source"] in visible_node_ids and link["target"] in visible_node_ids
        ],
        "categories": payload["categories"],
    }


@bp.get("/graph")
@api_login_required
def graph_view():
    return jsonify(_visible_graph_payload())


@bp.get("/graph/manage")
@api_admin_required
def graph_manage():
    nodes = GraphNode.query.order_by(GraphNode.id.desc()).limit(60).all()
    edges = GraphEdge.query.order_by(GraphEdge.id.desc()).limit(60).all()
    return jsonify(
        {
            "nodes": [
                {
                    "id": node.id,
                    "name": node.name,
                    "node_type": node.node_type,
                    "description": node.description or "",
                }
                for node in nodes
            ],
            "edges": [
                {
                    "id": edge.id,
                    "source": edge.source.name,
                    "target": edge.target.name,
                    "relation": edge.relation,
                }
                for edge in edges
            ],
            "node_types": ["document", "department", "project", "keyword", "concept"],
        }
    )


@bp.post("/graph/nodes")
@api_admin_required
def add_graph_node():
    data = _json_body()
    name = (data.get("name") or "").strip()
    if not name:
        return _validation("节点名称不能为空")
    node = get_or_create_node(
        name,
        (data.get("node_type") or "concept").strip(),
        (data.get("description") or "").strip(),
    )
    db.session.commit()
    return jsonify({"id": node.id, "name": node.name, "message": "节点已添加"}), 201


@bp.post("/graph/edges")
@api_admin_required
def add_graph_edge():
    data = _json_body()
    source_name = (data.get("source_name") or "").strip()
    target_name = (data.get("target_name") or "").strip()
    relation = (data.get("relation") or "关联").strip() or "关联"
    if not source_name or not target_name:
        return _validation("起点和终点名称不能为空")
    source = get_or_create_node(source_name, "concept")
    target = get_or_create_node(target_name, "concept")
    ensure_edge(source, target, relation)
    db.session.commit()
    return jsonify({"message": "关系已添加"}), 201


@bp.get("/admin/users")
@api_admin_required
def admin_users():
    users = User.query.order_by(User.id).all()
    counts = {
        row[0]: row[1]
        for row in db.session.query(Document.author_id, func.count(Document.id))
        .filter(Document.author_id.isnot(None))
        .group_by(Document.author_id)
        .all()
    }
    return jsonify(
        {
            "items": [
                {**_user_payload(user), "document_count": counts.get(user.id, 0)} for user in users
            ],
            "summary": {
                "total": len(users),
                "admins": sum(1 for user in users if user.is_admin),
                "employees": sum(1 for user in users if not user.is_admin),
            },
        }
    )


@bp.get("/admin/audits")
@api_admin_required
def admin_audits():
    action = request.args.get("action", "").strip()
    user_kw = request.args.get("user", "").strip()
    detail_kw = request.args.get("detail", "").strip()
    page = max(request.args.get("page", 1, type=int) or 1, 1)
    per_page = 25

    query = AuditLog.query
    if action in ACTION_LABELS:
        query = query.filter(AuditLog.action == action)
    if detail_kw:
        query = query.filter(AuditLog.detail.like(f"%{detail_kw}%"))
    if user_kw:
        query = query.join(User, AuditLog.user_id == User.id, isouter=True).filter(
            User.username.like(f"%{user_kw}%")
        )

    total = query.count()
    pages = max((total + per_page - 1) // per_page, 1)
    page = min(page, pages)
    logs = (
        query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    action_stats = {
        row[0]: row[1]
        for row in db.session.query(AuditLog.action, func.count(AuditLog.id))
        .group_by(AuditLog.action)
        .all()
    }
    return jsonify(
        {
            "items": [_audit_payload(log) for log in logs],
            "pagination": {"page": page, "pages": pages, "total": total, "per_page": per_page},
            "action_stats": action_stats,
            "actions": [{"value": key, "label": value} for key, value in ACTION_LABELS.items()],
        }
    )


@bp.get("/about")
@api_login_required
def about():
    visible_docs = searchable_documents(current_user)
    visible_ids = [doc.id for doc in visible_docs]
    visible_chunks = (
        KnowledgeChunk.query.filter(KnowledgeChunk.document_id.in_(visible_ids)).count()
        if visible_ids
        else 0
    )
    return jsonify(
        {
            "app": {
                "name": meta.APP_NAME,
                "name_en": meta.APP_NAME_EN,
                "version": meta.APP_VERSION,
                "tagline": meta.TAGLINE,
                "tech_stack": meta.TECH_STACK,
                "features": list(meta.FEATURES),
                "scenarios": list(meta.SCENARIOS),
            },
            "stats": {
                "documents": len(visible_docs),
                "chunks": visible_chunks,
                "nodes": GraphNode.query.count(),
                "edges": GraphEdge.query.count(),
                "qa": QAHistory.query.filter_by(user_id=current_user.id).count(),
            },
            "scope": "本人可见范围",
        }
    )
