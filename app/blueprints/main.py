from collections import Counter
from datetime import timedelta

from flask import Blueprint, jsonify, render_template
from flask_login import current_user, login_required
from sqlalchemy import text

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
from app.services.rag import searchable_documents
from app.utils import utcnow

bp = Blueprint("main", __name__)

QUICK_QUESTIONS = [
    "员工年假有几天？",
    "差旅住宿标准是多少？",
    "加班怎么补偿？",
    "采购超过两万元要找谁审批？",
]


@bp.route("/")
def index():
    from flask import redirect, url_for
    from flask_login import current_user as cu

    if cu.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("main/index.html")


@bp.route("/dashboard")
@login_required
def dashboard():
    docs = searchable_documents(current_user)
    fav_count = Favorite.query.filter_by(user_id=current_user.id).count()
    qa_count = QAHistory.query.filter_by(user_id=current_user.id).count()
    week_ago = utcnow() - timedelta(days=7)
    qa_week = (
        QAHistory.query.filter_by(user_id=current_user.id)
        .filter(QAHistory.created_at >= week_ago)
        .count()
    )
    recent_docs = docs[:6]
    recent_qa = (
        QAHistory.query.filter_by(user_id=current_user.id)
        .order_by(QAHistory.created_at.desc())
        .limit(6)
        .all()
    )
    recent_logs = []
    if current_user.is_admin:
        recent_logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(10).all()
    dept_counter = Counter(d.department for d in docs if d.department)
    dept_stats = sorted(dept_counter.items(), key=lambda x: (-x[1], x[0]))
    cat_counter = Counter((d.category.name if d.category else "未分类") for d in docs)
    cat_stats = sorted(cat_counter.items(), key=lambda x: (-x[1], x[0]))[:6]
    return render_template(
        "main/dashboard.html",
        doc_count=len(docs),
        fav_count=fav_count,
        qa_count=qa_count,
        qa_week=qa_week,
        recent_docs=recent_docs,
        recent_qa=recent_qa,
        recent_logs=recent_logs,
        total_published=Document.query.filter_by(status="published").count(),
        chunk_count=KnowledgeChunk.query.count(),
        node_count=GraphNode.query.count(),
        edge_count=GraphEdge.query.count(),
        category_count=Category.query.count(),
        user_count=User.query.count(),
        audit_count=AuditLog.query.count(),
        dept_stats=dept_stats,
        cat_stats=cat_stats,
        quick_questions=QUICK_QUESTIONS,
    )


@bp.route("/about")
@login_required
def about():
    """关于页。

    统计口径跟随当前用户的可见范围：机密文档的只数、以及由此切分出的片段数
    属于权限信息，直接显示全库数字会让看不到文档的人推断出库里有多少机密材料。
    图谱节点/边与问答历史保持全量口径（前者是结构概览，后者只统计自己的提问）。
    """
    visible_docs = searchable_documents(current_user)
    visible_ids = [d.id for d in visible_docs]
    visible_chunks = (
        KnowledgeChunk.query.filter(KnowledgeChunk.document_id.in_(visible_ids)).count()
        if visible_ids
        else 0
    )
    return render_template(
        "main/about.html",
        meta=meta,
        stats={
            "documents": len(visible_docs),
            "chunks": visible_chunks,
            "nodes": GraphNode.query.count(),
            "edges": GraphEdge.query.count(),
            "qa": QAHistory.query.filter_by(user_id=current_user.id).count(),
        },
        stats_scope="本人可见范围",
    )


@bp.route("/health")
def health():
    try:
        db.session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:  # noqa: BLE001
        db_ok = False
    return jsonify(
        {
            "status": "ok" if db_ok else "degraded",
            "app": meta.APP_NAME,
            "version": meta.APP_VERSION,
            "database": db_ok,
        }
    )
