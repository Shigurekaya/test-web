from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.models import AuditLog, User
from app.utils import DEMO_ACCOUNTS, RateLimiter, audit_detail, safe_next_url

bp = Blueprint("auth", __name__, url_prefix="/auth")

# 登录防爆破：按 IP 计数。阈值走配置，便于演示时放宽、生产时收紧。
login_limiter = RateLimiter(key_prefix="login")


def configure_login_limits(app) -> None:
    """把配置里的限额写进限流器。

    在 create_app 里调用一次；限流器是模块级单例，若在请求里反复赋值，
    测试或运维临时调整的阈值会被配置默认值覆盖掉。
    """
    cfg = app.config
    login_limiter.max_attempts = int(cfg.get("LOGIN_MAX_ATTEMPTS", 8))
    login_limiter.window_seconds = int(cfg.get("LOGIN_WINDOW_SECONDS", 300))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        next_url = safe_next_url(request.args.get("next")) or url_for("main.dashboard")
        return redirect(next_url)

    if request.method == "POST":
        # 先查锁定状态，再校验密码，避免爆破绕过锁定
        if login_limiter.is_locked_from_request():
            retry_after = login_limiter.retry_after_from_request()
            flash(
                f"登录失败次数过多，请 {retry_after} 秒后再试",
                "danger",
            )
            return render_template("auth/login.html", demo_accounts=DEMO_ACCOUNTS), 429

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_limiter.clear_from_request()
            login_user(user)
            db.session.add(
                AuditLog(
                    user_id=user.id, action="login", detail=audit_detail("login", username=username)
                )
            )
            db.session.commit()
            flash("登录成功", "success")
            next_url = safe_next_url(
                request.form.get("next") or request.args.get("next")
            ) or url_for("main.dashboard")
            return redirect(next_url)

        # 失败同样落审计：只看成功记录的审计日志看不出爆破
        login_limiter.record_failure_from_request()
        db.session.add(
            AuditLog(
                user_id=user.id if user else None,
                action="login_failed",
                detail=audit_detail("login_failed", username=username or None),
            )
        )
        db.session.commit()
        flash("用户名或密码错误", "danger")

    return render_template("auth/login.html", demo_accounts=DEMO_ACCOUNTS)


@bp.route("/logout")
@login_required
def logout():
    db.session.add(
        AuditLog(
            user_id=current_user.id,
            action="logout",
            detail=audit_detail("logout", username=current_user.username),
        )
    )
    db.session.commit()
    logout_user()
    flash("已退出登录", "info")
    return redirect(url_for("auth.login"))
