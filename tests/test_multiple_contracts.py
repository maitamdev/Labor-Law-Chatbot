# -*- coding: utf-8 -*-
"""
Tests for Multiple Labor Contracts citation locking (Điều 19 Bộ luật Lao động 2019).
Guarantees zero hallucination of foreign worker articles (Điều 154) when consulting
on domestic multiple employment contract situations.
"""
from __future__ import annotations

import pytest

from rag.legal_issue_parser import LegalIssueParser
from rag.query_router import QueryRouter
from rag.evidence_selector import EvidenceSelector


def test_multiple_contracts_event_and_role_detection():
    router = QueryRouter()
    parser = LegalIssueParser(router=router)
    q = (
        "Anh T là kế toán cho doanh nghiệp B. Để tăng thu nhập, anh nhận thêm việc "
        "quyết toán thuế cho một số cơ sở kinh doanh nhỏ lẻ vào cuối tháng và có ký kết "
        "hợp đồng lao động với các cơ sở kinh doanh này. Việc làm này của anh T có hợp pháp không?"
    )
    issue = parser.parse(q)
    assert "MULTIPLE_CONTRACTS" in issue.legal_events
    assert "MULTIPLE_CONTRACTS_PERMISSION" in getattr(issue, "required_evidence_roles", [])


def test_multiple_contracts_evidence_selection_locks_d19():
    router = QueryRouter()
    parser = LegalIssueParser(router=router)
    selector = EvidenceSelector()

    q = (
        "Anh T là kế toán cho doanh nghiệp B. Để tăng thu nhập, anh nhận thêm việc "
        "quyết toán thuế cho một số cơ sở kinh doanh nhỏ lẻ vào cuối tháng và có ký kết "
        "hợp đồng lao động với các cơ sở kinh doanh này. Việc làm này của anh T có hợp pháp không?"
    )
    issue = parser.parse(q)

    mock_candidates = [
        {
            "chunk_id": "VBHN_18_2026#d154-k5",
            "doc_id": "VBHN_18_2026",
            "article_number": 154,
            "clause_number": 5,
            "article_title": "Người lao động nước ngoài làm việc tại Việt Nam không thuộc diện cấp giấy phép lao động",
            "content": "Người lao động nước ngoài làm việc tại Việt Nam không thuộc diện cấp giấy phép lao động...",
            "score": 0.9,
        },
        {
            "chunk_id": "VBHN_18_2026#d19-k1",
            "doc_id": "VBHN_18_2026",
            "article_number": 19,
            "clause_number": 1,
            "article_title": "Giao kết nhiều hợp đồng lao động",
            "content": "1. Người lao động có thể giao kết nhiều hợp đồng lao động với nhiều người sử dụng lao động nhưng phải bảo đảm thực hiện đầy đủ các nội dung đã giao kết.",
            "score": 0.85,
        },
        {
            "chunk_id": "VBHN_18_2026#d19-k2",
            "doc_id": "VBHN_18_2026",
            "article_number": 19,
            "clause_number": 2,
            "article_title": "Giao kết nhiều hợp đồng lao động",
            "content": "2. Người lao động đồng thời giao kết nhiều hợp đồng lao động với nhiều người sử dụng lao động thì việc tham gia bảo hiểm xã hội, bảo hiểm y tế, bảo hiểm thất nghiệp được thực hiện theo quy định của pháp luật...",
            "score": 0.82,
        },
    ]

    res = selector.select_evidence(issue, mock_candidates)

    # Must select Điều 19
    assert "VBHN_18_2026#d19-k1" in res.selected_chunk_ids
    # Must NEVER select Điều 154
    assert "VBHN_18_2026#d154-k5" not in res.selected_chunk_ids
