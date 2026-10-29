"""Regression coverage for Vietnamese words that collide after accent folding."""

import unicodedata

import pytest

from app.smalltalk import answer_out_of_scope_fast
from rag.conversational import fold_vietnamese
from rag.followup_rewriter import looks_like_followup
from rag.query_router import QueryRouter, is_contextual_followup, is_out_of_scope_query

SAFETY_AND_BONUS_QUESTION = (
    "Người lao động có quyền từ chối làm việc khi có nguy cơ sạt lở đe dọa "
    "tính mạng không và công ty cắt thưởng đúng hay sai?"
)


@pytest.mark.parametrize("has_history", [False, True])
@pytest.mark.parametrize("question", [
    SAFETY_AND_BONUS_QUESTION,
    unicodedata.normalize("NFD", SAFETY_AND_BONUS_QUESTION),
    SAFETY_AND_BONUS_QUESTION.upper(),
    fold_vietnamese(SAFETY_AND_BONUS_QUESTION),
    SAFETY_AND_BONUS_QUESTION.replace("đe dọa", "đe doạ"),
    SAFETY_AND_BONUS_QUESTION.replace("lở đe", "lở, đe"),
    "Sườn núi bị lở đe dọa tính mạng, công ty có được ép làm việc không?",
    "Suon nui bi lo de doa tinh mang, cong ty co duoc ep lam viec khong?",
    "Còn chờ công ty trả lương thì sao?",
    "Nhân viên tăng ca sinh nhật có được trả thêm lương không?",
    "Trợ cấp mất việc làm được tính như thế nào và tối thiểu bằng mấy tháng lương?",
    "Người lao động bị tạm giữ hoặc tạm giam theo pháp luật tố tụng hình sự thì HĐLĐ xử lý thế nào?",
    "Người lao động bị kết án tù mà không được hưởng án treo và không thuộc trường hợp được trả tự do theo luật tố tụng hình sự thì HĐLĐ có thể chấm dứt không?",
    "Người lao động có hành vi trộm cắp, tham ô tài sản tại nơi làm việc thì người sử dụng lao động có quyền áp dụng hình thức kỷ luật nào cao nhất?",
    "Anh Minh có hành vi trộm cắp, tham ô tài sản tại nơi làm việc thì người sử dụng lao động có quyền áp dụng hình thức kỷ luật nào cao nhất?",
    "Người lao động bị phạt tù thì hợp đồng lao động có chấm dứt không?",
    "Làm việc từ 22-6 giờ có được tính tiền lương ban đêm không?",
    "Người lao động nghỉ 3-5 ngày thì có bị sa thải không?",
])
def test_labor_questions_are_not_rejected_by_colliding_words(question, has_history):
    assert not is_out_of_scope_query(question, has_history=has_history)
    assert answer_out_of_scope_fast(question, has_history=has_history) is None
    assert QueryRouter().route(question, has_history=has_history).strategy == "hybrid"


def test_safety_and_bonus_question_routes_to_both_law_domains():
    decision = QueryRouter().route(SAFETY_AND_BONUS_QUESTION)
    assert decision.domain == "CROSS_DOMAIN"
    assert set(decision.target_domains) == {"OCCUPATIONAL_SAFETY", "CORE_LABOR"}


def test_followup_keeps_diacritics_when_checking_off_topic_words():
    question = "Vậy còn chờ thêm thì sao?"
    assert is_contextual_followup(question, has_history=True)
    assert answer_out_of_scope_fast(question, has_history=True) is None


@pytest.mark.parametrize("has_history", [False, True])
@pytest.mark.parametrize("question", [
    "Còn lô đề thì sao?",
    "Con lo de thi sao?",
    "Còn lô de thì sao?",
    "Còn lo đề thì sao?",
    unicodedata.normalize("NFD", "CÒN LÔ ĐỀ THÌ SAO?"),
    "Công ty kinh doanh lô đề thế nào?",
    "Lo de de doa cong ty nhu the nao?",
    "Lo de doanh nghiep nao to chuc?",
    "Còn con chó thì sao?",
    "Con ca si thi sao?",
    "Dự báo thời tiết hôm nay thế nào?",
    "Viet code python giai phuong trinh",
    "Người lao động trộm cắp tài sản thì bị phạt tù bao nhiêu năm?",
    "Tôi có HĐLĐ, trộm cắp bị phạt tù bao lâu?",
    "Thủ tục tố tụng hình sự như thế nào?",
    "1 + 1 bằng mấy?",
])
def test_explicit_off_topic_questions_still_rejected(question, has_history):
    assert is_out_of_scope_query(question, has_history=has_history)
    assert not looks_like_followup(question, has_history=has_history)
    assert QueryRouter().route(question, has_history=has_history).strategy == "out_of_scope"
    reply = answer_out_of_scope_fast(question, has_history=has_history)
    assert reply is not None and reply["out_of_scope"] is True
