# -*- coding: utf-8 -*-
"""
VietLabor AI - Phase 5H Wave 2 Regression Benchmark
Verifies zero regression on:
1. Frozen CORE benchmark (data/evaluation/phase5c_eval_dataset.json - 69 in-scope queries)
2. Frozen Wave 1 benchmark (data/evaluation/extended_gold_set.json - 65 queries)
Compares V2 production path vs V3 production path.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
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


def evaluate_core_on_index(index_version: str) -> Dict[str, float]:
    retriever = HybridRetriever(index_version=index_version)
    router = QueryRouter()
    selector = EvidenceSelector()
    issue_parser = LegalIssueParser()

    with open("data/evaluation/phase5c_eval_dataset.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    in_scope = [q for q in data if q.get("query_type") == "in_scope"]
    top1_correct = 0
    support_correct = 0
    total = len(in_scope)

    for q in in_scope:
        q_text = q["question"]
        req_evidence = q.get("required_evidence", [])
        if not req_evidence:
            continue

        route_dec = router.route(q_text)
        candidates = retriever.retrieve(q_text, top_k=20)
        issue = issue_parser.parse(q_text)
        sel_result = selector.select_evidence(issue, candidates)
        locked = sel_result.locked_evidence_blocks

        if locked:
            support_correct += 1
            top_meta = locked[0].raw_chunk.get("metadata", {})
            if any(match_chunk_to_evidence(top_meta, req) for req in req_evidence):
                top1_correct += 1
        elif candidates:
            top_meta = candidates[0].get("metadata", {})
            if any(match_chunk_to_evidence(top_meta, req) for req in req_evidence):
                top1_correct += 1

    return {
        "top1_acc": (top1_correct / total) * 100,
        "support_acc": (support_correct / total) * 100,
        "total": total,
    }


def evaluate_wave1_on_index(index_version: str) -> Dict[str, float]:
    retriever = HybridRetriever(index_version=index_version)
    router = QueryRouter()

    with open("data/evaluation/extended_gold_set.json", "r", encoding="utf-8") as f:
        queries = json.load(f)

    total = len(queries)
    hits5 = 0
    mrr_list = []

    for q in queries:
        q_text = q["question"]
        retrieved = retriever.retrieve(q_text, top_k=10)
        found_rank = None

        rel_cids = q.get("relevant_chunk_ids", [])
        rel_docs = q.get("relevant_documents", [])
        rel_arts = [str(a) for a in q.get("relevant_articles", [])]

        for rank, chunk in enumerate(retrieved, start=1):
            meta = chunk.get("metadata", {})
            cid = chunk.get("chunk_id") or meta.get("chunk_id", "")
            doc_id = chunk.get("doc_id") or meta.get("doc_id", "")
            art = str(chunk.get("article_number") or meta.get("article_number") or "")

            if cid in rel_cids or (doc_id in rel_docs and art in rel_arts):
                found_rank = rank
                break

        if found_rank is not None:
            if found_rank <= 5:
                hits5 += 1
            mrr_list.append(1.0 / found_rank)
        else:
            mrr_list.append(0.0)

    return {
        "hit5": (hits5 / total) * 100,
        "mrr": statistics.mean(mrr_list),
        "total": total,
    }


def main():
    print("=" * 80)
    print("VIETLABOR AI - PHASE 5H REGRESSION AUDIT (V2 vs V3)")
    print("=" * 80)

    # 1. Evaluate Core on V2 vs V3
    print("\n[1/2] Evaluating Frozen Core (69 in-scope queries)...")
    core_v2 = evaluate_core_on_index("v2")
    core_v3 = evaluate_core_on_index("v3")
    print(f"  V2 Core Top-1 Accuracy: {core_v2['top1_acc']:.2f}% (Support: {core_v2['support_acc']:.2f}%)")
    print(f"  V3 Core Top-1 Accuracy: {core_v3['top1_acc']:.2f}% (Support: {core_v3['support_acc']:.2f}%)")
    core_diff = core_v3['top1_acc'] - core_v2['top1_acc']
    print(f"  Core Delta: {core_diff:+.2f}%")

    # 2. Evaluate Wave 1 on V2 vs V3
    print("\n[2/2] Evaluating Frozen Wave 1 (65 queries)...")
    w1_v2 = evaluate_wave1_on_index("v2")
    w1_v3 = evaluate_wave1_on_index("v3")
    print(f"  V2 Wave 1 Hit@5: {w1_v2['hit5']:.2f}% (MRR: {w1_v2['mrr']:.4f})")
    print(f"  V3 Wave 1 Hit@5: {w1_v3['hit5']:.2f}% (MRR: {w1_v3['mrr']:.4f})")
    w1_diff = w1_v3['hit5'] - w1_v2['hit5']
    print(f"  Wave 1 Delta: {w1_diff:+.2f}%")

    print("\n" + "=" * 80)
    core_no_regression = core_diff >= -0.01
    w1_no_regression = w1_diff >= -0.01
    all_pass = core_no_regression and w1_no_regression
    print(f"Regression Gate Status: {'PASS (Zero Material Production Regression)' if all_pass else 'FAIL'}")
    print("=" * 80)

    # Save results
    out_path = Path("evaluation/results/wave2_regression_audit.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "core_v2": core_v2,
            "core_v3": core_v3,
            "core_delta": core_diff,
            "wave1_v2": w1_v2,
            "wave1_v3": w1_v3,
            "wave1_delta": w1_diff,
            "all_pass": all_pass,
        }, f, indent=2)


if __name__ == "__main__":
    main()
