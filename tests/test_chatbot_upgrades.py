# -*- coding: utf-8 -*-
"""Tests for follow-up rewriting, warm-up, feedback logging and regenerate support."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from rag.followup_rewriter import (
    FollowupRewriter,
    looks_like_followup,
    validate_standalone,
)


class _FakeLLM:
    def __init__(self, content):
        self.content = content
        self.calls = []

    def invoke(self, messages):
        self.calls.append(messages)
        if isinstance(self.content, Exception):
            raise self.content
        return SimpleNamespace(content=self.content)


class _FakeManager:
    def __init__(self, content):
        self.llm = _FakeLLM(content)
        self.aux_kwargs = None

    def get_aux_llm(self, json_schema=None, num_predict=160):
        self.aux_kwargs = {"json_schema": json_schema, "num_predict": num_predict}
        return self.llm


def _history():
    return [SimpleNamespace(
        user_query="Lương tối thiểu vùng I năm 2026 là bao nhiêu?",
        assistant_response="Mức lương tối thiểu tháng vùng I là 5.310.000 đồng/tháng.",
    )]


# --- follow-up detection ----------------------------------------------------

def test_followup_detection_requires_history():
    assert not looks_like_followup("Còn vùng III thì sao?", has_history=False)
    assert looks_like_followup("Còn vùng III thì sao?", has_history=True)


def test_followup_detection_markers_on_longer_turns():
    q = "Nếu trường hợp đó công ty vẫn không trả lương thì tôi có được nghỉ ngang không"
    assert looks_like_followup(q, has_history=True)
    standalone = (
        "Người lao động làm việc theo hợp đồng xác định thời hạn hai năm muốn đơn phương "
        "chấm dứt hợp đồng lao động phải báo trước bao nhiêu ngày theo Bộ luật Lao động"
    )
    assert not looks_like_followup(standalone, has_history=True)


# --- validation -------------------------------------------------------------

def test_validation_rejects_invented_numbers():
    hist = "Lương tối thiểu vùng I là 5.310.000 đồng"
    assert validate_standalone("Lương tối thiểu vùng III theo Điều 90 là bao nhiêu?", "Còn vùng III?", hist) is None
    ok = validate_standalone("Lương tối thiểu vùng III năm 2026 là bao nhiêu?", "Còn vùng III năm 2026?", hist)
    assert ok == "Lương tối thiểu vùng III năm 2026 là bao nhiêu?"


def test_validation_rejects_unchanged_empty_and_non_string():
    assert validate_standalone("Còn vùng III thì sao?", "Còn vùng III thì sao?", "") is None
    assert validate_standalone("", "x", "") is None
    assert validate_standalone(None, "x", "") is None
    assert validate_standalone("a" * 500, "x", "") is None


# --- rewriter ---------------------------------------------------------------

def test_rewriter_returns_standalone_question():
    mgr = _FakeManager(json.dumps(
        {"standalone_question": "Lương tối thiểu vùng III năm 2026 là bao nhiêu?"}, ensure_ascii=False,
    ))
    rw = FollowupRewriter(llm_manager=mgr, enabled=True)
    result = rw.rewrite("Còn vùng III thì sao?", _history())
    assert result is not None
    assert result.standalone == "Lương tối thiểu vùng III năm 2026 là bao nhiêu?"
    # Uses the schema-constrained aux model, not the legal-answer model.
    assert mgr.aux_kwargs["json_schema"]["required"] == ["standalone_question"]
    prompt = mgr.llm.calls[0][1].content
    assert "Lương tối thiểu vùng I" in prompt and "Còn vùng III" in prompt


@pytest.mark.parametrize("content", [
    RuntimeError("ollama down"),
    "not json at all",
    json.dumps({"answer": "legal schema output"}),
    SimpleNamespace(),  # mocks returning non-string content
])
def test_rewriter_falls_back_silently(content):
    rw = FollowupRewriter(llm_manager=_FakeManager(content), enabled=True)
    assert rw.rewrite("Còn vùng III thì sao?", _history()) is None


def test_rewriter_disabled_or_no_history_never_calls_llm():
    mgr = _FakeManager(json.dumps({"standalone_question": "X Y Z"}))
    assert FollowupRewriter(llm_manager=mgr, enabled=False).rewrite("Còn vùng III thì sao?", _history()) is None
    assert FollowupRewriter(llm_manager=mgr, enabled=True).rewrite("Còn vùng III thì sao?", []) is None
    assert mgr.llm.calls == []


def test_chain_resolve_followup_uses_rewrite_and_keeps_rule_hints():
    from rag.chain import ConversationMemory, VietLaborRAGChain

    chain = object.__new__(VietLaborRAGChain)
    chain.memory = ConversationMemory(max_turns=3)
    chain.memory.add_turn(
        user_query="Tôi đang thử việc, công ty trả lương thử việc 70% có đúng không?",
        assistant_response="Tiền lương thử việc ít nhất bằng 85% mức lương của công việc đó.",
    )
    chain.followup_rewriter = FollowupRewriter(
        llm_manager=_FakeManager(json.dumps(
            {"standalone_question": "Công ty trả lương thử việc 70% thì tôi có được đòi lại phần chênh lệch không?"},
            ensure_ascii=False,
        )),
        enabled=True,
    )
    stages = []
    resolved, standalone = chain._resolve_followup("Vậy tôi đòi lại được không?", lambda k, l: stages.append(k))
    assert standalone.startswith("Công ty trả lương thử việc 70%")
    assert resolved.startswith(standalone)
    assert stages == ["analyze"]

    # Fallback path: identical to the legacy rule-based resolution.
    chain.followup_rewriter = FollowupRewriter(llm_manager=_FakeManager(RuntimeError("x")), enabled=True)
    resolved2, standalone2 = chain._resolve_followup("Vậy tôi đòi lại được không?")
    assert standalone2 is None
    assert resolved2 == chain.memory.resolve_context("Vậy tôi đòi lại được không?")


def test_query_rewriter_uses_schema_free_aux_llm():
    from rag.query_rewriter import AdaptiveQueryRewriter

    mgr = _FakeManager("đơn phương chấm dứt hợp đồng lao động trái pháp luật")
    out = AdaptiveQueryRewriter(llm_manager=mgr).rewrite("bị đuổi ngang", use_llm=True)
    assert out == "đơn phương chấm dứt hợp đồng lao động trái pháp luật"
    assert mgr.aux_kwargs["json_schema"] is None


# --- warm-up ----------------------------------------------------------------

def test_background_warmup_runs_once():
    from app import warmup

    warmup._reset_for_tests()
    calls = []

    class _Mgr:
        def warm_up(self):
            calls.append(1)
            return True

    t1 = warmup.start_background_warmup(manager_factory=_Mgr, enabled=True)
    t2 = warmup.start_background_warmup(manager_factory=_Mgr, enabled=True)
    assert t1 is t2
    t1.join(timeout=5)
    assert calls == [1]
    assert warmup.warmup_state() == {"started": True, "done": True, "ok": True}
    warmup._reset_for_tests()
    assert warmup.start_background_warmup(manager_factory=_Mgr, enabled=False) is None


def test_warmup_never_raises_when_ollama_offline():
    from models.local_llm import LocalLLMManager

    assert LocalLLMManager(base_url="http://127.0.0.1:9").warm_up(timeout=1) is False


# --- feedback + regenerate ---------------------------------------------------

def test_feedback_record_roundtrip(tmp_path: Path):
    from app.feedback import build_feedback_record, load_feedback, record_feedback

    path = tmp_path / "fb.jsonl"
    rec = build_feedback_record(
        "down", "Thử việc tối đa bao lâu?", "Không quá 180 ngày…", conv_id="c1", msg_id="m1",
        structured_data={"citations": [{"chunk_id": "BLLD_2019#d25"}], "retrieval_method": "BM25"},
    )
    assert record_feedback(rec, path=path)
    rows = load_feedback(path)
    assert rows[0]["rating"] == "down"
    assert rows[0]["citations"] == ["BLLD_2019#d25"]
    with pytest.raises(ValueError):
        build_feedback_record("meh", "q", "a")


def test_session_pop_last_exchange_and_feedback(tmp_path: Path):
    from ui.utils.session import SessionManager

    mgr = SessionManager(tmp_path / "history.json")
    conv = mgr.create_conversation()
    mgr.append_message(conv["id"], "user", "Câu 1")
    mgr.append_message(conv["id"], "assistant", "Trả lời 1")
    mgr.append_message(conv["id"], "user", "Câu 2")
    mgr.append_message(conv["id"], "assistant", "Trả lời 2")

    msgs = mgr.get_conversation(conv["id"])["messages"]
    assert mgr.set_message_feedback(conv["id"], msgs[1]["id"], "up")
    assert not mgr.set_message_feedback(conv["id"], msgs[0]["id"], "up")  # user msg

    assert mgr.pop_last_exchange(conv["id"]) == "Câu 2"
    msgs = mgr.get_conversation(conv["id"])["messages"]
    assert [m["content"] for m in msgs] == ["Câu 1", "Trả lời 1"]
    assert msgs[1]["feedback"] == "up"

    mgr.append_message(conv["id"], "user", "Câu chưa trả lời")
    assert mgr.pop_last_exchange(conv["id"]) is None
