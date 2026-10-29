"""配置类：默认 / 测试 / 生产三套，敏感项一律走环境变量。"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    """默认配置（开发 / 演示）。"""

    SECRET_KEY = os.environ.get("SECRET_KEY", "kb-wealth-dev-secret")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'knowledge.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    UPLOAD_FOLDER = BASE_DIR / "uploads"
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {"txt", "md", "pdf", "docx"}

    # 可选 LLM（OpenAI 兼容协议）；留空则使用本地检索摘要模式
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    OPENAI_TIMEOUT = int(os.environ.get("OPENAI_TIMEOUT", "30"))

    # RAG 切分与检索
    CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", "400"))
    CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", "50"))
    TOP_K = int(os.environ.get("TOP_K", "5"))

    # 会话安全：Cookie 有效期（秒）
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = int(os.environ.get("SESSION_LIFETIME", "43200"))  # 12h

    # 自动建表与演示数据灌入；生产环境应显式关闭（见 ProductionConfig）
    AUTO_SEED = os.environ.get("AUTO_SEED", "1") not in ("0", "false", "False")

    # 登录防爆破：同一 IP 在窗口内失败次数超过阈值即临时锁定
    LOGIN_MAX_ATTEMPTS = int(os.environ.get("LOGIN_MAX_ATTEMPTS", "8"))
    LOGIN_WINDOW_SECONDS = int(os.environ.get("LOGIN_WINDOW_SECONDS", "300"))

    @staticmethod
    def init_app(app):
        """各环境共用的初始化钩子。"""
        pass


class TestingConfig(Config):
    """测试配置：独立临时库 + 关闭 CSRF 之外的副作用，绝不触碰生产数据。"""

    TESTING = True
    SECRET_KEY = "kb-wealth-testing-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite://"  # 内存库，进程退出即消失
    WTF_CSRF_ENABLED = False
    AUTO_SEED = True
    # 演示数据本身较重（需分词建索引），测试里按需显式重建
    LOGIN_DISABLED = False


class ProductionConfig(Config):
    """生产配置：不自动灌演示数据、错误不外泄细节。"""

    SECRET_KEY = os.environ.get("SECRET_KEY")
    AUTO_SEED = False
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "1") not in (
        "0",
        "false",
        "False",
    )

    @staticmethod
    def init_app(app):
        if not app.config.get("SECRET_KEY"):
            raise RuntimeError("生产环境必须显式设置 SECRET_KEY")


config_by_name = {
    "default": Config,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def resolve_config_name() -> str:
    """根据 FLASK_ENV / APP_ENV 选择配置类名。"""
    env = (os.environ.get("FLASK_ENV") or os.environ.get("APP_ENV") or "default").lower()
    return env if env in config_by_name else "default"
