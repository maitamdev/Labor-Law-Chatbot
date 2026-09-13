# -*- coding: utf-8 -*-
"""
VietLabor AI - Hybrid Retriever
Fuses BM25 lexical search and BGE-M3 dense vector search
using Reciprocal Rank Fusion (RRF) to avoid score scaling distortion.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from rag.bm25_retriever import BM25Retriever
from rag.dense_retriever import DenseRetriever

logger = logging.getLogger(__name__)

DEFAULT_RRF_K = 60


class HybridRetriever:
    """Hybrid legal retriever combining BM25 and Dense retrieval via RRF."""

    def __init__(
        self,
        bm25_retriever: Optional[BM25Retriever] = None,
        dense_retriever: Optional[DenseRetriever] = None,
        rrf_k: int = DEFAULT_RRF_K,
        bm25_weight: float = 1.0,
        dense_weight: float = 1.0,
    ):
        self.bm25_retriever = bm25_retriever or BM25Retriever()
        self.dense_retriever = dense_retriever or DenseRetriever()
        self.rrf_k = rrf_k
        self.bm25_weight = bm25_weight
        self.dense_weight = dense_weight

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        candidate_multiplier: int = 4,
    ) -> List[Dict[str, Any]]:
        """Retrieves top-k chunks using Reciprocal Rank Fusion (RRF).
        
        Formula:
            RRF(d) = w_dense / (k + rank_dense(d)) + w_bm25 / (k + rank_bm25(d))
            
        Args:
            query: User search query.
            top_k: Number of final results to return.
            candidate_multiplier: Number of candidates fetched per retriever (min 20).
            
        Returns:
            List of ranked chunk dicts with fused score and provenance metadata.
        """
        clean_query = query.strip() if query else ""
        if not clean_query:
            return []

        n_candidates = max(top_k * candidate_multiplier, 20)

        # 1. Fetch lexical candidates
        bm25_candidates = self.bm25_retriever.retrieve(clean_query, top_k=n_candidates)

        # 2. Fetch dense vector candidates
        dense_candidates = self.dense_retriever.retrieve(clean_query, top_k=n_candidates)

        # 3. Fuse via Reciprocal Rank Fusion
        fused_pool: Dict[str, Dict[str, Any]] = {}

        # Process BM25 rankings
        for rank_idx, item in enumerate(bm25_candidates, start=1):
            cid = item["chunk_id"]
            rrf_term = self.bm25_weight / (self.rrf_k + rank_idx)
            if cid not in fused_pool:
                fused_pool[cid] = {
                    "chunk_id": cid,
                    "rrf_score": 0.0,
                    "bm25_rank": rank_idx,
                    "bm25_score": item["score"],
                    "dense_rank": None,
                    "dense_score": None,
                    "content": item["content"],
                    "retrieval_text": item.get("retrieval_text", ""),
                    "metadata": item["metadata"],
                }
            else:
                fused_pool[cid]["bm25_rank"] = rank_idx
                fused_pool[cid]["bm25_score"] = item["score"]
            fused_pool[cid]["rrf_score"] += rrf_term

        # Process Dense rankings
        for rank_idx, item in enumerate(dense_candidates, start=1):
            cid = item["chunk_id"]
            rrf_term = self.dense_weight / (self.rrf_k + rank_idx)
            if cid not in fused_pool:
                fused_pool[cid] = {
                    "chunk_id": cid,
                    "rrf_score": 0.0,
                    "bm25_rank": None,
                    "bm25_score": None,
                    "dense_rank": rank_idx,
                    "dense_score": item["score"],
                    "content": item["content"],
                    "retrieval_text": item.get("retrieval_text", ""),
                    "metadata": item["metadata"],
                }
            else:
                fused_pool[cid]["dense_rank"] = rank_idx
                fused_pool[cid]["dense_score"] = item["score"]
            fused_pool[cid]["rrf_score"] += rrf_term

        # 4. Sort by RRF score descending
        fused_results = list(fused_pool.values())
        fused_results.sort(key=lambda x: x["rrf_score"], reverse=True)

        # Format output items
        output: List[Dict[str, Any]] = []
        for r in fused_results[:top_k]:
            output.append({
                "chunk_id": r["chunk_id"],
                "score": r["rrf_score"],
                "bm25_rank": r["bm25_rank"],
                "bm25_score": r["bm25_score"],
                "dense_rank": r["dense_rank"],
                "dense_score": r["dense_score"],
                "content": r["content"],
                "retrieval_text": r["retrieval_text"],
                "metadata": r["metadata"],
            })

        return output
