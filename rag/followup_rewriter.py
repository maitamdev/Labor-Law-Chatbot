# -*- coding: utf-8 -*-
"""
VietLabor AI - LLM Follow-up Question Rewriter

Turns context-dependent follow-ups ("Còn vùng III thì sao?", "Trường hợp đó
có được bồi thường không?") into standalone questions before retrieval, using a
short schema-constrained call to the local model.

Safety properties:
- Only runs when there is conversation history AND the turn looks like a follow-up.
- Output is validated: non-empty, bounded length, and it may not introduce any
  number (article, amount, date...) that does not appear in the history or the
  current question, so the rewrite cannot smuggle in invented legal facts.
- Any failure (Ollama offline, bad JSON, mocks in tests) returns None and the
  caller falls back to the rule-based ConversationMemory.resolve_context().
"""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Optional, Sequence

from langchain_core.messages import HumanMessage, SystemMessage

from rag.conversational import fold_vietnamese

logger = logging.getLogger(__name__)

FOLLOWUP_JSON_SCHEMA = {
    "type": "object",
    "properties": {"standalone_question": {"type": "string"}},
    "required": ["standalone_question"],
}

# Folded (accent-free) markers that signal the turn depends on earlier context.
_LEADING_MARKERS = (
    "con ", "the con", "vay con", "vay thi", "vay ", "neu vay", "nhung ", "the ",
    "the thi", "the neu", "con neu", "con truong hop", "ngoai ra",
)
_INLINE_MARKERS = (
    "thi sao", "truong hop do", "truong hop nay", "truong hop tren", "nhu vay",
    "nhu tren", "cai do", "cai nay", "khi do", "luc do", "vua roi", "o tren",
    "dieu do", "dieu nay", "van de do", "van de nay", "muc do", "khoan do",
    "khoan tien do", "so tien do", "hop dong do", "ben do", "cong ty do",
)

MAX_SHORT_FOLLOWUP_WORDS = 8
MAX_STANDALONE_WORDS = 40
MAX_STANDALONE_CHARS = 400

SYSTEM_PROMPT = (
    "Bạn là bộ phận tiền xử lý của trợ lý pháp luật lao động Việt Nam. "
    "Nhiệm vụ DUY NHẤT: viết lại câu hỏi mới nhất của người dùng thành MỘT câu hỏi "
    "độc lập, đầy đủ chủ ngữ và đối tượng, hiểu được mà không cần đọc hội thoại trước.\n"
    "Quy tắc:\n"
    "- KHÔNG trả lời câu hỏi.\n"
    "- KHÔNG thêm số Điều, số tiền, mốc thời gian hay sự kiện không có trong hội thoại.\n"
    "- Giữ nguyên ý định và các chi tiết người dùng đã nêu.\n"
    "- Nếu câu hỏi đã độc lập thì trả lại nguyên văn.\n"
    "Trả về JSON: {\"standalone_question\": \"...\"}"
)

_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)*")


@dataclass
class FollowupRewrite:
    """Outcome of a successful follow-up rewrite."""
    original: str
    standalone: str
    latency_ms: float


def looks_like_followup(query: str, has_history: bool) -> bool:
    """Cheap heuristic deciding whether an LLM rewrite is worth the latency."""
    if not has_history:
        return False
    folded = fold_vietnamese(query).strip()
    if not folded:
        return False
    words = folded.split()
    if len(words) > MAX_STANDALONE_WORDS:
        return False  # long, detailed turns are already self-contained
    if len(words) <= MAX_SHORT_FOLLOWUP_WORDS:
        return True
    if any(folded.startswith(marker) for marker in _LEADING_MARKERS):
        return True
    return any(marker in folded for marker in _INLINE_MARKERS)


def _numbers(text: str) -> set[str]:
    return {re.sub(r"[.,]", "", n) for n in _NUMBER_RE.findall(text or "")}


def validate_standalone(candidate: Any, query: str, history_text: str) -> Optional[str]:
    """Returns a cleaned standalone question, or None if it is unsafe/unusable."""
    if not isinstance(candidate, str):
        return None
    text = " ".join(candidate.split()).strip().strip("\"'`").strip()
    if len(text) < 4 or len(text) > MAX_STANDALONE_CHARS:
        return None
    if len(text.split()) > MAX_STANDALONE_WORDS + 20:
        return None
    # Never accept numbers that neither the user nor the conversation mentioned.
    if not _numbers(text) <= (_numbers(query) | _numbers(history_text)):
        return None
    if fold_vietnamese(text) == fold_vietnamese(query):
        return None  # unchanged → let rule-based resolution handle it
    return text


def _parse_content(content: Any) -> Optional[str]:
    if not isinstance(content, str) or not content.strip():
        return None
    raw = content.strip()
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return None
        try:
            data = json.loads(match.group(0))
        except (ValueError, TypeError):
            return None
    if not isinstance(data, dict):
        return None
    value = data.get("standalone_question")
    return value if isinstance(value, str) else None


class FollowupRewriter:
    """LLM-backed follow-up rewriter with strict validation and silent fallback."""

    def __init__(
        self,
        llm_manager: Optional[Any] = None,
        enabled: bool = True,
        max_history_turns: int = 2,
        answer_preview_chars: int = 280,
        num_predict: int = 120,
    ):
        self.llm_manager = llm_manager
        self.enabled = enabled
        self.max_history_turns = max_history_turns
        self.answer_preview_chars = answer_preview_chars
        self.num_predict = num_predict

    def _format_history(self, history: Sequence[Any]) -> str:
        lines = []
        for turn in list(history)[-self.max_history_turns:]:
            user = str(getattr(turn, "user_query", "") or "").strip()
            answer = " ".join(str(getattr(turn, "assistant_response", "") or "").split())
            if len(answer) > self.answer_preview_chars:
                answer = answer[: self.answer_preview_chars] + "…"
            if user:
                lines.append(f"Người dùng: {user}")
            if answer:
                lines.append(f"Trợ lý: {answer}")
        return "\n".join(lines)

    def rewrite(self, query: str, history: Sequence[Any]) -> Optional[FollowupRewrite]:
        """Returns a validated standalone question, or None to use the fallback."""
        if not self.enabled or self.llm_manager is None:
            return None
        if not looks_like_followup(query, has_history=bool(history)):
            return None

        history_text = self._format_history(history)
        if not history_text:
            return None

        t0 = time.perf_counter()
        try:
            get_aux = getattr(self.llm_manager, "get_aux_llm", None)
            if not callable(get_aux):
                return None
            llm = get_aux(json_schema=FOLLOWUP_JSON_SCHEMA, num_predict=self.num_predict)
            response = llm.invoke([
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=(
                    f"Hội thoại trước:\n{history_text}\n\n"
                    f"Câu hỏi mới nhất: {query}"
                )),
            ])
            candidate = _parse_content(getattr(response, "content", None))
        except Exception as exc:  # Ollama offline, timeouts, mocks...
            logger.info("Follow-up rewrite skipped: %s", exc)
            return None

        standalone = validate_standalone(candidate, query, history_text)
        if standalone is None:
            return None
        latency_ms = (time.perf_counter() - t0) * 1000
        logger.info("Follow-up rewrite (%.0f ms): '%s' -> '%s'", latency_ms, query, standalone)
        return FollowupRewrite(original=query, standalone=standalone, latency_ms=latency_ms)
