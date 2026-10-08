"""Question bank may guide retrieval, but never supply answer prose."""
import json

from rag.qa_anchor import QuestionLawAnchorIndex
from rag.bm25_retriever import BM25Retriever
from rag.query_router import QueryRouter
from scripts.qa_source_normalizations import normalize_source


def test_missing_formal_source_numbers_are_normalized_to_current_official_citations():
    bhxh = normalize_source(422, "Điểm đ khoản 1 Điều 31 — Luật BHXH 2024")
    assert "41/2024/QH15" in bhxh
    assert "19/VBHN-VPQH" in bhxh
    assert "congbao.chinhphu.vn" in bhxh

    bll = normalize_source(
        652,
        "Khoản 1 Điều 75 Bộ luật Lao động 2019\n"
        "https://vanban.chinhphu.vn/?classid=2629&docid=217002&pageid=27160",
    )
    assert "45/2019/QH14" in bll
    assert "18/VBHN-VPQH" in bll
    assert "congbao.chinhphu.vn" in bll


def test_verified_question_points_to_real_statutory_chunks():
    index = QuestionLawAnchorIndex()
    rows = [json.loads(line) for line in index.anchor_path.read_text(encoding="utf-8").splitlines()]
    question = next(row["question"] for row in rows if row["sheet_row"] == 1006)

    matches = index.nominate(question)

    assert index.matching_question(question)["sheet_row"] == 1006
    assert {(item["metadata"]["doc_id"], item["metadata"]["article_number"]) for item in matches} == {
        ("LVL_74_2025", "39"),
        ("ND_374_2025", "15"),
    }
    assert all("answer" not in item and "source" not in item for item in matches)


def test_authorized_capital_rep_suspension_anchor_includes_return_to_work_rule():
    index = QuestionLawAnchorIndex()
    rows = [json.loads(line) for line in index.anchor_path.read_text(encoding="utf-8").splitlines()]
    row = next(item for item in rows if item["sheet_row"] == 95)

    matches = index.nominate(row["question"])
    assert {
        "VBHN_18_2026#d30-k1-g",
        "VBHN_18_2026#d31",
    } <= {item["chunk_id"] for item in matches}
    assert all("answer" not in item and "source" not in item for item in matches)


def test_termination_allowance_and_representation_anchors_cover_reviewed_clauses():
    index = QuestionLawAnchorIndex()
    rows = [json.loads(line) for line in index.anchor_path.read_text(encoding="utf-8").splitlines()]
    expected = {
        158: {"ND_145_2020#d8-k3", "ND_145_2020#d8-k3-a"},
        162: {"VBHN_18_2026#d48-k1"},
        168: {"VBHN_18_2026#d178-k7", "VBHN_18_2026#d67-k5"},
    }

    for sheet_row, expected_chunks in expected.items():
        question = next(row["question"] for row in rows if row["sheet_row"] == sheet_row)
        matches = index.nominate(question)
        assert expected_chunks <= {item["chunk_id"] for item in matches}
        assert all("answer" not in item and "source" not in item for item in matches)


def test_household_owner_social_insurance_anchors_include_2026_threshold_and_overlap_rule():
    index = QuestionLawAnchorIndex()
    rows = [json.loads(line) for line in index.anchor_path.read_text(encoding="utf-8").splitlines()]
    expected = {
        414: {
            "ND_158_2025#d3-k2-a",
            "ND_158_2025#d3-k2-b",
            "ND_141_2026#d1-k1",
            "ND_141_2026#d3",
        },
        415: {
            "ND_158_2025#d3-k2-b",
            "ND_141_2026#d1-k1",
            "ND_141_2026#d3",
        },
        417: {
            "VBHN_58_2025#d2-k5-e",
            "ND_158_2025#d3-k2-a",
            "ND_158_2025#d3-k2-b",
            "ND_158_2025#d3-k3-a",
            "ND_141_2026#d1-k1",
            "ND_141_2026#d3",
        },
    }

    for sheet_row, expected_chunks in expected.items():
        question = next(row["question"] for row in rows if row["sheet_row"] == sheet_row)
        matches = index.nominate(question)
        assert index.matching_question(question)["sheet_row"] == sheet_row
        assert expected_chunks <= {item["chunk_id"] for item in matches}
        assert all("answer" not in item and "source" not in item for item in matches)


def test_current_bhxh_consolidation_and_second_child_maternity_anchors():
    index = QuestionLawAnchorIndex()
    corpus = [json.loads(line) for line in index.corpus_path.read_text(encoding="utf-8").splitlines()]
    by_id = {item["chunk_id"]: item for item in corpus}

    assert by_id["VBHN_58_2025#d1"]["document_no"] == "19/VBHN-VPQH"
    assert "thủ tục phục hồi" in by_id["VBHN_58_2025#d37-k1"]["content"]
    assert "vợ sinh con thứ hai" in by_id["VBHN_58_2025#d53-k2-b"]["content"]
    assert "không giảm tỷ lệ phần trăm hưởng lương hưu" in by_id["VBHN_58_2025#d66-k3"]["content"]
    assert "không được hưởng chế độ nghỉ thai sản khi sinh con thứ hai" in by_id["ND_168_2026#d2-k2"]["content"]

    anchors = [json.loads(line) for line in index.anchor_path.read_text(encoding="utf-8").splitlines()]
    expected = {
        454: {"VBHN_58_2025#d52-k2", "LUAT_113_2025#d29-k2", "ND_168_2026#d2-k2"},
        455: {
            "VBHN_58_2025#d53-k2-a",
            "VBHN_58_2025#d53-k2-b",
            "VBHN_58_2025#d53-k2-d",
            "VBHN_58_2025#d53-k3",
            "LUAT_113_2025#d29-k2",
            "ND_168_2026#d2-k1-b",
        },
        457: {
            "VBHN_58_2025#d53-k5",
            "VBHN_58_2025#d53-k7",
            "LUAT_113_2025#d29-k1",
            "ND_168_2026#d2-k1-a",
        },
        480: {"VBHN_58_2025#d66-k3"},
        500: {
            "VBHN_58_2025#d2-k2",
            "VBHN_58_2025#d70-k2",
            "VBHN_58_2025#d70-k2-d",
        },
        506: {
            "VBHN_58_2025#d86-k2-a",
            "VBHN_58_2025#d86-k2-b",
            "VBHN_58_2025#d86-k2-c",
            "VBHN_58_2025#d86-k2-d",
            "VBHN_58_2025#d86-k2-đ",
        },
        509: {"VBHN_58_2025#d87-k3"},
        531: {"ND_135_2020#d6-k1", "ND_135_2020#d6-k2"},
        522: {"ND_159_2025#d5-k1", "ND_159_2025#d5-k2"},
        532: {"ND_135_2020#d3-k1", "ND_135_2020#d3-k2"},
        538: {"LVL_74_2025#d31-k1-d", "VBHN_58_2025#d2-k5-a"},
    }
    for sheet_row, expected_chunks in expected.items():
        anchor = next(row for row in anchors if row["sheet_row"] == sheet_row)
        matches = index.nominate(anchor["question"], limit=12)
        nominated = {item["chunk_id"] for item in matches}
        assert expected_chunks <= nominated
        assert all("answer" not in item and "source" not in item for item in matches)

    corrected = [
        json.loads(line)
        for line in (index.anchor_path.parent.parent / "evaluation/labor_qa_corrected.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    answer_480 = next(row["answer"] for row in corrected if row["sheet_row"] == 480)
    assert "khoản 3a Điều 66" in answer_480
    answer_500 = next(row["answer"] for row in corrected if row["sheet_row"] == 500)
    assert "đã chấm dứt tham gia BHXH" in answer_500
    assert "Nếu vẫn đang làm việc và tham gia BHXH" in answer_500
    answer_506 = next(row["answer"] for row in corrected if row["sheet_row"] == 506)
    assert "người mang thai hộ đang mang thai" in answer_506
    answer_509 = next(row["answer"] for row in corrected if row["sheet_row"] == 509)
    assert "người mẹ nhờ mang thai hộ chết" in answer_509
    answer_531 = next(row["answer"] for row in corrected if row["sheet_row"] == 531)
    assert "không quá 05 năm" in answer_531


def test_accident_compensation_anchor_includes_fault_qualification_and_allowance_rule():
    index = QuestionLawAnchorIndex()
    rows = [json.loads(line) for line in index.anchor_path.read_text(encoding="utf-8").splitlines()]
    expected = {"L_84_2015#d38-k4-b", "L_84_2015#d38-k5"}

    for sheet_row in (852, 862):
        anchor = next(row for row in rows if row["sheet_row"] == sheet_row)
        matches = index.nominate(anchor["question"])
        assert index.matching_question(anchor["question"])["sheet_row"] == sheet_row
        assert expected <= {item["chunk_id"] for item in matches}


def test_current_penalty_transition_and_workplace_dialogue_anchors_cover_exceptions():
    index = QuestionLawAnchorIndex()
    rows = [json.loads(line) for line in index.anchor_path.read_text(encoding="utf-8").splitlines()]
    expected = {
        203: {
            "ND_283_2026#d66-k1",
            "ND_283_2026#d66-k4",
            "ND_283_2026#d67-k1",
            "ND_283_2026#d67-k2",
            "ND_283_2026#d67-k3",
        },
        204: {
            "ND_145_2020#d39-k4",
            "ND_145_2020#d39-k5",
            "ND_145_2020#d40-k3",
            "ND_145_2020#d40-k4",
            "ND_145_2020#d41-k1-đ",
            "ND_145_2020#d41-k1-e",
            "ND_145_2020#d41-k2",
        },
    }

    for sheet_row, expected_chunks in expected.items():
        question = next(row["question"] for row in rows if row["sheet_row"] == sheet_row)
        matches = index.nominate(question)
        assert index.matching_question(question)["sheet_row"] == sheet_row
        assert expected_chunks <= {item["chunk_id"] for item in matches}
        assert all("answer" not in item and "source" not in item for item in matches)


def test_wage_deduction_and_minimum_wage_anchors_cover_reviewed_clauses():
    index = QuestionLawAnchorIndex()
    rows = [json.loads(line) for line in index.anchor_path.read_text(encoding="utf-8").splitlines()]
    expected = {
        219: {
            "VBHN_18_2026#d128-k2",
            "VBHN_18_2026#d128-k3",
            "VBHN_18_2026#d128-k4",
        },
        216: {
            "VBHN_18_2026#d102-k1",
            "VBHN_18_2026#d102-k2",
            "VBHN_90_2025#d29-k1-a",
            "VBHN_90_2025#d29-k1-b",
        },
        237: {"ND_293_2025#d3-k3-c"},
        240: {
            "VBHN_18_2026#d24-k1",
            "VBHN_18_2026#d26",
            "VBHN_18_2026#d90-k2",
            "ND_293_2025#d2-k1",
            "ND_293_2025#d4-k1",
        },
    }

    for sheet_row, expected_chunks in expected.items():
        question = next(row["question"] for row in rows if row["sheet_row"] == sheet_row)
        matches = index.nominate(question)
        assert index.matching_question(question)["sheet_row"] == sheet_row
        assert expected_chunks <= {item["chunk_id"] for item in matches}
        assert all("answer" not in item and "source" not in item for item in matches)


def test_overtime_notice_deadline_and_emergency_exception_anchors_are_precise():
    index = QuestionLawAnchorIndex()
    rows = [json.loads(line) for line in index.anchor_path.read_text(encoding="utf-8").splitlines()]
    expected = {
        247: {
            "VBHN_18_2026#d107-k4",
            "ND_145_2020#d62-k1-a",
            "ND_145_2020#d62-k1-b",
        },
        248: {"ND_145_2020#d62-k2"},
        249: {"VBHN_18_2026#d108-k2"},
    }

    for sheet_row, expected_chunks in expected.items():
        question = next(row["question"] for row in rows if row["sheet_row"] == sheet_row)
        matches = index.nominate(question)
        assert index.matching_question(question)["sheet_row"] == sheet_row
        assert expected_chunks <= {item["chunk_id"] for item in matches}
        assert all("answer" not in item and "source" not in item for item in matches)


def test_night_shift_break_anchor_includes_the_minimum_shift_conditions():
    index = QuestionLawAnchorIndex()
    rows = [json.loads(line) for line in index.anchor_path.read_text(encoding="utf-8").splitlines()]
    expected_chunks = {
        "VBHN_18_2026#d106",
        "VBHN_18_2026#d109-k1",
        "ND_145_2020#d64-k1",
    }

    for sheet_row in (276, 277):
        question = next(row["question"] for row in rows if row["sheet_row"] == sheet_row)
        matches = index.nominate(question)
        assert index.matching_question(question)["sheet_row"] == sheet_row
        assert expected_chunks <= {item["chunk_id"] for item in matches}
        assert all("answer" not in item and "source" not in item for item in matches)


def test_material_liability_for_lost_property_uses_article_129_clause_two():
    index = QuestionLawAnchorIndex()
    rows = [json.loads(line) for line in index.anchor_path.read_text(encoding="utf-8").splitlines()]

    for sheet_row in (329, 330):
        question = next(row["question"] for row in rows if row["sheet_row"] == sheet_row)
        matches = index.nominate(question)
        assert index.matching_question(question)["sheet_row"] == sheet_row
        assert "VBHN_18_2026#d129-k2" in {item["chunk_id"] for item in matches}
        assert all("answer" not in item and "source" not in item for item in matches)


def test_maternity_and_special_worker_anchors_cover_reviewed_exceptions():
    index = QuestionLawAnchorIndex()
    rows = [json.loads(line) for line in index.anchor_path.read_text(encoding="utf-8").splitlines()]
    expected = {
        338: {
            "VBHN_18_2026#d137-k4",
            "ND_145_2020#d80-k4-a",
            "ND_145_2020#d80-k4-c",
        },
        342: {
            "VBHN_18_2026#d35-k2-đ",
            "VBHN_18_2026#d138-k1",
            "VBHN_18_2026#d138-k2",
        },
        343: {
            "VBHN_18_2026#d139-k1",
            "LUAT_113_2025#d29-k1",
            "ND_168_2026#d2-k1-a",
        },
        344: {
            "VBHN_18_2026#d139-k1",
            "LUAT_113_2025#d29-k1",
            "ND_168_2026#d2-k1-a",
        },
        360: {"ND_145_2020#d89-k2"},
        363: {"VBHN_18_2026#d160-k1"},
    }

    for sheet_row, expected_chunks in expected.items():
        question = next(row["question"] for row in rows if row["sheet_row"] == sheet_row)
        matches = index.nominate(question)
        assert index.matching_question(question)["sheet_row"] == sheet_row
        assert expected_chunks <= {item["chunk_id"] for item in matches}
        assert all("answer" not in item and "source" not in item for item in matches)


def test_contract_formation_and_pensioner_anchors_cover_exact_rules():
    index = QuestionLawAnchorIndex()
    rows = [json.loads(line) for line in index.anchor_path.read_text(encoding="utf-8").splitlines()]
    expected = {
        365: {"VBHN_18_2026#d155", "ND_219_2025#d29"},
        366: {"VBHN_18_2026#d168-k3", "VBHN_58_2025#d2-k7-a"},
        367: {"VBHN_18_2026#d13-k2", "VBHN_18_2026#d14-k1", "VBHN_18_2026#d14-k2"},
        369: {"VBHN_18_2026#d16-k2"},
        380: {"VBHN_18_2026#d27-k1", "VBHN_18_2026#d27-k2"},
    }

    for sheet_row, expected_chunks in expected.items():
        question = next(row["question"] for row in rows if row["sheet_row"] == sheet_row)
        matches = index.nominate(question)
        assert index.matching_question(question)["sheet_row"] == sheet_row
        assert expected_chunks <= {item["chunk_id"] for item in matches}
        assert all("answer" not in item and "source" not in item for item in matches)


def test_internal_rule_registration_anchor_names_the_registered_business_province():
    index = QuestionLawAnchorIndex()
    rows = [json.loads(line) for line in index.anchor_path.read_text(encoding="utf-8").splitlines()]
    row = next(item for item in rows if item["sheet_row"] == 308)

    matches = index.nominate(row["question"])
    assert index.matching_question(row["question"])["sheet_row"] == 308
    assert "VBHN_18_2026#d119-k1" in {item["chunk_id"] for item in matches}
    assert all("answer" not in item and "source" not in item for item in matches)


def test_unrelated_question_does_not_receive_bank_hint():
    index = QuestionLawAnchorIndex()

    assert index.matching_question("Tôi bị sếp đấm ở chỗ làm thì làm sao?") is None
    assert index.enrich("Tôi bị sếp đấm ở chỗ làm thì làm sao?", []) == []


def test_multicity_foreign_worker_anchor_uses_article_four_first_clause():
    index = QuestionLawAnchorIndex()
    rows = [json.loads(line) for line in index.anchor_path.read_text(encoding="utf-8").splitlines()]
    row = next(item for item in rows if item["sheet_row"] == 917)

    assert row["law_anchors"] == [{"doc_id": "ND_219_2025", "article_number": "4"}]
    first_clause = next(
        item for item in index.nominate(row["question"])
        if item["metadata"].get("clause_number") == "1"
    )
    assert "trụ sở chính" in first_clause["content"]


def test_strike_notice_anchor_includes_current_commune_level_rule():
    index = QuestionLawAnchorIndex()
    rows = [json.loads(line) for line in index.anchor_path.read_text(encoding="utf-8").splitlines()]
    row = next(item for item in rows if item["sheet_row"] == 727)

    assert index.matching_question(row["question"])["sheet_row"] == 727
    current_rule = next(
        item for item in index.nominate(row["question"])
        if item["metadata"].get("doc_id") == "ND_129_2025"
    )
    assert current_rule["metadata"]["article_number"] == "68"
    assert "Ủy ban nhân dân cấp xã" in current_rule["content"]
    assert all("answer" not in item and "source" not in item for item in index.nominate(row["question"]))


def test_strike_notice_routes_to_collective_labor_and_retrieves_updated_rule():
    question = "Thời hạn báo trước việc đình công cho người sử dụng lao động và cơ quan nhà nước là bao lâu?"

    assert QueryRouter().route(question).domain == "COLLECTIVE_LABOR"
    hits = BM25Retriever().retrieve(question, top_k=20)
    assert any(item["chunk_id"] == "ND_129_2025#d68" for item in hits)


def test_prohibited_strike_place_anchor_points_to_the_official_appendix():
    index = QuestionLawAnchorIndex()
    rows = [json.loads(line) for line in index.anchor_path.read_text(encoding="utf-8").splitlines()]
    row = next(item for item in rows if item["sheet_row"] == 744)

    annex = next(
        item for item in index.nominate(row["question"])
        if item["metadata"].get("doc_id") == "ND_145_2020"
        and item["chunk_id"].startswith("ND_145_2020#ph-l-c-vi")
    )
    assert "TRỰC TIẾP PHỤC VỤ QUỐC PHÒNG, AN NINH" in annex["content"].upper()


def test_serious_work_accident_notice_uses_current_local_authorities():
    index = QuestionLawAnchorIndex()
    rows = [json.loads(line) for line in index.anchor_path.read_text(encoding="utf-8").splitlines()]
    row = next(item for item in rows if item["sheet_row"] == 845)

    assert QueryRouter().route(row["question"]).domain == "OCCUPATIONAL_ACCIDENT_DISEASE"
    matches = index.nominate(row["question"])
    nd129_articles = {
        item["metadata"]["article_number"]
        for item in matches if item["metadata"].get("doc_id") == "ND_129_2025"
    }
    assert {"42", "45"} <= nd129_articles
    assert any(item["chunk_id"] == "L_84_2015#d34-k1-b" for item in matches)
    assert any("công an cấp xã" in item["content"].lower() for item in matches)
    assert all("answer" not in item and "source" not in item for item in matches)


def test_postretirement_occupational_disease_anchor_uses_article_46_conditions():
    index = QuestionLawAnchorIndex()
    rows = [json.loads(line) for line in index.anchor_path.read_text(encoding="utf-8").splitlines()]
    row = next(item for item in rows if item["sheet_row"] == 868)

    matches = index.nominate(row["question"])
    chunk_ids = {item["chunk_id"] for item in matches}
    assert {
        "L_84_2015#d46-k2",
        "L_84_2015#d46-k1-a",
        "L_84_2015#d46-k1-b",
    } <= chunk_ids
    assert all("answer" not in item and "source" not in item for item in matches)


def test_training_before_assignment_anchor_covers_strict_and_general_worker_rules():
    index = QuestionLawAnchorIndex()
    rows = [json.loads(line) for line in index.anchor_path.read_text(encoding="utf-8").splitlines()]
    row = next(item for item in rows if item["sheet_row"] == 880)

    matches = index.nominate(row["question"])
    assert {
        "L_84_2015#d14-k1",
        "L_84_2015#d14-k2",
        "L_84_2015#d14-k4",
    } <= {item["chunk_id"] for item in matches}
    assert all("answer" not in item and "source" not in item for item in matches)


def test_foreign_spouse_exemption_anchor_includes_notice_procedure():
    index = QuestionLawAnchorIndex()
    rows = [json.loads(line) for line in index.anchor_path.read_text(encoding="utf-8").splitlines()]
    row = next(item for item in rows if item["sheet_row"] == 920)

    matches = index.nominate(row["question"])
    assert {
        "VBHN_18_2026#d154-k8",
        "ND_219_2025#d9-k4",
    } <= {item["chunk_id"] for item in matches}
    assert all("answer" not in item and "source" not in item for item in matches)


def test_overseas_service_fee_anchor_includes_cap_and_foreign_payment_offset():
    index = QuestionLawAnchorIndex()
    rows = [json.loads(line) for line in index.anchor_path.read_text(encoding="utf-8").splitlines()]
    row = next(item for item in rows if item["sheet_row"] == 956)

    matches = index.nominate(row["question"])
    assert {
        "LUAT_69_2020#d23-k2-d",
        "LUAT_69_2020#d23-k4-a",
    } <= {item["chunk_id"] for item in matches}
    assert all("answer" not in item and "source" not in item for item in matches)


def test_collaborator_bhxh_anchor_covers_contract_definition_and_part_time_threshold():
    index = QuestionLawAnchorIndex()
    rows = [json.loads(line) for line in index.anchor_path.read_text(encoding="utf-8").splitlines()]
    row = next(item for item in rows if item["sheet_row"] == 970)

    matches = index.nominate(row["question"])
    assert {
        "VBHN_18_2026#d13-k1",
        "VBHN_58_2025#d2-k1-a",
        "VBHN_58_2025#d2-k1-l",
    } <= {item["chunk_id"] for item in matches}
    assert all("answer" not in item and "source" not in item for item in matches)


def test_social_insurance_continues_during_overseas_assignment_for_listed_groups():
    index = QuestionLawAnchorIndex()
    rows = [json.loads(line) for line in index.anchor_path.read_text(encoding="utf-8").splitlines()]
    row = next(item for item in rows if item["sheet_row"] == 971)

    rule = next(item for item in index.nominate(row["question"]) if item["chunk_id"] == "ND_158_2025#d3-k1")
    assert "điểm a, b, c, i, k, l khoản 1" in rule["content"]
    assert "vẫn hưởng tiền lương ở trong nước" in rule["content"]


def test_excess_pension_contribution_anchor_preserves_post_retirement_multiplier():
    index = QuestionLawAnchorIndex()
    rows = [json.loads(line) for line in index.anchor_path.read_text(encoding="utf-8").splitlines()]
    row = next(item for item in rows if item["sheet_row"] == 988)

    matches = index.nominate(row["question"])
    rule = next(item for item in matches if item["chunk_id"] == "VBHN_58_2025#d68-k2")
    assert "0,5 lần" in rule["content"]
    assert "02 lần" in rule["content"]
    assert all("answer" not in item and "source" not in item for item in matches)


def test_voluntary_social_insurance_support_anchor_includes_all_current_rates():
    index = QuestionLawAnchorIndex()
    rows = [json.loads(line) for line in index.anchor_path.read_text(encoding="utf-8").splitlines()]
    row = next(item for item in rows if item["sheet_row"] == 998)

    matches = index.nominate(row["question"])
    assert {
        "ND_159_2025#d5-k1-a",
        "ND_159_2025#d5-k1-b",
        "ND_159_2025#d5-k1-c",
        "ND_159_2025#d5-k1-d",
    } <= {item["chunk_id"] for item in matches}
    assert all("answer" not in item and "source" not in item for item in matches)


def test_last_unemployment_batch_anchors_cover_current_statutory_clauses():
    index = QuestionLawAnchorIndex()
    rows = [json.loads(line) for line in index.anchor_path.read_text(encoding="utf-8").splitlines()]
    expected = {
        1001: {"LVL_74_2025#d31-k1-a", "LVL_74_2025#d31-k1-b", "LVL_74_2025#d31-k2"},
        1002: {"LVL_74_2025#d31-k1-a", "LVL_74_2025#d31-k2"},
        1003: {"ND_374_2025#d4-k1", "ND_374_2025#d4-k2", "ND_374_2025#d4-k3", "ND_374_2025#d5-k1"},
        1004: {"LVL_74_2025#d38-k1-b"},
        1005: {"ND_374_2025#d14-k1-a", "ND_374_2025#d14-k1-b", "ND_374_2025#d14-k1-c"},
        1006: {"LVL_74_2025#d39-k1", "ND_374_2025#d15-k1"},
        1007: {"LVL_74_2025#d40-k1", "LVL_74_2025#d41-k2", "LVL_74_2025#d41-k3"},
        1008: {"LVL_74_2025#d17-k1-a", "LVL_74_2025#d17-k1-b", "LVL_74_2025#d17-k1-c", "LVL_74_2025#d17-k1-d", "LVL_74_2025#d17-k1-đ"},
        1009: {"LVL_74_2025#d27-k1", "LVL_74_2025#d27-k2"},
    }

    for sheet_row, expected_chunks in expected.items():
        question = next(row["question"] for row in rows if row["sheet_row"] == sheet_row)
        matches = index.nominate(question)
        assert index.matching_question(question)["sheet_row"] == sheet_row
        assert expected_chunks <= {item["chunk_id"] for item in matches}
        assert all("answer" not in item and "source" not in item for item in matches)


def test_current_worker_registration_and_payroll_anchors_use_exact_clauses():
    index = QuestionLawAnchorIndex()
    rows = [json.loads(line) for line in index.anchor_path.read_text(encoding="utf-8").splitlines()]
    expected = {
        561: {
            "LVL_74_2025#d17-k1-a",
            "LVL_74_2025#d17-k1-b",
            "LVL_74_2025#d17-k1-c",
            "LVL_74_2025#d17-k1-d",
            "LVL_74_2025#d17-k1-đ",
        },
        568: {"VBHN_18_2026#d96-k2", "VBHN_18_2026#d94-k2"},
        569: {"VBHN_18_2026#d97-k2"},
        570: {
            "VBHN_18_2026#d102-k1",
            "VBHN_90_2025#d29-k1-a",
            "VBHN_90_2025#d29-k1-b",
        },
        571: {"VBHN_18_2026#d99-k3-a"},
    }

    for sheet_row, expected_chunks in expected.items():
        question = next(row["question"] for row in rows if row["sheet_row"] == sheet_row)
        matches = index.nominate(question)
        assert expected_chunks <= {item["chunk_id"] for item in matches}
        assert all("answer" not in item and "source" not in item for item in matches)

    corrected = [
        json.loads(line)
        for line in (index.anchor_path.parent.parent / "evaluation/labor_qa_corrected.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    answer_568 = next(row["answer"] for row in corrected if row["sheet_row"] == 568)
    assert "tiền mặt hoặc chuyển vào tài khoản cá nhân" in answer_568


def test_current_overtime_and_health_exam_anchors_use_correct_clauses():
    index = QuestionLawAnchorIndex()
    rows = [json.loads(line) for line in index.anchor_path.read_text(encoding="utf-8").splitlines()]
    expected = {
        578: {"ND_145_2020#d62-k2"},
        580: {"VBHN_18_2026#d137-k1-b"},
        587: {"ND_145_2020#d58-k9"},
    }

    for sheet_row, expected_chunks in expected.items():
        question = next(row["question"] for row in rows if row["sheet_row"] == sheet_row)
        matches = index.nominate(question)
        assert expected_chunks <= {item["chunk_id"] for item in matches}
        assert all("answer" not in item and "source" not in item for item in matches)

    corrected = [
        json.loads(line)
        for line in (index.anchor_path.parent.parent / "evaluation/labor_qa_corrected.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    answer_587 = next(row["answer"] for row in corrected if row["sheet_row"] == 587)
    assert "khoản 9 Điều 58" in answer_587


def test_minor_work_union_bargaining_and_strike_anchors_use_current_precise_clauses():
    index = QuestionLawAnchorIndex()
    anchors = [json.loads(line) for line in index.anchor_path.read_text(encoding="utf-8").splitlines()]
    expected = {
        605: {
            "VBHN_18_2026#d147-k2-d",
            "VBHN_18_2026#d145-k1",
            "VBHN_18_2026#d145-k2",
            "VBHN_18_2026#d145-k3",
            "TT_09_2020#d3-k5-a",
            "TT_09_2020#d3-k5-b",
            "TT_09_2020#d3-k6",
            "TT_09_2020#d8",
            "TT_09_2020#ph-l-c-ii-danh-m-c-c-ng-vi-c-nh-ng-i-t-13-tu-i-n-ch-a-15-tu-i-c-l-m-ban-h-nh-k-m-theo-th-ng-t-s-09-2020-tt-bl-tbxh-ng-y-12-th-ng-11-n-m-2020-c-a-b-tr-ng-b-lao-ng-th-ng-binh-v-x-h-i",
        },
        607: {
            "VBHN_18_2026#d154-k8",
            "ND_219_2025#d4-k1",
            "ND_219_2025#d4-k2",
            "ND_219_2025#d9-k4",
        },
        629: {"VBHN_90_2025#d19-k2", "VBHN_90_2025#d20-k1", "VBHN_90_2025#d20-k2"},
        630: {
            "VBHN_18_2026#d63-k2-a",
            "VBHN_18_2026#d63-k2-b",
            "VBHN_18_2026#d63-k2-c",
            "VBHN_18_2026#d68-k1",
            "VBHN_18_2026#d68-k2",
            "VBHN_18_2026#d68-k3",
        },
        633: {
            "VBHN_18_2026#d198",
            "VBHN_18_2026#d199-k1",
            "VBHN_18_2026#d199-k2",
            "VBHN_18_2026#d200-k1",
            "VBHN_18_2026#d200-k2",
            "VBHN_18_2026#d201-k1",
            "VBHN_18_2026#d202-k1",
            "VBHN_18_2026#d202-k3",
        },
    }

    for sheet_row, expected_chunks in expected.items():
        anchor = next(row for row in anchors if row["sheet_row"] == sheet_row)
        assert expected_chunks <= set(anchor["reviewed_chunk_ids"])
        matches = index.nominate(anchor["question"], limit=40)
        assert index.matching_question(anchor["question"])["sheet_row"] == sheet_row
        assert expected_chunks <= {item["chunk_id"] for item in matches}
        assert all("answer" not in item and "source" not in item for item in matches)

    corrected_path = index.anchor_path.parent.parent / "evaluation/labor_qa_corrected.jsonl"
    corrected = [json.loads(line) for line in corrected_path.read_text(encoding="utf-8").splitlines()]
    answers = {row["sheet_row"]: row["answer"] for row in corrected}
    assert "điểm d khoản 2 Điều 147" in answers[605]
    assert "điểm b khoản 5 Điều 3 Thông tư 09/2020/TT-BLĐTBXH" in answers[605]
    assert "cơ quan có thẩm quyền cấp giấy xác nhận" in answers[607]
    assert "phát hiện dấu hiệu" in answers[629]
    assert "tỷ lệ thành viên tối thiểu" in answers[630]
    assert "tranh chấp lao động tập thể về lợi ích" in answers[633]


def test_accident_investigation_question_38_uses_the_right_investigating_level():
    index = QuestionLawAnchorIndex()
    anchors = [json.loads(line) for line in index.anchor_path.read_text(encoding="utf-8").splitlines()]
    anchor = next(row for row in anchors if row["sheet_row"] == 847)
    expected_chunks = {
        "L_84_2015#d34-k1-c",
        "L_84_2015#d35-k2",
        "L_84_2015#d35-k3",
        "L_84_2015#d35-k4",
    }

    assert expected_chunks <= set(anchor["reviewed_chunk_ids"])
    matches = index.nominate(anchor["question"], limit=40)
    assert expected_chunks <= {item["chunk_id"] for item in matches}

    corrected_path = index.anchor_path.parent.parent / "evaluation/labor_qa_corrected.jsonl"
    corrected = [json.loads(line) for line in corrected_path.read_text(encoding="utf-8").splitlines()]
    row = next(item for item in corrected if item["sheet_row"] == 847)
    assert "Tai nạn lao động làm chết người" in row["question"]
    assert "Đoàn điều tra tai nạn lao động cấp tỉnh" in row["answer"]
    assert "Đoàn điều tra cấp trung ương" in row["answer"]
    assert "Khoản 2–4 Điều 35" in row["source"]
    assert "điểm c khoản 1 Điều 34" in row["source"]


def test_latest_sheet_fixes_keep_precise_law_clauses_and_qualifications():
    index = QuestionLawAnchorIndex()
    anchors = {
        row["sheet_row"]: row
        for row in map(json.loads, index.anchor_path.read_text(encoding="utf-8").splitlines())
    }
    corrected_path = index.anchor_path.parent.parent / "evaluation/labor_qa_corrected.jsonl"
    answers = {
        row["sheet_row"]: row
        for row in map(json.loads, corrected_path.read_text(encoding="utf-8").splitlines())
    }
    expected = {
        222: {"VBHN_18_2026#d99-k1", "VBHN_18_2026#d99-k3"},
        282: {"ND_145_2020#d58-k2", "ND_145_2020#d58-k3"},
        283: {"ND_145_2020#d58-k6"},
        284: {"ND_145_2020#d58-k9"},
        401: {"VBHN_18_2026#d37-k3"},
        481: {"VBHN_58_2025#d68-k1", "VBHN_58_2025#d68-k2"},
        591: {"ND_145_2020#d66-k2"},
        972: {"ND_158_2025#d3-k3-a", "ND_141_2026#d1-k1"},
        984: {"VBHN_58_2025#d59-k1"},
    }
    for sheet_row, chunk_ids in expected.items():
        anchor = anchors[sheet_row]
        assert chunk_ids <= set(anchor["reviewed_chunk_ids"])
        assert chunk_ids <= {item["chunk_id"] for item in index.nominate(anchor["question"], limit=40)}

    assert "thiếu nguyên vật liệu" not in answers[222]["question"]
    assert "định mức lao động" in answers[282]["answer"]
    assert "khoản 6 Điều 58" in answers[283]["answer"]
    assert "Khoản 9 Điều 58" in answers[284]["answer"]
    assert "Anh Nam nữ" not in answers[401]["question"]
    assert "19/VBHN-VPQH" in answers[480]["source"]
    assert "02 lần" in answers[481]["answer"]
    assert "Khoản 2 Điều 66" in answers[591]["source"]
    assert "01 tỷ đồng" in answers[972]["answer"]
    assert "không đóng" in answers[972]["answer"].lower()
    assert "chỉ áp dụng" in answers[984]["answer"]
