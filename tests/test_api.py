"""REST API contract tests used by the Vue frontend."""

from __future__ import annotations

from app.extensions import db
from app.models import Category, Document, Favorite


def test_api_meta_is_public(client):
    response = client.get("/api/meta")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["name"] == "智慧企业知识财富库"
    assert payload["version"] == "2.0"
    assert payload["demo_accounts"]


def test_api_requires_authentication(client):
    response = client.get("/api/dashboard")
    assert response.status_code == 401
    assert response.get_json()["code"] == "AUTH_REQUIRED"


def test_api_login_logout_flow(client):
    failed = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert failed.status_code == 401

    success = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert success.status_code == 200
    assert success.get_json()["user"]["is_admin"] is True

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.get_json()["user"]["username"] == "admin"

    logout = client.post("/api/auth/logout")
    assert logout.status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_api_dashboard_payload(admin_client):
    response = admin_client.get("/api/dashboard")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["stats"]["visible_documents"] > 0
    assert isinstance(payload["charts"]["departments"], list)
    assert payload["quick_questions"]


def test_api_document_search_and_detail(admin_client):
    listing = admin_client.get("/api/documents?q=年假")
    assert listing.status_code == 200
    payload = listing.get_json()
    assert payload["pagination"]["total"] >= 1
    assert any("休假" in item["title"] or "年假" in item["summary"] for item in payload["items"])

    doc_id = payload["items"][0]["id"]
    detail = admin_client.get(f"/api/documents/{doc_id}")
    assert detail.status_code == 200
    assert detail.get_json()["document"]["content"]
    assert detail.get_json()["can_edit"] is True


def test_api_document_crud_and_favorite(admin_client, app):
    created = admin_client.post(
        "/api/documents",
        json={
            "title": "API 自动化测试文档",
            "content": "这是通过 REST API 创建的测试正文。\n\n第二段用于验证知识切分。",
            "summary": "API 测试摘要",
            "department": "综合部",
            "visibility": "internal",
            "status": "published",
            "version": "1.0",
            "tags": ["API", "测试"],
        },
    )
    assert created.status_code == 201
    doc_id = created.get_json()["document"]["id"]

    with app.app_context():
        doc = db.session.get(Document, doc_id)
        assert doc is not None
        assert doc.chunk_count >= 1

    favorite = admin_client.post(f"/api/documents/{doc_id}/favorite")
    assert favorite.status_code == 200
    assert favorite.get_json()["is_favorite"] is True
    with app.app_context():
        assert Favorite.query.filter_by(document_id=doc_id).count() == 1

    updated = admin_client.put(
        f"/api/documents/{doc_id}",
        json={
            "title": "API 自动化测试文档（已更新）",
            "content": "更新后的正文内容。\n\n保存后应重新建立索引。",
            "department": "综合部",
            "visibility": "public",
            "status": "published",
            "tags": ["API"],
        },
    )
    assert updated.status_code == 200
    assert updated.get_json()["document"]["title"].endswith("（已更新）")

    deleted = admin_client.delete(f"/api/documents/{doc_id}")
    assert deleted.status_code == 200
    with app.app_context():
        assert db.session.get(Document, doc_id) is None


def test_api_secret_document_permission(client):
    client.post("/api/auth/login", json={"username": "hr", "password": "hr123"})
    listing = client.get("/api/documents?per_page=50").get_json()["items"]
    visible_ids = {item["id"] for item in listing}

    with client.application.app_context():
        secret = Document.query.filter_by(visibility="secret").first()
        assert secret is not None
        assert secret.id not in visible_ids
        response = client.get(f"/api/documents/{secret.id}")
        assert response.status_code == 403


def test_api_qa_returns_traceable_sources(admin_client):
    response = admin_client.post("/api/qa/ask", json={"question": "员工年假有几天？"})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["answer"]
    assert payload["sources"]
    assert payload["sources"][0]["title"]
    assert payload["fragments"]


def test_api_graph_payload_is_visible_scope(admin_client):
    response = admin_client.get("/api/graph")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["nodes"]
    assert payload["links"]
    assert {node["category"] for node in payload["nodes"]} <= {
        "document",
        "department",
        "project",
        "keyword",
        "concept",
    }


def test_api_admin_endpoints_and_permission(client, admin_client):
    users = admin_client.get("/api/admin/users")
    audits = admin_client.get("/api/admin/audits?page=1")
    assert users.status_code == 200
    assert audits.status_code == 200
    assert users.get_json()["summary"]["total"] >= 5
    assert audits.get_json()["pagination"]["total"] > 0

    client.post("/api/auth/login", json={"username": "hr", "password": "hr123"})
    assert client.get("/api/admin/users").status_code == 403
    assert client.get("/api/admin/audits").status_code == 403


def test_api_admin_can_create_category(admin_client, app):
    response = admin_client.post(
        "/api/categories",
        json={"name": "API测试分类", "description": "仅用于自动化测试"},
    )
    assert response.status_code == 201
    with app.app_context():
        assert Category.query.filter_by(name="API测试分类").first() is not None


def test_api_history_detail_uses_json_sources(admin_client):
    asked = admin_client.post("/api/qa/ask", json={"question": "差旅住宿标准是多少？"})
    history_id = asked.get_json()["history_id"]
    response = admin_client.get(f"/api/qa/history/{history_id}")
    assert response.status_code == 200
    item = response.get_json()["item"]
    assert item["question"] == "差旅住宿标准是多少？"
    assert isinstance(item["sources"], list)
    assert item["answer"]
