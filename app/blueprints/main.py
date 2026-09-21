from flask import Blueprint, jsonify, render_template
from flask_login import login_required, current_user
from sqlalchemy import text

from app import meta
from app.extensions import db
from app.models import AuditLog, Document, Favorite, GraphEdge, GraphNode, KnowledgeChunk, QAHistory
from app.services.rag import searchable_documents

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    from flask import redirect, url_for
    from flask_login import current_user as cu

    if cu.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("auth.login"))


@bp.route("/dashboard")
@login_required
def dashboard():
    docs = searchable_documents(current_user)
    fav_count = Favorite.query.filter_by(user_id=current_user.id).count()
    qa_count = QAHistory.query.filter_by(user_id=current_user.id).count()
    recent_docs = docs[:5]
    recent_qa = (
        QAHistory.query.filter_by(user_id=current_user.id)
        .order_by(QAHistory.created_at.desc())
        .limit(5)
        .all()
    )
    recent_logs = []
    if current_user.is_admin:
        recent_logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(8).all()
    return render_template(
        "main/dashboard.html",
        doc_count=len(docs),
        fav_count=fav_count,
        qa_count=qa_count,
        recent_docs=recent_docs,
        recent_qa=recent_qa,
        recent_logs=recent_logs,
        total_published=Document.query.filter_by(status="published").count(),
        chunk_count=KnowledgeChunk.query.count(),
        node_count=GraphNode.query.count(),
        edge_count=GraphEdge.query.count(),
    )


@bp.route("/about")
@login_required
def about():
    return render_template(
        "main/about.html",
        meta=meta,
        stats={
            "documents": Document.query.count(),
            "chunks": KnowledgeChunk.query.count(),
            "nodes": GraphNode.query.count(),
            "edges": GraphEdge.query.count(),
            "qa": QAHistory.query.count(),
        },
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
