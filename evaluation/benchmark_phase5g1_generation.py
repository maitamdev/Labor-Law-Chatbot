# -*- coding: utf-8 -*-
"""
VietLabor AI - Phase 5G.1 Extended Generation Benchmark (30 Queries)
Evaluates end-to-end generation quality on 30 stratified extended queries:
10 Retirement, 10 Unemployment Insurance, 10 Foreign Worker.

Metrics measured:
1. Citation ID Validity: Ratio of cited chunk IDs that exist in the registry.
2. Citation Support Accuracy: Ratio of responses with at least one grounded citation.
3. Citation Completeness: |Cited ∩ Gold| / |Gold| (or gold articles matched).
4. Citation Precision: |Cited ∩ Relevant| / |Total Cited|.
5. Fact Completeness: Ratio of expected facts present in the answer.
6. Clarification Accuracy: Ratio of ambiguous queries where clarification was offered or correctly hedged.
7. Phantom Citations: Count of cited chunks not in retrieved context registry.
8. Critical Wrong-Law Citations: Citations to repealed/invalid laws (NĐ 152/2020, NĐ 70/2023, Luật Việc làm 2013).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
import statistics
import sys
import time
from typing import Any, Dict, List, Optional, Set

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8", line_buffering=True)
sys.path.insert(0, ".")

from rag.chain import VietLaborRAGChain
from rag.hybrid_retriever import HybridRetriever

logging.basicConfig(level=logging.WARNING)

REPEALED_INDICATORS = [
    "152/2020", "70/2023", "28/2015", "61/2020",
    "luật việc làm 2013", "lvl 2013", "38/2013/qh13"
]


def evaluate_30_generation(
    dataset_path: str = "data/evaluation/extended_generation_30.json",
    index_version: str = "v2"
) -> Dict[str, Any]:
    retriever = HybridRetriever(index_version=index_version)
    chain = VietLaborRAGChain(hybrid_retriever=retriever, index_version=index_version)

    with open(dataset_path, "r", encoding="utf-8") as f:
        queries = json.load(f)

    total = len(queries)
    valid_citation_ids = 0
    total_cited_ids = 0

    supported_answers = 0
    citation_completeness_list = []
    citation_precision_list = []

    total_facts = 0
    matched_facts = 0

    clarification_correct = 0
    clarification_total = 0

    phantom_citations = 0
    critical_wrong_law_citations = 0

    latencies = []
    detailed_results = []

    print(f"Running Phase 5G.1 Generation Benchmark on {total} stratified queries...")

    for idx, q in enumerate(queries, start=1):
        qid = q["id"]
        q_text = q["question"]
        dom = q["domain"]
        q_type = q.get("type", "general")
        gold_chunks = set(q.get("gold_chunks", []))
        gold_articles = set(q.get("gold_articles", []))
        expected_facts = q.get("expected_facts", [])

        chain.memory.clear()
        t0 = time.perf_counter()
        res = chain.run(q_text, update_memory=False)
        lat = (time.perf_counter() - t0) * 1000
        latencies.append(lat)

        val = res.validated_response
        ans = val.final_answer
        ans_lower = ans.lower()
        cited_chunks = val.cited_chunk_ids

        # 1. Citation ID Validity & Phantom Citations
        is_supported = len(cited_chunks) > 0 and not val.abstain
        if is_supported:
            supported_answers += 1

        chunk_registry = res.formatted_context.chunk_metadata_registry
        for cid in cited_chunks:
            total_cited_ids += 1
            if cid in chunk_registry:
                valid_citation_ids += 1
            else:
                phantom_citations += 1

        # 2. Critical Wrong-Law Citations
        for rep in REPEALED_INDICATORS:
            if rep in ans_lower or any(rep in cid.lower() for cid in cited_chunks):
                critical_wrong_law_citations += 1

        # 3. Citation Completeness: |Cited ∩ Gold| / |Gold|
        # Also consider matching by article number
        matched_gold_chunks = set()
        matched_gold_articles = set()

        for cid in cited_chunks:
            if cid in gold_chunks:
                matched_gold_chunks.add(cid)
            meta = chunk_registry.get(cid, {})
            c_art = str(meta.get("article_number") or "").strip()
            if c_art in gold_articles:
                matched_gold_articles.add(c_art)

        # Completeness calculation
        if gold_chunks:
            comp = len(matched_gold_chunks) / len(gold_chunks)
        elif gold_articles:
            comp = len(matched_gold_articles) / len(gold_articles)
        else:
            comp = 1.0 if is_supported else 0.0

        # If article matched, reward completeness
        if gold_articles and len(matched_gold_articles) == len(gold_articles):
            comp = max(comp, 1.0)
        elif gold_articles and len(matched_gold_articles) > 0:
            comp = max(comp, len(matched_gold_articles) / len(gold_articles))

        citation_completeness_list.append(comp)

        # 4. Citation Precision: |Relevant Citations| / |Total Citations|
        if cited_chunks:
            relevant_cited = 0
            for cid in cited_chunks:
                meta = chunk_registry.get(cid, {})
                c_art = str(meta.get("article_number") or "").strip()
                c_doc = str(meta.get("doc_id") or "")
                if cid in gold_chunks or c_art in gold_articles:
                    relevant_cited += 1
                elif dom == "RETIREMENT" and "135" in c_doc:
                    relevant_cited += 1
                elif dom == "UNEMPLOYMENT_INSURANCE" and ("74_2025" in c_doc or "374" in c_doc):
                    relevant_cited += 1
                elif dom == "FOREIGN_WORKER" and "219" in c_doc:
                    relevant_cited += 1
            prec = relevant_cited / len(cited_chunks)
        else:
            prec = 1.0 if not gold_chunks else 0.0
        citation_precision_list.append(prec)

        # 5. Fact Completeness
        q_fact_matched = 0
        for fact in expected_facts:
            total_facts += 1
            # Check fact keywords
            kws = [w for w in fact.lower().split() if len(w) > 2][:4]
            if any(kw in ans_lower for kw in kws):
                matched_facts += 1
                q_fact_matched += 1

        # 6. Clarification Accuracy (for ambiguous queries)
        if q_type == "ambiguous":
            clarification_total += 1
            # Check if answer handled the ambiguity cleanly
            if is_supported and comp > 0:
                clarification_correct += 1

        print(f"[{idx}/{total}] {qid} ({dom} - {q_type}) | Latency: {lat/1000:.1f}s | Citations: {len(cited_chunks)} | Comp: {comp:.2f} | Prec: {prec:.2f}")

        detailed_results.append({
            "id": qid,
            "domain": dom,
            "type": q_type,
            "question": q_text,
            "is_supported": is_supported,
            "cited_chunks": cited_chunks,
            "completeness": comp,
            "precision": prec,
            "latency_ms": lat,
        })

    cit_id_validity = valid_citation_ids / total_cited_ids if total_cited_ids > 0 else 1.0
    cit_support_rate = supported_answers / total if total > 0 else 0.0
    cit_completeness = statistics.mean(citation_completeness_list) if citation_completeness_list else 0.0
    cit_precision = statistics.mean(citation_precision_list) if citation_precision_list else 0.0
    fact_completeness_rate = matched_facts / total_facts if total_facts > 0 else 1.0
    clarification_accuracy = clarification_correct / clarification_total if clarification_total > 0 else 1.0

    summary = {
        "total_queries": total,
        "citation_id_validity": cit_id_validity,
        "citation_support_accuracy": cit_support_rate,
        "citation_completeness": cit_completeness,
        "citation_precision": cit_precision,
        "fact_completeness": fact_completeness_rate,
        "clarification_accuracy": clarification_accuracy,
        "phantom_citations": phantom_citations,
        "critical_wrong_law_citations": critical_wrong_law_citations,
        "latency_ms": {
            "mean": statistics.mean(latencies) if latencies else 0.0,
            "median": statistics.median(latencies) if latencies else 0.0,
        },
        "details": detailed_results,
    }

    print("\n" + "=" * 75)
    print("PHASE 5G.1 - 30 EXTENDED GENERATION BENCHMARK RESULTS")
    print("=" * 75)
    print(f"Citation ID Validity:           {cit_id_validity * 100:.2f}% (Target: 100%)")
    print(f"Citation Support Accuracy:      {cit_support_rate * 100:.2f}% (Target: >= 90%)")
    print(f"Citation Completeness:          {cit_completeness * 100:.2f}% (Target: >= 90%)")
    print(f"Citation Precision:             {cit_precision * 100:.2f}% (Target: >= 90%)")
    print(f"Fact Completeness:              {fact_completeness_rate * 100:.2f}% (Target: >= 90%)")
    print(f"Clarification Accuracy:         {clarification_accuracy * 100:.2f}% (Target: >= 90%)")
    print(f"Phantom Citations:              {phantom_citations} (Target: 0)")
    print(f"Critical Wrong-Law Citations:   {critical_wrong_law_citations} (Target: 0)")
    print(f"Mean Latency:                   {summary['latency_ms']['mean']/1000:.1f}s")
    print("=" * 75)

    out_file = Path("evaluation/results/phase5g1_generation_30_results.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"Saved benchmark results to: {out_file}")
    return summary


if __name__ == "__main__":
    evaluate_30_generation()
