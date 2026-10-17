from datetime import UTC, datetime
from functools import wraps
from urllib.parse import urlparse

from flask import abort, flash, redirect, url_for
from flask_login import current_user


def safe_next_url(value: str | None) -> str | None:
    """仅允许站内相对路径，防止登录后 open redirect。"""
    if not value:
        return None
    value = value.strip()
    if not value.startswith("/") or value.startswith("//"):
        return None
    if any(ch in value for ch in ("\\", "\n", "\r", "\0")):
        return None
    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc:
        return None
    if parsed.path.startswith("//"):
        return None
    return value


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

DEMO_ACCOUNTS = (
    {"username": "admin", "password": "admin123", "label": "管理员", "hint": "看全貌与审计"},
    {"username": "hr", "password": "hr123", "label": "人事部", "hint": "普通业务权限"},
    {"username": "finance", "password": "fin123", "label": "财务部", "hint": "差旅 / 采购"},
    {"username": "it", "password": "it123", "label": "信息部", "hint": "可看本部门机密"},
    {"username": "product", "password": "prod123", "label": "产品部", "hint": "FAQ / 话术"},
)


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


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


def normalize_choice(value: str | None, allowed: dict, default: str) -> str:
    value = (value or "").strip()
    return value if value in allowed else default


def auto_summary(content: str, limit: int = 140) -> str:
    """正文为空摘要时，截取首段作为预览。"""
    import re

    text = re.sub(r"\s+", " ", (content or "").strip())
    if not text:
        return ""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    for sep in ("。", "！", "？", "；", ".", "!", "?", ";"):
        idx = cut.rfind(sep)
        if idx > limit // 3:
            return cut[: idx + 1]
    return cut.rstrip(" ,，、") + "…"


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("请先登录后再访问", "warning")
            return redirect(url_for("auth.login"))
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped
