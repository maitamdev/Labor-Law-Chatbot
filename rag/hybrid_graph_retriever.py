# -*- coding: utf-8 -*-
"""
VietLabor AI - Hybrid GraphRAG Retriever (Model 3)
Unifies Dense Vector Search (ChromaDB), Sparse Lexical Search (BM25s),
and Knowledge Graph Traversal (Neo4j) into a single cohesive retrieval engine.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from graph.retriever import LegalGraphRetriever
from rag.bm25_retriever import BM25Retriever
from rag.dense_retriever import DenseRetriever
from rag.hybrid_retriever import HybridRetriever
from rag.reranker import CrossEncoderReranker

logger = logging.getLogger(__name__)


class HybridGraphRetriever(HybridRetriever):
    """Hybrid GraphRAG retriever combining:
    1. Lexical retrieval via BM25s (exact keywords, article numbers, fine sums).
    2. Dense retrieval via ChromaDB + BGE-M3 (semantic concepts).
    3. Graph retrieval via Neo4j (statutory bridges, multi-hop penalty and hierarchy tracing).
    4. Optional Cross-Encoder reranking.
    """

    def __init__(
        self,
        bm25_retriever: Optional[BM25Retriever] = None,
        dense_retriever: Optional[DenseRetriever] = None,
        graph_retriever: Optional[LegalGraphRetriever] = None,
        reranker: Optional[CrossEncoderReranker] = None,
        use_reranker: bool = False,
        rrf_k: int = 60,
        bm25_weight: float = 1.0,
        dense_weight: float = 1.0,
        graph_weight: float = 1.2,
        max_graph_chunks: int = 6,
        index_version: str = "v3",
    ):
        super().__init__(
            bm25_retriever=bm25_retriever,
            dense_retriever=dense_retriever,
            reranker=reranker,
            use_reranker=use_reranker,
            rrf_k=rrf_k,
            bm25_weight=bm25_weight,
            dense_weight=dense_weight,
            index_version=index_version,
        )
        self.graph_retriever = graph_retriever or LegalGraphRetriever()
        self.graph_weight = graph_weight
        self.max_graph_chunks = max_graph_chunks
        self.max_chunks_per_related_article = 3
        self.last_graph_expansion: int = 0

    @property
    def graph_available(self) -> bool:
        try:
            return bool(self.graph_retriever.is_available())
        except Exception:
            return False

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        candidate_multiplier: int = 4,
        expand_graph: bool = True,
    ) -> List[Dict[str, Any]]:
        """Executes Hybrid GraphRAG retrieval.

        1. BM25 + Dense candidates fused with RRF (identical to HybridRetriever).
        2. If Neo4j is reachable, the top hits seed a GUIDES/PENALIZES traversal;
           linked articles are loaded from the canonical corpus and added as
           candidates (tagged retrieval_source="graph"). Candidates that are
           also graph-linked get a score boost.
        3. Optional Cross-Encoder reranking.

        When Neo4j is offline the result is exactly the base hybrid result.
        """
        self.last_graph_expansion = 0
        base_candidates = super().retrieve(
            query=query, top_k=top_k, candidate_multiplier=candidate_multiplier,
        )
        if not expand_graph or not base_candidates or not self.graph_available:
            return base_candidates

        # Seeds: distinct (doc_id, article) among the top hits.
        seed_scores: Dict[tuple, float] = {}
        for cand in base_candidates[:8]:
            meta = cand.get("metadata") or {}
            doc_id = meta.get("doc_id")
            try:
                art = int(str(meta.get("article_number") or "").strip())
            except ValueError:
                continue
            if doc_id and (doc_id, art) not in seed_scores:
                seed_scores[(doc_id, art)] = float(cand.get("score") or 0.0)
        if not seed_scores:
            return base_candidates

        try:
            related = self.graph_retriever.expand_related_chunks(
                [{"doc_id": d, "number": n} for d, n in seed_scores],
                limit=self.max_graph_chunks * 8,
            )
        except Exception as exc:  # never let the graph break answering
            logger.warning("Graph expansion failed, using hybrid results only: %s", exc)
            return base_candidates

        by_id = {c["chunk_id"]: c for c in base_candidates}
        added: List[Dict[str, Any]] = []
        per_article: Dict[tuple, int] = {}
        for rec in related:
            cid = rec.get("chunk_id")
            if not cid:
                continue
            seed_key = (rec.get("seed_doc_id"), rec.get("seed_article"))
            seed_score = seed_scores.get(seed_key, 0.0)
            tag = {
                "graph_relation": rec.get("relation"),
                "graph_seed": f"{seed_key[0]} Điều {seed_key[1]}",
            }
            if cid in by_id:
                existing = by_id[cid]
                if not existing.get("has_graph_expansion"):
                    existing["score"] = float(existing.get("score") or 0.0) * self.graph_weight
                    existing.update(tag, has_graph_expansion=True)
                continue
            if len(added) >= self.max_graph_chunks:
                continue
            art_key = (rec.get("doc_id"), rec.get("article_number"))
            if per_article.get(art_key, 0) >= self.max_chunks_per_related_article:
                continue
            chunk = self.bm25_retriever.get_chunk(cid, score=seed_score * 0.9)
            if chunk is None:
                continue  # graph node not in the current canonical corpus
            status = str((chunk.get("metadata") or {}).get("status") or chunk.get("status") or "").upper()
            if status == "REPEALED":
                continue  # never inject repealed provisions via the graph
            chunk.update(tag, retrieval_source="graph", has_graph_expansion=True)
            per_article[art_key] = per_article.get(art_key, 0) + 1
            by_id[cid] = chunk
            added.append(chunk)

        self.last_graph_expansion = len(added)
        merged = sorted(by_id.values(), key=lambda x: float(x.get("score") or 0.0), reverse=True)

        if self.use_reranker and self.reranker is not None:
            return self.reranker.rerank(query, merged, top_k=top_k + len(added))
        return merged[: top_k + len(added)]
