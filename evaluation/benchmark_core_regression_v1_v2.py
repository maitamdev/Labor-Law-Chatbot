# -*- coding: utf-8 -*-
"""
VietLabor AI - Apples-to-Apples Core Regression Benchmark (v1 vs v2)
Evaluates identical frozen core query sets on both:
- Old production index v1 (storage/chroma, storage/bm25)
- New production candidate v2 (storage/chroma_v2, storage/bm25_v2)

Evaluates on TWO standard core benchmarks:
1. Set A: 69 in-scope queries from Phase 5C (strict clause/point evidence matching)
2. Set B: 145 queries from Phase 4 (retrieval_gold.json)
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
import statistics
import sys
import time
from typing import Any, Dict, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8", line_buffering=True)
sys.path.insert(0, ".")

from rag.hybrid_retriever import HybridRetriever
from rag.query_processor import normalize_query

logging.basicConfig(level=logging.WARNING)


# ----------------------------------------------------------------------
# Set A: Phase 5C In-Scope (69 queries) Matching
# ----------------------------------------------------------------------
def match_chunk_to_evidence(chunk_meta: Dict[str, Any], req: Dict[str, Any]) -> bool:
    c_doc = str(chunk_meta.get("doc_id") or "")
    c_doc_no = str(chunk_meta.get("document_no") or "")
    c_art = str(chunk_meta.get("article_number") or "").strip()
    c_cl = str(chunk_meta.get("clause_number") or "").strip()
    c_pt = str(chunk_meta.get("point") or "").strip()

    req_doc = str(req.get("doc_id") or "").strip()
    req_art = str(req.get("article") or "").strip()
    req_cl = str(req.get("clause") or "").strip() if req.get("clause") is not None else ""
    req_pt = str(req.get("point") or "").strip() if req.get("point") is not None else ""

    if req_doc and (req_doc not in c_doc and req_doc not in c_doc_no):
        return False
    if req_art and c_art != req_art:
        return False
    if req_cl and c_cl != req_cl:
        return False
    if req_pt and c_pt.lower() != req_pt.lower():
        return False
    return True


def eval_set_a_phase5c(retriever: HybridRetriever, dataset_path: str = "data/evaluation/phase5c_eval_dataset.json") -> Dict[str, Any]:
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    in_scope = [q for q in data if q.get("query_type") == "in_scope"]
    total = len(in_scope)
    hits1, hits3, hits5, hits10 = 0, 0, 0, 0
    rr_list, rec5_list, latencies = [], [], []

    for q in in_scope:
        q_text = normalize_query(q["question"])
        req_evidence = q.get("required_evidence", [])
        if not req_evidence:
            continue

        t0 = time.perf_counter()
        retrieved = retriever.retrieve(q_text, top_k=10)
        lat = (time.perf_counter() - t0) * 1000
        latencies.append(lat)

        found_rank = None
        matched_reqs = set()
        for rank, chunk in enumerate(retrieved, start=1):
            meta = chunk.get("metadata", {})
            for idx, req in enumerate(req_evidence):
                if match_chunk_to_evidence(meta, req):
                    matched_reqs.add(idx)
                    if found_rank is None:
                        found_rank = rank

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

        # Recall of required evidence items in top 5
        top5_matched = set()
        for chunk in retrieved[:5]:
            meta = chunk.get("metadata", {})
            for idx, req in enumerate(req_evidence):
                if match_chunk_to_evidence(meta, req):
                    top5_matched.add(idx)
        r5 = len(top5_matched) / len(req_evidence) if req_evidence else 0.0
        rec5_list.append(r5)

    return {
        "dataset_name": "Phase 5C In-Scope (69 queries)",
        "total_queries": total,
        "hit@1": hits1 / total,
        "hit@3": hits3 / total,
        "hit@5": hits5 / total,
        "hit@10": hits10 / total,
        "mrr": statistics.mean(rr_list) if rr_list else 0.0,
        "recall@5": statistics.mean(rec5_list) if rec5_list else 0.0,
        "mean_latency_ms": statistics.mean(latencies) if latencies else 0.0,
    }


# ----------------------------------------------------------------------
# Set B: Phase 4 Gold (145 queries) Matching
# ----------------------------------------------------------------------
def is_chunk_relevant_set_b(chunk: Dict[str, Any], gold_q: Dict[str, Any]) -> bool:
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


def eval_set_b_phase4(retriever: HybridRetriever, dataset_path: str = "data/evaluation/retrieval_gold.json") -> Dict[str, Any]:
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    total = len(data)
    hits1, hits3, hits5, hits10 = 0, 0, 0, 0
    rr_list, rec5_list, latencies = [], [], []

    for q in data:
        q_text = normalize_query(q["question"])
        gold_cids = set(q.get("relevant_chunk_ids", []))

        t0 = time.perf_counter()
        retrieved = retriever.retrieve(q_text, top_k=10)
        lat = (time.perf_counter() - t0) * 1000
        latencies.append(lat)

        found_rank = None
        for rank, chunk in enumerate(retrieved, start=1):
            if is_chunk_relevant_set_b(chunk, q):
                if found_rank is None:
                    found_rank = rank

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

        # Recall@5
        ret_cids = {c["chunk_id"] for c in retrieved[:5]}
        if gold_cids:
            r5 = len(gold_cids & ret_cids) / len(gold_cids)
        else:
            r5 = 1.0 if (found_rank and found_rank <= 5) else 0.0
        rec5_list.append(r5)

    return {
        "dataset_name": "Phase 4 Gold (145 queries)",
        "total_queries": total,
        "hit@1": hits1 / total,
        "hit@3": hits3 / total,
        "hit@5": hits5 / total,
        "hit@10": hits10 / total,
        "mrr": statistics.mean(rr_list) if rr_list else 0.0,
        "recall@5": statistics.mean(rec5_list) if rec5_list else 0.0,
        "mean_latency_ms": statistics.mean(latencies) if latencies else 0.0,
    }


def main():
    print("=" * 80)
    print("PHASE 5G.1 - TRUE CORE REGRESSION BENCHMARK (APPLES-TO-APPLES)")
    print("=" * 80)

    print("\n[1/4] Initializing V1 Retriever (storage/chroma + storage/bm25)...")
    r_v1 = HybridRetriever(index_version="v1")

    print("[2/4] Initializing V2 Retriever (storage/chroma_v2 + storage/bm25_v2)...")
    r_v2 = HybridRetriever(index_version="v2")

    # Benchmark Set A (69 queries)
    print("\n[3/4] Evaluating Set A (Phase 5C In-Scope: 69 queries)...")
    res_a_v1 = eval_set_a_phase5c(r_v1)
    res_a_v2 = eval_set_a_phase5c(r_v2)

    # Benchmark Set B (145 queries)
    print("\n[4/4] Evaluating Set B (Phase 4 Gold: 145 queries)...")
    res_b_v1 = eval_set_b_phase4(r_v1)
    res_b_v2 = eval_set_b_phase4(r_v2)

    def print_comparison_table(title: str, v1: Dict[str, Any], v2: Dict[str, Any]):
        print("\n" + "-" * 75)
        print(f"BENCHMARK: {title} ({v1['total_queries']} queries)")
        print("-" * 75)
        print(f"{'Metric':<20} | {'V1 (Baseline)':<15} | {'V2 (Candidate)':<15} | {'Delta (v2 - v1)':<15}")
        print("-" * 75)
        for m in ["hit@1", "hit@3", "hit@5", "hit@10", "mrr", "recall@5"]:
            val_v1 = v1[m]
            val_v2 = v2[m]
            delta = val_v2 - val_v1
            pct_str = f"{delta * 100:+.2f}%" if "hit" in m or "recall" in m else f"{delta:+.4f}"
            fmt_v1 = f"{val_v1 * 100:.2f}%" if "hit" in m or "recall" in m else f"{val_v1:.4f}"
            fmt_v2 = f"{val_v2 * 100:.2f}%" if "hit" in m or "recall" in m else f"{val_v2:.4f}"
            print(f"{m.upper():<20} | {fmt_v1:<15} | {fmt_v2:<15} | {pct_str:<15}")

        lat_v1 = v1["mean_latency_ms"]
        lat_v2 = v2["mean_latency_ms"]
        d_lat = lat_v2 - lat_v1
        print(f"{'LATENCY (ms)':<20} | {lat_v1:<15.1f} | {lat_v2:<15.1f} | {d_lat:+<15.1f}")
        print("-" * 75)

    print_comparison_table("Set A: Phase 5C In-Scope", res_a_v1, res_a_v2)
    print_comparison_table("Set B: Phase 4 Gold (145)", res_b_v1, res_b_v2)

    # Save to file
    out_dir = Path("evaluation/results")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "core_regression_apples_to_apples.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "set_a_phase5c": {"v1": res_a_v1, "v2": res_a_v2},
            "set_b_phase4": {"v1": res_b_v1, "v2": res_b_v2},
        }, f, ensure_ascii=False, indent=2)

    print(f"\nAll comparison data saved to: {out_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()
