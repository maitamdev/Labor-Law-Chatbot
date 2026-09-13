# -*- coding: utf-8 -*-
"""
VietLabor AI - Retrieval Evaluation & Benchmarking Engine
Evaluates BM25, Dense (BGE-M3), and Hybrid (RRF) retrieval strategies
against the 155-question legal gold dataset.
Calculates Hit@1, Hit@3, Hit@5, Hit@10, MRR, Recall@5, Recall@10, Latency,
breakdown by query type and topic, and generates detailed error analysis.
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

# Ensure workspace root is in sys.path
workspace_root = Path(__file__).resolve().parent.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

from rag.bm25_retriever import BM25Retriever
from rag.dense_retriever import DenseRetriever
from rag.hybrid_retriever import HybridRetriever

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("evaluate_retrieval")

GOLD_DATASET_PATH = Path("data/evaluation/retrieval_gold.json")
RESULTS_DIR = Path("evaluation/results")


def is_chunk_relevant(chunk: dict[str, Any], gold_q: dict[str, Any]) -> bool:
    """Determines whether a retrieved chunk satisfies the gold relevance criteria."""
    chunk_id = chunk.get("chunk_id", "")
    expected_chunk_ids = gold_q.get("relevant_chunk_ids", [])
    if expected_chunk_ids and chunk_id in expected_chunk_ids:
        return True

    meta = chunk.get("metadata", {})
    doc_id = meta.get("doc_id") or ""
    article_number = str(meta.get("article_number") or "").strip()

    expected_docs = gold_q.get("relevant_documents", [])
    expected_articles = [str(a).strip() for a in gold_q.get("relevant_articles", [])]

    if expected_docs and doc_id not in expected_docs:
        return False

    if expected_articles and article_number in expected_articles:
        return True

    return False


def evaluate_single_query(
    retriever: Any,
    gold_q: dict[str, Any],
    top_k: int = 10,
) -> dict[str, Any]:
    """Evaluates a single query against gold ground-truth."""
    query = gold_q["question"]
    is_out_of_scope = gold_q.get("topic") == "out_of_scope" or not gold_q.get("relevant_articles")

    t0 = time.perf_counter()
    retrieved_chunks = retriever.retrieve(query, top_k=top_k)
    latency_ms = (time.perf_counter() - t0) * 1000.0

    retrieved_summary = []
    relevant_ranks: List[int] = []
    found_articles = set()

    for rank, chunk in enumerate(retrieved_chunks, start=1):
        meta = chunk.get("metadata", {})
        rel = is_chunk_relevant(chunk, gold_q)
        art = str(meta.get("article_number") or "")
        if rel:
            relevant_ranks.append(rank)
            if art:
                found_articles.add(art)

        retrieved_summary.append({
            "rank": rank,
            "chunk_id": chunk.get("chunk_id", ""),
            "doc_id": meta.get("doc_id", ""),
            "article_number": art,
            "article_title": meta.get("article_title", ""),
            "score": float(chunk.get("score", 0.0)),
            "is_relevant": rel,
            "content_preview": chunk.get("content", "")[:120],
        })

    # Calculate metrics
    hit_1 = 1 if (relevant_ranks and relevant_ranks[0] == 1) else 0
    hit_3 = 1 if (relevant_ranks and relevant_ranks[0] <= 3) else 0
    hit_5 = 1 if (relevant_ranks and relevant_ranks[0] <= 5) else 0
    hit_10 = 1 if (relevant_ranks and relevant_ranks[0] <= 10) else 0

    mrr = 1.0 / relevant_ranks[0] if relevant_ranks else 0.0

    expected_articles = set(str(a).strip() for a in gold_q.get("relevant_articles", []))
    n_expected = len(expected_articles) if expected_articles else 1

    # Recall at 5 and 10
    found_at_5 = set(
        s["article_number"] for s in retrieved_summary[:5] if s["is_relevant"] and s["article_number"]
    )
    found_at_10 = set(
        s["article_number"] for s in retrieved_summary[:10] if s["is_relevant"] and s["article_number"]
    )

    recall_5 = len(found_at_5) / n_expected if not is_out_of_scope else 0.0
    recall_10 = len(found_at_10) / n_expected if not is_out_of_scope else 0.0

    max_score = float(retrieved_chunks[0]["score"]) if retrieved_chunks else 0.0

    return {
        "question_id": gold_q["question_id"],
        "question": query,
        "topic": gold_q.get("topic", ""),
        "query_type": gold_q.get("query_type", ""),
        "difficulty": gold_q.get("difficulty", "medium"),
        "is_out_of_scope": is_out_of_scope,
        "latency_ms": latency_ms,
        "hit@1": hit_1,
        "hit@3": hit_3,
        "hit@5": hit_5,
        "hit@10": hit_10,
        "mrr": mrr,
        "recall@5": recall_5,
        "recall@10": recall_10,
        "max_score": max_score,
        "first_relevant_rank": relevant_ranks[0] if relevant_ranks else None,
        "retrieved_summary": retrieved_summary,
    }


def aggregate_metrics(query_results: List[dict[str, Any]]) -> dict[str, Any]:
    """Computes mean and breakdown metrics for in-scope queries."""
    in_scope = [q for q in query_results if not q["is_out_of_scope"]]
    out_of_scope = [q for q in query_results if q["is_out_of_scope"]]

    def mean_val(lst: List[float]) -> float:
        return sum(lst) / len(lst) if lst else 0.0

    n = len(in_scope)
    summary: dict[str, Any] = {
        "total_queries": len(query_results),
        "in_scope_queries": n,
        "out_of_scope_queries": len(out_of_scope),
        "hit@1": mean_val([q["hit@1"] for q in in_scope]),
        "hit@3": mean_val([q["hit@3"] for q in in_scope]),
        "hit@5": mean_val([q["hit@5"] for q in in_scope]),
        "hit@10": mean_val([q["hit@10"] for q in in_scope]),
        "mrr": mean_val([q["mrr"] for q in in_scope]),
        "recall@5": mean_val([q["recall@5"] for q in in_scope]),
        "recall@10": mean_val([q["recall@10"] for q in in_scope]),
        "avg_latency_ms": mean_val([q["latency_ms"] for q in query_results]),
        "out_of_scope_avg_max_score": mean_val([q["max_score"] for q in out_of_scope]),
    }

    # Breakdown by query type
    query_types = sorted(list(set(q["query_type"] for q in in_scope)))
    by_query_type: dict[str, Any] = {}
    for qt in query_types:
        subset = [q for q in in_scope if q["query_type"] == qt]
        by_query_type[qt] = {
            "count": len(subset),
            "hit@1": mean_val([q["hit@1"] for q in subset]),
            "hit@3": mean_val([q["hit@3"] for q in subset]),
            "hit@5": mean_val([q["hit@5"] for q in subset]),
            "mrr": mean_val([q["mrr"] for q in subset]),
            "recall@5": mean_val([q["recall@5"] for q in subset]),
        }
    summary["by_query_type"] = by_query_type

    # Breakdown by topic
    topics = sorted(list(set(q["topic"] for q in in_scope)))
    by_topic: dict[str, Any] = {}
    for top in topics:
        subset = [q for q in in_scope if q["topic"] == top]
        by_topic[top] = {
            "count": len(subset),
            "hit@1": mean_val([q["hit@1"] for q in subset]),
            "hit@5": mean_val([q["hit@5"] for q in subset]),
            "mrr": mean_val([q["mrr"] for q in subset]),
        }
    summary["by_topic"] = by_topic

    return summary


def diagnose_failure_reason(gold_q: dict[str, Any], query_res: dict[str, Any], method: str) -> str:
    """Categorizes the primary failure reason for error analysis."""
    qt = gold_q.get("query_type", "")
    question = gold_q.get("question", "")

    if qt == "exact_reference":
        return "Exact reference syntax mismatch or missing cross-document link"
    elif qt == "numeric":
        return "Numeric threshold mismatch or dense embedding invariant to exact digit values"
    elif qt == "colloquial":
        return "Colloquial terminology gap / informal phrasing not in official statutory text"
    elif qt == "paraphrase":
        return "Synonym vocabulary mismatch in lexical search or semantic drift"
    elif qt == "cross_reference":
        return "Decree to Law cross-reference gap (retrieved overarching Law instead of specific Decree)"
    elif qt == "long":
        return "Multi-sentence context dilution / query noise"
    elif qt == "short":
        return "High lexical ambiguity from overly brief query"
    else:
        return "Semantic boundary mismatch"


def run_benchmark_for_method(
    method: str,
    gold_questions: List[dict[str, Any]],
    top_k: int = 10,
) -> Tuple[dict[str, Any], List[dict[str, Any]], List[dict[str, Any]]]:
    """Runs complete benchmark for a single retrieval strategy."""
    logger.info(f"Running benchmark for method: {method.upper()} on {len(gold_questions)} questions...")

    if method == "bm25":
        retriever = BM25Retriever()
        retriever.load_index()
    elif method == "dense":
        retriever = DenseRetriever()
    elif method == "hybrid":
        retriever = HybridRetriever()
    else:
        raise ValueError(f"Unknown method: {method}")

    query_results: List[dict[str, Any]] = []
    failures: List[dict[str, Any]] = []

    for idx, gold_q in enumerate(gold_questions, start=1):
        res = evaluate_single_query(retriever, gold_q, top_k=top_k)
        query_results.append(res)

        # Collect failure if in-scope and Hit@5 == 0
        if not res["is_out_of_scope"] and res["hit@5"] == 0:
            reason = diagnose_failure_reason(gold_q, res, method)
            failures.append({
                "question_id": gold_q["question_id"],
                "question": gold_q["question"],
                "query_type": gold_q.get("query_type", ""),
                "topic": gold_q.get("topic", ""),
                "expected_documents": gold_q.get("relevant_documents", []),
                "expected_articles": gold_q.get("relevant_articles", []),
                "method": method,
                "retrieved_top3": [
                    {
                        "chunk_id": s["chunk_id"],
                        "doc_id": s["doc_id"],
                        "article": s["article_number"],
                        "score": s["score"],
                        "preview": s["content_preview"],
                    }
                    for s in res["retrieved_summary"][:3]
                ],
                "failure_reason": reason,
            })

        if idx % 50 == 0 or idx == len(gold_questions):
            logger.info(f"[{method.upper()}] Evaluated {idx}/{len(gold_questions)} queries...")

    summary = aggregate_metrics(query_results)
    summary["method"] = method
    summary["failure_count"] = len(failures)

    return summary, query_results, failures


def main():
    parser = argparse.ArgumentParser(description="VietLabor AI Retrieval Benchmark")
    parser.add_argument(
        "--method",
        choices=["all", "bm25", "dense", "hybrid"],
        default="all",
        help="Retrieval method to benchmark (default: all).",
    )
    parser.add_argument("--top-k", type=int, default=10, help="Top-K candidates to evaluate.")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    if not GOLD_DATASET_PATH.exists():
        raise FileNotFoundError(f"Gold dataset not found: {GOLD_DATASET_PATH}")

    with open(GOLD_DATASET_PATH, "r", encoding="utf-8") as f:
        gold_questions = json.load(f)

    methods_to_run = ["bm25", "dense", "hybrid"] if args.method == "all" else [args.method]

    all_summaries: dict[str, Any] = {}
    all_failures: dict[str, List[dict[str, Any]]] = {}

    for method in methods_to_run:
        summary, query_results, failures = run_benchmark_for_method(
            method=method,
            gold_questions=gold_questions,
            top_k=args.top_k,
        )
        all_summaries[method] = summary
        all_failures[method] = failures

        # Save individual detailed results
        res_file = RESULTS_DIR / f"{method}_results.json"
        with open(res_file, "w", encoding="utf-8") as f:
            json.dump({
                "summary": summary,
                "queries": query_results,
                "failures": failures,
            }, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {method} results to {res_file}")

    # Generate comparison CSV
    csv_file = RESULTS_DIR / "retrieval_comparison.csv"
    with open(csv_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Method", "In-Scope Queries", "Hit@1", "Hit@3", "Hit@5", "Hit@10",
            "MRR", "Recall@5", "Recall@10", "Avg Latency (ms)", "Failures (Hit@5=0)"
        ])
        for method, s in all_summaries.items():
            writer.writerow([
                method.upper(),
                s["in_scope_queries"],
                f"{s['hit@1']:.4f}",
                f"{s['hit@3']:.4f}",
                f"{s['hit@5']:.4f}",
                f"{s['hit@10']:.4f}",
                f"{s['mrr']:.4f}",
                f"{s['recall@5']:.4f}",
                f"{s['recall@10']:.4f}",
                f"{s['avg_latency_ms']:.2f}",
                s["failure_count"],
            ])
    logger.info(f"Saved comparison CSV to {csv_file}")

    # Save combined error analysis
    err_file = RESULTS_DIR / "error_analysis.json"
    with open(err_file, "w", encoding="utf-8") as f:
        json.dump(all_failures, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved combined error analysis to {err_file}")

    # Print summary table
    print("\n" + "=" * 90)
    print("VIETLABOR AI - PHASE 4 RETRIEVAL BENCHMARK SUMMARY")
    print("=" * 90)
    print(f"{'Method':<10} | {'Hit@1':<8} | {'Hit@3':<8} | {'Hit@5':<8} | {'Hit@10':<8} | {'MRR':<8} | {'Recall@5':<9} | {'Latency':<10}")
    print("-" * 90)
    for method, s in all_summaries.items():
        print(
            f"{method.upper():<10} | "
            f"{s['hit@1']*100:>6.2f}% | "
            f"{s['hit@3']*100:>6.2f}% | "
            f"{s['hit@5']*100:>6.2f}% | "
            f"{s['hit@10']*100:>6.2f}% | "
            f"{s['mrr']:>8.4f} | "
            f"{s['recall@5']*100:>7.2f}% | "
            f"{s['avg_latency_ms']:>7.2f} ms"
        )
    print("=" * 90 + "\n")


if __name__ == "__main__":
    main()
