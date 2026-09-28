from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db
from app.models import AuditLog, User
from app.utils import safe_next_url

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        next_url = safe_next_url(request.args.get("next")) or url_for("main.dashboard")
        return redirect(next_url)
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            db.session.add(
                AuditLog(user_id=user.id, action="login", detail=f"用户 {username} 登录")
            )
            db.session.commit()
            flash("登录成功", "success")
            next_url = (
                safe_next_url(request.form.get("next") or request.args.get("next"))
                or url_for("main.dashboard")
            )
            return redirect(next_url)
        flash("用户名或密码错误", "danger")
    return render_template("auth/login.html")


@bp.route("/logout")
@login_required
def logout():
    db.session.add(
        AuditLog(user_id=current_user.id, action="logout", detail=f"用户 {current_user.username} 退出")
    )
    db.session.commit()
    logout_user()
    flash("已退出登录", "info")
    return redirect(url_for("auth.login"))
