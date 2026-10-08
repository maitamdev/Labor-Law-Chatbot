from rag.retirement_age import AGE_EVIDENCE_IDS, grounded_answer, request_details


def test_early_retirement_2026_requires_both_five_and_ten_year_cases():
    question = (
        "Một lao động nam nghỉ hưu trong năm 2026 thuộc trường hợp được nghỉ "
        "ở tuổi thấp hơn tuổi nghỉ hưu bình thường thì tuổi nghỉ hưu thấp nhất là bao nhiêu?"
    )
    answer = grounded_answer(question, set(AGE_EVIDENCE_IDS))

    assert answer is not None
    assert "61 tuổi 6 tháng" in answer
    assert "56 tuổi 6 tháng" in answer
    assert "51 tuổi 6 tháng" in answer
    assert grounded_answer(question, {AGE_EVIDENCE_IDS[0]}) is None


def test_female_query_does_not_match_vietnam_as_male():
    question = "Ở Việt Nam, lao động nữ nghỉ hưu sớm trong năm 2026 được tính tuổi thế nào?"

    assert request_details(question) == (2026, "nữ", "general")
    assert "57 tuổi" in grounded_answer(question, set(AGE_EVIDENCE_IDS))
