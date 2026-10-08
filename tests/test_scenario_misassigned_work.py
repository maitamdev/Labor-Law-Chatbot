# -*- coding: utf-8 -*-
"""Regression test for employee termination without notice due to misassigned work (BLLĐ 2019 Điều 35k2a, Điều 29, Điều 40)."""
import pytest
from rag.chain import VietLaborRAGChain


@pytest.fixture(scope="module")
def chain():
    return VietLaborRAGChain()


def test_misassigned_work_termination_scenario(chain):
    query = (
        "Chị Trang được tuyển dụng vào làm việc tại Công ty chế biến gỗ theo hợp đồng lao động thời hạn 36 tháng. "
        "Theo thỏa thuận trong hợp đồng, Chị Trang được tuyển dụng vào vị trí kiểm tra chất lượng sản phẩm. "
        "Tuy nhiên, đã 03 tháng kể từ khi vào công ty làm việc, chị lại phải làm công việc của công nhân bốc vác. "
        "Chị đã nhiều lần kiến nghị với Giám đốc công ty bố trí công việc theo đúng hợp đồng nhưng không được giải quyết "
        "cũng không được giải thích lý do. Chị đã nghỉ việc mà không báo trước cho công ty.\n"
        "Hỏi: Việc tự ý nghỉ việc của chị Trang có bị coi là đơn phương chấm dứt hợp đồng lao động trái pháp luật không? "
        "Trong trường hợp tự ý chấm dứt hợp đồng lao động chị Trang có phải bồi thường không?"
    )

    result = chain.run(query)

    assert result is not None
    assert not result.validated_response.abstain

    # Verify cited chunks cover the statutory provisions
    cited = result.validated_response.cited_chunk_ids
    assert "VBHN_18_2026#d35-k2-a" in cited
    assert "VBHN_18_2026#d29-k1" in cited or "VBHN_18_2026#d29-k2" in cited

    # Verify legal conclusions in answer
    answer = result.answer
    assert "KHÔNG bị coi là đơn phương chấm dứt hợp đồng lao động trái pháp luật" in answer or "không bị coi là đơn phương chấm dứt hợp đồng lao động trái pháp luật" in answer.lower()
    assert "KHÔNG phải bồi thường" in answer or "không phải bồi thường" in answer.lower()
