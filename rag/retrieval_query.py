# -*- coding: utf-8 -*-
"""Deterministic query preparation for lexical + dense retrieval (not for LLM prompts)."""
from __future__ import annotations

from rag.query_expander import QueryExpander
from rag.query_processor import normalize_colloquial_vietnamese, normalize_query
from rag.query_rewriter import AdaptiveQueryRewriter

_expander = QueryExpander()
_rewriter = AdaptiveQueryRewriter(llm_manager=None)


def prepare_retrieval_query(query: str, *, use_expander: bool = True) -> str:
    q = (query or "").strip()
    if not q:
        return ""
    q = normalize_colloquial_vietnamese(normalize_query(q)) or q
    q = _rewriter.rewrite_deterministic(q)
    if use_expander:
        q = _expander.expand(q)
    return q.strip()
