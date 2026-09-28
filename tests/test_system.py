"""系统自动化冒烟 / 回归测试（可直接写入测试报告）。"""
from __future__ import annotations

import unittest

from app import create_app
from app.extensions import db
from app.models import Document, User


class KnowledgeSystemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()

    def login(self, username: str, password: str):
        return self.client.post(
            "/auth/login",
            data={"username": username, "password": password},
            follow_redirects=True,
        )

    def test_01_health(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["status"], "ok")

    def test_02_login_fail(self):
        res = self.client.post(
            "/auth/login",
            data={"username": "admin", "password": "wrong"},
            follow_redirects=True,
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("用户名或密码错误".encode("utf-8"), res.data)

    def test_03_login_success_dashboard(self):
        res = self.login("admin", "admin123")
        self.assertEqual(res.status_code, 200)
        self.assertIn("工作台".encode("utf-8"), res.data)

    def test_04_search_leave_policy(self):
        self.login("admin", "admin123")
        res = self.client.get("/knowledge/?q=年假")
        self.assertEqual(res.status_code, 200)
        self.assertIn("年休假".encode("utf-8"), res.data)

    def test_05_rag_answer(self):
        self.login("admin", "admin123")
        res = self.client.post(
            "/qa/",
            data={"question": "员工年假有几天"},
            follow_redirects=True,
        )
        self.assertEqual(res.status_code, 200)
        text = res.get_data(as_text=True)
        self.assertTrue("年假" in text or "年休假" in text)

    def test_06_secret_denied_for_hr(self):
        self.client.get("/auth/logout", follow_redirects=True)
        self.login("hr", "hr123")
        with self.app.app_context():
            secret = Document.query.filter_by(visibility="secret").first()
            self.assertIsNotNone(secret)
            doc_id = secret.id
        res = self.client.get(f"/knowledge/{doc_id}")
        self.assertEqual(res.status_code, 403)

    def test_07_secret_allowed_for_it(self):
        self.client.get("/auth/logout", follow_redirects=True)
        self.login("it", "it123")
        with self.app.app_context():
            secret = Document.query.filter_by(visibility="secret").first()
            doc_id = secret.id
        res = self.client.get(f"/knowledge/{doc_id}")
        self.assertEqual(res.status_code, 200)
        self.assertIn("信息安全".encode("utf-8"), res.data)

    def test_08_graph_data(self):
        self.login("admin", "admin123")
        res = self.client.get("/graph/data")
        self.assertEqual(res.status_code, 200)
        payload = res.get_json()
        self.assertGreaterEqual(len(payload["nodes"]), 1)
        self.assertGreaterEqual(len(payload["links"]), 1)

    def test_09_create_document_and_index(self):
        self.login("admin", "admin123")
        res = self.client.post(
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
        self.assertEqual(res.status_code, 200)
        self.assertIn("加班管理制度测试稿".encode("utf-8"), res.data)
        qa = self.client.post(
            "/qa/",
            data={"question": "加班怎么补偿"},
            follow_redirects=True,
        )
        self.assertIn("加班".encode("utf-8"), qa.data)

    def test_10_users_seeded(self):
        with self.app.app_context():
            self.assertGreaterEqual(User.query.count(), 5)

    def test_11_datetime_filter_no_micros(self):
        from app.utils import format_dt
        from datetime import datetime

        raw = datetime(2026, 9, 15, 14, 30, 45, 123456)
        self.assertEqual(format_dt(raw), "2026-09-15 14:30:45")
        self.assertNotIn(".", format_dt(raw))

    def test_12_doc_list_cards_and_chinese_labels(self):
        self.login("admin", "admin123")
        res = self.client.get("/knowledge/")
        text = res.get_data(as_text=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn("内部", text)
        self.assertNotRegex(text, r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{6}")

    def test_13_unauthorized_dashboard_redirects_to_login(self):
        self.client.get("/auth/logout", follow_redirects=True)
        res = self.client.get("/dashboard")
        self.assertEqual(res.status_code, 302)
        loc = res.headers.get("Location", "")
        self.assertIn("/auth/login", loc)
        self.assertIn("next=", loc)

    def test_14_trailing_slash_ok(self):
        self.login("admin", "admin123")
        for path in ("/dashboard", "/dashboard/", "/knowledge", "/knowledge/", "/qa", "/qa/"):
            res = self.client.get(path)
            self.assertEqual(res.status_code, 200, msg=path)

    def test_15_unknown_path_is_404_not_login(self):
        self.client.get("/auth/logout", follow_redirects=True)
        res = self.client.get("/this-page-does-not-exist-xyz")
        self.assertEqual(res.status_code, 404)
        text = res.get_data(as_text=True)
        self.assertIn("页面不存在", text)
        self.assertNotIn("账号登录", text)

    def test_16_open_redirect_blocked(self):
        self.client.get("/auth/logout", follow_redirects=True)
        res = self.client.post(
            "/auth/login?next=https://evil.com",
            data={"username": "admin", "password": "admin123", "next": "https://evil.com"},
            follow_redirects=False,
        )
        self.assertEqual(res.status_code, 302)
        loc = res.headers.get("Location", "")
        self.assertNotIn("evil.com", loc)
        self.assertTrue(loc.endswith("/dashboard") or "/dashboard" in loc)

    def test_17_safe_next_allows_internal_path(self):
        self.client.get("/auth/logout", follow_redirects=True)
        res = self.client.post(
            "/auth/login",
            data={"username": "admin", "password": "admin123", "next": "/knowledge/"},
            follow_redirects=False,
        )
        self.assertEqual(res.status_code, 302)
        self.assertIn("/knowledge", res.headers.get("Location", ""))

    def test_18_non_admin_gets_403_on_admin(self):
        self.client.get("/auth/logout", follow_redirects=True)
        self.login("hr", "hr123")
        res = self.client.get("/admin/users")
        self.assertEqual(res.status_code, 403)


if __name__ == "__main__":
    unittest.main(verbosity=2)
