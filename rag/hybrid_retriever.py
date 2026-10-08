# -*- coding: utf-8 -*-
"""
VietLabor AI - Hybrid Retriever
Fuses BM25 lexical search and BGE-M3 dense vector search
using Reciprocal Rank Fusion (RRF) to avoid score scaling distortion.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from config.settings import BM25_INDEX_DIR, CHROMA_INDEX_DIR, PRODUCTION_CORPUS_PATH, STORAGE_DIR
from rag.bm25_retriever import BM25Retriever
from rag.dense_retriever import DenseRetriever
from rag.reranker import CrossEncoderReranker
from rag.vectorstore import LegalVectorStore

logger = logging.getLogger(__name__)

DEFAULT_RRF_K = 60


class HybridRetriever:
    """Hybrid legal retriever combining BM25 and Dense retrieval via RRF, with optional Cross-Encoder reranking."""

    def __init__(
        self,
        bm25_retriever: Optional[BM25Retriever] = None,
        dense_retriever: Optional[DenseRetriever] = None,
        reranker: Optional[CrossEncoderReranker] = None,
        use_reranker: bool = False,
        rrf_k: int = DEFAULT_RRF_K,
        bm25_weight: float = 1.0,
        dense_weight: float = 1.0,
        index_version: str = "v3",
    ):
        self.index_version = index_version
        self.use_reranker = use_reranker
        self.reranker = reranker
        if bm25_retriever is not None:
            self.bm25_retriever = bm25_retriever
        else:
            if index_version == "v3":
                self.bm25_retriever = BM25Retriever(
                    persist_dir=BM25_INDEX_DIR,
                    corpus_path=PRODUCTION_CORPUS_PATH,
                )
            elif index_version == "v2" and (STORAGE_DIR / "bm25_v2").exists():
                self.bm25_retriever = BM25Retriever(
                    persist_dir=STORAGE_DIR / "bm25_v2",
                    corpus_path=PRODUCTION_CORPUS_PATH.parent / "legal_documents_v2.jsonl",
                )
            else:
                self.bm25_retriever = BM25Retriever(
                    persist_dir=STORAGE_DIR / "bm25",
                    corpus_path=PRODUCTION_CORPUS_PATH.parent / "legal_documents.jsonl",
                )

        if dense_retriever is not None:
            self.dense_retriever = dense_retriever
            self.dense_ready = True
        else:
            if index_version == "v3":
                self.dense_retriever = DenseRetriever(
                    vectorstore=LegalVectorStore(
                        persist_dir=CHROMA_INDEX_DIR,
                        collection_name="vietlabor_chunks_v3",
                        corpus_path=PRODUCTION_CORPUS_PATH,
                    )
                )

            elif index_version == "v2" and (STORAGE_DIR / "chroma_v2").exists():
                self.dense_retriever = DenseRetriever(
                    vectorstore=LegalVectorStore(
                        persist_dir=STORAGE_DIR / "chroma_v2",
                        collection_name="vietlabor_chunks_v2",
                        corpus_path=PRODUCTION_CORPUS_PATH.parent / "legal_documents_v2.jsonl",
                    )
                )
            else:
                self.dense_retriever = DenseRetriever(
                    vectorstore=LegalVectorStore(
                        persist_dir=STORAGE_DIR / "chroma",
                        collection_name="vietlabor_chunks",
                        corpus_path=PRODUCTION_CORPUS_PATH.parent / "legal_documents.jsonl",
                    )
                )

            # A corpus refresh can leave Chroma only partly synchronized for a
            # while. Never answer from that stale/partial collection. BM25 is
            # complete and provides a fast, deterministic fallback.
            self.dense_ready = self.dense_retriever.vectorstore.is_index_valid(strict=False)
            if not self.dense_ready:
                logger.warning("Dense index is incomplete or stale; using current BM25 index only.")

        self.rrf_k = rrf_k
        self.bm25_weight = bm25_weight
        self.dense_weight = dense_weight
        self.dense_error: Optional[str] = None

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

        # 2. Fetch dense vector candidates. The Chroma index can be valid while
        # the embedding model itself fails to load (e.g. a corrupted Hugging
        # Face cache). That must degrade to lexical search, never crash a chat.
        dense_candidates: List[Dict[str, Any]] = []
        if self.dense_ready:
            try:
                dense_candidates = self.dense_retriever.retrieve(clean_query, top_k=n_candidates)
            except Exception as exc:
                self.dense_ready = False
                self.dense_error = f"{type(exc).__name__}: {exc}"
                logger.warning(
                    "Dense retrieval unavailable (%s). Falling back to BM25-only for this session. "
                    "Fix: delete the cached embedding model and re-download it.",
                    self.dense_error[:300],
                )

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

        # 5. Optional Cross-Encoder reranking for precision enhancement
        if self.use_reranker and self.reranker is not None:
            rerank_pool = [
                {
                    "chunk_id": r["chunk_id"],
                    "score": r["rrf_score"],
                    "rrf_score": r["rrf_score"],
                    "bm25_rank": r["bm25_rank"],
                    "bm25_score": r["bm25_score"],
                    "dense_rank": r["dense_rank"],
                    "dense_score": r["dense_score"],
                    "content": r["content"],
                    "retrieval_text": r["retrieval_text"],
                    "metadata": r["metadata"],
                }
                for r in fused_results[:max(top_k * 3, 20)]
            ]
            return self.reranker.rerank(clean_query, rerank_pool, top_k=top_k)

        # Format standard output items
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
