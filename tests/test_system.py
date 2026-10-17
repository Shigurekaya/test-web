"""系统级冒烟 / 回归测试（可直接写入测试报告）。

所有用例运行在独立数据库上（见 conftest.py），不会读写 `instance/knowledge.db`。
"""
from __future__ import annotations

from datetime import datetime

from app.models import Document
from app.utils import format_dt


def test_01_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ok"


def test_02_login_fail(client):
    res = client.post(
        "/auth/login", data={"username": "admin", "password": "wrong"}, follow_redirects=True
    )
    assert res.status_code == 200
    assert "用户名或密码错误".encode("utf-8") in res.data


def test_03_login_success_dashboard(admin_client):
    assert admin_client.get("/dashboard").status_code == 200


def test_04_search_leave_policy(admin_client):
    res = admin_client.get("/knowledge/?q=年假")
    assert res.status_code == 200
    assert "年假".encode("utf-8") in res.data


def test_05_rag_answer(admin_client):
    res = admin_client.post("/qa/", data={"question": "员工年假有几天？"}, follow_redirects=True)
    assert res.status_code == 200
    assert "年假".encode("utf-8") in res.data


def test_06_secret_denied_for_hr(client, app):
    client.post("/auth/login", data={"username": "hr", "password": "hr123"})
    with app.app_context():
        doc_id = Document.query.filter_by(visibility="secret").first().id
    assert client.get(f"/knowledge/{doc_id}").status_code == 403


def test_07_secret_allowed_for_it(client, app):
    client.post("/auth/login", data={"username": "it", "password": "it123"})
    with app.app_context():
        doc_id = Document.query.filter_by(visibility="secret").first().id
    res = client.get(f"/knowledge/{doc_id}")
    assert res.status_code == 200
    assert "信息安全".encode("utf-8") in res.data


def test_08_graph_data(admin_client):
    res = admin_client.get("/graph/data")
    assert res.status_code == 200
    payload = res.get_json()
    assert len(payload["nodes"]) >= 1
    assert len(payload["links"]) >= 1


def test_09_create_document_and_index(admin_client):
    res = admin_client.post(
        "/knowledge/create",
        data={
            "title": "加班管理制度测试稿",
            "summary": "测试自动索引",
            "department": "综合部",
            "visibility": "internal",
            "status": "published",
            "version": "1.0",
            "tags": "加班,测试",
            "category_id": "",
            "content": "加班需提前申请。工作日加班补偿调休，法定节假日加班按三倍工资计发。",
        },
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert "加班管理制度测试稿".encode("utf-8") in res.data
    qa = admin_client.post("/qa/", data={"question": "加班怎么补偿"}, follow_redirects=True)
    assert "加班".encode("utf-8") in qa.data


def test_10_users_seeded(app):
    from app.models import User

    assert User.query.count() >= 5


def test_11_datetime_filter_no_micros():
    raw = datetime(2026, 9, 15, 14, 30, 45, 123456)
    assert format_dt(raw) == "2026-09-15 14:30:45"
    assert "." not in format_dt(raw)


def test_12_doc_list_cards_and_chinese_labels(admin_client):
    res = admin_client.get("/knowledge/")
    text = res.get_data(as_text=True)
    assert res.status_code == 200
    assert "内部" in text
    assert r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{6}" not in text


def test_13_unauthorized_dashboard_redirects_to_login(client):
    res = client.get("/dashboard")
    assert res.status_code == 302
    loc = res.headers.get("Location", "")
    assert "/auth/login" in loc
    assert "next=" in loc


def test_14_trailing_slash_ok(admin_client):
    for path in ("/dashboard", "/dashboard/", "/knowledge", "/knowledge/", "/qa", "/qa/"):
        assert admin_client.get(path).status_code == 200, path


def test_15_unknown_path_is_404_not_login(client):
    res = client.get("/this-page-does-not-exist-xyz")
    assert res.status_code == 404
    text = res.get_data(as_text=True)
    assert "页面不存在" in text
    assert "账号登录" not in text


def test_16_open_redirect_blocked(client):
    res = client.post(
        "/auth/login?next=https://evil.com",
        data={"username": "admin", "password": "admin123", "next": "https://evil.com"},
        follow_redirects=False,
    )
    assert res.status_code == 302
    loc = res.headers.get("Location", "")
    assert "evil.com" not in loc
    assert "/dashboard" in loc


def test_17_safe_next_allows_internal_path(client):
    res = client.post(
        "/auth/login",
        data={"username": "admin", "password": "admin123", "next": "/knowledge/"},
        follow_redirects=False,
    )
    assert res.status_code == 302
    assert "/knowledge" in res.headers.get("Location", "")


def test_18_non_admin_gets_403_on_admin(client):
    client.post("/auth/login", data={"username": "hr", "password": "hr123"})
    assert client.get("/admin/users").status_code == 403


# --- 可靠性：全新数据库可自动建表并灌入演示数据 ---

def test_19_fresh_database_builds_and_seeds(fresh_client, fresh_app):
    from app.extensions import db
    from app.models import (AuditLog, Category, Document, GraphEdge, GraphNode, KnowledgeChunk, QAHistory, User)

    assert fresh_client.get("/health").status_code == 200
    with fresh_app.app_context():
        assert Document.query.count() > 0
        assert User.query.count() >= 5
        assert Category.query.count() > 0
        assert KnowledgeChunk.query.count() > 0
        assert GraphNode.query.count() > 0
        assert GraphEdge.query.count() > 0
        assert QAHistory.query.count() >= 0
        assert AuditLog.query.count() >= 0


def test_20_demo_storyline_smoke(fresh_client):
    """演示故事线：登录 → 工作台 → 文档 → 问答 → 图谱 → 关于。"""
    fresh_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    for path in ("/dashboard", "/knowledge/", "/qa/", "/graph/", "/about"):
        assert fresh_client.get(path).status_code == 200, path
    assert fresh_client.post(
        "/qa/", data={"question": "员工年假有几天？"}, follow_redirects=True
    ).status_code == 200

