"""Serve the production Vue build from /ui without interfering with legacy pages."""

from pathlib import Path

from flask import Blueprint, send_from_directory

bp = Blueprint("spa", __name__, url_prefix="/ui")
DIST_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@bp.get("")
@bp.get("/")
def index():
    index_file = DIST_DIR / "index.html"
    if not index_file.exists():
        return (
            "<h1>前端尚未构建</h1><p>请在 frontend 目录执行 <code>npm install && npm run build</code>。</p>",
            503,
            {"Content-Type": "text/html; charset=utf-8"},
        )
    return send_from_directory(DIST_DIR, "index.html")


@bp.get("/<path:path>")
def assets_or_history(path: str):
    index_file = DIST_DIR / "index.html"
    if not index_file.exists():
        return (
            "<h1>前端尚未构建</h1><p>请在 frontend 目录执行 <code>npm install && npm run build</code>。</p>",
            503,
            {"Content-Type": "text/html; charset=utf-8"},
        )
    target = DIST_DIR / path
    if target.is_file():
        return send_from_directory(DIST_DIR, path)
    return send_from_directory(DIST_DIR, "index.html")
