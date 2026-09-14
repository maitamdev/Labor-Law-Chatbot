# -*- coding: utf-8 -*-
"""
VietLabor AI - Phase 5E Full Generation & Evidence Grounding Benchmark
Evaluates the full 99-query evaluation dataset:
- 69 in-scope
- 20 ambiguous
- 10 out-of-scope
- 5 compound
- 3 mandatory cases (A, B, C)
- 3 multi-turn scenarios

Metrics:
- Final Citation ID Validity (Gate: >= 99%, final visible phantom citations = 0)
- Raw LLM Evidence-ID Validity
- Citation Support Accuracy (Gate: >= 90%, Target: >= 95%)
- Citation Completeness (Gate: >= 90%, Target: >= 95%)
- Ambiguous Accuracy (Gate: >= 90%)
- Out-of-scope Accuracy (Gate: >= 95%)
- Compound fully-supported accuracy (Gate: >= 80%)
- Mandatory cases A, B, C (Gate: 100%)
- Critical wrong-law citations = 0
"""
from __future__ import annotations

import json
import logging
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding='utf-8', line_buffering=True)
sys.path.insert(0, ".")

from rag.chain import VietLaborRAGChain
from rag.output_validator import OutputValidator


def match_chunk_to_evidence(chunk_or_meta: Dict[str, Any], req: Dict[str, Any]) -> bool:
    meta = chunk_or_meta.get("metadata") or chunk_or_meta
    c_doc = str(meta.get("doc_id") or "")
    c_doc_no = str(meta.get("document_no") or "")
    c_art = str(meta.get("article_number") or "").strip()
    c_cl = str(meta.get("clause_number") or "").strip()
    c_pt = str(meta.get("point") or "").strip()

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


def run_phase5e_benchmark(dataset_path: str = "data/evaluation/phase5c_eval_dataset.json"):
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    print(f"Loaded {len(dataset)} evaluation items from {dataset_path}.")

    chain = VietLaborRAGChain()

    in_scope_items = [q for q in dataset if q["query_type"] == "in_scope"]
    ambiguous_items = [q for q in dataset if q["query_type"] == "ambiguous"]
    oos_items = [q for q in dataset if q["query_type"] == "out_of_scope"]
    compound_items = [q for q in dataset if q.get("topic") == "compound"]

    print(f"Breakdown: In-scope = {len(in_scope_items)}, Ambiguous = {len(ambiguous_items)}, Out-of-scope = {len(oos_items)}, Compound = {len(compound_items)}")

    # Telemetry
    retrieval_latencies = []
    selection_latencies = []
    llm_latencies = []
    total_latencies = []

    # Citation Validity Tracking
    total_raw_evidence_tokens = 0
    total_raw_valid_tokens = 0
    raw_invalid_tokens_list = []

    total_final_visible_citations = 0
    total_valid_final_citations = 0
    final_visible_phantom_citations = []

    # In-Scope Metrics
    fully_supported_questions = 0
    total_supported_evidence_items = 0
    total_required_evidence_items = 0

    failed_in_scope = []
    in_scope_results = []

    # Wrong law tracking
    critical_wrong_law_citations = []

    print("\n" + "=" * 60)
    print("RUNNING 69 IN-SCOPE QUERIES BENCHMARK (Phase 5E)")
    print("=" * 60)

    for i, item in enumerate(in_scope_items, 1):
        qid = item["id"]
        q_text = item["question"]
        req_evidence = item.get("required_evidence", [])

        chain.memory.clear()
        t0 = time.perf_counter()
        res = chain.run(q_text, update_memory=False)
        dur = time.perf_counter() - t0

        retrieval_latencies.append(res.retrieval_latency_ms)
        selection_latencies.append(res.selection_latency_ms)
        llm_latencies.append(res.llm_latency_ms)
        total_latencies.append(res.total_latency_ms)

        cited_cids = res.validated_response.cited_chunk_ids
        rejected_cids = res.validated_response.rejected_chunk_ids

        raw_validity = res.validated_response.raw_evidence_validity
        raw_emitted = len(cited_cids) + len(rejected_cids)
        if raw_emitted > 0:
            raw_valid_cnt = len(cited_cids)
            total_raw_evidence_tokens += raw_emitted
            total_raw_valid_tokens += raw_valid_cnt
            if rejected_cids:
                raw_invalid_tokens_list.append({"qid": qid, "rejected": rejected_cids})

        for cid in cited_cids:
            total_final_visible_citations += 1
            if cid in res.formatted_context.available_chunk_ids or cid in res.locked_chunk_ids:
                total_valid_final_citations += 1
            else:
                final_visible_phantom_citations.append({"qid": qid, "cid": cid})

        eval_res = OutputValidator.evaluate_multi_evidence(
            cited_cids, res.formatted_context.chunk_metadata_registry, req_evidence
        )

        num_req = eval_res["total_required"]
        num_supp = eval_res["supported_count"]
        q_complete = (eval_res["completeness"] == 1.0) and (num_req > 0)

        total_supported_evidence_items += num_supp
        total_required_evidence_items += num_req

        if q_complete:
            fully_supported_questions += 1
        else:
            missing_reqs = eval_res["missing_items"]
            failed_in_scope.append({
                "qid": qid,
                "question": q_text,
                "expected": req_evidence,
                "missing": missing_reqs,
                "cited": cited_cids,
                "raw_validity": raw_validity,
                "answer_preview": res.answer[:200],
            })

        if "nhân viên văn phòng" in q_text.lower() or "bình thường" in q_text.lower():
            for cid in cited_cids:
                meta = res.formatted_context.chunk_metadata_registry.get(cid, {})
                if meta.get("doc_id") == "ND_145_2020" and str(meta.get("article_number")) == "7":
                    critical_wrong_law_citations.append({"qid": qid, "issue": "General worker citing ND145 d7"})

        status_sym = "✅ PASS" if q_complete else "❌ FAIL"
        print(f"[{i:02d}/{len(in_scope_items)}] {status_sym} {qid}: {q_text[:45]}... (Evidence: {num_supp}/{num_req}) | Cited: {cited_cids}")

    # Ambiguous Benchmark
    print("\n" + "=" * 60)
    print("RUNNING 20 AMBIGUOUS QUERIES BENCHMARK")
    print("=" * 60)
    ambiguous_passed = 0
    for i, item in enumerate(ambiguous_items, 1):
        chain.memory.clear()
        res = chain.run(item["question"], update_memory=False)
        passed = (res.validated_response.needs_clarification is True) and (not res.validated_response.abstain)
        if passed:
            ambiguous_passed += 1
        sym = "✅ PASS" if passed else "❌ FAIL"
        print(f"[{i:02d}/{len(ambiguous_items)}] {sym} {item['id']}: {item['question'][:50]} (clarify={res.validated_response.needs_clarification})")

    # Out of Scope Benchmark
    print("\n" + "=" * 60)
    print("RUNNING 10 OUT-OF-SCOPE QUERIES BENCHMARK")
    print("=" * 60)
    oos_passed = 0
    for i, item in enumerate(oos_items, 1):
        chain.memory.clear()
        res = chain.run(item["question"], update_memory=False)
        passed = (res.validated_response.abstain is True) and (len(res.validated_response.cited_chunk_ids) == 0)
        if passed:
            oos_passed += 1
        sym = "✅ PASS" if passed else "❌ FAIL"
        print(f"[{i:02d}/{len(oos_items)}] {sym} {item['id']}: {item['question'][:50]} (abstained={res.validated_response.abstain})")

    # Compound Evaluation
    print("\n" + "=" * 60)
    print("EVALUATING 5 COMPOUND QUESTIONS")
    print("=" * 60)
    compound_results = []
    compound_fully_supported = 0
    compound_total_req = 0
    compound_total_supp = 0
    for c_item in compound_items:
        qid = c_item["id"]
        q_text = c_item["question"]
        req = c_item["required_evidence"]
        chain.memory.clear()
        res = chain.run(q_text, update_memory=False)
        cited = res.validated_response.cited_chunk_ids
        eval_res = OutputValidator.evaluate_multi_evidence(
            cited, res.formatted_context.chunk_metadata_registry, req
        )
        comp = eval_res["completeness"]
        sc = eval_res["supported_count"]
        tr = eval_res["total_required"]
        if comp == 1.0:
            compound_fully_supported += 1
        compound_total_supp += sc
        compound_total_req += tr
        c_status = "✅ PASS" if comp == 1.0 else "❌ FAIL"
        print(f"  {c_status} [{qid}] Completeness: {comp:.2f} ({sc}/{tr})")
        print(f"    Cited: {cited}")
        compound_results.append({
            "qid": qid,
            "completeness": comp,
            "supported": sc,
            "required": tr,
            "cited": cited,
            "missing": eval_res["missing_items"],
            "status": "PASS" if comp == 1.0 else "FAIL"
        })

    # Mandatory Cases Verification
    print("\n" + "=" * 60)
    print("VERIFYING MANDATORY CASES A, B, C")
    print("=" * 60)

    # Case A: Office worker 2-year contract notice
    chain.memory.clear()
    res_a = chain.run("Tôi ký hợp đồng 2 năm làm nhân viên văn phòng, muốn nghỉ thì báo trước bao lâu?")
    cited_a = res_a.validated_response.cited_chunk_ids
    arts_a = [str(res_a.formatted_context.chunk_metadata_registry.get(cid, {}).get("article_number") or "") for cid in cited_a]
    pass_a = ("30" in res_a.answer) and ("120" not in res_a.answer) and ("35" in arts_a) and ("7" not in arts_a)
    print(f"Case A (Office 2yr notice): {'✅ PASS' if pass_a else '❌ FAIL'}")

    # Case B: Flight crew 2-year contract notice (MUST CITE BOTH Điều 35k1d AND Điều 7 NĐ 145)
    chain.memory.clear()
    res_b = chain.run("Tôi là thành viên tổ lái tàu bay, ký hợp đồng 2 năm, muốn nghỉ việc thì phải báo trước bao lâu?")
    cited_b = res_b.validated_response.cited_chunk_ids
    arts_b = [str(res_b.formatted_context.chunk_metadata_registry.get(cid, {}).get("article_number") or "") for cid in cited_b]
    pass_b = ("120" in res_b.answer) and ("7" in arts_b) and ("35" in arts_b)
    print(f"Case B (Flight crew notice): {'✅ PASS' if pass_b else '❌ FAIL'}")

    # Case C: Ambiguous 3-month probation
    chain.memory.clear()
    res_c = chain.run("Công ty bắt tôi thử việc 3 tháng có đúng không?")
    pass_c = (res_c.validated_response.needs_clarification is True) and (not res_c.validated_response.abstain)
    print(f"Case C (Ambiguous probation): {'✅ PASS' if pass_c else '❌ FAIL'}")

    mandatory_results = {
        "Case A (General resignation 30d)": "PASS" if pass_a else "FAIL",
        "Case B (Special flight crew 120d, both Điều 35k1d + Điều 7)": "PASS" if pass_b else "FAIL",
        "Case C (Ambiguous probation clarification)": "PASS" if pass_c else "FAIL",
        "all_passed": pass_a and pass_b and pass_c
    }

    # Multi-turn Scenarios Verification
    print("\n" + "=" * 60)
    print("VERIFYING 3 MULTI-TURN SCENARIOS")
    print("=" * 60)
    chain.memory.clear()

    # Scenario 1: Ambiguous probation -> user clarifies qualification level -> system answers
    m_res1 = chain.run("Công ty bắt tôi thử việc 3 tháng có đúng luật không?", update_memory=True)
    m_pass1 = m_res1.validated_response.needs_clarification is True
    m_res2 = chain.run("Tôi làm vị trí kế toán yêu cầu bằng đại học", update_memory=True)
    m_pass2 = ("60" in m_res2.answer) and any("d25-k2" in c for c in m_res2.validated_response.cited_chunk_ids)

    # Scenario 2: Resignation notice -> user specifies 2-year contract
    chain.memory.clear()
    m_res3 = chain.run("Tôi muốn xin thôi việc thì phải báo trước bao nhiêu ngày?", update_memory=True)
    m_res4 = chain.run("Hợp đồng lao động của tôi là loại xác định thời hạn 2 năm", update_memory=True)
    m_pass3 = ("30" in m_res4.answer) and any("d35" in c for c in m_res4.validated_response.cited_chunk_ids)

    # Scenario 3: Special occupation follow-up
    chain.memory.clear()
    m_res5 = chain.run("Tôi làm phi công tổ lái tàu bay", update_memory=True)
    m_res6 = chain.run("Tôi muốn đơn phương chấm dứt hợp đồng 2 năm thì báo trước mấy ngày?", update_memory=True)
    m_pass4 = ("120" in m_res6.answer) and any("ND_145_2020#d7" in c for c in m_res6.validated_response.cited_chunk_ids)

    multi_turn_passed = m_pass1 and m_pass2 and m_pass3 and m_pass4
    print(f"Multi-turn Scenarios: {'✅ PASS (3/3)' if multi_turn_passed else '❌ FAIL'}")

    # Summary Metrics Calculation
    n_in = len(in_scope_items)
    n_amb = len(ambiguous_items)
    n_oos = len(oos_items)

    final_validity_pct = (total_valid_final_citations / total_final_visible_citations * 100) if total_final_visible_citations > 0 else 100.0
    raw_validity_pct = (total_raw_valid_tokens / total_raw_evidence_tokens * 100) if total_raw_evidence_tokens > 0 else 100.0
    support_acc_pct = (fully_supported_questions / n_in * 100) if n_in > 0 else 0.0
    completeness_pct = (total_supported_evidence_items / total_required_evidence_items * 100) if total_required_evidence_items > 0 else 0.0
    amb_acc_pct = (ambiguous_passed / n_amb * 100) if n_amb > 0 else 0.0
    oos_acc_pct = (oos_passed / n_oos * 100) if n_oos > 0 else 0.0
    compound_acc_pct = (compound_fully_supported / len(compound_items) * 100) if compound_items else 0.0

    retrieval_latencies.sort()
    selection_latencies.sort()
    llm_latencies.sort()
    total_latencies.sort()
    p95_idx = int(n_in * 0.95)

    summary = {
        "metrics": {
            "final_citation_id_validity": {
                "valid": total_valid_final_citations,
                "total": total_final_visible_citations,
                "percentage": round(final_validity_pct, 2),
                "gate_passed": final_validity_pct >= 99.0 and len(final_visible_phantom_citations) == 0,
            },
            "raw_evidence_id_validity": {
                "valid": total_raw_valid_tokens,
                "total": total_raw_evidence_tokens,
                "percentage": round(raw_validity_pct, 2),
                "raw_invalid_count": len(raw_invalid_tokens_list),
            },
            "citation_support_accuracy": {
                "passed": fully_supported_questions,
                "total": n_in,
                "percentage": round(support_acc_pct, 2),
                "gate_passed": support_acc_pct >= 90.0,
            },
            "citation_completeness": {
                "supported": total_supported_evidence_items,
                "total": total_required_evidence_items,
                "percentage": round(completeness_pct, 2),
                "gate_passed": completeness_pct >= 90.0,
            },
            "ambiguous_accuracy": {
                "passed": ambiguous_passed,
                "total": n_amb,
                "percentage": round(amb_acc_pct, 2),
                "gate_passed": amb_acc_pct >= 90.0,
            },
            "out_of_scope_accuracy": {
                "passed": oos_passed,
                "total": n_oos,
                "percentage": round(oos_acc_pct, 2),
                "gate_passed": oos_acc_pct >= 95.0,
            },
            "compound_full_support_accuracy": {
                "passed": compound_fully_supported,
                "total": len(compound_items),
                "percentage": round(compound_acc_pct, 2),
                "gate_passed": compound_acc_pct >= 80.0,
            },
            "mandatory_cases": mandatory_results,
            "multi_turn_passed": multi_turn_passed,
            "critical_wrong_law_citations": len(critical_wrong_law_citations),
            "final_visible_phantom_citations": len(final_visible_phantom_citations),
        },
        "latencies": {
            "retrieval": {
                "mean_ms": round(statistics.mean(retrieval_latencies), 1),
                "median_ms": round(statistics.median(retrieval_latencies), 1),
                "p95_ms": round(retrieval_latencies[p95_idx] if p95_idx < n_in else retrieval_latencies[-1], 1),
            },
            "selection": {
                "mean_ms": round(statistics.mean(selection_latencies), 1),
                "median_ms": round(statistics.median(selection_latencies), 1),
                "p95_ms": round(selection_latencies[p95_idx] if p95_idx < n_in else selection_latencies[-1], 1),
            },
            "llm": {
                "mean_ms": round(statistics.mean(llm_latencies), 1),
                "median_ms": round(statistics.median(llm_latencies), 1),
                "p95_ms": round(llm_latencies[p95_idx] if p95_idx < n_in else llm_latencies[-1], 1),
            },
            "total": {
                "mean_ms": round(statistics.mean(total_latencies), 1),
                "median_ms": round(statistics.median(total_latencies), 1),
                "p95_ms": round(total_latencies[p95_idx] if p95_idx < n_in else total_latencies[-1], 1),
            },
        },
        "compound_results": compound_results,
        "failed_in_scope_queries": failed_in_scope,
        "raw_invalid_tokens": raw_invalid_tokens_list,
        "critical_wrong_law_details": critical_wrong_law_citations,
    }

    out_file = Path("evaluation/results/phase5e_generation_results.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("PHASE 5E BENCHMARK OVERALL REPORT")
    print("=" * 60)
    print(f"Final Citation ID Validity     : {total_valid_final_citations}/{total_final_visible_citations} = {final_validity_pct:.2f}% (Phantom = {len(final_visible_phantom_citations)})")
    print(f"Raw Evidence-ID Validity       : {total_raw_valid_tokens}/{total_raw_evidence_tokens} = {raw_validity_pct:.2f}% (Invalid tokens = {len(raw_invalid_tokens_list)})")
    print(f"Citation Support Accuracy      : {fully_supported_questions}/{n_in} = {support_acc_pct:.2f}% (Gate >= 90%, Target >= 95%)")
    print(f"Citation Completeness          : {total_supported_evidence_items}/{total_required_evidence_items} = {completeness_pct:.2f}% (Gate >= 90%, Target >= 95%)")
    print(f"Ambiguous-query Accuracy       : {ambiguous_passed}/{n_amb} = {amb_acc_pct:.2f}% (Gate >= 90%)")
    print(f"Out-of-scope Accuracy          : {oos_passed}/{n_oos} = {oos_acc_pct:.2f}% (Gate >= 95%)")
    print(f"Compound Full Support Accuracy : {compound_fully_supported}/{len(compound_items)} = {compound_acc_pct:.2f}% (Gate >= 80%)")
    print(f"Mandatory Cases                : {'100% PASS' if mandatory_results['all_passed'] else 'FAIL'}")
    print(f"Multi-turn Scenarios           : {'100% PASS' if multi_turn_passed else 'FAIL'}")
    print(f"Critical Wrong-Law Citations   : {len(critical_wrong_law_citations)}")
    print("------------------------------------------------------------")
    print(f"Latencies (ms): Retrieval={summary['latencies']['retrieval']['mean_ms']}, Selection={summary['latencies']['selection']['mean_ms']}, LLM={summary['latencies']['llm']['mean_ms']}, Total={summary['latencies']['total']['mean_ms']}")
    print(f"Remaining Failed Queries       : {len(failed_in_scope)}")
    print("============================================================\n")

    return summary


if __name__ == "__main__":
    run_phase5e_benchmark()
