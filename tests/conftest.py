"""pytest 公共夹具：为每个用例提供独立的内存数据库与已登录客户端。

关键约定：
- 任何用例都不会读写 `instance/knowledge.db`（生产 / 演示库）；
- 数据库结构在会话级创建一次，用例之间用事务回滚隔离，兼顾速度与洁净度；
- 需要"全新建库"的用例可用 `fresh_app` 夹具按完整流程（含 seed）重建。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("SECRET_KEY", "kb-wealth-testing-secret")
os.environ.pop("OPENAI_API_KEY", None)

from app import create_app  # noqa: E402
from app.config import TestingConfig  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import User  # noqa: E402


@pytest.fixture(scope="session")
def app_ctx():
    """会话级 app：仅用于共享 jieba 等一次性初始化开销。"""
    app = create_app(TestingConfig)
    with app.app_context():
        yield app


@pytest.fixture()
def app(app_ctx):
    """用例级 app：同一进程内复用结构，数据由事务回滚隔离。"""
    with app_ctx.app_context():
        db.create_all()
        try:
            yield app_ctx
        finally:
            db.session.rollback()
            db.session.remove()


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, username: str, password: str):
    return client.post(
        "/auth/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


@pytest.fixture()
def admin_client(client):
    assert login(client, "admin", "admin123").status_code == 200
    return client


def _teardown_engine(app):
    db.session.remove()
    engine = db.engine
    if engine is not None:
        engine.dispose()


@pytest.fixture()
def fresh_app(tmp_path):
    """完整重建一个全新库（含 seed），用于建库 / 种子数据回归。

    注意：app 上下文在整个用例期间保持打开，因此用例内可直接查询数据库。
    """
    db_file = tmp_path / "fresh.db"
    TestingConfig.SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_file.as_posix()}"
    TestingConfig.SQLALCHEMY_ENGINE_OPTIONS = {}
    ctx = None
    try:
        app = create_app(TestingConfig)
        ctx = app.app_context()
        ctx.push()
        db.create_all()
        from app.seed import seed_all

        seed_all(app)
        yield app
    finally:
        if ctx is not None:
            try:
                db.session.rollback()
                db.session.remove()
            except Exception:  # noqa: BLE001
                pass
            ctx.pop()
        TestingConfig.SQLALCHEMY_DATABASE_URI = "sqlite://"
        TestingConfig.SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}


@pytest.fixture()
def fresh_client(fresh_app):
    return fresh_app.test_client()


@pytest.fixture()
def db_counts(app):
    """返回数据库各表行数，便于断言状态迁移。"""
    from app.models import (
        AuditLog,
        Category,
        Document,
        Favorite,
        GraphEdge,
        GraphNode,
        KnowledgeChunk,
        QAHistory,
    )

    models = (
        User,
        Category,
        Document,
        KnowledgeChunk,
        GraphNode,
        GraphEdge,
        Favorite,
        AuditLog,
        QAHistory,
    )

    def read():
        return {m.__name__: m.query.count() for m in models}

    return read

