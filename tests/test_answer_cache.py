# -*- coding: utf-8 -*-
"""Answer cache: exact first-turn matches only, grounded answers only."""
from __future__ import annotations

from typing import Any, Dict, List

import pytest

from app import answer_cache
from app.chat_service import ChatService


class _FakeMemory:
    def __init__(self) -> None:
        self.history: List[Any] = []

    def add_turn(self, user_query: str, assistant_response: str) -> None:
        self.history.append((user_query, assistant_response))

    def clear(self) -> None:
        self.history.clear()


class _CountingService(ChatService):
    """ChatService whose RAG call is replaced by a counter."""

    def __init__(self, payload: Dict[str, Any]) -> None:
        self.chain = type("FakeChain", (), {"memory": _FakeMemory()})()
        self.calls = 0
        self._payload = payload

    def _ask_uncached(self, norm_q, update_memory, on_stage, on_token):
        self.calls += 1
        if update_memory:
            self.chain.memory.add_turn(norm_q, self._payload["answer"])
        return dict(self._payload)


GROUNDED = {"answer": "Tối đa 60 ngày.", "final_answer": "Tối đa 60 ngày.", "is_fully_grounded": True,
            "needs_clarification": False, "unresolved_issue_ids": [], "citations": [{"chunk_id": "d25"}]}


@pytest.fixture(autouse=True)
def _enable_cache(monkeypatch):
    monkeypatch.setenv("VIETLABOR_ANSWER_CACHE", "1")
    answer_cache.clear()
    yield
    answer_cache.clear()


def test_repeated_first_turn_question_is_served_from_cache():
    first = _CountingService(GROUNDED)
    first.ask("Thời gian thử việc tối đa là bao lâu?")
    second = _CountingService(GROUNDED)
    res = second.ask("  thời gian thử việc tối đa là bao lâu  ")
    assert second.calls == 0
    assert res["cache_hit"] is True
    assert res["answer"] == "Tối đa 60 ngày."
    # Memory is still updated so the next follow-up keeps context.
    assert len(second.chain.memory.history) == 1


def test_numbers_change_the_key():
    assert answer_cache.make_key("Hợp đồng 12 tháng báo trước bao lâu?") != answer_cache.make_key(
        "Hợp đồng 36 tháng báo trước bao lâu?"
    )


def test_follow_up_turns_bypass_cache():
    svc = _CountingService(GROUNDED)
    svc.ask("Tôi ký hợp đồng 24 tháng")
    svc.ask("Thời gian thử việc tối đa là bao lâu?")
    other = _CountingService(GROUNDED)
    other.ask("Thời gian thử việc tối đa là bao lâu?")
    assert other.calls == 1  # second-turn answer was never cached


@pytest.mark.parametrize("override", [
    {"needs_clarification": True},
    {"is_fully_grounded": False},
    {"unresolved_issue_ids": ["issue_2"]},
    {"is_smalltalk": True},
])
def test_non_final_answers_are_not_cached(override):
    _CountingService({**GROUNDED, **override}).ask("Câu hỏi X?")
    again = _CountingService(GROUNDED)
    again.ask("Câu hỏi X?")
    assert again.calls == 1


def test_cache_can_be_disabled(monkeypatch):
    monkeypatch.setenv("VIETLABOR_ANSWER_CACHE", "0")
    _CountingService(GROUNDED).ask("Câu hỏi Y?")
    again = _CountingService(GROUNDED)
    again.ask("Câu hỏi Y?")
    assert again.calls == 1


def test_cached_payload_is_isolated_from_caller_mutation():
    svc = _CountingService(GROUNDED)
    res = svc.ask("Câu hỏi Z?")
    res["answer"] = "bị sửa"
    assert _CountingService(GROUNDED).ask("Câu hỏi Z?")["answer"] == "Tối đa 60 ngày."


def test_regeneration_retires_old_answer_when_new_answer_is_not_grounded():
    _CountingService(GROUNDED).ask("Regenerate question", update_memory=False)
    replacement = _CountingService({**GROUNDED, "is_fully_grounded": False})
    replacement.ask("Regenerate question", update_memory=False, bypass_cache=True)
    final = _CountingService(GROUNDED)
    final.ask("Regenerate question")
    assert final.calls == 1
