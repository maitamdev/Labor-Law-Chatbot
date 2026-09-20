# -*- coding: utf-8 -*-
"""
VietLabor AI - Phase 5H Wave 2 Retrieval Benchmark
Evaluates V3 Hybrid Retrieval and Domain Routing on the 100-query Wave 2 Gold Dataset:
- Domain Routing Accuracy (Target: >= 95%)
- Hit@1, Hit@3, Hit@5, Hit@10, MRR, Recall@5, Gold Evidence Recall
- Domain breakdown: SOCIAL_INSURANCE, OCCUPATIONAL_SAFETY, CROSS_DOMAIN, CALCULATION, SCENARIO
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
import statistics
import sys
import time
from typing import Any, Dict, List, Optional, Set, Tuple

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8", line_buffering=True)
sys.path.insert(0, ".")

from rag.hybrid_retriever import HybridRetriever
from rag.issue_decomposer import IssueDecomposer
from rag.query_expander import QueryExpander
from rag.query_processor import normalize_query
from rag.query_router import QueryRouter

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("benchmark_wave2_retrieval")

GOLD_DATASET_PATH = Path("data/evaluation/wave2_gold_set.json")


def is_chunk_relevant(chunk: Dict[str, Any], query_item: Dict[str, Any]) -> bool:
    """Checks if a retrieved chunk matches relevant articles or chunk_ids of gold query."""
    meta = chunk.get("metadata", {})
    cid = chunk.get("chunk_id") or meta.get("chunk_id", "")
    doc_id = chunk.get("doc_id") or meta.get("doc_id", "")
    art = str(chunk.get("article_number") or meta.get("article_number") or "")

    rel_cids = query_item.get("relevant_chunk_ids", [])
    rel_docs = query_item.get("relevant_documents", [])
    rel_arts = [str(a) for a in query_item.get("relevant_articles", [])]

    # Exact chunk ID match
    if cid in rel_cids:
        return True

    # Document + Article match
    if doc_id in rel_docs and art in rel_arts:
        return True

    # Preamble match when Article 1 is expected
    if doc_id in rel_docs and "1" in rel_arts and ("preamble" in cid or "d1" in cid):
        return True

    return False


def run_benchmark():
    print("=" * 80)
    print("VIETLABOR AI - PHASE 5H WAVE 2 RETRIEVAL BENCHMARK (V3 INDEX)")
    print("=" * 80)

    if not GOLD_DATASET_PATH.exists():
        print(f"Error: Gold dataset not found at {GOLD_DATASET_PATH}")
        sys.exit(1)

    with open(GOLD_DATASET_PATH, "r", encoding="utf-8") as f:
        queries = json.load(f)

    print(f"Loaded {len(queries)} gold queries from {GOLD_DATASET_PATH}.")

    print("Initializing QueryRouter, Expander, Decomposer and V3 HybridRetriever...")
    router = QueryRouter()
    expander = QueryExpander()
    decomposer = IssueDecomposer(query_expander=expander)
    retriever = HybridRetriever(index_version="v3")

    # 1. Evaluate Domain Routing
    print("\n--- [1/3] DOMAIN ROUTING EVALUATION ---")
    routing_correct = 0
    routing_by_domain: Dict[str, Dict[str, int]] = {}

    for q in queries:
        expected = q["expected_domain"]
        decision = router.route(q["question"])
        detected = decision.domain

        stats = routing_by_domain.setdefault(expected, {"total": 0, "correct": 0})
        stats["total"] += 1

        is_match = False
        if detected == expected:
            is_match = True
        elif expected == "CROSS_DOMAIN" and decision.domain == "CROSS_DOMAIN":
            is_match = True
        elif expected in ("OCCUPATIONAL_SAFETY", "OCCUPATIONAL_ACCIDENT_DISEASE") and decision.domain in ("OCCUPATIONAL_SAFETY", "OCCUPATIONAL_ACCIDENT_DISEASE"):
            is_match = True

        if is_match:
            routing_correct += 1
            stats["correct"] += 1
        else:
            print(f"  [Routing Mismatch] {q['id']}: '{q['question'][:50]}...' -> Expected: {expected}, Got: {detected}")

    routing_acc = (routing_correct / len(queries)) * 100
    print(f"\nOverall Domain Routing Accuracy: {routing_correct}/{len(queries)} ({routing_acc:.2f}%)")
    for dom, st in routing_by_domain.items():
        acc = (st["correct"] / st["total"]) * 100 if st["total"] > 0 else 0
        print(f"  - {dom:<30}: {st['correct']}/{st['total']} ({acc:.2f}%)")

    # 2. Evaluate Retrieval Metrics
    print("\n--- [2/3] V3 HYBRID RETRIEVAL BENCHMARK ---")
    hits1, hits3, hits5, hits10 = 0, 0, 0, 0
    rr_list = []
    recalls5 = []

    # Category breakdown collectors
    cat_metrics: Dict[str, Dict[str, Any]] = {
        "ALL": {"hits5": 0, "total": 0, "rr": []},
        "SOCIAL_INSURANCE": {"hits5": 0, "total": 0, "rr": []},
        "OCCUPATIONAL_SAFETY": {"hits5": 0, "total": 0, "rr": []},
        "CROSS_DOMAIN": {"hits5": 0, "total": 0, "rr": []},
        "CALCULATION": {"hits5": 0, "total": 0, "rr": []},
        "SCENARIO": {"hits5": 0, "total": 0, "rr": []},
    }

    t0 = time.time()
    for idx, q in enumerate(queries, start=1):
        decision = router.route(q["question"])

        # Production retrieval strategy: Cross-domain decomposition vs single-domain expansion
        if decision.domain == "CROSS_DOMAIN":
            sub_issues = decomposer.decompose(q["question"])
            retrieved_pool: Dict[str, Tuple[Dict[str, Any], float]] = {}
            for issue in sub_issues:
                sub_res = retriever.retrieve(issue.retrieval_query, top_k=10)
                for r_idx, c in enumerate(sub_res, 1):
                    cid = c.get("chunk_id") or c.get("metadata", {}).get("chunk_id", "")
                    score = 1.0 / (60 + r_idx)
                    if cid in retrieved_pool:
                        retrieved_pool[cid] = (c, retrieved_pool[cid][1] + score)
                    else:
                        retrieved_pool[cid] = (c, score)
            sorted_items = sorted(retrieved_pool.values(), key=lambda x: x[1], reverse=True)
            retrieved = [x[0] for x in sorted_items[:10]]
        else:
            expanded_q = expander.expand(q["question"])
            retrieved = retriever.retrieve(expanded_q, top_k=10)

        found_rank = None
        relevant_in_top5 = 0
        total_relevant = len(q.get("relevant_articles", [1]))

        for rank, chunk in enumerate(retrieved, start=1):
            if is_chunk_relevant(chunk, q):
                if found_rank is None:
                    found_rank = rank
                if rank <= 5:
                    relevant_in_top5 += 1

        if found_rank is not None:
            if found_rank <= 1:
                hits1 += 1
            if found_rank <= 3:
                hits3 += 1
            if found_rank <= 5:
                hits5 += 1
            if found_rank <= 10:
                hits10 += 1
            rr_list.append(1.0 / found_rank)
        else:
            rr_list.append(0.0)

        recall_5 = min(1.0, relevant_in_top5 / max(total_relevant, 1))
        recalls5.append(recall_5)

        # Categorize
        dom = q["expected_domain"]
        q_type = q.get("query_type", "")

        categories = ["ALL"]
        if dom in ("SOCIAL_INSURANCE", "OCCUPATIONAL_SAFETY", "CROSS_DOMAIN"):
            categories.append(dom)
        elif dom == "OCCUPATIONAL_ACCIDENT_DISEASE":
            categories.append("OCCUPATIONAL_SAFETY")
        if q_type == "calculation":
            categories.append("CALCULATION")
        if q_type in ("scenario", "ambiguous_premise"):
            categories.append("SCENARIO")

        for c in categories:
            if c in cat_metrics:
                cat_metrics[c]["total"] += 1
                if found_rank and found_rank <= 5:
                    cat_metrics[c]["hits5"] += 1
                cat_metrics[c]["rr"].append(1.0 / found_rank if found_rank else 0.0)

    elapsed = time.time() - t0
    n = len(queries)
    h1 = (hits1 / n) * 100
    h3 = (hits3 / n) * 100
    h5 = (hits5 / n) * 100
    h10 = (hits10 / n) * 100
    mrr = statistics.mean(rr_list) if rr_list else 0.0
    rec5 = statistics.mean(recalls5) * 100 if recalls5 else 0.0

    print(f"\nCompleted {n} queries in {elapsed:.2f}s ({elapsed/n*1000:.1f}ms/query)")
    print(f"Overall Retrieval Metrics:")
    print(f"  Hit@1 : {hits1}/{n} ({h1:.2f}%)")
    print(f"  Hit@3 : {hits3}/{n} ({h3:.2f}%)")
    print(f"  Hit@5 : {hits5}/{n} ({h5:.2f}%)")
    print(f"  Hit@10: {hits10}/{n} ({h10:.2f}%)")
    print(f"  MRR   : {mrr:.4f}")
    print(f"  Recall@5: {rec5:.2f}%")

    print("\n--- [3/3] BREAKDOWN BY DOMAIN & QUERY TYPE ---")
    print(f"{'Category':<25} | {'Count':<8} | {'Hit@5 (%)':<12} | {'MRR':<8}")
    print("-" * 60)
    for cat, data in cat_metrics.items():
        if data["total"] > 0:
            c_h5 = (data["hits5"] / data["total"]) * 100
            c_mrr = statistics.mean(data["rr"])
            print(f"{cat:<25} | {data['total']:<8} | {c_h5:<12.2f} | {c_mrr:.4f}")

    print("=" * 80)
    pass_gate = (h5 >= 85.0) and (routing_acc >= 95.0)
    print(f"Retrieval Acceptance Gate (Hit@5 >= 85%, Router >= 95%): {'PASS' if pass_gate else 'FAIL'}")
    print("=" * 80)

    # Save results to json
    res_path = Path("evaluation/results/wave2_retrieval_benchmark.json")
    res_path.parent.mkdir(parents=True, exist_ok=True)
    with open(res_path, "w", encoding="utf-8") as f:
        json.dump({
            "total_queries": n,
            "routing_accuracy": routing_acc,
            "hit_1": h1,
            "hit_3": h3,
            "hit_5": h5,
            "hit_10": h10,
            "mrr": mrr,
            "recall_5": rec5,
            "pass_gate": pass_gate,
        }, f, indent=2)


if __name__ == "__main__":
    run_benchmark()
