from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import AuditLog, Category, Document, Favorite, KnowledgeChunk
from app.services.graph import sync_document_graph
from app.services.rag import can_view_document, rebuild_chunks_for_document, searchable_documents
from app.utils import STATUS_LABELS, VISIBILITY_LABELS, admin_required

bp = Blueprint("knowledge", __name__, url_prefix="/knowledge")

DEPARTMENTS = ["综合部", "人事部", "财务部", "信息部", "产品部"]


@bp.route("/")
@login_required
def list_docs():
    q = request.args.get("q", "").strip()
    category_id = request.args.get("category_id", type=int)
    department = request.args.get("department", "").strip()
    visibility = request.args.get("visibility", "").strip()
    page = max(request.args.get("page", 1, type=int) or 1, 1)
    per_page = 8

    docs = searchable_documents(current_user)
    if category_id:
        docs = [d for d in docs if d.category_id == category_id]
    if department:
        docs = [d for d in docs if d.department == department]
    if visibility:
        docs = [d for d in docs if d.visibility == visibility]
    if q:
        ql = q.lower()
        docs = [
            d
            for d in docs
            if ql in (d.title or "").lower()
            or ql in (d.content or "").lower()
            or ql in (d.tags or "").lower()
            or ql in (d.summary or "").lower()
        ]

    total = len(docs)
    pages = max((total + per_page - 1) // per_page, 1)
    page = min(page, pages)
    start = (page - 1) * per_page
    page_docs = docs[start : start + per_page]
    categories = Category.query.order_by(Category.name).all()

    return render_template(
        "knowledge/list.html",
        documents=page_docs,
        categories=categories,
        departments=DEPARTMENTS,
        q=q,
        category_id=category_id,
        department=department,
        visibility=visibility,
        page=page,
        pages=pages,
        total=total,
        visibility_labels=VISIBILITY_LABELS,
    )


@bp.route("/<int:doc_id>")
@login_required
def detail(doc_id: int):
    doc = db.get_or_404(Document, doc_id)
    if not can_view_document(current_user, doc):
        abort(403)
    fav = Favorite.query.filter_by(user_id=current_user.id, document_id=doc.id).first()
    db.session.add(
        AuditLog(
            user_id=current_user.id,
            action="view_document",
            detail=f"查看文档 #{doc.id} {doc.title}",
        )
    )
    db.session.commit()

    related = []
    if doc.category_id:
        candidates = (
            Document.query.filter(
                Document.category_id == doc.category_id,
                Document.id != doc.id,
                Document.status == "published",
            )
            .order_by(Document.updated_at.desc())
            .limit(8)
            .all()
        )
        related = [c for c in candidates if can_view_document(current_user, c)][:4]

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
        cat_raw = request.form.get("category_id") or ""
        category_id = int(cat_raw) if str(cat_raw).isdigit() else None
        doc = Document(
            title=title,
            content=content,
            summary=request.form.get("summary", "").strip()[:500],
            department=request.form.get("department") or current_user.department,
            visibility=request.form.get("visibility", "internal"),
            status=request.form.get("status", "published"),
            version=request.form.get("version", "1.0"),
            tags=request.form.get("tags", "").strip(),
            category_id=category_id,
            author_id=current_user.id,
        )
        db.session.add(doc)
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
        doc.title = request.form.get("title", "").strip()
        doc.content = request.form.get("content", "").strip()
        doc.summary = request.form.get("summary", "").strip()[:500]
        doc.department = request.form.get("department") or doc.department
        doc.visibility = request.form.get("visibility", "internal")
        doc.status = request.form.get("status", "published")
        doc.version = request.form.get("version", "1.0")
        doc.tags = request.form.get("tags", "").strip()
        cat = request.form.get("category_id")
        doc.category_id = int(cat) if cat and str(cat).isdigit() else None
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
    return render_template("knowledge/categories.html", categories=cats)
