import json

from flask import Blueprint, current_app, render_template, request
from flask_login import current_user, login_required

from app.extensions import db
from app.models import AuditLog, QAHistory
from app.qa_content import suggestions_for
from app.services.qa_history import recent_unique_qa
from app.services.rag import ask, group_hits_by_document
from app.utils import audit_detail

bp = Blueprint("qa", __name__, url_prefix="/qa")


@bp.route("/", methods=["GET", "POST"])
@login_required
def ask_page():
    result = None
    question = ""
    # 仅 POST 触发问答，避免示例链接用 GET 时刷新页面重复写入历史
    if request.method == "POST":
        question = request.form.get("question", "").strip()
        if question:
            result = ask(question, current_user, current_app.config)
            db.session.add(
                AuditLog(
                    user_id=current_user.id,
                    action="ask_qa",
                    detail=audit_detail("ask_qa", question=question),
                )
            )
            db.session.commit()
    else:
        question = request.args.get("q", "").strip()

    history = recent_unique_qa(current_user.id, limit=20)
    return render_template(
        "qa/ask.html",
        result=result,
        result_sources=group_hits_by_document(result["hits"]) if result else [],
        question=question,
        history=history,
        llm_enabled=bool(current_app.config.get("OPENAI_API_KEY")),
        suggestions=suggestions_for(current_user),
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
