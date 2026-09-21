"""文档切分、关键词提取、检索与问答（轻量 RAG）。"""
from __future__ import annotations

import json
import re
from typing import Any

import jieba
import jieba.analyse

from app.extensions import db
from app.models import Document, KnowledgeChunk, QAHistory


def chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    # 优先按段落切
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    chunks: list[str] = []
    buf = ""
    for para in paragraphs:
        if len(buf) + len(para) + 1 <= chunk_size:
            buf = f"{buf}\n{para}".strip() if buf else para
        else:
            if buf:
                chunks.append(buf)
            if len(para) <= chunk_size:
                buf = para
            else:
                start = 0
                while start < len(para):
                    end = start + chunk_size
                    chunks.append(para[start:end])
                    start = max(end - overlap, start + 1)
                buf = ""
    if buf:
        chunks.append(buf)
    return chunks


def extract_keywords(text: str, top_k: int = 8) -> str:
    tags = jieba.analyse.extract_tags(text or "", topK=top_k)
    return ",".join(tags)


def rebuild_chunks_for_document(doc: Document, chunk_size: int = 400, overlap: int = 50) -> int:
    KnowledgeChunk.query.filter_by(document_id=doc.id).delete()
    pieces = chunk_text(doc.content, chunk_size=chunk_size, overlap=overlap)
    for i, piece in enumerate(pieces):
        db.session.add(
            KnowledgeChunk(
                document_id=doc.id,
                chunk_index=i,
                content=piece,
                keywords=extract_keywords(piece),
            )
        )
    db.session.commit()
    return len(pieces)


def _tokenize(text: str) -> set[str]:
    return {t.strip() for t in jieba.lcut(text or "") if len(t.strip()) > 1}


def score_chunk(question_tokens: set[str], chunk: KnowledgeChunk) -> float:
    content_tokens = _tokenize(chunk.content)
    kw_tokens = {k for k in (chunk.keywords or "").split(",") if k}
    if not question_tokens:
        return 0.0
    content_hit = len(question_tokens & content_tokens)
    kw_hit = len(question_tokens & kw_tokens)
    # 关键词命中加权
    return content_hit + kw_hit * 1.5


def searchable_documents(user) -> list[Document]:
    q = Document.query.filter_by(status="published")
    docs = q.order_by(Document.updated_at.desc()).all()
    result = []
    for doc in docs:
        if can_view_document(user, doc):
            result.append(doc)
    return result


def can_view_document(user, doc: Document) -> bool:
    if user is None:
        return False
    if user.is_admin:
        return True
    if doc.visibility == "secret":
        return doc.department == user.department or doc.author_id == user.id
    if doc.visibility == "internal":
        return True
    return True  # public


def retrieve(question: str, user, top_k: int = 5) -> list[dict[str, Any]]:
    allowed_ids = {d.id for d in searchable_documents(user)}
    if not allowed_ids:
        return []
    q_tokens = _tokenize(question)
    chunks = KnowledgeChunk.query.filter(KnowledgeChunk.document_id.in_(allowed_ids)).all()
    scored = []
    for ch in chunks:
        s = score_chunk(q_tokens, ch)
        if s > 0:
            scored.append((s, ch))
    scored.sort(key=lambda x: x[0], reverse=True)
    results = []
    for s, ch in scored[:top_k]:
        results.append(
            {
                "score": round(s, 2),
                "chunk_id": ch.id,
                "document_id": ch.document_id,
                "title": ch.document.title if ch.document else "",
                "content": ch.content,
                "department": ch.document.department if ch.document else "",
            }
        )
    return results


def build_local_answer(question: str, hits: list[dict[str, Any]]) -> str:
    if not hits:
        return (
            "未在可访问的知识库中检索到相关内容。"
            "请换个问法，或确认文档已发布且您有权限查看。"
        )
    lines = [
        f"根据企业知识库检索，针对「{question}」整理如下：",
        "",
    ]
    for i, h in enumerate(hits, 1):
        snippet = h["content"].strip().replace("\n", " ")
        if len(snippet) > 220:
            snippet = snippet[:220] + "…"
        lines.append(f"{i}. 【{h['title']}】{snippet}")
        lines.append(f"   （来源文档 #{h['document_id']}，相关部门：{h['department']}，相关度 {h['score']}）")
        lines.append("")
    lines.append("说明：当前为本地检索摘要模式。配置 OPENAI_API_KEY 后可启用大模型生成式回答。")
    return "\n".join(lines)


def _cfg(config, key: str, default=""):
    if hasattr(config, "get"):
        return config.get(key, default)
    return getattr(config, key, default)


def call_llm_answer(question: str, hits: list[dict[str, Any]], config) -> str | None:
    api_key = _cfg(config, "OPENAI_API_KEY", "") or ""
    if not api_key or not hits:
        return None
    try:
        from urllib import request

        context = "\n\n".join(
            f"[文档:{h['title']}]\n{h['content']}" for h in hits
        )
        payload = {
            "model": _cfg(config, "OPENAI_MODEL", "gpt-4o-mini"),
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是企业知识库助手。只能依据给定资料回答，"
                        "若资料不足请明确说明。回答简洁，并指出依据的文档标题。"
                    ),
                },
                {
                    "role": "user",
                    "content": f"问题：{question}\n\n参考资料：\n{context}",
                },
            ],
            "temperature": 0.2,
        }
        body = json.dumps(payload).encode("utf-8")
        base = _cfg(config, "OPENAI_BASE_URL", "https://api.openai.com/v1")
        url = str(base).rstrip("/") + "/chat/completions"
        req = request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        with request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:  # noqa: BLE001
        return f"（大模型调用失败，已回退本地摘要）错误：{exc}\n\n" + build_local_answer(
            question, hits
        )


def ask(question: str, user, config) -> dict[str, Any]:
    hits = retrieve(question, user, top_k=int(_cfg(config, "TOP_K", 5) or 5))
    llm_answer = call_llm_answer(question, hits, config)
    if llm_answer and not llm_answer.startswith("（大模型调用失败"):
        answer = llm_answer
        mode = "llm"
    elif llm_answer:
        answer = llm_answer
        mode = "local"
    else:
        answer = build_local_answer(question, hits)
        mode = "local"

    sources = json.dumps(
        [{"document_id": h["document_id"], "title": h["title"], "score": h["score"]} for h in hits],
        ensure_ascii=False,
    )
    hist = QAHistory(
        user_id=user.id if user else None,
        question=question,
        answer=answer,
        sources=sources,
        mode=mode,
    )
    db.session.add(hist)
    db.session.commit()
    return {"answer": answer, "hits": hits, "mode": mode, "history_id": hist.id}
