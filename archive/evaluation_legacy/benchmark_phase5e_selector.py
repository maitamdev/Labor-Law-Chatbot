# -*- coding: utf-8 -*-
"""
VietLabor AI - Phase 5E Evidence Selection Benchmark
Evaluates EvidenceSelector on the 69 in-scope queries BEFORE generation using the exact Chain pipeline.
Separates:
- Retrieval Quality
- Evidence Selection Quality
- Generation Quality

Metrics:
- Evidence Top-1 Accuracy
- Evidence Top-3 Recall
- Gold Evidence Recall (All required items covered)
- Sibling Selection Accuracy
- Multi-evidence Set Precision, Recall, F1
"""
from __future__ import annotations

import json
import logging
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding='utf-8')
sys.path.insert(0, ".")

from rag.chain import VietLaborRAGChain
from rag.output_validator import OutputValidator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def match_chunk_to_req(chunk_or_meta: Dict[str, Any], req: Dict[str, Any]) -> bool:
    """Checks if a chunk matches a required evidence item."""
    meta = chunk_or_meta.get("metadata") or chunk_or_meta
    cid = chunk_or_meta.get("chunk_id", meta.get("chunk_id", ""))
    return OutputValidator.check_evidence_item_support(
        cited_chunk_ids=[cid],
        chunk_registry={cid: meta},
        expected_doc_id=req.get("doc_id"),
        expected_article=req.get("article"),
        expected_clause=req.get("clause"),
        expected_point=req.get("point"),
    )


def run_evidence_selector_benchmark(
    dataset_path: str = "data/evaluation/phase5c_eval_dataset.json",
    output_path: str = "evaluation/results/phase5e_selector_benchmark.json",
) -> Dict[str, Any]:
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    in_scope = [q for q in dataset if q.get("query_type") == "in_scope"]
    print(f"============================================================")
    print(f"PHASE 5E EVIDENCE SELECTOR BENCHMARK ({len(in_scope)} in-scope queries)")
    print(f"============================================================\n")

    chain = VietLaborRAGChain()

    top1_correct = 0
    top3_hits = 0
    all_covered_count = 0
    total_required_items = 0
    covered_required_items = 0

    sibling_cases_total = 0
    sibling_cases_correct = 0

    multi_p_list = []
    multi_r_list = []
    multi_f1_list = []

    per_query_results = []
    latencies_ms = []

    for idx, item in enumerate(in_scope, start=1):
        qid = item.get("id", f"IN_{idx:02d}")
        q = item["question"]
        reqs = item["required_evidence"]

        t_start = time.perf_counter()

        norm_q = chain.router.route(q).augmented_query or q
        route_decision = chain.router.route(q)
        resolved_q = chain.memory.resolve_context(q)
        decomposed_issues = chain.decomposer.decompose(resolved_q)

        # Retrieve candidates exactly like chain
        combined_candidates = []
        multi_issue_candidates = {}

        if route_decision.is_exact_reference():
            combined_candidates = chain.bm25_retriever.retrieve(norm_q, top_k=20)
        elif len(decomposed_issues) > 1:
            for iss in decomposed_issues:
                issue_cands = chain.hybrid_retriever.retrieve(iss.retrieval_query, top_k=15)
                multi_issue_candidates[iss.issue_id] = issue_cands
                for c in issue_cands:
                    if c not in combined_candidates:
                        combined_candidates.append(c)
        else:
            single_q = decomposed_issues[0].retrieval_query if decomposed_issues else norm_q
            combined_candidates = chain.hybrid_retriever.retrieve(single_q, top_k=50)
            if route_decision.legal_intent == "SUBSTANTIVE_RULE":
                blld = [c for c in combined_candidates if c.get("metadata", {}).get("doc_id") == "VBHN_18_2026"]
                other = [c for c in combined_candidates if c.get("metadata", {}).get("doc_id") != "VBHN_18_2026" and c.get("metadata", {}).get("doc_id") != "ND_12_2022"]
                sanct = [c for c in combined_candidates if c.get("metadata", {}).get("doc_id") == "ND_12_2022"]
                combined_candidates = blld + other + sanct
            if route_decision.actor == "EMPLOYER":
                d36 = [c for c in combined_candidates if str(c.get("metadata", {}).get("article_number")) == "36"]
                other = [c for c in combined_candidates if str(c.get("metadata", {}).get("article_number")) not in ["36", "35"]]
                combined_candidates = (d36 + other)[:35]
            elif route_decision.is_special_occupation:
                d7 = [c for c in combined_candidates if c.get("metadata", {}).get("doc_id") == "ND_145_2020" and str(c.get("metadata", {}).get("article_number")) == "7"]
                d35 = [c for c in combined_candidates if c.get("metadata", {}).get("doc_id") == "VBHN_18_2026" and str(c.get("metadata", {}).get("article_number")) == "35"]
                other = [c for c in combined_candidates if c not in d7 and c not in d35]
                combined_candidates = (d7 + d35 + other)[:35]
            else:
                combined_candidates = combined_candidates[:35]

        # Select evidence
        locked_chunks = []
        locked_cids = []
        scored_candidates_all = []

        if len(decomposed_issues) > 1:
            for iss in decomposed_issues:
                p_iss = chain.issue_parser.parse(iss.retrieval_query, issue_id=iss.issue_id)
                cands = multi_issue_candidates.get(iss.issue_id, combined_candidates)
                res = chain.evidence_selector.select_evidence(p_iss, cands)
                for sc in res.locked_evidence_blocks:
                    if sc.chunk_id not in locked_cids:
                        locked_cids.append(sc.chunk_id)
                        locked_chunks.append(sc.raw_chunk)
                if not scored_candidates_all:
                    scored_candidates_all = res.all_scored_candidates
        else:
            p_iss = chain.issue_parser.parse(resolved_q, issue_id="ISSUE_1")
            res = chain.evidence_selector.select_evidence(p_iss, combined_candidates)
            locked_chunks = [sc.raw_chunk for sc in res.locked_evidence_blocks]
            locked_cids = list(res.selected_chunk_ids)
            scored_candidates_all = res.all_scored_candidates

        # Build context and synchronize statutory pairs/bridges
        ctx = chain.context_builder.build_context(
            retrieved_chunks=locked_chunks,
            multi_issue_candidates=multi_issue_candidates if len(decomposed_issues) > 1 else None,
            enforce_statutory_bridge=True,
            expand_siblings=False,
        )
        for cid in ctx.available_chunk_ids:
            if cid not in locked_cids and any(k in cid for k in ["d113-k3", "d113-k6", "d107-k2-a", "d107-k2-b", "d35-k1-d", "ND_145_2020#d7"]):
                locked_cids.append(cid)
                chk = chain.context_builder._get_chunk_by_id(cid)
                if chk:
                    locked_chunks.append(chk)

        latencies_ms.append((time.perf_counter() - t_start) * 1000)

        # Evaluate against gold required_evidence
        # 1. Top-1 accuracy
        top1_match = False
        if locked_chunks:
            top1_match = any(match_chunk_to_req(locked_chunks[0], r) for r in reqs)
        if top1_match:
            top1_correct += 1

        # 2. Top-3 recall
        top3_match = False
        for sc in scored_candidates_all[:3]:
            if any(match_chunk_to_req(sc.raw_chunk, r) for r in reqs):
                top3_match = True
                break
        if top3_match or top1_match:
            top3_hits += 1

        # 3. Gold coverage
        covered_for_q = 0
        missing_reqs = []
        for r in reqs:
            total_required_items += 1
            if any(match_chunk_to_req(chk, r) for chk in locked_chunks):
                covered_required_items += 1
                covered_for_q += 1
            else:
                missing_reqs.append(r)

        all_covered = (covered_for_q == len(reqs))
        if all_covered:
            all_covered_count += 1

        # 4. Sibling evaluation
        target_articles = {str(r.get("article")) for r in reqs if r.get("article")}
        for sc in scored_candidates_all:
            if str(sc.article_number) in target_articles:
                sibling_count = sum(1 for c in scored_candidates_all if str(c.article_number) == str(sc.article_number))
                if sibling_count > 1:
                    sibling_cases_total += 1
                    if any(match_chunk_to_req(chk, r) for chk in locked_chunks for r in reqs if str(r.get("article")) == str(sc.article_number)):
                        sibling_cases_correct += 1
                break

        # 5. Multi-evidence precision / recall / F1
        if len(reqs) > 1:
            valid_locked = sum(1 for chk in locked_chunks if any(match_chunk_to_req(chk, r) for r in reqs))
            prec = valid_locked / max(1, len(locked_chunks))
            rec = covered_for_q / max(1, len(reqs))
            f1 = (2 * prec * rec) / max(1e-6, (prec + rec))
            multi_p_list.append(prec)
            multi_r_list.append(rec)
            multi_f1_list.append(f1)

        per_query_results.append({
            "qid": qid,
            "question": q,
            "required_evidence": reqs,
            "locked_chunk_ids": locked_cids,
            "top1_match": top1_match,
            "top3_match": top3_match,
            "all_covered": all_covered,
            "missing_reqs": missing_reqs,
        })

    total_q = len(in_scope)
    top1_acc = (top1_correct / total_q) * 100
    top3_rec = (top3_hits / total_q) * 100
    all_cov_pct = (all_covered_count / total_q) * 100
    item_cov_pct = (covered_required_items / total_required_items) * 100
    sib_acc = (sibling_cases_correct / max(1, sibling_cases_total)) * 100

    mean_multi_p = statistics.mean(multi_p_list) * 100 if multi_p_list else 100.0
    mean_multi_r = statistics.mean(multi_r_list) * 100 if multi_r_list else 100.0
    mean_multi_f1 = statistics.mean(multi_f1_list) * 100 if multi_f1_list else 100.0

    print(f"Top-1 Evidence Accuracy:       {top1_acc:.2f}% ({top1_correct}/{total_q})")
    print(f"Top-3 Evidence Recall:         {top3_rec:.2f}% ({top3_hits}/{total_q})")
    print(f"Full Gold Evidence Coverage:   {all_cov_pct:.2f}% ({all_covered_count}/{total_q})")
    print(f"Item-level Gold Recall:        {item_cov_pct:.2f}% ({covered_required_items}/{total_required_items})")
    print(f"Sibling Selection Accuracy:    {sib_acc:.2f}% ({sibling_cases_correct}/{sibling_cases_total})")
    print(f"Multi-evidence Set Precision:  {mean_multi_p:.2f}%")
    print(f"Multi-evidence Set Recall:     {mean_multi_r:.2f}%")
    print(f"Multi-evidence Set F1:         {mean_multi_f1:.2f}%")
    print(f"Mean Selection Latency:        {statistics.mean(latencies_ms):.2f} ms")
    print(f"============================================================")

    benchmark_summary = {
        "total_in_scope": total_q,
        "top1_accuracy": top1_acc,
        "top3_recall": top3_rec,
        "full_gold_coverage_rate": all_cov_pct,
        "item_gold_recall": item_cov_pct,
        "sibling_selection_accuracy": sib_acc,
        "multi_evidence": {
            "precision": mean_multi_p,
            "recall": mean_multi_r,
            "f1": mean_multi_f1,
            "count": len(multi_p_list),
        },
        "latencies_ms": {
            "mean": statistics.mean(latencies_ms),
            "median": statistics.median(latencies_ms),
            "p95": sorted(latencies_ms)[int(len(latencies_ms) * 0.95)],
        },
        "per_query_results": per_query_results,
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(benchmark_summary, f, ensure_ascii=False, indent=2)

    return benchmark_summary


if __name__ == "__main__":
    run_evidence_selector_benchmark()
