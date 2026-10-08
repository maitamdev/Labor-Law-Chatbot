# -*- coding: utf-8 -*-
from types import SimpleNamespace

from rag.case_analyzer import CaseAnalyzer
from rag.evidence_completeness import EvidenceCompletenessGate
from rag.context_builder import ContextBuilder
from rag.evidence_mapper import EvidenceBlock, EvidenceMapper
from rag.issue_decomposer import IssueDecomposer
from rag.legal_issue_parser import detect_legal_events, determine_required_evidence_roles
from rag.output_validator import LegalAnswer, LegalFinding, OutputValidator


def _issue(issue_id, text, roles=None, events=None):
    return SimpleNamespace(
        issue_id=issue_id,
        raw_issue_text=text,
        domain="CORE_LABOR",
        legal_event=(events or ["UNKNOWN"])[0],
        legal_events=events or [],
        required_evidence_roles=roles or [],
    )


def test_case_analyzer_builds_auditable_case_file_for_long_scenario():
    issues = [
        _issue("issue_1", "Công ty chậm trả lương có đúng luật không?", events=["WAGE_AND_SALARY"]),
        _issue("issue_2", "Tôi nghỉ việc thì phải báo trước bao lâu?", events=["TERMINATION"]),
    ]
    query = (
        "Tôi ký hợp đồng lao động xác định thời hạn 24 tháng ngày 01/01/2025, "
        "lương 12 triệu đồng/tháng. Công ty đã chậm trả lương 20 ngày. "
        "Câu hỏi: 1. Công ty chậm trả lương có đúng luật không? "
        "2. Nếu tôi nghỉ việc thì phải báo trước bao lâu?"
    )

    result = CaseAnalyzer().analyze(query, issues)

    assert result.issue_count == 2
    assert result.is_complex is True
    assert {fact.fact_type for fact in result.facts} >= {"DATE", "MONEY", "DURATION", "CONTRACT"}
    assert [profile.issue_id for profile in result.issue_profiles] == ["issue_1", "issue_2"]
    assert "không được tự bổ sung" in result.to_prompt_block().lower()


def test_case_analyzer_calculates_notice_date_interval_instead_of_leaving_it_to_llm():
    result = CaseAnalyzer().analyze(
        "Ngày 20/09/2026 tôi báo nghỉ và dự kiến nghỉ từ ngày 01/10/2026.",
        [_issue("issue_1", "Tôi đã báo trước đủ chưa?", events=["TERMINATION"])],
    )
    intervals = [fact.value for fact in result.facts if fact.fact_type == "DATE_INTERVAL"]
    assert intervals == ["Từ 20/09/2026 đến 01/10/2026: 11 ngày theo lịch"]
    assert "KẾT QUẢ TÍNH NGÀY BẮT BUỘC" in result.to_prompt_block()


def test_termination_issue_inherits_late_wage_exception_role_from_scenario():
    issues = IssueDecomposer().decompose(
        "Công ty chậm trả lương của tôi 20 ngày. Câu hỏi: "
        "1. Việc chậm trả lương được xử lý thế nào? "
        "2. Tôi muốn nghỉ việc thì có phải báo trước không?"
    )

    termination = next(issue for issue in issues if "TERMINATION" in issue.legal_events)
    assert "EMPLOYEE_NO_NOTICE_EXCEPTION" in termination.required_evidence_roles


def test_numbered_question_keeps_termination_worded_as_nghi_from_date():
    issues = IssueDecomposer().decompose(
        "Công ty chậm trả lương 20 ngày. Ngày 20/09/2026 tôi báo nghỉ. "
        "Câu hỏi: 1. Công ty chậm lương có đúng không? "
        "2. Việc không xét thưởng có đúng không? "
        "3. Tôi nghỉ từ ngày 01/10/2026 thì có vi phạm thời hạn báo trước không?"
    )

    assert len(issues) == 3
    assert "TERMINATION" in issues[2].legal_events


def test_deterministic_guards_correct_date_contradiction_and_conditional_bonus():
    findings = [
        LegalFinding(issue_id="issue_2", issue="Thưởng", finding="Không xét thưởng chắc chắn trái luật."),
        LegalFinding(issue_id="issue_3", issue="Nghỉ việc", finding="Đã báo đủ 30 ngày."),
    ]
    case = SimpleNamespace(
        facts=[SimpleNamespace(fact_type="DATE_INTERVAL", value="Từ 20/09/2026 đến 01/10/2026: 11 ngày theo lịch")],
        issue_profiles=[
            SimpleNamespace(
                issue_id="issue_2",
                legal_events=["DISCIPLINE_AND_BONUS"],
                missing_material_facts=["quy chế thưởng, hợp đồng lao động hoặc thỏa ước lao động tập thể quy định điều kiện hưởng thưởng"],
            ),
            SimpleNamespace(issue_id="issue_3", legal_events=["TERMINATION"], missing_material_facts=[]),
        ],
    )

    changed = OutputValidator._apply_deterministic_case_guards(
        findings,
        case,
        {
            "issue_2": ["VBHN_18_2026#d104-k1"],
            "issue_3": ["VBHN_18_2026#d35-k1-b", "VBHN_18_2026#d35-k2-b"],
        },
    )

    assert changed is True
    assert "chưa thể kết luận" in findings[0].finding
    assert "11 ngày" in findings[1].finding
    assert "ngắn hơn mức 30 ngày" in findings[1].finding


def test_boss_assault_is_workplace_violence_not_employee_discipline():
    query = "Tôi đi làm mà bị sếp đấm thì sếp phải bị như nào?"
    events = detect_legal_events(query)
    roles = determine_required_evidence_roles(events, query.lower())

    assert events == ["WORKPLACE_VIOLENCE"]
    assert roles == [
        "EMPLOYER_MISTREATMENT_PROHIBITION",
        "EMPLOYEE_NO_NOTICE_FOR_MISTREATMENT",
        "EMPLOYER_MISTREATMENT_SANCTION",
    ]


def test_context_builder_replaces_discipline_noise_for_workplace_violence():
    builder = ContextBuilder()
    context = builder.build_context(
        retrieved_chunks=[
            builder._get_chunk_by_id("VBHN_18_2026#d8-k2"),
            builder._get_chunk_by_id("VBHN_18_2026#d122-k1-b"),
        ],
        expand_siblings=False,
    )
    chunk_ids = {block.chunk_id for block in context.evidence_blocks}

    assert "VBHN_18_2026#d122-k1-b" not in chunk_ids
    assert {
        "VBHN_18_2026#d8-k2",
        "VBHN_18_2026#d35-k2-c",
        "ND_283_2026#d17-k4",
        "ND_283_2026#d17-k4-a",
        "ND_283_2026#d7-k1",
    }.issubset(chunk_ids)


def test_deterministic_guard_gives_complete_workplace_violence_advice():
    finding = LegalFinding(issue_id="issue_1", issue="Sếp hành hung", finding="Có thể bị xử lý.")
    case = SimpleNamespace(
        facts=[],
        issue_profiles=[
            SimpleNamespace(
                issue_id="issue_1",
                legal_events=["WORKPLACE_VIOLENCE"],
                missing_material_facts=["mức độ thương tích và tài liệu y tế"],
            )
        ],
    )
    evidence = [
        "VBHN_18_2026#d8-k2",
        "VBHN_18_2026#d35-k2-c",
        "ND_283_2026#d17-k4",
        "ND_283_2026#d17-k4-a",
        "ND_283_2026#d7-k1",
    ]

    changed = OutputValidator._apply_deterministic_case_guards(
        [finding], case, {"issue_1": evidence}
    )

    assert changed is True
    assert "50 đến 75 triệu đồng" in finding.finding
    assert "không cần báo trước" in finding.finding
    assert "trình báo Công an" in finding.finding
    assert "chưa đủ để chốt tội danh" in finding.finding
    assert finding.supporting_chunk_ids == evidence


def test_work_before_signing_is_not_misclassified_as_fixed_term_renewal():
    query = "Doanh nghiệp cho một người vào làm chính thức rồi cuối tuần mới ký HĐLĐ được không?"
    events = detect_legal_events(query)
    roles = determine_required_evidence_roles(events, query.lower())

    assert events == ["CONTRACT_SIGNING_TIMING"]
    assert roles == [
        "PRE_WORK_CONTRACT_REQUIREMENT",
        "EMPLOYMENT_RELATIONSHIP_DEFINITION",
        "WRITTEN_CONTRACT_FORM",
        "ORAL_CONTRACT_EXCEPTION",
    ]


def test_contract_signing_timing_understands_common_paraphrases():
    variants = [
        "Công ty cho tôi đi làm trước rồi vài ngày sau mới ký hợp đồng lao động có được không?",
        "Tôi bắt đầu làm việc nhưng chưa ký HĐLĐ thì có hợp pháp không?",
        "Tôi đã làm được một tuần mà công ty vẫn chưa ký hợp đồng lao động.",
        "Doanh nghiệp hẹn ký hợp đồng sau khi tôi vào làm chính thức.",
        "Thứ hai tôi đi làm, thứ sáu công ty mới ký HĐLĐ có đúng không?",
        "Cho nhân viên làm việc không có hợp đồng vài ngày rồi mới ký được không?",
        "Tôi chưa được ký hợp đồng lao động nhưng đã bắt đầu làm việc.",
        "Có được ký HĐLĐ sau ngày người lao động bắt đầu đi làm không?",
    ]

    for query in variants:
        assert "CONTRACT_SIGNING_TIMING" in detect_legal_events(query), query


def test_contract_signing_timing_does_not_capture_expired_contract_renewal():
    renewal_queries = [
        "Hợp đồng hết hạn nhưng tôi tiếp tục làm việc thì khi nào phải ký hợp đồng mới?",
        "HĐLĐ cũ hết hạn, công ty cho đi làm tiếp rồi ký lần 2 có được không?",
        "Công ty gia hạn hợp đồng xác định thời hạn như thế nào?",
    ]

    for query in renewal_queries:
        assert "CONTRACT_SIGNING_TIMING" not in detect_legal_events(query), query


def test_context_builder_replaces_article_20_with_contract_signing_rules():
    builder = ContextBuilder()
    context = builder.build_context(
        retrieved_chunks=[
            builder._get_chunk_by_id("VBHN_18_2026#d20-k2-c"),
            builder._get_chunk_by_id("VBHN_18_2026#d13-k2"),
        ],
        expand_siblings=False,
    )
    chunk_ids = [block.chunk_id for block in context.evidence_blocks]

    assert "VBHN_18_2026#d20-k2-c" not in chunk_ids
    assert chunk_ids == [
        "VBHN_18_2026#d13-k2",
        "VBHN_18_2026#d13-k1",
        "VBHN_18_2026#d14-k1",
        "VBHN_18_2026#d14-k2",
    ]


def test_deterministic_guard_answers_work_before_signing_completely():
    finding = LegalFinding(issue_id="issue_1", issue="Thời điểm ký HĐLĐ", finding="Có thể ký sau.")
    case = SimpleNamespace(
        facts=[],
        issue_profiles=[
            SimpleNamespace(
                issue_id="issue_1",
                legal_events=["CONTRACT_SIGNING_TIMING"],
                missing_material_facts=["thời hạn dự kiến của hợp đồng"],
            )
        ],
    )
    evidence = [
        "VBHN_18_2026#d13-k2",
        "VBHN_18_2026#d13-k1",
        "VBHN_18_2026#d14-k1",
        "VBHN_18_2026#d14-k2",
    ]

    changed = OutputValidator._apply_deterministic_case_guards(
        [finding], case, {"issue_1": evidence}
    )

    assert changed is True
    assert "không được" in finding.finding
    assert "trước khi nhận người lao động" in finding.finding
    assert "dưới 01 tháng" in finding.finding
    assert "Điều 20" not in finding.finding
    assert finding.supporting_chunk_ids == evidence


def test_contract_formation_principles_route_to_article_15():
    variants = [
        "Nguyên tắc nền tảng khi giao kết HĐLĐ gồm những yêu cầu nào?",
        "Nguyên tắc giao kết hợp đồng lao động là gì?",
        "Khi giao kết hợp đồng lao động các bên phải tuân thủ những nguyên tắc nào?",
        "Việc ký kết HĐLĐ phải dựa trên những yêu cầu cơ bản gì?",
    ]

    for query in variants:
        events = detect_legal_events(query)
        roles = determine_required_evidence_roles(events, query.lower())
        assert "CONTRACT_FORMATION_PRINCIPLES" in events, query
        assert roles == [
            "FORMATION_EQUALITY_GOOD_FAITH",
            "FORMATION_FREEDOM_LIMITS",
        ], query


def test_information_duty_question_is_not_misrouted_to_contract_principles():
    variants = [
        "Người sử dụng lao động phải cung cấp thông tin gì khi giao kết hợp đồng lao động?",
        "Khi giao kết HĐLĐ, người lao động có nghĩa vụ khai báo thông tin nào?",
    ]

    for query in variants:
        assert "CONTRACT_FORMATION_PRINCIPLES" not in detect_legal_events(query), query


def test_context_builder_purges_article_16_from_principles_question():
    builder = ContextBuilder()
    context = builder.build_context(
        retrieved_chunks=[
            builder._get_chunk_by_id("VBHN_18_2026#d16-k1"),
            builder._get_chunk_by_id("VBHN_18_2026#d15-k1"),
        ],
        expand_siblings=False,
    )
    chunk_ids = [block.chunk_id for block in context.evidence_blocks]

    assert chunk_ids == ["VBHN_18_2026#d15-k1", "VBHN_18_2026#d15-k2"]
    assert "VBHN_18_2026#d16-k1" not in chunk_ids


def test_deterministic_guard_answers_contract_formation_principles():
    finding = LegalFinding(issue_id="issue_1", issue="Nguyên tắc giao kết", finding="Phải cung cấp thông tin.")
    case = SimpleNamespace(
        facts=[],
        issue_profiles=[
            SimpleNamespace(
                issue_id="issue_1",
                legal_events=["CONTRACT_FORMATION_PRINCIPLES"],
                missing_material_facts=[],
            )
        ],
    )
    evidence = ["VBHN_18_2026#d15-k1", "VBHN_18_2026#d15-k2"]

    changed = OutputValidator._apply_deterministic_case_guards(
        [finding], case, {"issue_1": evidence}
    )

    assert changed is True
    assert "tự nguyện, bình đẳng, thiện chí, hợp tác và trung thực" in finding.finding
    assert "không được trái pháp luật" in finding.finding
    assert "là một vấn đề pháp lý khác" in finding.finding
    assert finding.supporting_chunk_ids == evidence


def test_de_facto_contract_litigation_gets_procedure_role_without_overtime_noise():
    query = (
        "Hoan là sinh viên đi làm thêm, ký thỏa thuận công việc có việc làm, tiền công và chịu quản lý. "
        "Chủ quán nói đây không phải hợp đồng lao động nên không thể kiện. Hỏi: "
        "1. Nói thỏa thuận công việc không phải hợp đồng lao động nên không thể kiện có đúng không? "
        "2. Chủ quán có được giữ bản chính giấy tờ tùy thân không?"
    )
    issues = IssueDecomposer().decompose(query)

    assert len(issues) == 2
    assert issues[0].required_evidence_roles == [
        "EMPLOYMENT_RELATIONSHIP_DEFINITION",
        "INDIVIDUAL_LABOUR_DISPUTE_PROCEDURE",
    ]
    assert "OVERTIME_CONSENT" not in issues[0].required_evidence_roles


def test_context_builder_purges_irrelevant_overtime_and_wage_chunks_from_de_facto_issue():
    builder = ContextBuilder()
    get = builder._get_chunk_by_id
    context = builder.build_context(
        retrieved_chunks=[],
        multi_issue_candidates={
            "issue_1": [
                get("VBHN_18_2026#d13-k1"),
                get("VBHN_18_2026#d188-k1"),
                get("VBHN_18_2026#d107-k2-a"),
                get("VBHN_18_2026#d97-k1"),
            ],
            "issue_2": [get("VBHN_18_2026#d17-k1")],
        },
        expand_siblings=False,
    )
    chunk_ids = {block.chunk_id for block in context.evidence_blocks}

    assert "VBHN_18_2026#d107-k2-a" not in chunk_ids
    assert "VBHN_18_2026#d97-k1" not in chunk_ids
    assert {
        "VBHN_18_2026#d13-k1",
        "VBHN_18_2026#d188-k1",
        "VBHN_18_2026#d17-k1",
        "ND_283_2026#d15-k2-a",
        "ND_283_2026#d15-k3-d",
    }.issubset(chunk_ids)


def test_deterministic_guards_produce_complete_de_facto_and_original_document_advice():
    findings = [
        LegalFinding(issue_id="issue_1", issue="Quan hệ lao động", finding="Có thể kiện."),
        LegalFinding(issue_id="issue_2", issue="Giữ giấy tờ", finding="Không được giữ."),
    ]
    case = SimpleNamespace(
        facts=[],
        issue_profiles=[
            SimpleNamespace(issue_id="issue_1", legal_events=["DE_FACTO_LABOR_CONTRACT"], missing_material_facts=[]),
            SimpleNamespace(issue_id="issue_2", legal_events=["EMPLOYER_PROHIBITED_ACTS"], missing_material_facts=[]),
        ],
    )
    changed = OutputValidator._apply_deterministic_case_guards(
        findings,
        case,
        {
            "issue_1": [
                "VBHN_18_2026#d13-k1", "VBHN_18_2026#d188-k1",
                "VBHN_18_2026#d188-k1-a", "VBHN_18_2026#d188-k7-b", "VBHN_18_2026#d190-k3",
            ],
            "issue_2": [
                "VBHN_18_2026#d17-k1", "ND_283_2026#d15-k2",
                "ND_283_2026#d15-k2-a", "ND_283_2026#d15-k3-d",
            ],
        },
    )

    assert changed is True
    assert "Tên gọi “thỏa thuận công việc” không quyết định" in findings[0].finding
    assert "không bắt buộc hòa giải" in findings[0].finding
    assert "20 đến 25 triệu đồng" in findings[1].finding
    assert "ND_283_2026#d15-k3-d" in findings[1].supporting_chunk_ids


def test_evidence_gate_detects_issue_without_its_own_evidence():
    issues = [
        _issue("issue_1", "Quyền về tiền lương"),
        _issue("issue_2", "Quyền khi nghỉ việc"),
    ]
    result = EvidenceCompletenessGate().evaluate(
        issues,
        {
            "issue_1": [{"chunk_id": "law#d94", "rule_type": "GENERAL_RULE", "status": "CURRENT"}],
            "issue_2": [],
        },
    )

    assert result.all_issues_grounded is False
    assert result.coverage_ratio == 0.5
    assert result.unsupported_issue_ids == ["issue_2"]
    assert result.issues[1].can_conclude is False


def test_output_validator_keeps_citations_owned_by_each_issue_and_blocks_cross_use():
    blocks = [
        EvidenceBlock("E1", "law#d94", "45/2019/QH14", "Bộ luật Lao động", article_number=94, issue_id="issue_1"),
        EvidenceBlock("E2", "law#d35", "45/2019/QH14", "Bộ luật Lao động", article_number=35, issue_id="issue_2"),
    ]
    mapper = EvidenceMapper()
    mapper.register_blocks(blocks)
    registry = {
        "law#d94": {"chunk_id": "law#d94", "document_no": "45/2019/QH14", "article_number": 94},
        "law#d35": {"chunk_id": "law#d35", "document_no": "45/2019/QH14", "article_number": 35},
    }
    answer = LegalAnswer(
        answer="Kết quả phân tích.",
        findings=[
            LegalFinding(issue_id="issue_1", issue="Tiền lương", finding="Phải trả lương [E1].", evidence_ids=["E1"]),
            # Deliberate cross-issue citation: issue_2 tries to use E1.
            LegalFinding(issue_id="issue_2", issue="Nghỉ việc", finding="Được nghỉ theo [E1].", evidence_ids=["E1"]),
        ],
        evidence_ids=["E1", "E2"],
    )

    result = OutputValidator().validate_and_format(
        answer,
        set(registry),
        registry,
        evidence_mapper=mapper,
        locked_chunk_ids=list(registry),
        issue_evidence_map={"issue_1": ["law#d94"], "issue_2": ["law#d35"]},
        expected_issues=[_issue("issue_1", "Tiền lương"), _issue("issue_2", "Nghỉ việc")],
    )

    assert result.legal_findings[0].supporting_chunk_ids == ["law#d94"]
    assert result.legal_findings[1].supporting_chunk_ids == []
    assert result.legal_findings[1].grounding_status == "insufficient"
    assert "dùng nhầm căn cứ" in result.legal_findings[1].finding
    assert "E1" in result.rejected_chunk_ids
    assert result.is_fully_grounded is False


def test_output_validator_suppresses_unsupported_issue_conclusion():
    block = EvidenceBlock("E1", "law#d94", "45/2019/QH14", "Bộ luật Lao động", article_number=94, issue_id="issue_1")
    mapper = EvidenceMapper()
    mapper.register_blocks([block])
    answer = LegalAnswer(
        answer="Công ty chắc chắn sai ở cả hai vấn đề.",
        findings=[
            LegalFinding(issue_id="issue_1", issue="Tiền lương", finding="Phải trả đủ lương.", evidence_ids=["E1"]),
            LegalFinding(issue_id="issue_2", issue="Vấn đề chưa có nguồn", finding="Công ty chắc chắn sai.", evidence_ids=[]),
        ],
    )
    result = OutputValidator().validate_and_format(
        answer,
        {"law#d94"},
        {"law#d94": {"chunk_id": "law#d94", "document_no": "45/2019/QH14", "article_number": 94}},
        evidence_mapper=mapper,
        locked_chunk_ids=["law#d94"],
        issue_evidence_map={"issue_1": ["law#d94"], "issue_2": []},
        expected_issues=[_issue("issue_1", "Tiền lương"), _issue("issue_2", "Vấn đề chưa có nguồn")],
        unsupported_issue_ids=["issue_2"],
    )

    unsupported = next(f for f in result.legal_findings if f.issue_id == "issue_2")
    assert unsupported.grounding_status == "insufficient"
    assert "chưa đủ căn cứ" in unsupported.finding.lower()
    assert "chắc chắn sai ở cả hai" not in result.final_answer.lower()
    assert result.unresolved_issue_ids == ["issue_2"]


def test_output_validator_recovers_findings_from_numbered_markdown_sections():
    blocks = [
        EvidenceBlock("E1", "law#wage", "45/2019/QH14", "Bộ luật Lao động", article_number=97, issue_id="issue_1"),
        EvidenceBlock("E2", "law#notice", "45/2019/QH14", "Bộ luật Lao động", article_number=35, issue_id="issue_2"),
    ]
    mapper = EvidenceMapper()
    mapper.register_blocks(blocks)
    registry = {
        "law#wage": {"chunk_id": "law#wage", "document_no": "45/2019/QH14", "article_number": 97},
        "law#notice": {"chunk_id": "law#notice", "document_no": "45/2019/QH14", "article_number": 35},
    }
    answer = LegalAnswer(
        answer=(
            "### Vấn đề 1: Trả lương\nTheo [E1], công ty phải trả lương đúng hạn.\n\n"
            "### Vấn đề 2: Báo trước\nTheo [E2], thời hạn báo trước phụ thuộc loại hợp đồng."
        ),
        findings=[],
    )
    result = OutputValidator().validate_and_format(
        answer,
        set(registry),
        registry,
        evidence_mapper=mapper,
        locked_chunk_ids=list(registry),
        issue_evidence_map={"issue_1": ["law#wage"], "issue_2": ["law#notice"]},
        expected_issues=[_issue("issue_1", "Trả lương"), _issue("issue_2", "Báo trước")],
    )

    assert [f.issue_id for f in result.legal_findings] == ["issue_1", "issue_2"]
    assert [f.supporting_chunk_ids for f in result.legal_findings] == [["law#wage"], ["law#notice"]]
    assert result.unresolved_issue_ids == []
    assert result.is_fully_grounded is True
