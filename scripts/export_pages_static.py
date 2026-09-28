"""Export authenticated Flask pages to Cloudflare Pages static tree."""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from app import create_app
from app.models import Document

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
  if (m === 'post' || a.indexOf('create') >= 0 || a.indexOf('manage') >= 0 || a.indexOf('categories') >= 0) {
    e.preventDefault();
    alert('这是部署在 lkaya.com 的作业展示站（静态页），不连接真实后台。完整功能请本地运行 Flask。');
  }
});
</script>
"""


def rewrite(html: str) -> str:
    html = re.sub(
        r'<form[^>]*method="post"[^>]*action="[^"]*login[^"]*"[^>]*>',
        '<form onsubmit="location.href=\'/dashboard/\';return false;">',
        html,
        count=1,
        flags=re.I,
    )
    if "demo-static-intercept" not in html:
        html = html.replace("</body>", INTERCEPT + "\n</body>")
    # QA form -> demo answer for static browsing
    html = re.sub(
        r'<form method="post">',
        '<form method="get" action="/qa/demo/">',
        html,
        count=1,
    )
    return html


def save(out: Path, url_path: str, html: str, raw: Path | None = None, raw_name: str | None = None) -> None:
    html2 = rewrite(html)
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

    app = create_app()
    with app.app_context():
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
            save(OUT, out_path, resp.get_data(as_text=True), RAW, raw_name)

        # login page must be fetched without session
        anon = app.test_client()
        login_resp = anon.get("/auth/login")
        if login_resp.status_code == 200:
            save(OUT, "/auth/login/", login_resp.get_data(as_text=True), RAW, "login.html")
        else:
            print("WARN /auth/login", login_resp.status_code)

        entry = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>企业知识库 · 作业展示站</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="/static/css/app.css" rel="stylesheet"></head>
<body>
<nav class="navbar navbar-expand-lg navbar-dark app-nav"><div class="container">
<a class="navbar-brand fw-semibold" href="/dashboard/"><span class="brand-mark">KB</span> 企业知识库</a>
</div></nav>
<main class="container py-5">
<h1 class="h3 page-title mb-2">作业展示站入口</h1>
<p class="text-muted mb-4">静态导出 · 外观与本地 Flask 一致 · 写入操作会提示未连接后台</p>
<div class="row g-3">
<div class="col-md-6"><div class="card panel"><div class="card-body">
<div class="fw-semibold mb-2">快速入口</div>
<ul class="mb-0">
<li><a href="/auth/login/">登录页</a>（演示账号 admin / admin123）</li>
<li><a href="/dashboard/">工作台</a></li>
<li><a href="/knowledge/">知识文档</a></li>
<li><a href="/qa/">智能问答</a></li>
<li><a href="/graph/">关系图</a></li>
<li><a href="/admin/users/">用户列表</a></li>
<li><a href="/admin/audits/">审计日志</a></li>
</ul>
</div></div></div>
<div class="col-md-6"><div class="card panel"><div class="card-body">
<div class="fw-semibold mb-2">本站数据规模（展示）</div>
<p class="mb-0 small text-muted">已充实用户、分类、文档、问答与审计等虚构演示数据，便于课堂演示。</p>
</div></div></div>
</div>
</main>
<footer class="app-footer"><div class="container small text-muted">综合项目实践 · 企业知识库管理系统 v1.0 · lkaya.com 展示站</div></footer>
</body></html>
"""
        (OUT / "index.html").write_text(entry, encoding="utf-8")

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

        resp = client.get("/qa/", query_string={"q": "员工年假有几天？"})
        if resp.status_code == 200:
            save(OUT, "/qa/demo/", resp.get_data(as_text=True))

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
    (OUT / "_redirects").write_text("/graph/data /graph/data.json 200\n", encoding="utf-8")
    print("DONE", OUT)


if __name__ == "__main__":
    main()
