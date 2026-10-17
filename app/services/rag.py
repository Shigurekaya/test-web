"""文档切分、关键词提取、检索与问答（轻量 RAG）。"""
from __future__ import annotations

import json
import re
from typing import Any

import jieba
import jieba.analyse

from app.extensions import db
from app.models import Document, KnowledgeChunk, QAHistory
from app.utils import auto_summary

_DOMAIN_LOADED = False


def chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
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


# 领域补充词表：jieba 默认词典未收录、但本系统高频使用的业务词。
# 「年假」就是一个典型——默认分词会切成 ['年','假']，两个单字都被长度过滤丢掉，
# 于是整个分词结果为空集，标题/标签加权全部失效（本系统的示例检索词正是「年假」）。
DOMAIN_WORDS = (
    "年假 年休假 调休 加班 报销 差旅 出差 住宿 试用期 入职 离职 转正 社保 公积金 基数",
    "密钥 轮换 密级 机密 脱敏 备份 容灾 演练 限流 网关 密钥轮换",
    "续费 商机 线索 首触 成交 话术 值班 升级矩阵 客诉",
    "用印 印章 合同模板 发票 验真 驳回 预算 滚动预测 采购 审批流",
    "复盘 述职 学分 选修课 固定资产 盘点 门禁 VPN 发布窗口 代码评审",
    "知识库 知识财富库 关系图 图谱 检索 问答 分词 切分 片段 权限",
    "OA 工号 直属主管 分管领导 人事部 财务部 信息部 产品部 运营部 市场部 法务部 技术部 综合部",
)


def _ensure_domain_words() -> None:
    """把领域词表注册进 jieba（幂等，只在首次调用时执行）。"""
    global _DOMAIN_LOADED
    if _DOMAIN_LOADED:
        return
    words = [w for group in DOMAIN_WORDS for w in group.split() if len(w) > 1]
    for word in words:
        jieba.add_word(word, freq=200_000)
    _DOMAIN_LOADED = True


def _cjk_bigrams(text: str) -> set[str]:
    """连续汉字的相邻二字组合。

    作为分词的安全网：即使某个词不在任何词典里（如新造的业务缩写），
    二字组也能让检索拿到可用的重叠信号，而不是空集。
    """
    chars = [c for c in text if "\u4e00" <= c <= "\u9fff"]
    return {"".join(chars[i : i + 2]) for i in range(len(chars) - 1)}


def _tokenize(text: str) -> set[str]:
    """把查询或正文切成用于检索的词集合。

    组合三种信号，尽量不出现空集：
    1. jieba 分词结果（词典词，精度高）；
    2. 领域补充词表覆盖的业务术语；
    3. 相邻汉字二字组，用于兜底词典未收录的新词。

    单个汉字不进入结果（噪声太高），因此纯单字输入仍可能为空集，
    此时打分逻辑会退化为整串子串匹配（见 score_chunk）。
    """
    text = text or ""
    if not text.strip():
        return set()
    _ensure_domain_words()
    lower = text.lower()
    tokens = {t.strip().lower() for t in jieba.lcut(lower) if len(t.strip()) > 1}
    if not tokens:
        tokens = _cjk_bigrams(lower)
    return tokens


def score_chunk(question: str, question_tokens: set[str], chunk: KnowledgeChunk) -> float:
    """综合：词重叠 + 关键词加权 + 标题命中 + 短语包含。"""
    if not question_tokens and not (question or "").strip():
        return 0.0

    content = chunk.content or ""
    content_l = content.lower()
    content_tokens = _tokenize(content)
    kw_tokens = {k.strip().lower() for k in (chunk.keywords or "").split(",") if k.strip()}
    title = chunk.document.title if chunk.document else ""
    title_tokens = _tokenize(title)
    q = (question or "").strip().lower()

    content_hit = len(question_tokens & content_tokens)
    kw_hit = len(question_tokens & kw_tokens)
    title_hit = len(question_tokens & title_tokens)
    coverage = (content_hit / len(question_tokens)) if question_tokens else 0.0

    score = content_hit * 1.0 + kw_hit * 1.8 + title_hit * 3.2 + coverage * 2.0

    if q:
        if q in content_l:
            score += 10.0
        elif len(q) >= 4 and q[: max(4, len(q) // 2)] in content_l:
            score += 4.0
        if q in (title or "").lower():
            score += 6.0
        # 去掉疑问助词后的短句再匹配一次
        q_core = re.sub(r"[吗呢啊呀？?]+$", "", q).strip()
        if q_core and q_core != q and q_core in content_l:
            score += 5.0

    return score


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


def searchable_documents(user) -> list[Document]:
    docs = Document.query.filter_by(status="published").order_by(Document.updated_at.desc()).all()
    return [doc for doc in docs if can_view_document(user, doc)]


def rank_documents(docs: list[Document], q: str) -> list[Document]:
    """列表页关键词排序：标题 / 标签优先，其次摘要与正文。"""
    ql = (q or "").strip().lower()
    if not ql:
        return docs

    q_tokens = _tokenize(ql)
    scored: list[tuple[float, Document]] = []
    for d in docs:
        title = (d.title or "").lower()
        summary = (d.summary or "").lower()
        tags = (d.tags or "").lower()
        content = (d.content or "").lower()
        score = 0.0
        if ql in title:
            score += 20
        if ql in tags:
            score += 12
        if ql in summary:
            score += 8
        if ql in content:
            score += 4
        if q_tokens:
            score += 3 * len(q_tokens & _tokenize(d.title or ""))
            score += 2 * len(q_tokens & _tokenize(d.tags or ""))
            score += 1 * len(q_tokens & _tokenize(d.summary or ""))
        if score > 0:
            scored.append((score, d))
    scored.sort(
        key=lambda x: (
            -x[0],
            -(x[1].updated_at.timestamp() if x[1].updated_at else 0),
        )
    )
    return [d for _, d in scored]


def related_documents(doc: Document, user, limit: int = 4) -> list[Document]:
    """按同分类 / 标签重叠 / 同部门挑选相关文档。"""
    base_tags = set(doc.tag_list)
    candidates = (
        Document.query.filter(
            Document.id != doc.id,
            Document.status == "published",
        )
        .order_by(Document.updated_at.desc())
        .limit(40)
        .all()
    )
    scored: list[tuple[float, Document]] = []
    for c in candidates:
        if not can_view_document(user, c):
            continue
        score = 0.0
        if doc.category_id and c.category_id == doc.category_id:
            score += 5
        if c.department == doc.department:
            score += 2
        overlap = len(base_tags & set(c.tag_list))
        score += overlap * 3
        if score > 0:
            scored.append((score, c))
    scored.sort(key=lambda x: (-x[0], -(x[1].updated_at.timestamp() if x[1].updated_at else 0)))
    return [c for _, c in scored[:limit]]


def retrieve(question: str, user, top_k: int = 5) -> list[dict[str, Any]]:
    allowed_ids = {d.id for d in searchable_documents(user)}
    if not allowed_ids:
        return []
    q_tokens = _tokenize(question)
    chunks = KnowledgeChunk.query.filter(KnowledgeChunk.document_id.in_(allowed_ids)).all()
    scored: list[tuple[float, KnowledgeChunk]] = []
    for ch in chunks:
        s = score_chunk(question, q_tokens, ch)
        if s > 0:
            scored.append((s, ch))
    scored.sort(key=lambda x: x[0], reverse=True)

    # 同一篇文档最多贡献 2 个片段：既保证来源多样，又允许长文从两处佐证。
    # 额外给每个片段标注它在所属文档内的序号，供界面合并展示，避免同一篇
    # 文档被渲染成两张内容几乎一样的卡片。
    results: list[dict[str, Any]] = []
    per_doc: dict[int, int] = {}
    for s, ch in scored:
        count = per_doc.get(ch.document_id, 0)
        if count >= 2:
            continue
        per_doc[ch.document_id] = count + 1
        results.append(
            {
                "score": round(s, 2),
                "chunk_id": ch.id,
                "document_id": ch.document_id,
                "title": ch.document.title if ch.document else "",
                "content": ch.content,
                "department": ch.document.department if ch.document else "",
                "fragment_no": count + 1,
                "fragment_total": 0,  # 下面回填
            }
        )
        if len(results) >= top_k:
            break

    for item in results:
        item["fragment_total"] = per_doc[item["document_id"]]
    return results


def group_hits_by_document(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """把命中片段按文档合并，供「检索依据」按文档展示。

    返回的每项：document_id / title / department / score（取该文档最高分）/
    fragments（该文档的片段列表）。
    """
    grouped: dict[int, dict[str, Any]] = {}
    for hit in hits:
        bucket = grouped.get(hit["document_id"])
        if bucket is None:
            bucket = {
                "document_id": hit["document_id"],
                "title": hit["title"],
                "department": hit["department"],
                "score": hit["score"],
                "fragments": [],
            }
            grouped[hit["document_id"]] = bucket
        else:
            bucket["score"] = max(bucket["score"], hit["score"])
        bucket["fragments"].append(hit)
    return sorted(grouped.values(), key=lambda g: g["score"], reverse=True)


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
        snippet = auto_summary(h["content"].strip().replace("\n", " "), limit=220)
        lines.append(f"{i}. 【{h['title']}】{snippet}")
        lines.append(
            f"   （来源文档 #{h['document_id']}，相关部门：{h['department']}，相关度 {h['score']}）"
        )
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

        context = "\n\n".join(f"[文档:{h['title']}]\n{h['content']}" for h in hits)
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
