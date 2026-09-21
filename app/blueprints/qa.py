import json

from flask import Blueprint, current_app, render_template, request
from flask_login import current_user, login_required

from app.extensions import db
from app.models import AuditLog, QAHistory
from app.services.rag import ask

bp = Blueprint("qa", __name__, url_prefix="/qa")

SUGGESTED_QUESTIONS = [
    "员工年假有几天？",
    "差旅住宿标准是多少？",
    "加班怎么补偿？",
    "如何重置产品A密码？",
    "采购超过两万元要找谁审批？",
    "知识库怎么用？",
]


@bp.route("/", methods=["GET", "POST"])
@login_required
def ask_page():
    result = None
    question = ""
    if request.method == "POST":
        question = request.form.get("question", "").strip()
    else:
        question = request.args.get("q", "").strip()

    if question:
        result = ask(question, current_user, current_app.config)
        db.session.add(
            AuditLog(
                user_id=current_user.id,
                action="ask_qa",
                detail=f"提问：{question[:80]}",
            )
        )
        db.session.commit()

    history = (
        QAHistory.query.filter_by(user_id=current_user.id)
        .order_by(QAHistory.created_at.desc())
        .limit(10)
        .all()
    )
    return render_template(
        "qa/ask.html",
        result=result,
        question=question,
        history=history,
        llm_enabled=bool(current_app.config.get("OPENAI_API_KEY")),
        suggestions=SUGGESTED_QUESTIONS,
    )


@bp.route("/history/<int:hid>")
@login_required
def history_detail(hid: int):
    item = db.get_or_404(QAHistory, hid)
    if item.user_id != current_user.id and not current_user.is_admin:
        from flask import abort

        abort(403)
    sources = []
    try:
        sources = json.loads(item.sources or "[]")
    except json.JSONDecodeError:
        sources = []
    return render_template("qa/history_detail.html", item=item, sources=sources)
