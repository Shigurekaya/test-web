"""Capture current Vue UI screenshots with a temporary seeded Flask app."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
OUT = ROOT / "docs" / "screenshots"
PORT = 5099
BASE_URL = f"http://127.0.0.1:{PORT}"


def build_app():
    temp_dir = Path(tempfile.mkdtemp(prefix="kb-ui-"))
    os.environ["DATABASE_URL"] = f"sqlite:///{(temp_dir / 'ui.db').as_posix()}"
    os.environ["SECRET_KEY"] = "ui-screenshot-secret"
    os.environ["AUTO_SEED"] = "1"
    os.environ["OPENAI_API_KEY"] = ""
    from app import create_app

    application = create_app()
    return application, temp_dir


def wait_for_server(timeout: float = 40.0) -> None:
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"{BASE_URL}/api/health", timeout=1).read()
            return
        except Exception:
            time.sleep(0.3)
    raise RuntimeError("Flask screenshot server did not start")


def attach_browser_checks(page, errors: list[str], external_requests: list[str]) -> None:
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(str(exc)))

    def track_request(request) -> None:
        url = request.url
        if url.startswith(("http://", "https://")) and not url.startswith(BASE_URL):
            external_requests.append(url)

    page.on("request", track_request)


def login(page, username: str, password: str) -> None:
    page.goto(f"{BASE_URL}/ui/login", wait_until="networkidle")
    page.fill('input[autocomplete="username"]', username)
    page.fill('input[autocomplete="current-password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_url("**/ui/dashboard")
    page.wait_for_load_state("networkidle")


def main() -> int:
    from werkzeug.serving import make_server

    application, temp_dir = build_app()
    server = make_server("127.0.0.1", PORT, application, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    wait_for_server()
    OUT.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    external_requests: list[str] = []

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 950})
            attach_browser_checks(page, errors, external_requests)

            page.goto(f"{BASE_URL}/ui/login", wait_until="networkidle")
            page.screenshot(path=str(OUT / "01-login.png"), full_page=False)
            login(page, "admin", "admin123")

            shots = [
                ("02-dashboard.png", "/ui/dashboard"),
                ("03-documents.png", "/ui/documents"),
                ("04-document-detail.png", "/ui/documents/1"),
                ("05-document-editor.png", "/ui/documents/new"),
                ("06-qa.png", "/ui/qa"),
                ("07-graph.png", "/ui/graph"),
                ("08-users.png", "/ui/admin/users"),
                ("09-audits.png", "/ui/admin/audits"),
                ("10-about.png", "/ui/about"),
            ]
            for filename, path in shots:
                page.goto(f"{BASE_URL}{path}", wait_until="networkidle")
                page.wait_for_timeout(500)
                page.screenshot(path=str(OUT / filename), full_page=False)

            page.goto(f"{BASE_URL}/ui/qa", wait_until="networkidle")
            page.fill(".qa-composer textarea", "员工年假有几天？")
            page.click('.qa-composer button[type="submit"]')
            page.wait_for_selector(".message--answer", timeout=30000)
            page.wait_for_timeout(1200)
            page.evaluate(
                """() => {
                    const answers = document.querySelectorAll(".message--answer");
                    const last = answers[answers.length - 1];
                    if (last) last.scrollIntoView({ block: "center" });
                }"""
            )
            page.wait_for_timeout(300)
            page.screenshot(path=str(OUT / "11-qa-answer.png"), full_page=False)

            mobile = browser.new_page(viewport={"width": 390, "height": 844})
            attach_browser_checks(mobile, errors, external_requests)
            login(mobile, "admin", "admin123")
            mobile.evaluate("window.scrollTo(0, 0)")
            mobile.wait_for_timeout(500)
            mobile.screenshot(path=str(OUT / "12-mobile-dashboard.png"), full_page=False)
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        shutil.rmtree(temp_dir, ignore_errors=True)

    if errors:
        raise RuntimeError("Browser console errors: " + " | ".join(errors[:5]))
    if external_requests:
        unique = sorted(set(external_requests))
        raise RuntimeError("External network requests detected: " + " | ".join(unique[:5]))
    print(f"captured screenshots in {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
