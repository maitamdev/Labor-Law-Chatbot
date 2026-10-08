"""The employer's temporary workplace closure must not map to termination law."""
from rag.chain import VietLaborRAGChain
from rag.query_router import QueryRouter
from rag.workplace_lockout import (
    LOCKOUT_EVIDENCE_IDS,
    grounded_workplace_lockout_answer,
    standalone_lockout_rule_request,
    workplace_lockout_request,
)


QUESTION = (
    "Xin cho Tôi biết Người sử dụng lao động có quyền đóng cửa nơi làm việc không? "
    "đóng cửa nơi làm việc trong trường hợp nào?"
)


def test_lockout_scope_does_not_capture_generic_business_closure_or_other_issues():
    assert workplace_lockout_request(QUESTION)
    assert standalone_lockout_rule_request(QUESTION)
    assert standalone_lockout_rule_request("Công ty được đóng cửa chỗ làm khi đình công không?")
    assert not workplace_lockout_request("Doanh nghiệp đóng cửa cửa hàng vì hết hàng")
    assert not standalone_lockout_rule_request("Đóng cửa nơi làm việc trái luật bị phạt bao nhiêu?")
    assert not standalone_lockout_rule_request("Đóng cửa nơi làm việc có phải trả lương không?")
    assert QueryRouter().route(QUESTION).domain == "COLLECTIVE_LABOR"


def test_current_decree_closure_notice_is_in_the_canonical_corpus():
    chain = VietLaborRAGChain()
    chunks = chain.qa_anchor_index.lookup_chunk_ids(LOCKOUT_EVIDENCE_IDS)

    assert len(chunks) == len(LOCKOUT_EVIDENCE_IDS)
    notice = next(chunk for chunk in chunks if chunk["chunk_id"] == "ND_129_2025#d69")
    assert "Ủy ban nhân dân cấp xã" in notice["content"]
    assert "03 ngày làm việc" in notice["content"]
    assert notice["metadata"]["official_source"].startswith("https://congbao.chinhphu.vn/")
    assert grounded_workplace_lockout_answer(QUESTION, LOCKOUT_EVIDENCE_IDS)
    assert grounded_workplace_lockout_answer(QUESTION, LOCKOUT_EVIDENCE_IDS[:-1]) is None


def test_user_question_gets_complete_grounded_answer_without_ollama():
    result = VietLaborRAGChain().run(QUESTION, update_memory=False)

    assert result.route_decision.domain == "COLLECTIVE_LABOR"
    assert result.retrieval_method == "Verified Workplace Lockout Provisions"
    assert result.llm_latency_ms == 0
    assert set(LOCKOUT_EVIDENCE_IDS) <= set(result.validated_response.cited_chunk_ids)
    assert "VBHN_18_2026#d36-k1-d" not in result.locked_chunk_ids
    answer = result.validated_response.final_answer
    assert "Có. Người sử dụng lao động có quyền" in answer
    assert "không đủ điều kiện duy trì hoạt động bình thường" in answer
    assert "để bảo vệ tài sản" in answer
    assert "03 ngày làm việc" in answer
    assert "Ủy ban nhân dân cấp xã" in answer
    assert "12 giờ" in answer
    assert "Điều 36" in answer and "không phải căn cứ" in answer
