# -*- coding: utf-8 -*-
import json
from pathlib import Path

from rag.statutory_constraints import CHECKS, StatutoryConstraintEngine


def test_all_constraint_inject_ids_exist_in_corpus():
    corpus_path = Path("data/processed/legal_documents_v3.jsonl")
    assert corpus_path.exists()
    with corpus_path.open("r", encoding="utf-8") as f:
        corpus_ids = {json.loads(line)["chunk_id"] for line in f if line.strip()}

    missing = []
    for check in CHECKS:
        for cid in check.inject_ids:
            if cid not in corpus_ids:
                missing.append((check.check_id, cid))
    assert not missing, f"Missing constraint inject_ids in corpus: {missing}"


def test_discipline_statute_of_limitations_fires():
    engine = StatutoryConstraintEngine()
    plan = engine.plan("Em vi phạm nội quy từ 8 tháng trước, nay công ty mới họp xử lý kỷ luật sa thải thì có còn thời hiệu không?")
    fired_ids = {f.check.check_id for f in plan.fired}
    assert "DISCIPLINE_STATUTE_OF_LIMITATIONS" in fired_ids
    injected_chunks = [cid for cid, _ in plan.priority_chunk_ids]
    assert "VBHN_18_2026#d123-k1" in injected_chunks


def test_prohibited_id_deposit_retention_fires_and_audits():
    engine = StatutoryConstraintEngine()
    plan = engine.plan("Khi nhận việc công ty yêu cầu giữ bản chính bằng đại học và đặt cọc 5 triệu đồng thì có đúng luật không?")
    fired_ids = {f.check.check_id for f in plan.fired}
    assert "PROHIBITED_ID_DEPOSIT_RETENTION" in fired_ids
    chunk_map = {"VBHN_18_2026#d17-k1": "E1", "VBHN_18_2026#d17-k2": "E2"}
    bad_answer = "Công ty được phép giữ bản chính bằng đại học nếu hai bên có thỏa thuận."
    violations = engine.audit(plan, bad_answer, chunk_map)
    assert any(v.check.check_id == "PROHIBITED_ID_DEPOSIT_RETENTION" for v in violations)
    assert len(engine.contradicted(violations, bad_answer)) == 1

    good_answer = "Theo Điều 17 Bộ luật Lao động 2019 [E1, E2], người sử dụng lao động không được giữ bản chính văn bằng và không được yêu cầu đặt cọc."
    assert engine.audit(plan, good_answer, chunk_map) == []


def test_workplace_accident_liability_fires():
    engine = StatutoryConstraintEngine()
    plan = engine.plan("Người lao động bị tai nạn lao động mà công ty không đóng bảo hiểm thì trách nhiệm bồi thường và chi phí y tế thế nào?")
    fired_ids = {f.check.check_id for f in plan.fired}
    assert "WORKPLACE_ACCIDENT_LIABILITY" in fired_ids
    injected_chunks = [cid for cid, _ in plan.priority_chunk_ids]
    assert "L_84_2015#d38-k1" in injected_chunks
    assert "L_84_2015#d39-k4" in injected_chunks


def test_multi_issue_diploma_deposit_and_discipline_limitation_end_to_end():
    from rag.case_analyzer import CaseAnalyzer
    from rag.context_builder import ContextBuilder
    from rag.evidence_selector import EvidenceSelector
    from rag.issue_decomposer import IssueDecomposer
    from rag.legal_issue_parser import LegalIssueParser
    from rag.output_validator import LegalAnswer, LegalFinding, OutputValidator

    query = (
        "Khi vào làm công ty giữ bằng đại học bản gốc của em và yêu cầu đặt cọc 5 triệu. "
        "Nay phát hiện lỗi vi phạm nội quy từ 8 tháng trước thì công ty có còn thời hiệu kỷ luật sa thải em không"
    )
    decomposed = IssueDecomposer().decompose(query)
    assert len(decomposed) == 2

    parser = LegalIssueParser()
    parsed_1 = parser.parse(decomposed[0].raw_issue_text, issue_id="issue_1")
    parsed_2 = parser.parse(decomposed[1].raw_issue_text, issue_id="issue_2")
    assert "PROHIBITED_ORIGINAL_DOCUMENT_RETENTION" in parsed_1.required_evidence_roles
    assert "PROHIBITED_SECURITY_DEPOSIT" in parsed_1.required_evidence_roles
    assert "DISCIPLINE_LIMITATION_PERIOD" in parsed_2.required_evidence_roles
    assert "contract_under_12_months" not in parsed_2.qualifiers

    cb = ContextBuilder(max_context_chars=5500, max_chunks=8)
    c1 = [
        cb._get_chunk_by_id(cid)
        for cid in [
            "VBHN_18_2026#d17-k1",
            "VBHN_18_2026#d17-k2",
            "ND_283_2026#d15-k2",
            "ND_283_2026#d15-k2-a",
            "ND_283_2026#d15-k2-b",
            "ND_283_2026#d15-k3-d",
            "ND_283_2026#d15-k3-đ",
        ]
    ]
    c2 = [
        cb._get_chunk_by_id(cid)
        for cid in [
            "VBHN_18_2026#d123-k1",
            "VBHN_18_2026#d123-k2",
            "VBHN_18_2026#d123-k3",
            "VBHN_18_2026#d122-k1-a",
            "VBHN_18_2026#d122-k4",
            "VBHN_18_2026#d125-k1",
            "VBHN_18_2026#d125-k2",
        ]
    ]
    selector = EvidenceSelector()
    s1 = selector.select_evidence(parsed_1, c1)
    s2 = selector.select_evidence(parsed_2, c2)
    assert "VBHN_18_2026#d17-k1" in s1.selected_chunk_ids
    assert "VBHN_18_2026#d17-k2" in s1.selected_chunk_ids
    assert "VBHN_18_2026#d123-k1" in s2.selected_chunk_ids

    engine = StatutoryConstraintEngine()
    plan = engine.plan(query, issues=decomposed, selected_chunks=c1 + c2)
    ctx = cb.build_context(
        retrieved_chunks=c1 + c2,
        multi_issue_candidates={
            "issue_1": [x.raw_chunk for x in s1.locked_evidence_blocks],
            "issue_2": [x.raw_chunk for x in s2.locked_evidence_blocks],
        },
        expand_siblings=False,
        query=query,
        priority_chunk_ids=plan.priority_chunk_ids,
    )
    imap = {
        "issue_1": [b.chunk_id for b in ctx.evidence_blocks if b.issue_id == "issue_1"],
        "issue_2": [b.chunk_id for b in ctx.evidence_blocks if b.issue_id == "issue_2"],
    }
    ca = CaseAnalyzer().analyze(query, decomposed)
    validated = OutputValidator().validate_and_format(
        legal_answer=LegalAnswer(
            answer="Bản nháp",
            findings=[
                LegalFinding(
                    issue_id="issue_1",
                    issue=decomposed[0].raw_issue_text,
                    finding="Bản nháp 1",
                    evidence_ids=["E1"],
                )
            ],
        ),
        available_chunk_ids=ctx.available_chunk_ids,
        chunk_registry=ctx.chunk_metadata_registry,
        evidence_mapper=ctx.evidence_mapper,
        locked_chunk_ids=list(ctx.available_chunk_ids),
        issue_evidence_map=imap,
        expected_issues=decomposed,
        unsupported_issue_ids=[],
        case_analysis=ca,
    )
    assert validated.is_fully_grounded
    assert validated.phantom_citations == []
    assert "Khoản 1 Điều 17" in validated.final_answer
    assert "Khoản 2 Điều 17" in validated.final_answer
    assert "Khoản 1 Điều 123" in validated.final_answer
    assert "8 tháng trước" in validated.final_answer
    assert "Lưu ý đối chiếu bắt buộc" not in validated.final_answer

    chunk_to_ev = {b.chunk_id: b.evidence_id for b in ctx.evidence_blocks}
    assert engine.audit(plan, validated.final_answer, chunk_to_ev) == []
