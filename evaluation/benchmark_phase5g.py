# -*- coding: utf-8 -*-
"""
VietLabor AI - Phase 5G Comprehensive Benchmark
Evaluates the Wave 1 Extended Legal Corpus & Domain Routing:
1. Core Regression Check (Zero degradation on core labor queries)
2. Domain Routing Accuracy (Target: >= 95%)
3. Extended Retrieval Metrics (Hit@1, Hit@3, Hit@5, Hit@10, MRR, Recall@5)
4. Extended Generation & Citation Quality (Citation support >= 90%, Zero phantom citations, Zero repealed law citations)
5. Cross-domain compound query handling
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
    getattr(sys.stdout, "reconfigure")(encoding='utf-8', line_buffering=True)
sys.path.insert(0, ".")

from rag.chain import VietLaborRAGChain
from rag.hybrid_retriever import HybridRetriever
from rag.query_processor import normalize_query
from rag.query_router import QueryRouter

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def match_chunk_to_evidence(chunk_meta: Dict[str, Any], req: Dict[str, Any]) -> bool:
    """Checks if a retrieved chunk matches a required gold evidence item."""
    c_doc = str(chunk_meta.get("doc_id") or "")
    c_doc_no = str(chunk_meta.get("document_no") or "")
    c_art = str(chunk_meta.get("article_number") or "").strip()
    c_cl = str(chunk_meta.get("clause_number") or "").strip()
    c_pt = str(chunk_meta.get("point") or "").strip()

    req_doc = str(req.get("doc_id") or "").strip()
    req_art = str(req.get("article") or "").strip()
    req_cl = str(req.get("clause") or "").strip() if req.get("clause") is not None else ""
    req_pt = str(req.get("point") or "").strip() if req.get("point") is not None else ""

    # Document check
    if req_doc and (req_doc not in c_doc and req_doc not in c_doc_no):
        return False
    # Article check
    if req_art and c_art != req_art:
        return False
    # Clause check (if specified)
    if req_cl and c_cl != req_cl:
        return False
    # Point check (if specified)
    if req_pt and c_pt.lower() != req_pt.lower():
        return False

    return True


def evaluate_core_regression(
    retriever: HybridRetriever,
    core_dataset_path: str = "data/evaluation/phase5c_eval_dataset.json",
) -> Dict[str, float]:
    """Evaluates core labor queries on V2 index to verify zero regression."""
    with open(core_dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    in_scope_queries = [q for q in data if q.get("query_type") == "in_scope"]
    total = len(in_scope_queries)
    if total == 0:
        return {}

    hits1 = 0
    hits3 = 0
    hits5 = 0
    hits10 = 0
    rr_list = []

    for q in in_scope_queries:
        q_text = normalize_query(q["question"])
        req_evidence = q.get("required_evidence", [])
        if not req_evidence:
            continue

        retrieved = retriever.retrieve(q_text, top_k=10)

        # Find first relevant rank
        found_rank = None
        for rank, chunk in enumerate(retrieved, start=1):
            meta = chunk.get("metadata", {})
            if any(match_chunk_to_evidence(meta, req) for req in req_evidence):
                found_rank = rank
                break

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

    mrr = statistics.mean(rr_list) if rr_list else 0.0
    return {
        "core_queries_count": total,
        "hit@1": hits1 / total,
        "hit@3": hits3 / total,
        "hit@5": hits5 / total,
        "hit@10": hits10 / total,
        "mrr": mrr,
    }


def evaluate_domain_routing(
    extended_dataset_path: str = "data/evaluation/extended_gold_set.json",
    core_dataset_path: str = "data/evaluation/phase5c_eval_dataset.json",
) -> Dict[str, Any]:
    """Measures domain router precision across extended and core queries."""
    router = QueryRouter()

    with open(extended_dataset_path, "r", encoding="utf-8") as f:
        extended_data = json.load(f)

    with open(core_dataset_path, "r", encoding="utf-8") as f:
        core_data = json.load(f)

    correct = 0
    total = 0
    domain_stats: Dict[str, Dict[str, int]] = {}

    # Test extended queries
    for item in extended_data:
        q_text = item["question"]
        exp_dom = item["expected_domain"]
        dec = router.route(q_text)
        pred_dom = dec.domain

        stats = domain_stats.setdefault(exp_dom, {"total": 0, "correct": 0})
        stats["total"] += 1
        total += 1

        if pred_dom == exp_dom or (exp_dom == "CROSS_DOMAIN" and dec.domain in ("CROSS_DOMAIN", "CORE_LABOR", "UNEMPLOYMENT_INSURANCE", "FOREIGN_WORKER")):
            stats["correct"] += 1
            correct += 1

    # Test sample of core queries
    core_sample = [q for q in core_data if q.get("query_type") == "in_scope"][:30]
    core_stats = domain_stats.setdefault("CORE_LABOR", {"total": 0, "correct": 0})
    for item in core_sample:
        q_text = item["question"]
        dec = router.route(q_text)
        core_stats["total"] += 1
        total += 1
        if dec.domain == "CORE_LABOR":
            core_stats["correct"] += 1
            correct += 1

    overall_acc = correct / total if total > 0 else 0.0
    return {
        "total_queries": total,
        "overall_accuracy": overall_acc,
        "domain_breakdown": domain_stats,
    }


def evaluate_extended_retrieval(
    retriever: HybridRetriever,
    extended_dataset_path: str = "data/evaluation/extended_gold_set.json",
) -> Dict[str, Any]:
    """Evaluates retrieval accuracy across the 65 extended queries."""
    with open(extended_dataset_path, "r", encoding="utf-8") as f:
        queries = json.load(f)

    total = len(queries)
    hits1 = 0
    hits3 = 0
    hits5 = 0
    hits10 = 0
    rr_list = []
    recall5_list = []
    latencies = []

    domain_hits: Dict[str, Dict[str, int]] = {}

    for q in queries:
        qid = q["id"]
        q_text = normalize_query(q["question"])
        dom = q["domain"]
        gold_chunks = set(q.get("relevant_chunk_ids", []))
        rel_docs = set(q.get("relevant_documents", []))
        rel_arts = set(q.get("relevant_articles", []))

        d_stat = domain_hits.setdefault(dom, {"total": 0, "hit@5": 0, "mrr_sum": 0.0})
        d_stat["total"] += 1

        t0 = time.perf_counter()
        retrieved = retriever.retrieve(q_text, top_k=10)
        lat = (time.perf_counter() - t0) * 1000
        latencies.append(lat)

        found_rank = None
        retrieved_cids = [c["chunk_id"] for c in retrieved]

        for rank, chunk in enumerate(retrieved, start=1):
            cid = chunk["chunk_id"]
            meta = chunk.get("metadata", {})
            c_doc = str(meta.get("doc_id") or "")
            c_art = str(meta.get("article_number") or "").strip()

            is_match = False
            if cid in gold_chunks:
                is_match = True
            elif any(d in c_doc for d in rel_docs) and c_art in rel_arts:
                is_match = True

            if is_match and found_rank is None:
                found_rank = rank

        if found_rank is not None:
            if found_rank <= 1:
                hits1 += 1
            if found_rank <= 3:
                hits3 += 1
            if found_rank <= 5:
                hits5 += 1
                d_stat["hit@5"] += 1
            if found_rank <= 10:
                hits10 += 1
            rr = 1.0 / found_rank
            rr_list.append(rr)
            d_stat["mrr_sum"] += rr
        else:
            rr_list.append(0.0)

        # Recall@5
        top5_cids = set(retrieved_cids[:5])
        matched_gold = len(gold_chunks & top5_cids)
        r5 = matched_gold / len(gold_chunks) if gold_chunks else (1.0 if found_rank and found_rank <= 5 else 0.0)
        recall5_list.append(r5)

    mrr = statistics.mean(rr_list) if rr_list else 0.0
    rec5 = statistics.mean(recall5_list) if recall5_list else 0.0

    return {
        "total_queries": total,
        "hit@1": hits1 / total,
        "hit@3": hits3 / total,
        "hit@5": hits5 / total,
        "hit@10": hits10 / total,
        "mrr": mrr,
        "recall@5": rec5,
        "latency_ms": {
            "mean": statistics.mean(latencies),
            "median": statistics.median(latencies),
            "p95": sorted(latencies)[int(len(latencies) * 0.95)],
        },
        "domain_metrics": {
            d: {
                "hit@5": s["hit@5"] / s["total"] if s["total"] else 0,
                "mrr": s["mrr_sum"] / s["total"] if s["total"] else 0,
            }
            for d, s in domain_hits.items()
        },
    }


def evaluate_extended_generation(
    chain: VietLaborRAGChain,
    extended_dataset_path: str = "data/evaluation/extended_gold_set.json",
    sample_size: Optional[int] = None,
) -> Dict[str, Any]:
    """Runs full generation benchmark on extended queries."""
    with open(extended_dataset_path, "r", encoding="utf-8") as f:
        queries = json.load(f)

    if sample_size and sample_size < len(queries):
        # Evenly select across domains
        sampled = []
        by_dom: Dict[str, List[Dict[str, Any]]] = {}
        for q in queries:
            by_dom.setdefault(q["domain"], []).append(q)
        per_dom = max(1, sample_size // len(by_dom))
        for dom, qlist in by_dom.items():
            sampled.extend(qlist[:per_dom])
        queries = sampled

    total = len(queries)
    supported_answers = 0
    total_required_facts = 0
    supported_facts = 0
    phantom_citations = 0
    repealed_law_citations = 0
    latencies = []

    REPEALED_INDICATORS = ["152/2020", "70/2023", "28/2015", "luật việc làm 2013", "lvl 2013"]

    results_detail = []

    for i, q in enumerate(queries, start=1):
        q_text = q["question"]
        dom = q["domain"]
        expected_facts = q.get("expected_answer_facts", [])
        gold_chunks = set(q.get("relevant_chunk_ids", []))
        rel_docs = set(q.get("relevant_documents", []))
        rel_arts = set(q.get("relevant_articles", []))

        chain.memory.clear()
        t0 = time.perf_counter()
        res = chain.run(q_text, update_memory=False)
        lat = (time.perf_counter() - t0) * 1000
        latencies.append(lat)

        val = res.validated_response
        ans = val.final_answer.lower()
        cited_chunks = val.cited_chunk_ids

        # Check citation groundedness
        is_supported = len(cited_chunks) > 0 and not val.abstain
        if is_supported:
            supported_answers += 1

        # Check facts
        for fact in expected_facts:
            total_required_facts += 1
            # Check keywords of fact in answer
            fact_kw = [w for w in fact.lower().split() if len(w) > 3][:4]
            if any(kw in ans for kw in fact_kw):
                supported_facts += 1

        # Check phantom citations (cited chunk IDs not in context registry)
        for cid in cited_chunks:
            if cid not in res.formatted_context.chunk_metadata_registry:
                phantom_citations += 1

        # Check repealed law hallucination
        for rep in REPEALED_INDICATORS:
            if rep in ans or any(rep in cid.lower() for cid in cited_chunks):
                repealed_law_citations += 1

        results_detail.append({
            "id": q["id"],
            "domain": dom,
            "question": q_text,
            "is_supported": is_supported,
            "cited_chunks": cited_chunks,
            "latency_ms": lat,
        })

    fact_completeness = supported_facts / total_required_facts if total_required_facts > 0 else 1.0
    citation_support_rate = supported_answers / total if total > 0 else 0.0

    return {
        "evaluated_queries": total,
        "citation_support_rate": citation_support_rate,
        "fact_completeness_rate": fact_completeness,
        "phantom_citations_count": phantom_citations,
        "repealed_law_citations_count": repealed_law_citations,
        "generation_latency_ms": {
            "mean": statistics.mean(latencies) if latencies else 0.0,
            "median": statistics.median(latencies) if latencies else 0.0,
        },
        "details": results_detail,
    }


def main():
    print("=" * 75)
    print("PHASE 5G – CURRENT-LAW CORPUS EXPANSION & DOMAIN ROUTING BENCHMARK")
    print("=" * 75)

    retriever_v2 = HybridRetriever(index_version="v2")
    chain_v2 = VietLaborRAGChain(hybrid_retriever=retriever_v2, index_version="v2")

    # 1. Domain Routing Benchmark
    print("\n[1/4] Evaluating Domain Routing Accuracy...")
    router_results = evaluate_domain_routing()
    print(f"  Overall Accuracy: {router_results['overall_accuracy'] * 100:.2f}% ({router_results['total_queries']} queries)")
    for dom, st in router_results["domain_breakdown"].items():
        acc = (st["correct"] / st["total"] * 100) if st["total"] else 0
        print(f"    - {dom}: {acc:.1f}% ({st['correct']}/{st['total']})")

    # 2. Core Regression Benchmark
    print("\n[2/4] Evaluating Core Regression (Baseline Preservation)...")
    core_results = evaluate_core_regression(retriever_v2)
    print(f"  Core Queries: {core_results['core_queries_count']}")
    print(f"  Core Hit@1:  {core_results['hit@1'] * 100:.2f}%")
    print(f"  Core Hit@3:  {core_results['hit@3'] * 100:.2f}%")
    print(f"  Core Hit@5:  {core_results['hit@5'] * 100:.2f}%")
    print(f"  Core Hit@10: {core_results['hit@10'] * 100:.2f}%")
    print(f"  Core MRR:    {core_results['mrr']:.4f}")

    # 3. Extended Retrieval Benchmark
    print("\n[3/4] Evaluating Extended Retrieval on 65 Gold Queries...")
    ext_retrieval = evaluate_extended_retrieval(retriever_v2)
    print(f"  Extended Hit@1:  {ext_retrieval['hit@1'] * 100:.2f}%")
    print(f"  Extended Hit@3:  {ext_retrieval['hit@3'] * 100:.2f}%")
    print(f"  Extended Hit@5:  {ext_retrieval['hit@5'] * 100:.2f}%")
    print(f"  Extended Hit@10: {ext_retrieval['hit@10'] * 100:.2f}%")
    print(f"  Extended MRR:    {ext_retrieval['mrr']:.4f}")
    print(f"  Extended Recall@5: {ext_retrieval['recall@5'] * 100:.2f}%")
    print(f"  Mean Latency:    {ext_retrieval['latency_ms']['mean']:.1f}ms")
    print("  Per-Domain Performance:")
    for dom, met in ext_retrieval["domain_metrics"].items():
        print(f"    - {dom}: Hit@5 = {met['hit@5'] * 100:.1f}%, MRR = {met['mrr']:.4f}")

    # 4. Extended End-to-End Generation Benchmark (Test 16 queries across domains)
    print("\n[4/4] Evaluating Extended End-to-End Generation & Citation Support...")
    ext_gen = evaluate_extended_generation(chain_v2, sample_size=16)
    print(f"  Evaluated Queries:        {ext_gen['evaluated_queries']}")
    print(f"  Citation Support Rate:    {ext_gen['citation_support_rate'] * 100:.2f}% (Target: >= 90%)")
    print(f"  Fact Completeness Rate:   {ext_gen['fact_completeness_rate'] * 100:.2f}% (Target: >= 90%)")
    print(f"  Phantom Citations:        {ext_gen['phantom_citations_count']} (Target: 0)")
    print(f"  Repealed Law Citations:   {ext_gen['repealed_law_citations_count']} (Target: 0)")

    # Save benchmark results
    out_dir = Path("evaluation/results")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "phase5g_benchmark_results.json"
    full_results = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "domain_routing": router_results,
        "core_regression": core_results,
        "extended_retrieval": ext_retrieval,
        "extended_generation": ext_gen,
    }
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(full_results, f, ensure_ascii=False, indent=2)

    print(f"\nAll benchmark results saved to: {out_file}")
    print("=" * 75)


if __name__ == "__main__":
    main()
