r"""用真实浏览器给每个页面截图，用于 UI 走查。

    .\.venv\Scripts\python.exe scripts\ui_screenshots.py

脚本会自己起一个临时数据库 + 本地 Flask 服务，因此不会碰到 instance/knowledge.db。
产物在 .cache/ui/。不属于测试套件，仅供人工检查界面与收集浏览器控制台报错。
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

PORT = 5099
OUT_DIR = Path(".cache/ui")

# (名称, 路径, 登录账号)——账号为 None 表示匿名访问
SHOTS = [
    ("login", "/auth/login", None),
    ("index", "/", None),
    ("dashboard", "/dashboard", ("admin", "admin123")),
    ("knowledge", "/knowledge/", ("admin", "admin123")),
    ("doc_detail", "/knowledge/1", ("admin", "admin123")),
    ("doc_form", "/knowledge/create", ("admin", "admin123")),
    ("qa", "/qa/", ("admin", "admin123")),
    ("graph", "/graph/", ("admin", "admin123")),
    ("graph_manage", "/graph/manage", ("admin", "admin123")),
    ("about", "/about", ("admin", "admin123")),
    ("favorites", "/knowledge/favorites", ("admin", "admin123")),
    ("categories", "/knowledge/categories", ("admin", "admin123")),
    ("admin_users", "/admin/users", ("admin", "admin123")),
    ("admin_audits", "/admin/audits", ("admin", "admin123")),
    ("hr_dashboard", "/dashboard", ("hr", "hr123")),
    ("hr_qa", "/qa/", ("hr", "hr123")),
]


def wait_for_server(url: str, timeout: float = 40.0) -> bool:
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1).read()
            return True
        except Exception:  # noqa: BLE001
            time.sleep(0.4)
    return False


def build_app():
    """在临时库里建好应用并灌入演示数据。"""
    tmp = tempfile.mkdtemp(prefix="uishot_")
    os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tmp, "ui.db").replace(os.sep, "/")
    os.environ["SECRET_KEY"] = "ui-shots"

    from app import create_app
    from app.extensions import db
    from app.seed import seed_all

    application = create_app()
    with application.app_context():
        db.create_all()
        seed_all(application)
    return application


def main() -> int:
    application = build_app()

    server = threading.Thread(
        target=lambda: application.run(
            host="127.0.0.1", port=PORT, debug=False, use_reloader=False
        ),
        daemon=True,
    )
    server.start()
    if not wait_for_server(f"http://127.0.0.1:{PORT}/health"):
        print("server failed to start")
        return 1

    from playwright.sync_api import sync_playwright

    shutil.rmtree(OUT_DIR, ignore_errors=True)
    OUT_DIR.mkdir(parents=True)

    failures: list[str] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for name, path, creds in SHOTS:
            page = browser.new_page(viewport={"width": 1440, "height": 950})
            errors: list[str] = []

            def on_console(msg, _sink=errors):
                if msg.type == "error":
                    _sink.append(msg.text)

            def on_pageerror(exc, _sink=errors):
                _sink.append(str(exc))

            page.on("console", on_console)
            page.on("pageerror", on_pageerror)

            if creds:
                page.goto(f"http://127.0.0.1:{PORT}/auth/login")
                page.fill("input[name=username]", creds[0])
                page.fill("input[name=password]", creds[1])
                page.click("button[type=submit]")
                page.wait_for_load_state("networkidle")

            page.goto(f"http://127.0.0.1:{PORT}{path}")
            page.wait_for_timeout(1100)
            page.screenshot(path=str(OUT_DIR / f"{name}.png"), full_page=True)
            height = page.evaluate("document.body.scrollHeight")
            status = "OK " if not errors else "JS!"
            print(f"{status} {name:14} height={height:<6} errors={len(errors)}")
            for message in errors[:2]:
                print("       !", message[:160])
                failures.append(f"{name}: {message[:160]}")
            page.close()
        browser.close()

    print(f"\n{len(SHOTS) - len({e.split(':')[0] for e in failures})}/{len(SHOTS)} pages clean")
    print("screenshots in", OUT_DIR.resolve())
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
