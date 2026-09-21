from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.utils import (
    MODE_LABELS,
    ROLE_LABELS,
    STATUS_BADGE,
    STATUS_LABELS,
    VISIBILITY_BADGE,
    VISIBILITY_LABELS,
    label_of,
    utcnow,
)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(64), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="employee")
    department = db.Column(db.String(64), nullable=False, default="综合部")
    created_at = db.Column(db.DateTime, default=utcnow)

    documents = db.relationship("Document", back_populates="author", lazy="dynamic")
    favorites = db.relationship("Favorite", back_populates="user", lazy="dynamic")
    audit_logs = db.relationship("AuditLog", back_populates="user", lazy="dynamic")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def role_label(self) -> str:
        return label_of(ROLE_LABELS, self.role)


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(255), default="")

    documents = db.relationship("Document", back_populates="category", lazy="dynamic")


class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False, default="")
    summary = db.Column(db.String(500), default="")
    department = db.Column(db.String(64), nullable=False, default="综合部")
    visibility = db.Column(db.String(20), nullable=False, default="internal")
    status = db.Column(db.String(20), nullable=False, default="published")
    version = db.Column(db.String(20), default="1.0")
    filename = db.Column(db.String(255), default="")
    tags = db.Column(db.String(255), default="")
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"))
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    category = db.relationship("Category", back_populates="documents")
    author = db.relationship("User", back_populates="documents")
    chunks = db.relationship("KnowledgeChunk", back_populates="document", cascade="all, delete-orphan")
    favorites = db.relationship("Favorite", back_populates="document", cascade="all, delete-orphan")

    @property
    def visibility_label(self) -> str:
        return label_of(VISIBILITY_LABELS, self.visibility)

    @property
    def status_label(self) -> str:
        return label_of(STATUS_LABELS, self.status)

    @property
    def visibility_badge(self) -> str:
        return VISIBILITY_BADGE.get(self.visibility, "secondary")

    @property
    def status_badge(self) -> str:
        return STATUS_BADGE.get(self.status, "secondary")

    @property
    def tag_list(self) -> list[str]:
        return [t.strip() for t in (self.tags or "").split(",") if t.strip()]

    @property
    def char_count(self) -> int:
        return len(self.content or "")

    @property
    def chunk_count(self) -> int:
        return len(self.chunks) if self.chunks is not None else 0


class KnowledgeChunk(db.Model):
    __tablename__ = "knowledge_chunks"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=False, index=True)
    chunk_index = db.Column(db.Integer, nullable=False, default=0)
    content = db.Column(db.Text, nullable=False)
    keywords = db.Column(db.String(500), default="")

    document = db.relationship("Document", back_populates="chunks")


class GraphNode(db.Model):
    __tablename__ = "graph_nodes"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    node_type = db.Column(db.String(40), nullable=False, default="concept")
    description = db.Column(db.String(255), default="")
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=True)

    out_edges = db.relationship(
        "GraphEdge",
        foreign_keys="GraphEdge.source_id",
        back_populates="source",
        cascade="all, delete-orphan",
    )
    in_edges = db.relationship(
        "GraphEdge",
        foreign_keys="GraphEdge.target_id",
        back_populates="target",
        cascade="all, delete-orphan",
    )


class GraphEdge(db.Model):
    __tablename__ = "graph_edges"

    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.Integer, db.ForeignKey("graph_nodes.id"), nullable=False)
    target_id = db.Column(db.Integer, db.ForeignKey("graph_nodes.id"), nullable=False)
    relation = db.Column(db.String(64), nullable=False, default="关联")

    source = db.relationship("GraphNode", foreign_keys=[source_id], back_populates="out_edges")
    target = db.relationship("GraphNode", foreign_keys=[target_id], back_populates="in_edges")


class Favorite(db.Model):
    __tablename__ = "favorites"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)

    user = db.relationship("User", back_populates="favorites")
    document = db.relationship("Document", back_populates="favorites")

    __table_args__ = (db.UniqueConstraint("user_id", "document_id", name="uq_user_doc_fav"),)


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(64), nullable=False)
    detail = db.Column(db.String(500), default="")
    created_at = db.Column(db.DateTime, default=utcnow)

    user = db.relationship("User", back_populates="audit_logs")


class QAHistory(db.Model):
    __tablename__ = "qa_history"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    sources = db.Column(db.Text, default="")
    mode = db.Column(db.String(20), default="local")
    created_at = db.Column(db.DateTime, default=utcnow)

    @property
    def mode_label(self) -> str:
        return label_of(MODE_LABELS, self.mode)
