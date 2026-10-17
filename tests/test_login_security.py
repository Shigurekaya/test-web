"""登录限流与失败审计测试。

对应安全需求 SR-AUTH-*：密码不可明文存储、登录失败可追溯、防爆破。
"""
from __future__ import annotations

import pytest

from app.blueprints.auth import login_limiter
from app.utils import RateLimiter


@pytest.fixture(autouse=True)
def reset_limiter():
    login_limiter.clear("login:testclient")
    login_limiter.clear("login:127.0.0.1")
    yield
    login_limiter.clear("login:testclient")
    login_limiter.clear("login:127.0.0.1")


class TestRateLimiterUnit:
    def test_allows_up_to_threshold(self):
        rl = RateLimiter(max_attempts=3, window_seconds=60)
        now = 1000.0
        assert rl.is_locked("k", now) is False
        rl.record_failure("k", now)
        rl.record_failure("k", now)
        assert rl.is_locked("k", now) is False
        rl.record_failure("k", now)
        assert rl.is_locked("k", now) is True

    def test_lock_expires_outside_window(self):
        rl = RateLimiter(max_attempts=2, window_seconds=60)
        for _ in range(2):
            rl.record_failure("k", 1000.0)
        assert rl.is_locked("k", 1000.0) is True
        assert rl.is_locked("k", 1000.0 + 61) is False

    def test_success_clears_counter(self):
        rl = RateLimiter(max_attempts=3, window_seconds=60)
        rl.record_failure("k", 1000.0)
        rl.record_failure("k", 1000.0)
        rl.clear("k")
        assert rl.is_locked("k", 1000.0) is False

    def test_retry_after_positive_when_locked(self):
        rl = RateLimiter(max_attempts=2, window_seconds=60)
        rl.record_failure("k", 1000.0)
        rl.record_failure("k", 1000.0)
        assert rl.retry_after("k", 1000.0) == 60

    def test_retry_after_zero_when_not_locked(self):
        rl = RateLimiter(max_attempts=5, window_seconds=60)
        assert rl.retry_after("k", 1000.0) == 0

    def test_keys_are_independent(self):
        rl = RateLimiter(max_attempts=2, window_seconds=60)
        rl.record_failure("a", 1000.0)
        rl.record_failure("a", 1000.0)
        assert rl.is_locked("a", 1000.0) is True
        assert rl.is_locked("b", 1000.0) is False

    def test_old_events_are_pruned_not_unbounded(self):
        rl = RateLimiter(max_attempts=3, window_seconds=10)
        for i in range(50):
            rl.record_failure("k", 1000.0 + i)
        # 只保留窗口内的事件，不会无限增长
        assert len(rl._events["k"]) <= 11


class TestLoginBruteForce:
    def test_repeated_failures_lock_the_ip(self, client, app):
        original = login_limiter.max_attempts
        login_limiter.max_attempts = 5
        try:
            for _ in range(5):
                res = client.post(
                    "/auth/login", data={"username": "admin", "password": "wrong"}
                )
                assert res.status_code == 200
            res = client.post(
                "/auth/login", data={"username": "admin", "password": "wrong"}
            )
            assert res.status_code == 429
            assert "登录失败次数过多".encode() in res.data
        finally:
            login_limiter.max_attempts = original
            login_limiter.clear("login:127.0.0.1")

    def test_correct_password_still_blocked_while_locked(self, client, app):
        """锁定后即便密码正确也不放行，否则爆破可以直接试中。"""
        original = login_limiter.max_attempts
        login_limiter.max_attempts = 3
        try:
            for _ in range(3):
                client.post("/auth/login", data={"username": "admin", "password": "no"})
            res = client.post(
                "/auth/login",
                data={"username": "admin", "password": "admin123"},
                follow_redirects=False,
            )
            assert res.status_code == 429
        finally:
            login_limiter.max_attempts = original
            login_limiter.clear("login:127.0.0.1")

    def test_successful_login_resets_counter(self, client, app):
        """登录成功后失败计数清零，爆破不能靠多次成功续命。"""
        original = login_limiter.max_attempts
        login_limiter.max_attempts = 4
        try:
            for _ in range(3):
                res = client.post(
                    "/auth/login", data={"username": "admin", "password": "no"}
                )
                assert res.status_code == 200

            # 用对密码登录一次；紧接着立刻退出，让计数被清掉
            client.post(
                "/auth/login",
                data={"username": "admin", "password": "admin123", "next": "/auth/logout"},
                follow_redirects=True,
            )
            client.get("/auth/logout", follow_redirects=True)

            # 清零后再来 3 次失败，还没到阈值 4，因此不会被锁
            for _ in range(3):
                res = client.post(
                    "/auth/login", data={"username": "admin", "password": "no"}
                )
                assert res.status_code == 200

            # 第 4 次失败把计数顶到阈值，同一次请求照常返回登录页；
            # 下一次请求才会看到锁定（锁定判定发生在密码校验之前）。
            res = client.post(
                "/auth/login", data={"username": "admin", "password": "no"}
            )
            assert res.status_code == 200

            res = client.post(
                "/auth/login", data={"username": "admin", "password": "no"}
            )
            assert res.status_code == 429
        finally:
            login_limiter.max_attempts = original
            login_limiter.clear("login:127.0.0.1")


class TestFailedLoginAudit:
    def test_failed_login_is_recorded(self, client, app):
        from app.models import AuditLog

        client.post("/auth/login", data={"username": "admin", "password": "bad"})
        with app.app_context():
            failed = AuditLog.query.filter_by(action="login_failed").all()
            assert len(failed) >= 1
            assert "admin" in failed[-1].detail

    def test_unknown_user_failure_is_recorded(self, client, app):
        from app.models import AuditLog

        client.post("/auth/login", data={"username": "ghost_user", "password": "x"})
        with app.app_context():
            failed = AuditLog.query.filter_by(action="login_failed").all()
            assert any("ghost_user" in f.detail for f in failed)

    def test_successful_login_action_label_exists(self):
        from app.utils import ACTION_LABELS

        assert ACTION_LABELS["login_failed"] == "登录失败"


class TestPasswordStorage:
    def test_password_is_hashed_not_stored(self, app):
        from app.models import User

        with app.app_context():
            user = User.query.filter_by(username="admin").first()
            assert user.password_hash != "admin123"
            assert user.password_hash.startswith(("scrypt:", "pbkdf2:"))
            assert user.check_password("admin123") is True
            assert user.check_password("admin1234") is False

class TestAuditDetailFormat:
    """审计明细统一由 audit_detail 拼装，避免各处格式漂移。"""

    def test_document_actions_include_id_and_title(self):
        from app.utils import audit_detail

        assert audit_detail("view_document", doc_id=17, title="年假办法") == "查看文档 #17 《年假办法》"
        assert audit_detail("edit_document", doc_id=3) == "编辑文档 #3"

    def test_question_is_truncated(self):
        from app.utils import audit_detail

        long_q = "长" * 120
        out = audit_detail("ask_qa", question=long_q)
        assert out.startswith("提问：")
        assert len(out) < 90
        assert out.endswith("…")

    def test_short_question_has_no_ellipsis(self):
        from app.utils import audit_detail

        assert audit_detail("ask_qa", question="年假几天") == "提问：年假几天"

    def test_account_actions(self):
        from app.utils import audit_detail

        assert audit_detail("login", username="admin") == "用户 admin 登录"
        assert audit_detail("logout", username="admin") == "用户 admin 退出"
        assert audit_detail("login_failed", username="ghost") == "登录失败：ghost"
        assert audit_detail("login_failed", username=None) == "登录失败：(空用户名)"

    def test_blueprints_and_seed_share_the_format(self, client, app):
        """运行时写入与种子数据的文案格式必须一致，审计页读起来才统一。"""
        import re

        from app.models import AuditLog

        client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        client.post("/auth/login", data={"username": "admin", "password": "bad"})

        with app.app_context():
            failed = AuditLog.query.filter_by(action="login_failed").all()
            ok = AuditLog.query.filter_by(action="login").all()
            assert failed and ok
            assert re.fullmatch(r"登录失败：\S+", failed[-1].detail)
            assert re.fullmatch(r"用户 \S+ 登录", ok[-1].detail)
