# -*- coding: utf-8 -*-
"""
VietLabor AI - Test Suite for ViLeXa Enhancements
Tests:
1. CrossEncoderReranker: Initialization, empty handling, score assignment, fallback.
2. RelevanceGrader: Threshold grading, primary doc validation.
3. AdaptiveQueryRewriter: Colloquial labor slang normalization to statutory articles.
4. VBPLCrawler: Session creation and URL builders.
"""
from __future__ import annotations

import pytest

from law_crawler.config import BASE_URL, TOANVAN_URL_TEMPLATE
from law_crawler.vbpl_crawler import build_resilient_session
from rag.query_rewriter import AdaptiveQueryRewriter, RelevanceGrader, COLLOQUIAL_LEGAL_MAP
from rag.reranker import CrossEncoderReranker


# ---------------------------------------------------------------------------
# 1. CrossEncoderReranker Unit Tests
# ---------------------------------------------------------------------------
class TestCrossEncoderReranker:
    def test_empty_candidates_returns_empty(self):
        reranker = CrossEncoderReranker(enabled=False)
        res = reranker.rerank("thử việc", [])
        assert res == []

    def test_empty_query_returns_candidates(self):
        reranker = CrossEncoderReranker(enabled=False)
        dummy_cands = [{"chunk_id": "c1", "score": 0.5}]
        res = reranker.rerank("", dummy_cands)
        assert res == dummy_cands

    def test_disabled_fallback_preserves_order(self):
        reranker = CrossEncoderReranker(enabled=False)
        cands = [
            {"chunk_id": "c1", "score": 0.9, "content": "Điều 25"},
            {"chunk_id": "c2", "score": 0.4, "content": "Điều 36"},
        ]
        res = reranker.rerank("thời gian thử việc", cands, top_k=1)
        assert len(res) == 1
        assert res[0]["chunk_id"] == "c1"


# ---------------------------------------------------------------------------
# 2. RelevanceGrader Unit Tests
# ---------------------------------------------------------------------------
class TestRelevanceGrader:
    def test_empty_candidates_fails_grade(self):
        grader = RelevanceGrader()
        res = grader.grade("công ty đuổi việc", [])
        assert res.is_relevant is False
        assert res.confidence_score == 0.0

    def test_low_score_fails_grade(self):
        grader = RelevanceGrader(min_top_score_threshold=0.5)
        cands = [
            {"chunk_id": "c1", "score": 0.001, "content": "nội quy văn phòng khác", "metadata": {}}
        ]
        res = grader.grade("thử việc 3 tháng", cands)
        assert res.is_relevant is False

    def test_primary_doc_missing_fails_grade(self):
        grader = RelevanceGrader()
        cands = [
            {"chunk_id": "c1", "score": 0.01, "content": "quy định hành chính", "metadata": {"doc_id": "DOC_OTHER"}}
        ]
        res = grader.grade("nghỉ việc báo trước", cands, primary_docs={"VBHN_18_2026"})
        assert res.is_relevant is False

    def test_high_confidence_chunk_passes_grade(self):
        grader = RelevanceGrader()
        cands = [
            {
                "chunk_id": "c1",
                "score": 0.8,
                "content": "Điều 25. Thời gian thử việc do hai bên thỏa thuận căn cứ vào tính chất",
                "metadata": {"doc_id": "VBHN_18_2026", "article_number": "25", "article_title": "Thời gian thử việc"},
            }
        ]
        res = grader.grade("thời gian thử việc", cands, primary_docs={"VBHN_18_2026"})
        assert res.is_relevant is True


# ---------------------------------------------------------------------------
# 3. AdaptiveQueryRewriter Unit Tests
# ---------------------------------------------------------------------------
class TestAdaptiveQueryRewriter:
    def test_rewrites_colloquial_duoi_viec(self):
        rewriter = AdaptiveQueryRewriter(llm_manager=None)
        q = "Tôi bị công ty đuổi việc bất ngờ thì phải làm sao?"
        rewritten = rewriter.rewrite_deterministic(q)
        assert "đơn phương chấm dứt hợp đồng lao động" in rewritten

    def test_rewrites_colloquial_giu_bang(self):
        rewriter = AdaptiveQueryRewriter(llm_manager=None)
        q = "Công ty bắt nộp giữ bằng gốc khi vào làm có đúng luật không?"
        rewritten = rewriter.rewrite_deterministic(q)
        assert "Điều 17" in rewritten

    def test_rewrites_colloquial_quit_luong(self):
        rewriter = AdaptiveQueryRewriter(llm_manager=None)
        q = "Sếp quỵt lương 2 tháng nay"
        rewritten = rewriter.rewrite_deterministic(q)
        assert "chậm trả tiền lương" in rewritten

    def test_standard_query_unchanged_or_preserved(self):
        rewriter = AdaptiveQueryRewriter(llm_manager=None)
        q = "Thời hạn báo trước theo Điều 35 Bộ luật Lao động"
        rewritten = rewriter.rewrite_deterministic(q)
        assert "Điều 35" in rewritten


# ---------------------------------------------------------------------------
# 4. VBPLCrawler Unit Tests
# ---------------------------------------------------------------------------
class TestVBPLCrawler:
    def test_session_has_retry_adapter(self):
        session = build_resilient_session(max_workers=2)
        assert "https://" in session.adapters
        assert session.headers.get("User-Agent") is not None

    def test_url_template_formatting(self):
        url = TOANVAN_URL_TEMPLATE.format(item_id="140456")
        assert "ItemID=140456" in url
        assert url.startswith(BASE_URL)

    def test_labor_domain_validation_accepts_labor_doc(self):
        from law_crawler.vbpl_crawler import VBPLCrawler
        is_valid, reason = VBPLCrawler.validate_labor_scope(
            title="Bộ luật Lao động số 45/2019/QH14",
            content="Quy định tiêu chuẩn lao động; quyền, nghĩa vụ, trách nhiệm của người lao động, người sử dụng lao động"
        )
        assert is_valid is True

    def test_labor_domain_validation_rejects_non_labor_doc(self):
        from law_crawler.vbpl_crawler import VBPLCrawler
        # Land law
        is_valid, reason = VBPLCrawler.validate_labor_scope(
            title="Luật Đất đai số 31/2024/QH15",
            content="Quy định về chế độ sở hữu đất đai, quyền hạn và trách nhiệm của Nhà nước"
        )
        assert is_valid is False
        assert "đất đai" in reason

        # Criminal code
        is_valid, reason = VBPLCrawler.validate_labor_scope(
            title="Bộ luật Hình sự số 100/2015/QH13",
            content="Tội phạm và hình phạt đối với người phạm tội"
        )
        assert is_valid is False
        assert "hình sự" in reason
