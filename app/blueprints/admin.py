from flask import Blueprint, render_template
from flask_login import login_required

from app.models import AuditLog, User
from app.utils import admin_required

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/users")
@login_required
@admin_required
def users():
    users = User.query.order_by(User.id).all()
    return render_template("admin/users.html", users=users)


@bp.route("/audits")
@login_required
@admin_required
def audits():
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(100).all()
    return render_template("admin/audits.html", logs=logs)
