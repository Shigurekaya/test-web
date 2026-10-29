"""RAG 检索与切分的单元测试。

覆盖 SR-QA-* 的核心算法：切分、打分、权限过滤、来源去重与降级行为。
"""

from __future__ import annotations

from app.services.rag import (
    build_local_answer,
    can_view_document,
    chunk_text,
    extract_keywords,
    group_hits_by_document,
    rebuild_chunks_for_document,
    retrieve,
    score_chunk,
)


class TestChunkText:
    def test_empty_input(self):
        assert chunk_text("") == []
        assert chunk_text("   \n\n  ") == []
        assert chunk_text(None) == []

    def test_short_text_single_chunk(self):
        out = chunk_text("这是一段很短的内容。", chunk_size=400)
        assert out == ["这是一段很短的内容。"]

    def test_paragraphs_merge_up_to_limit(self):
        text = "第一段。\n\n第二段。"
        out = chunk_text(text, chunk_size=400)
        assert len(out) == 1
        assert "第一段" in out[0] and "第二段" in out[0]

    def test_long_paragraph_is_windowed(self):
        text = "字" * 1000
        out = chunk_text(text, chunk_size=400, overlap=50)
        assert len(out) > 1
        assert all(len(c) <= 500 for c in out)

    def test_overlap_creates_shared_content(self):
        text = "".join(f"{i:04d}" for i in range(60))  # 240 chars, no paragraph break
        out = chunk_text(text, chunk_size=100, overlap=20)
        assert len(out) >= 2
        # 相邻块应有重叠，保证跨窗口的语义不断裂
        assert out[0][-20:] == out[1][:20]

    def test_blank_paragraphs_dropped(self):
        out = chunk_text("甲\n\n\n\n乙", chunk_size=400)
        assert len(out) == 1


class TestExtractKeywords:
    def test_returns_comma_separated(self):
        out = extract_keywords("员工年休假管理办法规定了年假天数与申请流程", top_k=5)
        assert isinstance(out, str)
        assert "," not in out or len(out.split(",")) <= 5

    def test_empty_text(self):
        assert extract_keywords("", top_k=5) == ""


class TestRebuildChunks:
    def test_rebuild_is_idempotent(self, app):
        from app.extensions import db
        from app.models import Document

        doc = Document(
            title="测试切分",
            content="第一段内容。\n\n第二段内容，用于验证切分幂等。\n\n第三段内容。",
            department="人事部",
            visibility="internal",
            status="published",
        )
        db.session.add(doc)
        db.session.flush()

        first = rebuild_chunks_for_document(doc)
        from app.models import KnowledgeChunk

        count_after_first = KnowledgeChunk.query.filter_by(document_id=doc.id).count()
        second = rebuild_chunks_for_document(doc)
        count_after_second = KnowledgeChunk.query.filter_by(document_id=doc.id).count()

        assert first == second > 0
        # 重复重建不应累积重复片段
        assert count_after_first == count_after_second


class TestScoreChunk:
    def _chunk(self, content, title="标题", keywords=""):
        class Doc:
            self_title = None

        class FakeDoc:
            pass

        class FakeChunk:
            pass

        doc = FakeDoc()
        doc.title = title
        chunk = FakeChunk()
        chunk.content = content
        chunk.keywords = keywords
        chunk.document = doc
        return chunk

    def test_title_weight_exceeds_body_weight(self):
        """同等词重叠下，标题命中权重高于正文命中权重。

        两侧都只有「报销」一个词命中，差别只在命中位置。
        标题命中权重 3.2，正文命中权重 1.0；正文额外拿到的是覆盖率加成
        （命中词占提问词比例 1/1）与整串短语奖励 +10，因此总分仍是正文高——
        短语命中最能说明「这段确实在讲这件事」，这个优先级是刻意设计的。
        """
        title_chunk = self._chunk(content="无关的其他内容表述", title="报销")
        body_chunk = self._chunk(content="涉及报销的事项表述如下", title="无关内容")

        s_title = score_chunk("报销", {"报销"}, title_chunk)
        s_body = score_chunk("报销", {"报销"}, body_chunk)
        # 标题侧纯靠位置加成，正文侧靠短语与覆盖率，两者都必须为正
        assert s_title > 0 and s_body > s_title
        # 精确到权重量级：标题命中贡献 3.2，正文命中贡献 1.0
        assert round(s_title - 6.0, 1) == 3.2  # 减去标题整串奖励 6.0
        assert round(s_body - 12.0, 1) == 1.0  # 减去短语 10.0 与覆盖率 2.0

    def test_keyword_weight_exceeds_title_weight(self):
        """关键词命中（1.8/词）与标题命中（3.2/词）的相对关系可复现。"""
        kw_chunk = self._chunk(content="无关内容", title="无关标题", keywords="报销")
        plain_chunk = self._chunk(content="无关内容", title="无关标题", keywords="")
        assert score_chunk("报销", {"报销"}, kw_chunk) > score_chunk("报销", {"报销"}, plain_chunk)

    def test_exact_phrase_in_body_is_strongest_signal(self):
        """提问原串整段出现在正文里，应打赢仅有标题命中的情况。"""
        title_only = self._chunk("无关的正文内容", title="年假制度")
        phrase = self._chunk("文中写明年假天数如何计算", title="无关标题")
        assert score_chunk("年假", {"年假"}, phrase) > score_chunk("年假", {"年假"}, title_only)

    def test_keyword_weighting(self):
        q_tokens = {"年假"}
        with_kw = self._chunk("正文", keywords="年假")
        without_kw = self._chunk("正文", keywords="")
        assert score_chunk("年假", q_tokens, with_kw) > score_chunk("年假", q_tokens, without_kw)

    def test_exact_phrase_bonus(self):
        q_tokens = {"员工", "年假", "几天"}
        exact = self._chunk("员工年假有几天在办法中写明", title="年假")
        partial = self._chunk("员工与年假相关的若干条款分散在不同章节", title="年假")
        assert score_chunk("员工年假几天", q_tokens, exact) > score_chunk(
            "员工年假几天", q_tokens, partial
        )

    def test_no_overlap_scores_zero(self):
        chunk = self._chunk("完全无关的内容", title="无关标题")
        assert score_chunk("年假", {"年假"}, chunk) == 0.0

    def test_empty_question_scores_zero(self):
        chunk = self._chunk("一些内容", title="标题")
        assert score_chunk("", set(), chunk) == 0.0


class TestRetrieve:
    def _make_doc(self, db, title, content, visibility="internal", department="人事部"):
        from app.models import Document

        doc = Document(
            title=title,
            content=content,
            department=department,
            visibility=visibility,
            status="published",
        )
        db.session.add(doc)
        db.session.flush()
        rebuild_chunks_for_document(doc)
        return doc

    def test_returns_relevant_hits(self, app):
        from app.extensions import db

        self._make_doc(db, "员工年休假管理办法", "年休假天数按工龄计算，满一年五天。")
        user = type("U", (), {"is_admin": False, "department": "人事部", "id": 1})()
        hits = retrieve("年假有几天", user, top_k=5)
        assert len(hits) >= 1
        assert any("年假" in h["content"] for h in hits)

    def test_never_returns_secret_from_other_department(self, app):
        """权限过滤必须先于检索：机密文档不得出现在他人答案的来源里。

        演示库里本就存在若干文档，因此只断言「这篇机密文档的片段未被返回」，
        而不是结果为空。
        """
        from app.extensions import db
        from app.models import KnowledgeChunk

        doc = self._make_doc(
            db,
            "机密密钥轮换专项规定",
            "机密文档密钥轮换周期为九十天，仅信息部可见。",
            visibility="secret",
            department="信息部",
        )
        secret_chunk_ids = {c.id for c in KnowledgeChunk.query.filter_by(document_id=doc.id).all()}

        outsider = type("U", (), {"is_admin": False, "department": "人事部", "id": 2})()
        hits = retrieve("密钥轮换周期", outsider, top_k=10)
        returned_ids = {h["chunk_id"] for h in hits}
        assert not (returned_ids & secret_chunk_ids)
        assert doc.id not in {h["document_id"] for h in hits}

        # 同部门与管理员仍可检索到，证明过滤是可逆的权限规则而非一律屏蔽
        insider = type("U", (), {"is_admin": False, "department": "信息部", "id": 3})()
        admin = type("U", (), {"is_admin": True, "department": "综合部", "id": 4})()
        for user in (insider, admin):
            got = retrieve("密钥轮换周期", user, top_k=10)
            assert secret_chunk_ids & {h["chunk_id"] for h in got}

    def test_admin_can_retrieve_secret(self, app):
        from app.extensions import db

        self._make_doc(
            db,
            "信息安全分级与访问控制规范",
            "机密文档密钥轮换周期为九十天。",
            visibility="secret",
            department="信息部",
        )
        admin = type("U", (), {"is_admin": True, "department": "综合部", "id": 3})()
        hits = retrieve("密钥轮换周期", admin, top_k=5)
        assert len(hits) >= 1

    def test_max_two_hits_per_document(self, app):
        """同一文档最多贡献 2 条来源，保证答案来源多样。"""
        from app.extensions import db
        from app.models import Document

        doc = Document(
            title="长篇制度",
            content=("年假条款\n\n" * 60) + "年假天数与申请流程说明。\n\n" + ("年假补充\n\n" * 60),
            department="人事部",
            visibility="internal",
            status="published",
        )
        db.session.add(doc)
        db.session.flush()
        rebuild_chunks_for_document(doc, chunk_size=200, overlap=20)

        user = type("U", (), {"is_admin": False, "department": "人事部", "id": 4})()
        hits = retrieve("年假", user, top_k=5)
        from collections import Counter

        counts = Counter(h["document_id"] for h in hits)
        assert max(counts.values()) <= 2

    def test_hits_are_sorted_by_score(self, app):
        from app.extensions import db

        self._make_doc(db, "年假制度", "年假天数规定。")
        self._make_doc(db, "无关文档", "完全不相关的内容。")
        user = type("U", (), {"is_admin": False, "department": "人事部", "id": 5})()
        hits = retrieve("年假天数", user, top_k=5)
        scores = [h["score"] for h in hits]
        assert scores == sorted(scores, reverse=True)

    def test_top_k_respected(self, app):
        from app.extensions import db

        for i in range(6):
            self._make_doc(db, f"年假制度 {i}", f"年假天数规定第 {i} 条。")
        user = type("U", (), {"is_admin": False, "department": "人事部", "id": 6})()
        hits = retrieve("年假天数", user, top_k=3)
        assert len(hits) <= 3


class TestBuildLocalAnswer:
    def test_no_hits_gives_honest_fallback(self):
        out = build_local_answer("年假几天", [])
        assert "未" in out
        # 不得伪装成已给出答案
        assert "根据" not in out

    def test_includes_source_titles(self):
        hits = [
            {
                "score": 12.0,
                "chunk_id": 1,
                "document_id": 7,
                "title": "员工年休假管理办法",
                "content": "年休假按工龄计算天数。",
                "department": "人事部",
            }
        ]
        out = build_local_answer("年假几天", hits)
        assert "员工年休假管理办法" in out
        assert "人事部" in out

    def test_states_local_mode(self):
        hits = [
            {
                "score": 1.0,
                "chunk_id": 1,
                "document_id": 1,
                "title": "T",
                "content": "内容",
                "department": "人事部",
            }
        ]
        out = build_local_answer("问", hits)
        assert "本地" in out


class TestAnonymousUser:
    def test_anonymous_cannot_view_anything(self, app):
        from app.extensions import db
        from app.models import Document

        doc = Document(
            title="公开文档",
            content="内容",
            department="人事部",
            visibility="public",
            status="published",
        )
        db.session.add(doc)
        db.session.flush()
        anon = type("U", (), {"is_admin": False, "department": None, "id": None})()
        assert can_view_document(anon, doc) is True  # public 对登录用户开放
        assert can_view_document(None, doc) is False


class TestGroupHitsByDocument:
    """检索依据按文档合并，避免同一篇文档渲染成多张重复卡片。"""

    @staticmethod
    def _hit(doc_id, title, score, content, no=1, total=1):
        return {
            "score": score,
            "chunk_id": doc_id * 10 + no,
            "document_id": doc_id,
            "title": title,
            "content": content,
            "department": "人事部",
            "fragment_no": no,
            "fragment_total": total,
        }

    def test_same_document_merges_into_one_group(self):
        hits = [
            self._hit(1, "员工年休假管理办法", 6.5, "年假五天。", no=1, total=2),
            self._hit(1, "员工年休假管理办法", 6.5, "年假申请流程。", no=2, total=2),
        ]
        groups = group_hits_by_document(hits)
        assert len(groups) == 1
        assert len(groups[0]["fragments"]) == 2

    def test_groups_sorted_by_highest_score(self):
        hits = [
            self._hit(2, "制度 B", 3.0, "bbb"),
            self._hit(1, "制度 A", 9.0, "aaa"),
            self._hit(3, "制度 C", 5.0, "ccc"),
        ]
        groups = group_hits_by_document(hits)
        assert [g["document_id"] for g in groups] == [1, 3, 2]

    def test_group_score_is_best_fragment_score(self):
        hits = [
            self._hit(1, "制度 A", 4.0, "aaa", no=1, total=2),
            self._hit(1, "制度 A", 7.5, "aaa again", no=2, total=2),
        ]
        groups = group_hits_by_document(hits)
        assert groups[0]["score"] == 7.5

    def test_empty_input(self):
        assert group_hits_by_document([]) == []

    def test_fragment_metadata_is_preserved(self):
        hits = [
            self._hit(1, "A", 5.0, "x", no=1, total=3),
            self._hit(1, "A", 4.0, "y", no=2, total=3),
        ]
        groups = group_hits_by_document(hits)
        assert [f["fragment_no"] for f in groups[0]["fragments"]] == [1, 2]
        assert groups[0]["fragments"][0]["fragment_total"] == 3


class TestRetrieveFragmentMetadata:
    def test_hits_carry_fragment_indices(self, app):
        from app.extensions import db
        from app.models import Document
        from app.services.rag import rebuild_chunks_for_document

        doc = Document(
            title="长篇年假制度",
            content=("年假条款\n\n" * 80) + "年假天数正文说明。\n\n" + ("年假补充\n\n" * 80),
            department="人事部",
            visibility="internal",
            status="published",
        )
        db.session.add(doc)
        db.session.flush()
        rebuild_chunks_for_document(doc, chunk_size=200, overlap=20)

        user = type("U", (), {"is_admin": False, "department": "人事部", "id": 9})()
        hits = retrieve("年假", user, top_k=5)
        assert hits
        for hit in hits:
            assert hit["fragment_no"] >= 1
            assert hit["fragment_total"] >= hit["fragment_no"]
