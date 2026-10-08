from rag.foreign_worker_multisite import (
    MULTISITE_EVIDENCE_IDS,
    grounded_answer,
    is_multisite_filing_question,
)


def test_multisite_filing_uses_head_office_clause_only():
    question = "Nếu một người nước ngoài làm việc cho cùng một người sử dụng lao động tại nhiều tỉnh, hồ sơ được nộp theo nơi nào?"
    assert is_multisite_filing_question(question)
    assert grounded_answer(question, []) is None

    answer = grounded_answer(question, MULTISITE_EVIDENCE_IDS)
    assert answer is not None
    assert "nơi người sử dụng lao động đặt trụ sở chính" in answer
    assert "không thể tùy ý chọn" in answer
    assert "khoản 1 Điều 4" in answer


def test_single_province_or_unrelated_question_does_not_trigger():
    assert not is_multisite_filing_question("Người nước ngoài làm việc ở một tỉnh nộp hồ sơ ở đâu?")
    assert not is_multisite_filing_question("Người lao động Việt Nam làm việc tại nhiều tỉnh được nghỉ mấy ngày?")
    assert not is_multisite_filing_question("Người nước ngoài làm tại nhiều tỉnh, đã có giấy phép thì thông báo hồ sơ trước mấy ngày?")
