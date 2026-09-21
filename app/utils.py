from datetime import datetime, timezone
from functools import wraps

from flask import flash, redirect, url_for
from flask_login import current_user

VISIBILITY_LABELS = {
    "public": "公开",
    "internal": "内部",
    "secret": "机密",
}

STATUS_LABELS = {
    "draft": "草稿",
    "published": "已发布",
    "archived": "已归档",
}

ROLE_LABELS = {
    "admin": "管理员",
    "employee": "员工",
}

MODE_LABELS = {
    "local": "本地检索",
    "llm": "大模型生成",
}

ACTION_LABELS = {
    "login": "登录",
    "logout": "退出",
    "view_document": "查看文档",
    "create_document": "创建文档",
    "edit_document": "编辑文档",
    "delete_document": "删除文档",
    "ask_qa": "智能问答",
}

VISIBILITY_BADGE = {
    "public": "success",
    "internal": "secondary",
    "secret": "danger",
}

STATUS_BADGE = {
    "draft": "warning",
    "published": "success",
    "archived": "dark",
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def format_dt(value, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """统一时间展示：去掉微秒，避免界面出现小数点后六位。"""
    if value is None:
        return "—"
    if isinstance(value, str):
        return value.split(".")[0].replace("T", " ")
    try:
        value = value.replace(microsecond=0)
        return value.strftime(fmt)
    except Exception:  # noqa: BLE001
        return str(value).split(".")[0]


def label_of(mapping: dict, key: str, default: str | None = None) -> str:
    if key is None:
        return default or "—"
    return mapping.get(key, default or key)


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("需要管理员权限", "danger")
            return redirect(url_for("main.dashboard"))
        return view(*args, **kwargs)

    return wrapped
