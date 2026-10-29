# -*- coding: utf-8 -*-
"""Fast, local responses for greetings and other non-legal small talk."""
from __future__ import annotations

import unicodedata
from typing import Any, Dict, Optional

from rag.conversational import detect_smalltalk
from rag.query_router import is_out_of_scope_query

_FAST_OOS_MESSAGE = (
    "Câu hỏi của bạn không thuộc phạm vi tra cứu pháp luật lao động Việt Nam "
    "(ví dụ: hôn nhân gia đình, đất đai, hình sự, giao thông, thuế doanh nghiệp, kiện đòi nợ, thủ tục doanh nghiệp, sở hữu trí tuệ, hoặc các chủ đề đời sống khác). "
    "VietLabor AI chỉ hỗ trợ tra cứu các quy định về quan hệ lao động, tiền lương, "
    "hợp đồng, kỷ luật, bảo hiểm và thời giờ làm việc theo Bộ luật Lao động và các văn bản hướng dẫn thi hành."
)

_FAST_OOS_SUGGESTIONS = [
    "Thử việc tối đa bao nhiêu ngày?",
    "Thời hạn báo trước khi nghỉ việc",
    "Làm thêm ngày lễ được tính lương thế nào?",
    "Các hình thức xử lý kỷ luật lao động",
]


def answer_smalltalk(question: str, has_history: bool = False) -> Optional[Dict[str, Any]]:
    """Return a ready-made reply without importing or initializing the RAG stack."""
    reply = detect_smalltalk(unicodedata.normalize("NFC", question or ""), has_history=has_history)
    if reply is None:
        return None
    return {
        "answer": reply.answer,
        "raw_answer": reply.answer,
        "final_answer": reply.answer,
        "findings": [],
        "citations": [],
        "needs_clarification": False,
        "clarification_question": None,
        "clarification_options": [],
        "out_of_scope": False,
        "is_smalltalk": True,
        "smalltalk_intent": reply.intent,
        "suggested_followups": list(reply.suggestions),
        "latency_ms": 0.0,
        "locked_chunk_ids": [],
        "graph_expanded_chunk_ids": [],
        "retrieval_method": "None (Conversational fast-track)",
        "evidence_coverage": {},
        "unresolved_issue_ids": [],
        "is_fully_grounded": True,
    }


def answer_out_of_scope_fast(question: str, has_history: bool = False) -> Optional[Dict[str, Any]]:
    """Return an instant 0ms refusal for off-topic or non-labor queries without touching retrieval or LLM."""
    norm_q = unicodedata.normalize("NFC", question or "").strip()
    if not norm_q or not is_out_of_scope_query(norm_q, has_history=has_history):
        return None
    return {
        "answer": _FAST_OOS_MESSAGE,
        "raw_answer": _FAST_OOS_MESSAGE,
        "final_answer": _FAST_OOS_MESSAGE,
        "findings": [],
        "citations": [],
        "needs_clarification": False,
        "clarification_question": None,
        "clarification_options": [],
        "out_of_scope": True,
        "is_smalltalk": False,
        "suggested_followups": list(_FAST_OOS_SUGGESTIONS),
        "latency_ms": 0.0,
        "locked_chunk_ids": [],
        "graph_expanded_chunk_ids": [],
        "retrieval_method": "None (Out-of-scope Abstained)",
        "evidence_coverage": {},
        "unresolved_issue_ids": [],
        "is_fully_grounded": True,
    }
