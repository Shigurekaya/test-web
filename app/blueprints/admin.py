from collections import Counter

from flask import Blueprint, render_template
from flask_login import login_required

from app.models import AuditLog, Document, User
from app.utils import ACTION_LABELS, admin_required

bp = Blueprint("admin", __name__, url_prefix="/admin")

DEPARTMENTS = [
    "综合部",
    "人事部",
    "财务部",
    "信息部",
    "产品部",
    "运营部",
    "市场部",
    "法务部",
    "技术部",
]


@bp.route("/users")
@login_required
@admin_required
def users():
    users = User.query.order_by(User.id).all()
    doc_counts = Counter(
        row[0]
        for row in Document.query.with_entities(Document.author_id).filter(Document.author_id.isnot(None)).all()
    )
    admin_count = sum(1 for u in users if u.role == "admin")
    employee_count = len(users) - admin_count
    return render_template(
        "admin/users.html",
        users=users,
        departments=DEPARTMENTS,
        doc_counts=doc_counts,
        admin_count=admin_count,
        employee_count=employee_count,
    )


@bp.route("/audits")
@login_required
@admin_required
def audits():
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(200).all()
    total = AuditLog.query.count()
    action_stats = Counter(a for (a,) in AuditLog.query.with_entities(AuditLog.action).all())
    return render_template(
        "admin/audits.html",
        logs=logs,
        total=total,
        action_stats=action_stats,
        action_labels=ACTION_LABELS,
    )
