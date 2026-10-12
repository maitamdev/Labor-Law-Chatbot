# -*- coding: utf-8 -*-
"""
Tests for Thai Nguyen PBGDPL 12 Legal Situations Integration.
Verifies training dataset completeness, ChatML format compliance,
and QuestionLawAnchorIndex statutory nominations.
"""
from __future__ import annotations

import json
from pathlib import Path
from config.settings import PROJECT_ROOT
from rag.qa_anchor import QuestionLawAnchorIndex


def test_thainguyen_situations_dataset_exists_and_valid():
    dataset_file = PROJECT_ROOT / "data/training/vietlabor_thainguyen_situations_chatml.jsonl"
    assert dataset_file.exists(), f"File {dataset_file} must exist."

    records = [json.loads(line) for line in dataset_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(records) == 12, f"Expected 12 situations, got {len(records)}"

    for rec in records:
        assert "messages" in rec
        msgs = rec["messages"]
        assert len(msgs) == 3
        assert msgs[0]["role"] == "system"
        assert msgs[1]["role"] == "user"
        assert msgs[2]["role"] == "assistant"
        # Ensure answers contain specific legal citations
        ans = msgs[2]["content"]
        assert any(k in ans for k in ["Điều", "Bộ luật Lao động", "Luật", "Nghị định"])
        assert "### 1. Kết luận" in ans
        assert "### 3. Khuyến nghị" in ans


def test_main_sft_dataset_contains_situations():
    main_file = PROJECT_ROOT / "data/training/vietlabor_sft_1000_chatml.jsonl"
    assert main_file.exists()
    lines = [json.loads(line) for line in main_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) >= 1012, f"Expected at least 1012 training records, got {len(lines)}"

    # Check that situation 1 (Lò Văn Dũng) is present
    has_dung = any("Lò Văn Dũng" in l["messages"][1]["content"] for l in lines)
    assert has_dung, "Tình huống Anh Lò Văn Dũng must be in the main training dataset."


def test_qa_anchor_index_nominates_thai_nguyen_questions():
    anchor_idx = QuestionLawAnchorIndex()

    # Test question 1: Tu choi lam viec nguy hiem sat lo
    q1 = "Việc anh Dũng từ chối làm việc khi nhận thấy có nguy cơ đe dọa trực tiếp đến tính mạng và sức khỏe của bản thân có phù hợp theo quy định pháp luật lao động?"
    match1 = anchor_idx.matching_question(q1)
    assert match1 is not None
    assert any(a["doc_id"] == "VBHN_18_2026" and a["article_number"] == "5" for a in match1["law_anchors"])

    # Test question 9: Di lam som thai san
    q9 = "Theo quy định của Bộ Luật lao động đi làm sớm hơn, chị Lan có được hưởng trợ cấp thai sản trong 01 tháng chênh lệch không?"
    match9 = anchor_idx.matching_question(q9)
    assert match9 is not None
    assert any(a["doc_id"] == "VBHN_18_2026" and a["article_number"] == "139" for a in match9["law_anchors"])
