from datetime import timedelta

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import AuditLog, Category, Document, Favorite, KnowledgeChunk
from app.services.graph import remove_document_graph, sync_document_graph
from app.services.rag import (
    can_view_document,
    rank_documents,
    rebuild_chunks_for_document,
    related_documents,
    searchable_documents,
)
from app.utils import (
    DEPARTMENTS,
    STATUS_LABELS,
    VISIBILITY_LABELS,
    admin_required,
    auto_summary,
    normalize_choice,
    now_naive,
)

bp = Blueprint("knowledge", __name__, url_prefix="/knowledge")


def _apply_doc_form(doc: Document | None) -> Document:
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    summary = request.form.get("summary", "").strip()[:500]
    if not summary:
        summary = auto_summary(content)

    cat_raw = request.form.get("category_id") or ""
    category_id = int(cat_raw) if str(cat_raw).isdigit() else None
    visibility = normalize_choice(request.form.get("visibility"), VISIBILITY_LABELS, "internal")
    status = normalize_choice(request.form.get("status"), STATUS_LABELS, "published")
    department = request.form.get("department") or (doc.department if doc else current_user.department)
    if department not in DEPARTMENTS:
        department = current_user.department

    if doc is None:
        doc = Document(author_id=current_user.id)
        db.session.add(doc)

    doc.title = title
    doc.content = content
    doc.summary = summary
    doc.department = department
    doc.visibility = visibility
    doc.status = status
    doc.version = (request.form.get("version") or "1.0").strip() or "1.0"
    doc.tags = request.form.get("tags", "").strip()
    doc.category_id = category_id
    return doc


@bp.route("/")
@login_required
def list_docs():
    q = request.args.get("q", "").strip()
    category_id = request.args.get("category_id", type=int)
    department = request.args.get("department", "").strip()
    visibility = request.args.get("visibility", "").strip()
    sort = request.args.get("sort", "updated").strip() or "updated"
    page = max(request.args.get("page", 1, type=int) or 1, 1)
    per_page = 12

    docs = searchable_documents(current_user)
    if category_id:
        docs = [d for d in docs if d.category_id == category_id]
    if department:
        docs = [d for d in docs if d.department == department]
    if visibility:
        docs = [d for d in docs if d.visibility == visibility]

    if q:
        docs = rank_documents(docs, q)
    elif sort == "title":
        docs = sorted(docs, key=lambda d: d.title or "")
    elif sort == "department":
        docs = sorted(docs, key=lambda d: (d.department or "", -(d.updated_at.timestamp() if d.updated_at else 0)))
    else:
        docs = sorted(docs, key=lambda d: d.updated_at or now_naive(), reverse=True)

    total = len(docs)
    pages = max((total + per_page - 1) // per_page, 1)
    page = min(page, pages)
    start = (page - 1) * per_page
    page_docs = docs[start : start + per_page]
    categories = Category.query.order_by(Category.name).all()
    has_filter = bool(q or category_id or department or visibility)

    return render_template(
        "knowledge/list.html",
        documents=page_docs,
        categories=categories,
        departments=DEPARTMENTS,
        q=q,
        category_id=category_id,
        department=department,
        visibility=visibility,
        sort=sort,
        page=page,
        pages=pages,
        total=total,
        has_filter=has_filter,
        visibility_labels=VISIBILITY_LABELS,
    )


@bp.route("/<int:doc_id>")
@login_required
def detail(doc_id: int):
    doc = db.get_or_404(Document, doc_id)
    if not can_view_document(current_user, doc):
        abort(403)
    if doc.status != "published" and not (
        current_user.is_admin or doc.author_id == current_user.id
    ):
        abort(403)

    fav = Favorite.query.filter_by(user_id=current_user.id, document_id=doc.id).first()

    # 同一用户 2 分钟内重复打开不刷审计
    recent = (
        AuditLog.query.filter_by(user_id=current_user.id, action="view_document")
        .filter(AuditLog.created_at >= now_naive() - timedelta(minutes=2))
        .order_by(AuditLog.created_at.desc())
        .limit(5)
        .all()
    )
    already = any(f"#{doc.id} " in (log.detail or "") for log in recent)
    if not already:
        db.session.add(
            AuditLog(
                user_id=current_user.id,
                action="view_document",
                detail=f"查看文档 #{doc.id} {doc.title}",
            )
        )
        db.session.commit()

    related = related_documents(doc, current_user, limit=4)
    chunk_count = KnowledgeChunk.query.filter_by(document_id=doc.id).count()
    return render_template(
        "knowledge/detail.html",
        doc=doc,
        is_fav=bool(fav),
        related=related,
        chunk_count=chunk_count,
    )


@bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    categories = Category.query.order_by(Category.name).all()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        if not title or not content:
            flash("标题与正文不能为空", "danger")
            return render_template(
                "knowledge/form.html",
                categories=categories,
                departments=DEPARTMENTS,
                doc=None,
                visibility_labels=VISIBILITY_LABELS,
                status_labels=STATUS_LABELS,
            )
        doc = _apply_doc_form(None)
        db.session.commit()
        rebuild_chunks_for_document(
            doc,
            chunk_size=current_app.config["CHUNK_SIZE"],
            overlap=current_app.config["CHUNK_OVERLAP"],
        )
        sync_document_graph(doc)
        db.session.add(
            AuditLog(user_id=current_user.id, action="create_document", detail=f"创建文档 #{doc.id}")
        )
        db.session.commit()
        flash("文档已创建，并完成知识切分与图谱同步", "success")
        return redirect(url_for("knowledge.detail", doc_id=doc.id))
    return render_template(
        "knowledge/form.html",
        categories=categories,
        departments=DEPARTMENTS,
        doc=None,
        visibility_labels=VISIBILITY_LABELS,
        status_labels=STATUS_LABELS,
    )


@bp.route("/<int:doc_id>/edit", methods=["GET", "POST"])
@login_required
def edit(doc_id: int):
    doc = db.get_or_404(Document, doc_id)
    if not (current_user.is_admin or doc.author_id == current_user.id):
        abort(403)
    categories = Category.query.order_by(Category.name).all()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        if not title or not content:
            flash("标题与正文不能为空", "danger")
            return render_template(
                "knowledge/form.html",
                categories=categories,
                departments=DEPARTMENTS,
                doc=doc,
                visibility_labels=VISIBILITY_LABELS,
                status_labels=STATUS_LABELS,
            )
        _apply_doc_form(doc)
        db.session.commit()
        rebuild_chunks_for_document(
            doc,
            chunk_size=current_app.config["CHUNK_SIZE"],
            overlap=current_app.config["CHUNK_OVERLAP"],
        )
        sync_document_graph(doc)
        db.session.add(
            AuditLog(user_id=current_user.id, action="edit_document", detail=f"编辑文档 #{doc.id}")
        )
        db.session.commit()
        flash("文档已更新", "success")
        return redirect(url_for("knowledge.detail", doc_id=doc.id))
    return render_template(
        "knowledge/form.html",
        categories=categories,
        departments=DEPARTMENTS,
        doc=doc,
        visibility_labels=VISIBILITY_LABELS,
        status_labels=STATUS_LABELS,
    )


@bp.route("/<int:doc_id>/delete", methods=["POST"])
@login_required
def delete(doc_id: int):
    doc = db.get_or_404(Document, doc_id)
    if not (current_user.is_admin or doc.author_id == current_user.id):
        abort(403)
    title = doc.title
    remove_document_graph(doc)
    db.session.delete(doc)
    db.session.add(
        AuditLog(user_id=current_user.id, action="delete_document", detail=f"删除文档 {title}")
    )
    db.session.commit()
    flash("文档已删除", "info")
    return redirect(url_for("knowledge.list_docs"))


@bp.route("/<int:doc_id>/favorite", methods=["POST"])
@login_required
def toggle_favorite(doc_id: int):
    doc = db.get_or_404(Document, doc_id)
    if not can_view_document(current_user, doc):
        abort(403)
    fav = Favorite.query.filter_by(user_id=current_user.id, document_id=doc.id).first()
    if fav:
        db.session.delete(fav)
        flash("已取消收藏", "info")
    else:
        db.session.add(Favorite(user_id=current_user.id, document_id=doc.id))
        flash("已收藏", "success")
    db.session.commit()
    return redirect(url_for("knowledge.detail", doc_id=doc.id))


@bp.route("/favorites")
@login_required
def favorites():
    items = (
        Favorite.query.filter_by(user_id=current_user.id)
        .order_by(Favorite.created_at.desc())
        .all()
    )
    items = [i for i in items if i.document and can_view_document(current_user, i.document)]
    return render_template("knowledge/favorites.html", items=items)


@bp.route("/categories", methods=["GET", "POST"])
@login_required
@admin_required
def categories():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        desc = request.form.get("description", "").strip()
        if name and not Category.query.filter_by(name=name).first():
            db.session.add(Category(name=name, description=desc))
            db.session.commit()
            flash("分类已添加", "success")
        else:
            flash("分类名为空或已存在", "warning")
        return redirect(url_for("knowledge.categories"))
    cats = Category.query.order_by(Category.id).all()
    from collections import Counter

    doc_counts = Counter(
        row[0]
        for row in Document.query.with_entities(Document.category_id)
        .filter(Document.category_id.isnot(None))
        .all()
    )
    total_docs = Document.query.count()
    return render_template(
        "knowledge/categories.html",
        categories=cats,
        doc_counts=doc_counts,
        total_docs=total_docs,
    )
