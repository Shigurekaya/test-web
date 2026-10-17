from collections import Counter

from flask import Blueprint, render_template, request
from flask_login import login_required

from app.models import AuditLog, Document, User
from app.utils import ACTION_LABELS, DEPARTMENTS, admin_required

bp = Blueprint("admin", __name__, url_prefix="/admin")


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


PER_PAGE = 25


@bp.route("/audits")
@login_required
@admin_required
def audits():
    """审计日志：服务端分页 + 服务端筛选。

    原来一次性取出 200 条、只在前端用 JS 隐藏行，页面高度 6000+ 像素，
    且筛选只是「看不看得到」而不是「查不查得到」。改为按 SQL 过滤并分页。
    """
    action = request.args.get("action", "").strip()
    user_kw = request.args.get("user", "").strip()
    detail_kw = request.args.get("detail", "").strip()
    page = max(request.args.get("page", 1, type=int) or 1, 1)

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
    pages = max((total + PER_PAGE - 1) // PER_PAGE, 1)
    page = min(page, pages)
    logs = (
        query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset((page - 1) * PER_PAGE)
        .limit(PER_PAGE)
        .all()
    )

    action_stats = Counter(a for (a,) in AuditLog.query.with_entities(AuditLog.action).all())
    return render_template(
        "admin/audits.html",
        logs=logs,
        total=total,
        pages=pages,
        page=page,
        per_page=PER_PAGE,
        action=action,
        user_kw=user_kw,
        detail_kw=detail_kw,
        has_filter=bool(action or user_kw or detail_kw),
        action_stats=action_stats,
        action_labels=ACTION_LABELS,
    )
