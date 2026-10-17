"""Export authenticated Flask pages to Cloudflare Pages static tree."""
from __future__ import annotations

import re
import shutil
from pathlib import Path
from urllib.parse import quote

from app import create_app
from app.blueprints.qa import SUGGESTED_QUESTIONS
from app.models import Document, QAHistory

ROOT = Path(__file__).resolve().parents[1]
WS = ROOT.parents[1]  # E:\网站\测试框架
OUT = WS / ".cache" / "lkaya-pages-deploy"
RAW = WS / ".cache" / "lkaya-demo-raw"
CSS_SRC = ROOT / "app" / "static" / "css" / "app.css"

INTERCEPT = """
<script id="demo-static-intercept">
document.addEventListener('submit', function (e) {
  var f = e.target;
  if (!f || !f.action) return;
  var a = (f.getAttribute('action') || '').toLowerCase();
  var m = (f.getAttribute('method') || 'get').toLowerCase();
  if (a.indexOf('/dashboard') >= 0) return;
  if (a.indexOf('/qa/demo') >= 0) return;
  if (m === 'post' || a.indexOf('create') >= 0 || a.indexOf('manage') >= 0 || a.indexOf('categories') >= 0) {
    e.preventDefault();
    alert('这是部署在 lkaya.com 的静态展示站，不连接真实后台。完整功能请本地运行 Flask。');
  }
});
</script>
"""

LANDING = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>智慧企业知识财富库 · 在线演示</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="/static/css/app.css" rel="stylesheet">
</head>
<body>
<main class="container py-5">
  <div class="card panel p-4" style="max-width:720px;margin:2rem auto;">
    <div style="display:inline-block;padding:.2rem .65rem;border-radius:999px;background:#e8f1f7;color:#1e4b6b;font-size:.78rem;margin-bottom:.75rem;">静态展示站 · lkaya.com</div>
    <h1 class="h3 mb-2">智慧企业知识财富库</h1>
    <p class="text-muted mb-3">本站为<strong>静态展示版</strong>（页面外观与本机 Flask 后台一致），方便直接浏览管理界面与示例问答。不连接真实数据库；写入类操作会被拦截提示。</p>
    <div class="d-grid gap-2">
      <a class="btn btn-primary btn-lg" href="/auth/login/">登录页（演示入口）</a>
      <a class="btn btn-outline-primary" href="/qa/">智能问答（含示例问题）</a>
      <a class="btn btn-outline-primary" href="/admin/users/">管理 · 用户列表</a>
      <a class="btn btn-outline-primary" href="/admin/audits/">管理 · 审计日志</a>
      <a class="btn btn-outline-primary" href="/knowledge/categories/">管理 · 分类管理</a>
      <a class="btn btn-outline-primary" href="/graph/manage/">管理 · 图谱维护</a>
      <a class="btn btn-outline-secondary" href="/dashboard/">工作台 / 知识文档 / 关系图</a>
    </div>
    <p class="small text-muted mt-3 mb-0">演示账号：admin / admin123（本展示站点「登录」即可进入前台预览页）</p>
  </div>
</main>
</body>
</html>
"""


def rewrite(html: str, suggest_map: dict[str, str] | None = None) -> str:
    html = re.sub(
        r'<form[^>]*method="post"[^>]*action="[^"]*login[^"]*"[^>]*>',
        '<form onsubmit="location.href=\'/dashboard/\';return false;">',
        html,
        count=1,
        flags=re.I,
    )
    if "demo-static-intercept" not in html:
        html = html.replace("</body>", INTERCEPT + "\n</body>")
    # QA form -> first demo answer page for static browsing
    html = re.sub(
        r'<form method="post">',
        '<form method="get" action="/qa/demo/1/">',
        html,
        count=1,
    )
    if suggest_map:
        for question, dest in suggest_map.items():
            # Flask url_for may emit + or %20 for spaces; cover both
            for encoded in {quote(question, safe=""), quote(question, safe="").replace("%20", "+")}:
                html = html.replace(f'href="/qa/?q={encoded}"', f'href="{dest}"')
                html = html.replace(f"href='/qa/?q={encoded}'", f"href='{dest}'")
    return html


def save(
    out: Path,
    url_path: str,
    html: str,
    raw: Path | None = None,
    raw_name: str | None = None,
    suggest_map: dict[str, str] | None = None,
) -> None:
    html2 = rewrite(html, suggest_map=suggest_map)
    rel = url_path.strip("/")
    dest = out if not rel else out / Path(rel)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "index.html").write_text(html2, encoding="utf-8")
    if raw is not None and raw_name:
        raw.mkdir(parents=True, exist_ok=True)
        (raw / raw_name).write_text(html2, encoding="utf-8")
    print(f"wrote {url_path} ({len(html2)})")


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    RAW.mkdir(parents=True, exist_ok=True)

    # suggested question -> static path map (1-based)
    suggest_map = {
        q: f"/qa/demo/{i}/" for i, q in enumerate(SUGGESTED_QUESTIONS, start=1)
    }

    app = create_app()
    with app.app_context():
        # Fetch login page BEFORE authenticating, so the session stays anonymous.
        anon = app.test_client()
        login_resp = anon.get("/auth/login")
        if login_resp.status_code == 200:
            save(OUT, "/auth/login/", login_resp.get_data(as_text=True), RAW, "login.html")
        else:
            print("WARN /auth/login", login_resp.status_code)

        client = app.test_client()
        r = client.post(
            "/auth/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=True,
        )
        assert r.status_code == 200, r.status_code

        pages = [
            ("/dashboard", "/dashboard/", "dashboard.html"),
            ("/knowledge/", "/knowledge/", "knowledge.html"),
            ("/knowledge/categories", "/knowledge/categories/", "categories.html"),
            ("/knowledge/favorites", "/knowledge/favorites/", "favorites.html"),
            ("/knowledge/create", "/knowledge/create/", None),
            ("/qa/", "/qa/", "qa.html"),
            ("/graph/", "/graph/", "graph.html"),
            ("/graph/manage", "/graph/manage/", "graph-manage.html"),
            ("/admin/users", "/admin/users/", "admin-users.html"),
            ("/admin/audits", "/admin/audits/", "admin-audits.html"),
            ("/about", "/about/", "about.html"),
        ]
        for flask_path, out_path, raw_name in pages:
            resp = client.get(flask_path)
            if resp.status_code != 200:
                print("WARN", flask_path, resp.status_code)
                continue
            save(
                OUT,
                out_path,
                resp.get_data(as_text=True),
                RAW,
                raw_name,
                suggest_map=suggest_map,
            )

        (OUT / "index.html").write_text(LANDING, encoding="utf-8")
        print("wrote / (landing)")

        for d in Document.query.order_by(Document.id.desc()).limit(50).all():
            resp = client.get(f"/knowledge/{d.id}")
            if resp.status_code == 200:
                save(OUT, f"/knowledge/{d.id}/", resp.get_data(as_text=True))

        resp = client.get("/graph/data")
        gdir = OUT / "graph"
        gdir.mkdir(parents=True, exist_ok=True)
        (gdir / "data.json").write_bytes(resp.data)
        print("wrote /graph/data.json", len(resp.data))

        # patch graph page to fetch data.json
        graph_index = OUT / "graph" / "index.html"
        if graph_index.exists():
            ghtml = graph_index.read_text(encoding="utf-8")
            ghtml = ghtml.replace("/graph/data", "/graph/data.json")
            graph_index.write_text(ghtml, encoding="utf-8")

        # Pre-render every suggested question so chips don't 404 / show empty answers
        for i, question in enumerate(SUGGESTED_QUESTIONS, start=1):
            resp = client.get("/qa/", query_string={"q": question})
            if resp.status_code != 200:
                print("WARN qa demo", i, question, resp.status_code)
                continue
            out_path = f"/qa/demo/{i}/"
            save(
                OUT,
                out_path,
                resp.get_data(as_text=True),
                suggest_map=suggest_map,
            )
            if i == 1:
                # keep /qa/demo/ as alias of first answer (form fallback)
                save(OUT, "/qa/demo/", resp.get_data(as_text=True), suggest_map=suggest_map)

        # Export recent history detail pages so "最近提问" links work
        for item in QAHistory.query.order_by(QAHistory.id.desc()).limit(40).all():
            resp = client.get(f"/qa/history/{item.id}")
            if resp.status_code == 200:
                save(OUT, f"/qa/history/{item.id}/", resp.get_data(as_text=True))

        # Soften history links without trailing slash via redirects file + also
        # rewrite /qa/history/N -> /qa/history/N/ in exported QA pages
        for qa_html in (OUT / "qa").rglob("index.html"):
            text = qa_html.read_text(encoding="utf-8")
            text2 = re.sub(r'href="/qa/history/(\d+)"', r'href="/qa/history/\1/"', text)
            if text2 != text:
                qa_html.write_text(text2, encoding="utf-8")

        # fix login page already handled by rewrite; soften intercept on login
        login = OUT / "auth" / "login" / "index.html"
        if login.exists():
            html = login.read_text(encoding="utf-8")
            if "onsubmit=" not in html:
                html = re.sub(
                    r"<form[^>]*>",
                    '<form onsubmit="location.href=\'/dashboard/\';return false;">',
                    html,
                    count=1,
                )
            login.write_text(html, encoding="utf-8")

    css_dest = OUT / "static" / "css"
    css_dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(CSS_SRC, css_dest / "app.css")
    shutil.copy2(CSS_SRC, RAW / "app.css")

    redirects = [
        "/graph/data /graph/data.json 200",
        # trailing-slash comfort for common entry paths
        "/qa /qa/ 301",
        "/dashboard /dashboard/ 301",
        "/knowledge /knowledge/ 301",
        "/graph /graph/ 301",
        "/about /about/ 301",
        "/auth/login /auth/login/ 301",
    ]
    (OUT / "_redirects").write_text("\n".join(redirects) + "\n", encoding="utf-8")
    print("DONE", OUT)


if __name__ == "__main__":
    main()
