# -*- coding: utf-8 -*-
"""Facts given early in a consultation must still reach the prompt after the
3-turn history window has rolled over."""
from rag.chain import ConversationMemory


def test_contract_term_survives_history_window():
    memory = ConversationMemory(max_turns=3)
    memory.add_turn("Tôi ký hợp đồng 24 tháng với công ty may", "Đã ghi nhận.")
    for i in range(4):
        memory.add_turn(f"Câu hỏi phụ số {i} về tiền lương", "Trả lời.")

    assert len(memory.history) == 3
    assert all("24 tháng" not in t.user_query for t in memory.history)

    summary = memory.get_history_summary()
    assert "Thời hạn hợp đồng: 24 tháng" in summary


def test_internal_codes_are_not_shown_to_llm():
    memory = ConversationMemory()
    memory.add_turn("Em là kỹ sư, công ty bảo thử việc trước khi ký", "OK")
    summary = memory.get_history_summary()
    assert "Trình độ / chức danh: cao đẳng trở lên" in summary
    assert "PROBATION" not in summary
    assert "IN_PROBATION" not in summary


def test_empty_memory_summary_unchanged():
    assert ConversationMemory().get_history_summary() == "Không có lịch sử trước đó."
