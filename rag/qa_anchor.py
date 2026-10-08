"""High-confidence question-pattern hints backed by statutory text.

The 1,000 QA answers are intentionally *not* exposed to the model. A close
question match may only nominate cited legal chunks; evidence selection and
citation validation still decide what can be used in the final answer.
"""
from __future__ import annotations

import difflib
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

from config.settings import PRODUCTION_CORPUS_PATH

DEFAULT_ANCHORS = Path(__file__).resolve().parents[1] / "data/processed/qa_question_anchors.jsonl"


def _normal(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text).lower()).strip()


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"\w+", _normal(text)))


class QuestionLawAnchorIndex:
    def __init__(self, anchor_path: Path = DEFAULT_ANCHORS, corpus_path: Path = PRODUCTION_CORPUS_PATH):
        self.anchor_path = Path(anchor_path)
        self.corpus_path = Path(corpus_path)
        self._questions: list[tuple[dict[str, Any], str, set[str]]] | None = None
        self._by_article: dict[tuple[str, str], list[dict[str, Any]]] | None = None
        self._by_id: dict[str, dict[str, Any]] | None = None

    def _load(self) -> None:
        if self._questions is not None:
            return
        if not self.anchor_path.is_file() or not self.corpus_path.is_file():
            self._questions, self._by_article, self._by_id = [], {}, {}
            return
        anchors = [json.loads(line) for line in self.anchor_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        self._questions = [(row, _normal(row["question"]), _tokens(row["question"])) for row in anchors]
        by_article: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        by_id: dict[str, dict[str, Any]] = {}
        for line in self.corpus_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            chunk = json.loads(line)
            by_id[chunk["chunk_id"]] = chunk
            if chunk.get("article_number") and chunk.get("doc_id") != "ND_12_2022":
                by_article[(chunk["doc_id"], str(chunk["article_number"]))].append(chunk)
        self._by_article = by_article
        self._by_id = by_id

    def matching_question(self, query: str) -> dict[str, Any] | None:
        self._load()
        if not self._questions:
            return None
        q_text, q_tokens = _normal(query), _tokens(query)
        if len(q_tokens) < 4:
            return None
        shortlist = []
        for row, text, tokens in self._questions:
            overlap = len(q_tokens & tokens)
            containment = overlap / max(1, len(tokens))
            if overlap >= 4 and containment >= 0.6:
                shortlist.append((containment, row, text))
        shortlist.sort(key=lambda item: item[0], reverse=True)
        best: tuple[float, dict[str, Any]] | None = None
        for containment, row, text in shortlist[:20]:
            similarity = difflib.SequenceMatcher(None, q_text, text).ratio()
            if similarity >= 0.86 or (similarity >= 0.70 and containment >= 0.92):
                score = similarity + 0.1 * containment
                if best is None or score > best[0]:
                    best = (score, row)
        return best[1] if best else None

    def nominate(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        row = self.matching_question(query)
        if not row:
            return []
        self._load()
        assert self._by_article is not None
        assert self._by_id is not None
        q_tokens = _tokens(query)
        nominated = [self._by_id[chunk_id] for chunk_id in row.get("reviewed_chunk_ids", []) if chunk_id in self._by_id]
        for ref in row.get("law_anchors", []):
            key = (ref["doc_id"], str(ref["article_number"]))
            chunks = self._by_article.get(key, [])
            ranked = sorted(
                chunks,
                key=lambda chunk: len(q_tokens & _tokens((chunk.get("article_title") or "") + " " + (chunk.get("content") or ""))),
                reverse=True,
            )
            nominated.extend(ranked[:2])
        seen = set()
        results = []
        for chunk in nominated:
            if chunk["chunk_id"] in seen:
                continue
            seen.add(chunk["chunk_id"])
            results.append({
                "chunk_id": chunk["chunk_id"],
                "score": 1.0,
                "content": chunk["content"],
                "retrieval_text": chunk.get("retrieval_text") or chunk["content"],
                "metadata": chunk,
            })
            if len(results) >= limit:
                break
        return results

    def lookup_chunk_ids(self, chunk_ids: list[str] | tuple[str, ...]) -> list[dict[str, Any]]:
        """Load exact statutory chunks for a verified legal-concept rule."""
        self._load()
        assert self._by_id is not None
        return [
            {
                "chunk_id": chunk_id,
                "score": 1.0,
                "content": self._by_id[chunk_id]["content"],
                "retrieval_text": self._by_id[chunk_id].get("retrieval_text") or self._by_id[chunk_id]["content"],
                "metadata": self._by_id[chunk_id],
            }
            for chunk_id in chunk_ids if chunk_id in self._by_id
        ]

    def enrich(self, query: str, candidates: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
        nominated = self.nominate(query, limit=limit)
        if not nominated:
            return candidates
        seen = {item["chunk_id"] for item in nominated}
        return nominated + [item for item in candidates if item.get("chunk_id") not in seen]
