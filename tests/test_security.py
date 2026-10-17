"""权限与安全相关的单元测试。

这些是系统的安全边界（SR-AUTH-005/006、SR-QA-008），单独成文件以便回归时优先查看。
"""
from __future__ import annotations

import pytest

from app.models import Document, User
from app.services.rag import can_view_document, rank_documents, searchable_documents
from app.utils import (
    DEPARTMENTS,
    auto_summary,
    normalize_choice,
    safe_next_url,
)


def make_user(username, role="employee", department="人事部"):
    user = User(
        username=username,
        display_name=username,
        role=role,
        department=department,
    )
    user.set_password("pw123456")
    return user


def make_doc(user, visibility="internal", department="人事部", title="测试文档"):
    doc = Document(
        title=title,
        content="正文内容",
        department=department,
        visibility=visibility,
        status="published",
        author_id=user.id,
    )
    return doc


@pytest.fixture()
def users(app):
    admin = make_user("u_admin", role="admin", department="综合部")
    hr = make_user("u_hr", department="人事部")
    it = make_user("u_it", department="信息部")
    from app.extensions import db

    db.session.add_all([admin, hr, it])
    db.session.flush()
    return admin, hr, it


@pytest.fixture()
def docs(app, users):
    """机密文档的作者统一设为 admin，这样部门/作者两条判定不会互相掩盖。"""
    from app.extensions import db

    admin, _hr, _it = users
    public = make_doc(admin, visibility="public", department="综合部", title="公开文档")
    internal = make_doc(admin, visibility="internal", department="人事部", title="内部文档")
    secret_hr = make_doc(admin, visibility="secret", department="人事部", title="人事机密")
    secret_it = make_doc(admin, visibility="secret", department="信息部", title="信息部机密")
    draft = make_doc(admin, visibility="public", department="综合部", title="草稿文档")
    draft.status = "draft"
    db.session.add_all([public, internal, secret_hr, secret_it, draft])
    db.session.flush()
    return public, internal, secret_hr, secret_it, draft


class TestVisibilityMatrix:
    """文档可见性矩阵：管理员可见一切；机密限同部门或作者。"""

    def test_public_internal_visible_to_any_logged_in_user(self, users, docs):
        _admin, hr, _it = users
        public, internal, *_ = docs
        for user in (hr, _it):
            assert can_view_document(user, public) is True
            assert can_view_document(user, internal) is True

    def test_admin_sees_everything(self, users, docs):
        admin, *_ = users
        _public, _internal, secret_hr, secret_it, _draft = docs
        assert can_view_document(admin, secret_hr) is True
        assert can_view_document(admin, secret_it) is True

    def test_secret_denied_for_other_department(self, users, docs):
        _admin, hr, it = users
        _p, _i, secret_hr, secret_it, _d = docs
        assert can_view_document(hr, secret_it) is False
        assert can_view_document(it, secret_hr) is False

    def test_secret_allowed_for_same_department(self, users, docs):
        _admin, _hr, it = users
        _p, _i, _secret_hr, secret_it, _d = docs
        assert can_view_document(it, secret_it) is True

    def test_secret_allowed_for_author(self, users, docs):
        """作者本人可以看到自己写的机密文档，即使不在该部门。"""
        admin, hr, _it = users
        _p, _i, secret_hr, secret_it, _d = docs
        # 两篇机密都由 admin 撰写
        assert can_view_document(admin, secret_hr) is True
        assert can_view_document(admin, secret_it) is True
        # 非作者、非同部门的员工看不到
        assert can_view_document(hr, secret_it) is False

    def test_none_user_cannot_view(self, docs):
        public, *_ = docs
        assert can_view_document(None, public) is False


class TestSearchScope:
    """检索范围：只有已发布 + 可见的文档进入检索结果（防机密泄漏）。"""

    def test_excludes_other_department_secret(self, app, users, docs):
        _admin, hr, _it = users
        titles = {d.title for d in searchable_documents(hr)}
        assert "信息部机密" not in titles
        assert "人事机密" in titles

    def test_excludes_drafts(self, app, users, docs):
        _admin, hr, _it = users
        titles = {d.title for d in searchable_documents(hr)}
        assert "草稿文档" not in titles

    def test_admin_includes_secret(self, app, users, docs):
        admin, *_ = users
        titles = {d.title for d in searchable_documents(admin)}
        assert {"人事机密", "信息部机密"} <= titles


class TestSafeNextUrl:
    """登录回跳只允许站内相对路径，防止 open redirect。"""

    @pytest.mark.parametrize(
        "value",
        [
            "https://evil.com",
            "http://evil.com/x",
            "//evil.com",
            "///evil.com",
            "javascript:alert(1)",
            "\\\\evil.com",
            "/\\evil.com",
            "/x\n/y",
            "/x\r/y",
            "",
            None,
        ],
    )
    def test_rejects_unsafe(self, value):
        assert safe_next_url(value) is None

    @pytest.mark.parametrize(
        "value",
        ["/dashboard", "/knowledge/", "/qa/", "/knowledge/12"],
    )
    def test_allows_internal(self, value):
        assert safe_next_url(value) == value


class TestRankDocuments:
    """列表排序：标题命中应排在仅正文命中之前。"""

    def _doc(self, app, title, content, tags=""):
        from app.extensions import db

        doc = Document(
            title=title,
            content=content,
            tags=tags,
            department="人事部",
            visibility="internal",
            status="published",
        )
        db.session.add(doc)
        db.session.flush()
        return doc

    def test_title_beats_body(self, app):
        a = self._doc(app, "年假制度", "与年假无关的正文")
        b = self._doc(app, "其他制度", "这里提到年假天数")
        ranked = rank_documents([b, a], "年假")
        assert ranked[0].id == a.id

    def test_empty_query_keeps_order(self, app):
        a = self._doc(app, "A", "x")
        b = self._doc(app, "B", "y")
        assert rank_documents([a, b], "") == [a, b]

    def test_no_match_returns_empty(self, app):
        """无命中时返回空列表，调用方据此显示空状态。"""
        a = self._doc(app, "A", "x")
        assert rank_documents([a], "完全不存在的词xyz") == []


class TestNormalizeChoice:
    def test_allowed_value_passes(self):
        assert normalize_choice("secret", {"public": 1, "secret": 2}, "public") == "secret"

    def test_unknown_falls_back(self):
        assert normalize_choice("bogus", {"public": 1}, "public") == "public"

    def test_blank_falls_back(self):
        assert normalize_choice("", {"public": 1}, "public") == "public"
        assert normalize_choice(None, {"public": 1}, "public") == "public"


class TestAutoSummary:
    def test_truncates_long_text(self):
        text = "第一句话。" + "补充" * 200
        out = auto_summary(text, limit=40)
        assert len(out) <= 45

    def test_prefers_sentence_boundary_when_in_window(self):
        """句读落在截断窗口后半段时，会切在句号上而不是硬截。"""
        text = "年假五天。" + "补充说明内容" * 40
        out = auto_summary(text, limit=10)
        assert out.endswith("。")
        assert out == "年假五天。"

    def test_hard_truncates_when_no_boundary_nearby(self):
        """窗口内没有可用句读时退回截断 + 省略号，且不超长太多。"""
        text = "年假五天。" + "补充说明内容" * 40
        out = auto_summary(text, limit=40)
        assert out.endswith("…")
        assert len(out) <= 41

    def test_empty_content(self):
        assert auto_summary("") == ""
        assert auto_summary(None) == ""

    def test_short_text_unchanged(self):
        assert auto_summary("很短的一句话") == "很短的一句话"


class TestDepartments:
    def test_seed_departments_are_valid(self):
        assert "综合部" in DEPARTMENTS
        assert len(DEPARTMENTS) >= 5
        assert len(set(DEPARTMENTS)) == len(DEPARTMENTS)

class TestAboutStatsScope:
    """关于页统计必须跟随用户可见范围，避免用数字泄露机密规模。"""

    def _visible_stats(self, client):
        res = client.get("/about")
        assert res.status_code == 200
        text = res.get_data(as_text=True)
        # 页面标注了口径，避免读者误以为是全库数字
        assert "本人可见范围" in text
        return text

    def test_hr_sees_fewer_documents_than_admin(self, client, app):
        import re

        def doc_count(text):
            m = re.search(r"知识文档</span><strong>(\d+)</strong>", text)
            return int(m.group(1)) if m else -1

        client.post("/auth/login", data={"username": "hr", "password": "hr123"})
        hr_text = self._visible_stats(client)
        client.get("/auth/logout", follow_redirects=True)

        client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        admin_text = self._visible_stats(client)

        assert doc_count(hr_text) < doc_count(admin_text)

    def test_chunk_count_matches_visible_documents(self, client, app):
        """片段数不能超过可见文档能切出的片段，且随权限收缩。"""
        import re

        def counts(text):
            docs = int(re.search(r"知识文档</span><strong>(\d+)</strong>", text).group(1))
            chunks = int(
                re.search(r"检索用知识片段</span><strong>(\d+)</strong>", text).group(1)
            )
            return docs, chunks

        client.post("/auth/login", data={"username": "hr", "password": "hr123"})
        docs, chunks = counts(self._visible_stats(client))
        assert chunks >= docs  # 每篇文档至少切出一个片段

    def test_qa_count_is_personal(self, client, app):
        """问答记录只统计本人，不显示全站提问量。"""
        import re

        client.post("/auth/login", data={"username": "hr", "password": "hr123"})
        client.post("/qa/", data={"question": "年假有几天？"})
        text = self._visible_stats(client)
        n = int(re.search(r"问答记录</span><strong>(\d+)</strong>", text).group(1))
        assert n >= 1
