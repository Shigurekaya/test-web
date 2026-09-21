import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "kb-wealth-dev-secret")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'knowledge.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {"txt", "md", "pdf", "docx"}

    # 可选 LLM（OpenAI 兼容协议）
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    # RAG
    CHUNK_SIZE = 400
    CHUNK_OVERLAP = 50
    TOP_K = 5
