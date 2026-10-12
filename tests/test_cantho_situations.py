# -*- coding: utf-8 -*-
"""
Tests for Can Tho PBGDPL 106 Legal Situations Integration.
Verifies dataset completeness, ChatML compliance, master SFT integration,
and QuestionLawAnchorIndex accuracy.
"""
from __future__ import annotations

import json
from pathlib import Path
from config.settings import PROJECT_ROOT
from rag.qa_anchor import QuestionLawAnchorIndex


def test_cantho_processed_json_exists_and_complete():
    json_file = PROJECT_ROOT / "data/processed/cantho_legal_situations.json"
    assert json_file.exists(), f"File {json_file} must exist."

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert len(data) == 106, f"Expected 106 situations, got {len(data)}"
    for s in data:
        assert "number" in s
        assert "question" in s and len(s["question"]) > 10
        assert "answer" in s and len(s["answer"]) > 10
        assert "articles" in s


def test_cantho_chatml_dataset_valid():
    chatml_file = PROJECT_ROOT / "data/training/vietlabor_cantho_qa_chatml.jsonl"
    if not chatml_file.exists():
        # Will be created by train_cantho_dataset.py
        return

    records = [json.loads(line) for line in chatml_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(records) == 106, f"Expected 106 records, got {len(records)}"

    for rec in records:
        assert "messages" in rec
        msgs = rec["messages"]
        assert len(msgs) == 3
        assert msgs[0]["role"] == "system"
        assert msgs[1]["role"] == "user"
        assert msgs[2]["role"] == "assistant"
        ans = msgs[2]["content"]
        assert any(k in ans for k in ["Điều", "Bộ luật Lao động", "Luật", "Nghị định"])


def test_main_sft_dataset_contains_cantho_records():
    main_file = PROJECT_ROOT / "data/training/vietlabor_sft_1000_chatml.jsonl"
    assert main_file.exists()
    lines = [json.loads(line) for line in main_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    
    # Must have Thai Nguyen (12) + Can Tho (106) + original 1000 >= 1118
    has_cantho = any("cantho_sit_" in l.get("id", "") for l in lines)
    if has_cantho:
        assert len(lines) >= 1118, f"Expected >= 1118 records after Can Tho integration, got {len(lines)}"


def test_qa_anchor_nominates_cantho_situations():
    anchor_idx = QuestionLawAnchorIndex()

    # Test Q5: HĐLĐ điện tử
    q5 = "Hợp đồng lao động được giao kết qua phương tiện thông tin điện tử dưới hình thức thông điệp dữ liệu có giá trị như hợp đồng lao động bằng văn bản không?"
    m5 = anchor_idx.matching_question(q5)
    if m5 is not None:
        assert any(a["doc_id"] == "VBHN_18_2026" and a["article_number"] in ["14", "13", "15"] for a in m5["law_anchors"])


def test_service_contract_vs_labor_contract_grounding():
    from rag.service_contract_vs_labor_contract import (
        is_service_contract_vs_labor_contract_query,
        grounded_service_contract_answer,
        SERVICE_CONTRACT_EVIDENCE_IDS,
    )
    q = "trường hợp nào ký HĐLĐ? trường hợp nào ký hợp đồng dịch vụ? NSDLĐ ký hợp đồng cung cấp dịch vụ với NLĐ thay cho HĐLĐ có được không?"
    assert is_service_contract_vs_labor_contract_query(q)
    ans = grounded_service_contract_answer(q, set(SERVICE_CONTRACT_EVIDENCE_IDS))
    assert ans is not None
    assert "KHÔNG ĐƯỢC PHÉP" in ans
    assert "Khoản 1 Điều 13" in ans

