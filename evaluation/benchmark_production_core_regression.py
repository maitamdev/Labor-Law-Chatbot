# -*- coding: utf-8 -*-
"""
VietLabor AI - Phase 5G.2 Production Core Regression Benchmark
Compares Production V1 vs Production V2 through the ACTUAL end-to-end production path:
Question -> QueryRouter -> Hybrid Retrieval -> LegalIssueParser -> EvidenceSelector -> Evidence Lock -> final evidence set

Tests:
- Set A: Phase 5C In-Scope (69 frozen core queries with strict required evidence matching)
- Set B: Phase 4 Gold Benchmark (155 queries / 145 in-scope queries)
Measures:
- Evidence Top-1 Accuracy
- Gold Evidence Recall
- Citation Support
- Citation Completeness
- Citation Precision
- Mean Latency

Proves whether DomainRouter + EvidenceSelector eliminate the ~7% collision regression observed
in raw retrieval.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
import re
import statistics
import sys
import time
from typing import Any, Dict, List, Set

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8", line_buffering=True)
sys.path.insert(0, ".")

from rag.evidence_selector import EvidenceSelector
from rag.hybrid_retriever import HybridRetriever
from rag.legal_issue_parser import LegalIssueParser
from rag.query_router import QueryRouter

logging.basicConfig(level=logging.WARNING)


def normalize_query(q: str) -> str:
    q = re.sub(r"\s+", " ", q).strip()
    return q


def match_chunk_to_evidence(chunk_meta: Dict[str, Any], req: Dict[str, Any]) -> bool:
    c_doc = str(chunk_meta.get("doc_id") or "")
    c_doc_no = str(chunk_meta.get("document_no") or "")
    c_art = str(chunk_meta.get("article_number") or "").strip()
    c_cl = str(chunk_meta.get("clause_number") or "").strip()
    c_pt = str(chunk_meta.get("point") or "").strip()

    req_doc = str(req.get("doc_id") or "").strip()
    req_art = str(req.get("article") or req.get("article_number") or "").strip()
    req_cl = str(req.get("clause") or req.get("clause_number") or "").strip() if (req.get("clause") is not None or req.get("clause_number") is not None) else ""
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


def evaluate_production_set_a(
    retriever: HybridRetriever,
    router: QueryRouter,
    selector: EvidenceSelector,
    issue_parser: LegalIssueParser,
    dataset_path: str = "data/evaluation/phase5c_eval_dataset.json",
    top_k: int = 35,
) -> Dict[str, Any]:
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    in_scope = [q for q in data if q.get("query_type") == "in_scope"]
    total = len(in_scope)
    top1_correct = 0
    support_list = []
    recall_list = []
    precision_list = []
    latencies = []

    for q in in_scope:
        q_text = normalize_query(q["question"])
        req_evidence = q.get("required_evidence", [])
        if not req_evidence:
            continue

        t0 = time.perf_counter()

        # Step 1: Domain Router
        route_decision = router.route(q_text)

        # Step 2: Hybrid Retrieval
        query_for_ret = route_decision.augmented_query or q_text
        raw_candidates = retriever.retrieve(query_for_ret, top_k=top_k)

        # Step 3: Issue Parser
        parsed_issue = issue_parser.parse(
            query=q_text,
            issue_id="ISSUE_1",
            context_facts={},
        )

        # Step 4: Evidence Selector with Domain Guidance
        sel_result = selector.select_evidence(
            issue=parsed_issue,
            candidate_chunks=raw_candidates,
        )

        lat_ms = (time.perf_counter() - t0) * 1000
        latencies.append(lat_ms)

        locked_blocks = sel_result.locked_evidence_blocks
        has_support = len(locked_blocks) > 0
        support_list.append(1.0 if has_support else 0.0)

        # Top 1 accuracy
        if locked_blocks:
            top_meta = locked_blocks[0].raw_chunk.get("metadata") or locked_blocks[0].raw_chunk
            if any(match_chunk_to_evidence(top_meta, req) for req in req_evidence):
                top1_correct += 1

        # Recall of required evidence
        matched_reqs = set()
        relevant_locked = 0
        for blk in locked_blocks:
            b_meta = blk.raw_chunk.get("metadata") or blk.raw_chunk
            is_rel = False
            for idx, req in enumerate(req_evidence):
                if match_chunk_to_evidence(b_meta, req):
                    matched_reqs.add(idx)
                    is_rel = True
            if is_rel:
                relevant_locked += 1

        rec = len(matched_reqs) / len(req_evidence) if req_evidence else (1.0 if has_support else 0.0)
        recall_list.append(rec)

        prec = relevant_locked / len(locked_blocks) if locked_blocks else 0.0
        precision_list.append(prec)

    return {
        "total_queries": total,
        "top1_accuracy": round(top1_correct / total * 100, 2),
        "gold_recall": round(statistics.mean(recall_list) * 100, 2),
        "citation_support": round(statistics.mean(support_list) * 100, 2),
        "citation_completeness": round(statistics.mean(recall_list) * 100, 2),
        "citation_precision": round(statistics.mean(precision_list) * 100, 2),
        "mean_latency_ms": round(statistics.mean(latencies), 1),
    }


def evaluate_production_set_b(
    retriever: HybridRetriever,
    router: QueryRouter,
    selector: EvidenceSelector,
    issue_parser: LegalIssueParser,
    dataset_path: str = "data/evaluation/retrieval_gold.json",
    top_k: int = 35,
) -> Dict[str, Any]:
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    total = len(data)
    top1_correct = 0
    support_list = []
    recall_list = []
    precision_list = []
    latencies = []

    for q in data:
        q_text = normalize_query(q["question"])
        gold_cids = set(q.get("relevant_chunk_ids", []))
        expected_docs = set(q.get("relevant_documents", []))
        expected_articles = set(str(a).strip() for a in q.get("relevant_articles", []))

        t0 = time.perf_counter()

        route_decision = router.route(q_text)
        query_for_ret = route_decision.augmented_query or q_text
        raw_candidates = retriever.retrieve(query_for_ret, top_k=top_k)

        parsed_issue = issue_parser.parse(
            query=q_text,
            issue_id="ISSUE_1",
            context_facts={},
        )
        sel_result = selector.select_evidence(
            issue=parsed_issue,
            candidate_chunks=raw_candidates,
        )

        lat_ms = (time.perf_counter() - t0) * 1000
        latencies.append(lat_ms)

        locked_blocks = sel_result.locked_evidence_blocks
        has_support = len(locked_blocks) > 0
        support_list.append(1.0 if has_support else 0.0)

        def is_chunk_relevant(chk: Dict[str, Any]) -> bool:
            cid = chk.get("chunk_id", "")
            if gold_cids and cid in gold_cids:
                return True
            meta = chk.get("metadata") or chk
            doc = meta.get("doc_id", "")
            art = str(meta.get("article_number") or "").strip()
            if expected_docs and doc not in expected_docs:
                return False
            if expected_articles and art in expected_articles:
                return True
            return False

        if locked_blocks:
            top_chunk = locked_blocks[0].raw_chunk
            if is_chunk_relevant(top_chunk):
                top1_correct += 1

        matched_cids = set()
        matched_articles = set()
        relevant_locked = 0

        for blk in locked_blocks:
            c = blk.raw_chunk
            if is_chunk_relevant(c):
                relevant_locked += 1
                cid = c.get("chunk_id", "")
                art = str((c.get("metadata") or c).get("article_number") or "").strip()
                if cid in gold_cids:
                    matched_cids.add(cid)
                if art in expected_articles:
                    matched_articles.add(art)

        if gold_cids:
            rec = len(matched_cids) / len(gold_cids)
        elif expected_articles:
            rec = len(matched_articles) / len(expected_articles)
        else:
            rec = 1.0 if relevant_locked > 0 else 0.0

        if expected_articles and len(matched_articles) > 0:
            rec = max(rec, len(matched_articles) / len(expected_articles))

        recall_list.append(rec)
        prec = relevant_locked / len(locked_blocks) if locked_blocks else 0.0
        precision_list.append(prec)

    return {
        "total_queries": total,
        "top1_accuracy": round(top1_correct / total * 100, 2),
        "gold_recall": round(statistics.mean(recall_list) * 100, 2),
        "citation_support": round(statistics.mean(support_list) * 100, 2),
        "citation_completeness": round(statistics.mean(recall_list) * 100, 2),
        "citation_precision": round(statistics.mean(precision_list) * 100, 2),
        "mean_latency_ms": round(statistics.mean(latencies), 1),
    }


def run_production_comparison():
    router = QueryRouter()
    selector = EvidenceSelector()
    issue_parser = LegalIssueParser()

    print("=" * 85)
    print("PHASE 5G.2 - PRODUCTION CORE REGRESSION BENCHMARK")
    print("Evaluating ACTUAL production pipeline: Router -> Retriever -> Selector -> Lock")
    print("=" * 85)

    print("\n[1/4] Running Production V1 on Set A (Phase 5C: 69 queries)...")
    r_v1 = HybridRetriever(index_version="v1")
    v1_set_a = evaluate_production_set_a(r_v1, router, selector, issue_parser)

    print("[2/4] Running Production V2 on Set A (Phase 5C: 69 queries)...")
    r_v2 = HybridRetriever(index_version="v2")
    v2_set_a = evaluate_production_set_a(r_v2, router, selector, issue_parser)

    print("\n[3/4] Running Production V1 on Set B (Phase 4 Gold: 155 queries)...")
    v1_set_b = evaluate_production_set_b(r_v1, router, selector, issue_parser)

    print("[4/4] Running Production V2 on Set B (Phase 4 Gold: 155 queries)...")
    v2_set_b = evaluate_production_set_b(r_v2, router, selector, issue_parser)

    def print_comparison(title: str, v1: Dict[str, Any], v2: Dict[str, Any]):
        print("\n" + "=" * 85)
        print(f"PRODUCTION BENCHMARK: {title} ({v1['total_queries']} queries)")
        print("=" * 85)
        print(f"{'Metric':<25} | {'Prod V1':<12} | {'Prod V2':<12} | {'Delta (V2 - V1)':<15}")
        print("-" * 80)
        for m in ["top1_accuracy", "gold_recall", "citation_support", "citation_completeness", "citation_precision"]:
            d = round(v2[m] - v1[m], 2)
            d_str = f"{d:+0.2f}%"
            print(f"{m:<25} | {v1[m]:>10.2f}% | {v2[m]:>10.2f}% | {d_str:>15}")
        lat_d = round(v2["mean_latency_ms"] - v1["mean_latency_ms"], 1)
        print(f"{'mean_latency_ms':<25} | {v1['mean_latency_ms']:>10.1f}ms | {v2['mean_latency_ms']:>10.1f}ms | {lat_d:>+14.1f}ms")

    print_comparison("Set A (Phase 5C In-Scope)", v1_set_a, v2_set_a)
    print_comparison("Set B (Phase 4 Gold Benchmark)", v1_set_b, v2_set_b)

    results = {
        "set_a_69": {
            "v1": v1_set_a,
            "v2": v2_set_a,
            "delta": {m: round(v2_set_a[m] - v1_set_a[m], 2) for m in v1_set_a},
        },
        "set_b_155": {
            "v1": v1_set_b,
            "v2": v2_set_b,
            "delta": {m: round(v2_set_b[m] - v1_set_b[m], 2) for m in v1_set_b},
        },
    }

    out_file = Path("evaluation/results/production_core_regression_results.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nSaved full results to: {out_file}")


if __name__ == "__main__":
    run_production_comparison()
