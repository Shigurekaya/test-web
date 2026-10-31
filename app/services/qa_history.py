"""Read helpers for the Q&A history sidebar and dashboard."""

from __future__ import annotations

import re

from app.models import QAHistory


def _question_key(question: str) -> str:
    text = re.sub(r"\s+", " ", (question or "").strip().casefold())
    return re.sub(r"[?？!！。.,，]+$", "", text).strip()


def recent_unique_qa(user_id: int, limit: int = 20) -> list[QAHistory]:
    """Return the latest record per normalized question for one user."""
    seen: set[str] = set()
    items: list[QAHistory] = []
    rows = (
        QAHistory.query.filter_by(user_id=user_id)
        .order_by(QAHistory.created_at.desc(), QAHistory.id.desc())
        .limit(max(limit * 12, 240))
        .all()
    )
    for item in rows:
        key = _question_key(item.question)
        if key in seen:
            continue
        seen.add(key)
        items.append(item)
        if len(items) >= limit:
            break
    return items
