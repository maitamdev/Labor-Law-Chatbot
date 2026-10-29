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

from config.settings import ANCHOR_HARD_LOCK_ENABLED, PRODUCTION_CORPUS_PATH
from rag.anchor_lock_policy import evaluate_anchor_hard_lock

DEFAULT_ANCHORS = Path(__file__).resolve().parents[1] / "data/processed/qa_question_anchors.jsonl"
CANTHO_SITUATIONS = Path(__file__).resolve().parents[1] / "data/processed/cantho_legal_situations.json"


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
        existing_norm = {_normal(row["question"]) for row in anchors if row.get("question")}
        for row in self._load_cantho_anchor_rows():
            if _normal(row.get("question", "")) not in existing_norm:
                anchors.append(row)
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

    @staticmethod
    def _load_cantho_anchor_rows() -> list[dict[str, Any]]:
        """Official PBGDPL Can Tho scenario questions (statutory anchors only, no answer text)."""
        if not CANTHO_SITUATIONS.is_file():
            return []
        rows: list[dict[str, Any]] = []
        for sit in json.loads(CANTHO_SITUATIONS.read_text(encoding="utf-8")):
            law_anchors: list[dict[str, str]] = []
            for art_label in sit.get("articles") or []:
                m = re.search(r"(\d+[a-z]?)", str(art_label), re.IGNORECASE)
                if m:
                    law_anchors.append({"doc_id": "VBHN_18_2026", "article_number": m.group(1)})
            if not law_anchors:
                continue
            rows.append(
                {
                    "id": f"cantho_sit_{int(sit['number']):03d}",
                    "question": sit["question"],
                    "law_anchors": law_anchors,
                    "reviewed_chunk_ids": [],
                    "source": "pbgdpl.cantho.gov.vn",
                }
            )
        return rows

    @staticmethod
    def _match_thresholds(query: str) -> tuple[float, float, float, int]:
        """Return (min_similarity, min_similarity_with_containment, min_containment, min_token_overlap)."""
        if len(_normal(query)) >= 120:
            return 0.78, 0.68, 0.55, 3
        return 0.86, 0.70, 0.60, 4

    def matching_question(self, query: str) -> dict[str, Any] | None:
        scored = self.matching_question_scored(query)
        return scored[0] if scored else None

    def ranked_question_matches(self, query: str, top_n: int = 3) -> list[tuple[dict[str, Any], float, float]]:
        """Return [(row, combined_score, sequence_similarity), ...] best first."""
        self._load()
        if not self._questions:
            return []
        q_text, q_tokens = _normal(query), _tokens(query)
        min_sim, min_sim_contain, min_contain, min_overlap = self._match_thresholds(query)
        if len(q_tokens) < min_overlap:
            return []
        shortlist: list[tuple[float, dict[str, Any], str]] = []
        for row, text, tokens in self._questions:
            overlap = len(q_tokens & tokens)
            containment = overlap / max(1, len(tokens))
            if overlap >= min_overlap and containment >= min_contain:
                shortlist.append((containment, row, text))
        shortlist.sort(key=lambda item: item[0], reverse=True)
        ranked: list[tuple[dict[str, Any], float, float]] = []
        for containment, row, text in shortlist[:25]:
            seq_sim = difflib.SequenceMatcher(None, q_text, text).ratio()
            if seq_sim >= min_sim or (seq_sim >= min_sim_contain and containment >= 0.85):
                score = seq_sim + 0.1 * containment
                ranked.append((row, score, seq_sim))
        ranked.sort(key=lambda item: item[1], reverse=True)
        return ranked[:top_n]

    def matching_question_scored(self, query: str) -> tuple[dict[str, Any], float] | None:
        ranked = self.ranked_question_matches(query, top_n=1)
        if not ranked:
            return None
        row, score, _seq = ranked[0]
        return row, score

    def chunks_for_confident_statutory_lock(
        self,
        query: str,
        limit: int = 6,
        retrieval_candidates: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Hard-lock only on high-precision pattern match + retrieval agreement."""
        if not ANCHOR_HARD_LOCK_ENABLED:
            return []
        ranked = self.ranked_question_matches(query, top_n=2)
        if not ranked:
            return []
        row, score, seq_sim = ranked[0]
        runner_up = None
        if len(ranked) > 1:
            q0 = _normal(row.get("question", ""))
            for row2, score2, _ in ranked[1:]:
                if _normal(row2.get("question", "")) != q0:
                    runner_up = score2
                    break
        decision = evaluate_anchor_hard_lock(
            query,
            row,
            score,
            seq_sim,
            runner_up,
            retrieval_candidates,
        )
        if not decision.allow_lock:
            return []
        chunks = self.nominate(query, limit=limit)
        if not chunks:
            return []
        anchor_arts = {str(a["article_number"]) for a in row.get("law_anchors", [])}
        chunk_arts = {
            str((c.get("metadata") or {}).get("article_number") or "")
            for c in chunks
        }
        if anchor_arts and not anchor_arts.intersection(chunk_arts):
            return []
        return chunks

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
            per_art = 3 if len(row.get("law_anchors", [])) > 2 else 2
            nominated.extend(ranked[:per_art])
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
