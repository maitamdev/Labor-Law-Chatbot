# -*- coding: utf-8 -*-
"""
VietLabor AI - Answer feedback log (👍 / 👎).

Appends one JSON object per line to storage/feedback.jsonl so poorly rated
answers can be reviewed and turned into regression/evaluation cases later.
Stays 100% local; never raises into the UI.
"""
from __future__ import annotations

import datetime
import json
import logging
import threading
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)

_WRITE_LOCK = threading.Lock()
VALID_RATINGS = {"up", "down"}
MAX_TEXT_CHARS = 4000


def _citation_labels(citations: Optional[Iterable[Dict[str, Any]]]) -> List[str]:
    labels: List[str] = []
    for c in citations or []:
        if not isinstance(c, dict):
            continue
        label = c.get("chunk_id") or c.get("label") or c.get("article")
        if label:
            labels.append(str(label))
    return labels


def build_feedback_record(
    rating: str,
    question: str,
    answer: str,
    conv_id: str = "",
    msg_id: str = "",
    structured_data: Optional[Dict[str, Any]] = None,
    comment: str = "",
) -> Dict[str, Any]:
    if rating not in VALID_RATINGS:
        raise ValueError("rating must be 'up' or 'down'")
    data = structured_data or {}
    return {
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "rating": rating,
        "conv_id": conv_id,
        "msg_id": msg_id,
        "question": (question or "")[:MAX_TEXT_CHARS],
        "answer": (answer or "")[:MAX_TEXT_CHARS],
        "citations": _citation_labels(data.get("citations")),
        "retrieval_method": data.get("retrieval_method"),
        "comment": (comment or "")[:1000],
    }


def record_feedback(record: Dict[str, Any], path: Optional[Path] = None) -> bool:
    """Appends a feedback record. Returns False (and logs) on any I/O error."""
    if path is None:
        from config.settings import FEEDBACK_LOG_PATH
        path = FEEDBACK_LOG_PATH
    try:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, ensure_ascii=False)
        with _WRITE_LOCK, path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        return True
    except Exception as exc:
        logger.warning("Could not write feedback: %s", exc)
        return False


def load_feedback(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Reads all feedback records (skips malformed lines)."""
    if path is None:
        from config.settings import FEEDBACK_LOG_PATH
        path = FEEDBACK_LOG_PATH
    path = Path(path)
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(raw))
        except ValueError:
            continue
    return rows
