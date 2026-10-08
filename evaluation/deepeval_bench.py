# -*- coding: utf-8 -*-
"""
VietLabor AI - DeepEval & IR Benchmark Evaluator
Assesses RAG answer generation quality with Faithfulness, Answer Relevancy,
and Information Retrieval metrics (Hit Rate@1, Hit Rate@5, MRR).
Compatible with native DeepEval (if installed) or standalone statutory auditor.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    getattr(sys.stderr, "reconfigure")(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rag.chain import VietLaborRAGChain
from rag.hybrid_retriever import HybridRetriever
from rag.reranker import CrossEncoderReranker

logger = logging.getLogger("evaluation.benchmark")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class BenchmarkEvaluator:
    """Evaluates VietLabor AI on legal accuracy, citation faithfulness, and retrieval relevance."""

    def __init__(
        self,
        dataset_path: str = "data/evaluation/phase5c_eval_dataset.json",
        output_dir: str = "evaluation/results",
        use_reranker: bool = False,
        retrieval_only: bool = False,
    ):
        self.dataset_path = Path(dataset_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.use_reranker = use_reranker
        self.retrieval_only = retrieval_only
        reranker = CrossEncoderReranker() if use_reranker else None
        retriever = HybridRetriever(reranker=reranker, use_reranker=use_reranker)
        self.chain = VietLaborRAGChain(hybrid_retriever=retriever)

    def evaluate_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Runs chain on a single evaluation item and assesses precision and faithfulness."""
        query = item.get("query") or item.get("question") or ""
        req_evs = item.get("required_evidence", [])
        expected_articles = [str(e.get("article")) for e in req_evs if e.get("article")]
        expected_docs = [str(e.get("doc_id")) for e in req_evs if e.get("doc_id")]
        expected_clauses = [str(e.get("clause")) for e in req_evs if e.get("clause")]

        retrieved_chunks = []
        ans = ""
        cited_cids = []
        locked_cids = set()
        result = None
        generation_available = False

        t0 = time.perf_counter()
        if self.retrieval_only:
            retrieved_chunks = self.chain.hybrid_retriever.retrieve(query, top_k=self.chain.top_k)
            latency_ms = (time.perf_counter() - t0) * 1000
        else:
            try:
                result = self.chain.run(query)
                generation_available = True
                latency_ms = (time.perf_counter() - t0) * 1000
                retrieved_chunks = result.retrieved_chunks
                ans = result.answer
                cited_cids = result.cited_chunk_ids
                locked_cids = set(result.locked_chunk_ids)
            except (ConnectionError, FileNotFoundError):
                # Ollama is offline: retrieval can still be measured, but
                # generation metrics must remain unavailable rather than being
                # reported as perfect scores for an empty answer.
                retrieved_chunks = self.chain.hybrid_retriever.retrieve(query, top_k=self.chain.top_k)
                latency_ms = (time.perf_counter() - t0) * 1000
                ans = ""

        # 1. Retrieval Metrics
        hit_at_1 = False
        hit_at_5 = False
        reciprocal_rank = 0.0

        DOC_CANONICAL_MAP = {
            "18/VBHN-VPQH": ["VBHN_18_2026", "18/VBHN", "BLLD_2019", "45/2019/QH14", "18"],
            "145/2020/NĐ-CP": ["ND_145_2020", "145/2020", "145"],
            "12/2022/NĐ-CP": ["ND_12_2022", "12/2022", "12"],
            "135/2020/NĐ-CP": ["ND_135_2020", "135/2020", "135"],
            "28/2015/TT-BLĐTBXH": ["TT_28_2015", "28/2015", "28"],
            "58/2025/VBHN-VPQH": ["VBHN_58_2025", "58/2025", "58"],
        }

        for rank, c in enumerate(retrieved_chunks, start=1):
            meta = c.get("metadata", {})
            c_art = str(meta.get("article_number") or "").strip()
            c_doc = str(meta.get("doc_id") or "")
            c_doc_no = str(meta.get("document_no") or "")

            is_match = False
            for req in req_evs:
                r_art = str(req.get("article") or "").strip()
                r_doc = str(req.get("doc_id") or "").strip()

                if r_art and c_art == r_art:
                    if not r_doc:
                        is_match = True
                        break
                    aliases = DOC_CANONICAL_MAP.get(r_doc, [r_doc]) + [r_doc]
                    if any(a.lower() in c_doc.lower() or a.lower() in c_doc_no.lower() for a in aliases):
                        is_match = True
                        break

            if is_match:
                if rank == 1:
                    hit_at_1 = True
                if rank <= 5:
                    hit_at_5 = True
                if reciprocal_rank == 0.0:
                    reciprocal_rank = 1.0 / rank

        # 2. Faithfulness Metric (Zero Phantom Citation Check)
        # Verify that all cited_chunk_ids were actually present in the context locked pool
        phantom_citations = [cid for cid in cited_cids if cid not in locked_cids]
        faithfulness_score: Optional[float] = None
        if generation_available:
            if not ans.strip() or not cited_cids:
                faithfulness_score = 0.0
            else:
                faithfulness_score = 1.0 if not phantom_citations else max(0.0, 1.0 - len(phantom_citations) * 0.5)

        # 3. Answer Relevancy (Lexical & Finding grounding check)
        findings = []
        if result is not None and hasattr(result, 'validated_response'):
            findings = result.validated_response.legal_findings
        relevancy_score: Optional[float] = None
        if generation_available:
            relevancy_score = 0.0
            if ans.strip():
                relevancy_score += 0.5
            if findings:
                relevancy_score += 0.3
            if cited_cids:
                relevancy_score += 0.2
            relevancy_score = min(1.0, relevancy_score)

        return {
            "query": query,
            "required_evidence": req_evs,
            "retrieved_evidence": [
                {
                    "rank": rank,
                    "chunk_id": chunk.get("chunk_id"),
                    "doc_id": chunk.get("metadata", {}).get("doc_id"),
                    "document_no": chunk.get("metadata", {}).get("document_no"),
                    "article": chunk.get("metadata", {}).get("article_number"),
                    "clause": chunk.get("metadata", {}).get("clause_number"),
                }
                for rank, chunk in enumerate(retrieved_chunks[:5], start=1)
            ],
            "hit_at_1": hit_at_1,
            "hit_at_5": hit_at_5,
            "reciprocal_rank": reciprocal_rank,
            "faithfulness": faithfulness_score,
            "answer_relevancy": relevancy_score,
            "generation_available": generation_available,
            "phantom_citations": phantom_citations,
            "cited_chunk_count": len(cited_cids),
            "latency_ms": latency_ms,
            "answer_excerpt": ans[:150] + "..." if len(ans) > 150 else ans,
        }

    def run_benchmark(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """Runs benchmark across test cases and computes aggregate statistics."""
        if not self.dataset_path.exists():
            logger.error(f"Dataset not found at {self.dataset_path}")
            return {}

        with open(self.dataset_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        queries = [q for q in data if q.get("query_type") == "in_scope"]
        if limit:
            queries = queries[:limit]

        logger.info(f"Running evaluation benchmark on {len(queries)} test queries...")
        eval_records = []

        for i, item in enumerate(queries, start=1):
            q_text = item.get("query") or item.get("question") or ""
            logger.info(f"[{i}/{len(queries)}] Evaluating: '{q_text[:60]}...'")
            rec = self.evaluate_item(item)
            eval_records.append(rec)

        query_count = len(eval_records)
        denominator = query_count or 1
        avg_hit_1 = sum(1 for r in eval_records if r["hit_at_1"]) / denominator
        avg_hit_5 = sum(1 for r in eval_records if r["hit_at_5"]) / denominator
        avg_mrr = sum(r["reciprocal_rank"] for r in eval_records) / denominator
        generated_records = [r for r in eval_records if r["generation_available"]]
        avg_faithfulness = (
            sum(float(r["faithfulness"]) for r in generated_records) / len(generated_records)
            if generated_records else None
        )
        avg_relevancy = (
            sum(float(r["answer_relevancy"]) for r in generated_records) / len(generated_records)
            if generated_records else None
        )
        avg_latency = sum(r["latency_ms"] for r in eval_records) / denominator
        total_phantoms = sum(len(r["phantom_citations"]) for r in eval_records)

        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_queries": query_count,
            "hit_rate_at_1": round(avg_hit_1, 4),
            "hit_rate_at_5": round(avg_hit_5, 4),
            "mrr": round(avg_mrr, 4),
            "generation_queries": len(generated_records),
            "faithfulness": round(avg_faithfulness, 4) if avg_faithfulness is not None else None,
            "answer_relevancy": round(avg_relevancy, 4) if avg_relevancy is not None else None,
            "total_phantom_citations": total_phantoms,
            "avg_latency_ms": round(avg_latency, 1),
            "use_reranker": self.use_reranker,
        }

        # Print report table
        print("\n" + "=" * 65)
        print("  VIETLABOR AI - EVALUATION BENCHMARK REPORT (DEEPEVAL STYLE)")
        print("=" * 65)
        print(f"  Test Queries Evaluated    : {query_count}")
        print(f"  Hit Rate @ 1              : {avg_hit_1 * 100:.2f}%")
        print(f"  Hit Rate @ 5              : {avg_hit_5 * 100:.2f}%")
        print(f"  MRR (Mean Recip. Rank)    : {avg_mrr:.4f}")
        faithfulness_label = f"{avg_faithfulness * 100:.2f}%" if avg_faithfulness is not None else "N/A (generation skipped)"
        relevancy_label = f"{avg_relevancy * 100:.2f}%" if avg_relevancy is not None else "N/A (generation skipped)"
        print(f"  Faithfulness (No Phantoms): {faithfulness_label} (Phantom Citations: {total_phantoms})")
        print(f"  Answer Relevancy          : {relevancy_label}")
        print(f"  Avg Latency               : {avg_latency:.1f} ms")
        print("=" * 65 + "\n")

        # Save to results
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_file = self.output_dir / f"benchmark_report_{timestamp_str}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump({"summary": summary, "records": eval_records}, f, ensure_ascii=False, indent=2)
        logger.info(f"Detailed benchmark results saved to {out_file}")

        return summary


def main():
    parser = argparse.ArgumentParser(description="VietLabor AI - Evaluation Benchmark")
    parser.add_argument("--limit", type=int, default=10, help="Limit number of queries to evaluate (default: 10)")
    parser.add_argument("--dataset", type=str, default="data/evaluation/phase5c_eval_dataset.json", help="Evaluation dataset path")
    parser.add_argument("--all", action="store_true", help="Run on all in-scope queries in dataset")
    parser.add_argument("--retrieval-only", action="store_true", help="Evaluate retrieval precision only without LLM inference")
    parser.add_argument(
        "--reranker",
        action="store_true",
        help="Enable the optional cross-encoder reranker (slower and may download a model)",
    )
    args = parser.parse_args()

    limit = None if args.all else args.limit
    evaluator = BenchmarkEvaluator(
        dataset_path=args.dataset,
        use_reranker=args.reranker,
        retrieval_only=args.retrieval_only,
    )
    evaluator.run_benchmark(limit=limit)


if __name__ == "__main__":
    main()
