# -*- coding: utf-8 -*-
"""
VietLabor AI - Answer cache for repeated first-turn questions.

Design choices (legal domain):
* Exact match after normalization, NOT embedding similarity. "Hợp đồng 12 tháng"
  and "hợp đồng 36 tháng" embed almost identically but have different notice
  periods, so a semantic cache would return confidently wrong answers.
* Only first-turn questions (empty conversation memory) are cached; follow-ups
  depend on facts from earlier turns.
* Only fully grounded, final answers are stored (no clarification requests,
  no partially blocked multi-issue answers).
* In-process LRU with TTL: restarting the app (e.g. after re-indexing the
  corpus) always starts with an empty cache.
"""
from __future__ import annotations

import copy
import hashlib
import os
import re
import threading
import time
import unicodedata
from collections import OrderedDict
from typing import Any, Dict, Optional

MAX_ENTRIES = 256
TTL_SECONDS = 6 * 3600

_lock = threading.Lock()
_store: "OrderedDict[str, tuple[float, Dict[str, Any]]]" = OrderedDict()


def enabled() -> bool:
    return os.environ.get("VIETLABOR_ANSWER_CACHE", "1").strip().lower() not in {"0", "false", "no", "off"}


def normalize_question(question: str) -> str:
    text = unicodedata.normalize("NFC", question or "").lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text.rstrip(" ?.!…")


def make_key(question: str) -> str:
    return hashlib.sha256(normalize_question(question).encode("utf-8")).hexdigest()


def is_cacheable(payload: Dict[str, Any]) -> bool:
    return bool(
        payload.get("answer")
        and not payload.get("is_smalltalk")
        and not payload.get("needs_clarification")
        and not payload.get("unresolved_issue_ids")
        and payload.get("is_fully_grounded", False)
    )


def get(key: str) -> Optional[Dict[str, Any]]:
    now = time.monotonic()
    with _lock:
        item = _store.get(key)
        if item is None:
            return None
        stored_at, payload = item
        if now - stored_at > TTL_SECONDS:
            del _store[key]
            return None
        _store.move_to_end(key)
        return copy.deepcopy(payload)


def put(key: str, payload: Dict[str, Any]) -> None:
    with _lock:
        _store[key] = (time.monotonic(), copy.deepcopy(payload))
        _store.move_to_end(key)
        while len(_store) > MAX_ENTRIES:
            _store.popitem(last=False)


def evict_question(question: str) -> None:
    """Drops a cached answer (e.g. after a thumbs-down rating)."""
    with _lock:
        _store.pop(make_key(question), None)


def clear() -> None:
    with _lock:
        _store.clear()


def size() -> int:
    with _lock:
        return len(_store)
