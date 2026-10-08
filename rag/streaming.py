# -*- coding: utf-8 -*-
"""
VietLabor AI - Streaming helpers.

The local model answers in a strict JSON schema ({"answer": "...", "findings": [...]})
so that the citation guard can validate it. To still give the user real-time
feedback, we read the *partial* JSON while tokens arrive and surface the
growing value of the "answer" field as a live draft. The validated answer
replaces the draft once generation finishes.
"""
from __future__ import annotations

import re
from typing import Optional

_ESCAPES = {'"': '"', "\\": "\\", "/": "/", "b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t"}
_EVIDENCE_TOKEN = re.compile(r"\[\s*E\d+\s*\]|\(\s*E\d+\s*\)")


def extract_partial_json_string(buffer: str, key: str = "answer") -> Optional[str]:
    """Returns the (possibly unfinished) string value of `key` in a partial JSON text.

    Returns None if the key has not appeared yet. Handles escape sequences and
    stops cleanly at a truncated escape at the end of the buffer.
    """
    match = re.search(r'"%s"\s*:\s*"' % re.escape(key), buffer)
    if not match:
        return None
    out = []
    i = match.end()
    n = len(buffer)
    while i < n:
        ch = buffer[i]
        if ch == '"':
            break
        if ch == "\\":
            if i + 1 >= n:
                break  # truncated escape: wait for more tokens
            nxt = buffer[i + 1]
            if nxt == "u":
                hex_part = buffer[i + 2:i + 6]
                if len(hex_part) < 4:
                    break
                try:
                    out.append(chr(int(hex_part, 16)))
                except ValueError:
                    pass
                i += 6
                continue
            out.append(_ESCAPES.get(nxt, nxt))
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def clean_draft_text(text: str) -> str:
    """Removes internal evidence tokens ([E1], (E2)) and cleans dangling punctuation from a live draft."""
    if not text:
        return ""
    cleaned = _EVIDENCE_TOKEN.sub("", text)
    # Clean up internal backend artifacts from draft
    cleaned = re.sub(r"(?mi)^#*\s*issue_\d+\s*\n*", "", cleaned)
    cleaned = re.sub(r"(?mi)^(?:Finding|Kết luận)\s*:\s*", "", cleaned)
    # Clean up dangling connectors caused by stripped tokens like "đòi lại và ,"
    cleaned = re.sub(r"\s+và\s*,\s*", ", ", cleaned)
    cleaned = re.sub(r"\s+và\s*\.\s*", ". ", cleaned)
    cleaned = re.sub(r"\s*,\s*,+", ",", cleaned)
    return re.sub(r"[ \t]{2,}", " ", cleaned).strip()
