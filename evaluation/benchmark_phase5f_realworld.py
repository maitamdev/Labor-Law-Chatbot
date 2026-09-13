# -*- coding: utf-8 -*-
"""
VietLabor AI - Phase 5F Unseen Real-World Benchmark Evaluator
Evaluates 30 NEW unseen colloquial/real-world queries:
- Clarification Decision Accuracy (Target: >= 90%)
- Premature Answer Rate (Target: <= 5%)
- Wrong Intent Routing Rate (Target: <= 5%)
- Forbidden Evidence Avoidance (Zero Điều 46 on internship/wage queries)
- Post-Clarification Multi-Turn Accuracy & Citation Support (Target: >= 90%)
- Conversation State Accuracy (Target: >= 90%)
"""
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
sys.path.insert(0, ".")

from rag.chain import VietLaborRAGChain
from rag.output_validator import OutputValidator


def run_phase5f_realworld_benchmark(
    dataset_path: str = "data/evaluation/phase5f_realworld_dataset.json",
) -> Dict[str, Any]:
    print("=" * 70)
    print("PHASE 5F – REAL-WORLD INTENT & AMBIGUITY BENCHMARK")
    print("=" * 70)

    with open(dataset_path, "r", encoding="utf-8") as f:
        queries = json.load(f)

    print(f"Total unseen real-world queries: {len(queries)}")

    chain = VietLaborRAGChain()

    # Metrics counters
    total_queries = len(queries)
    correct_decisions = 0
    premature_answers = 0
    expected_clarify_count = 0
    wrong_intent_routing_count = 0
    forbidden_evidence_violations = 0

    # In-scope answer evaluation
    answer_queries_count = 0
    answer_supported_count = 0
    total_required_items = 0
    total_supported_items = 0
    total_visible_citations = 0
    total_supporting_citations = 0

    results_detail = []

    print("\n" + "-" * 70)
    print("RUNNING 30 UNSEEN QUERIES EVALUATION")
    print("-" * 70)

    for i, item in enumerate(queries, 1):
        qid = item["id"]
        q_text = item["question"]
        cat = item["category"]
        exp_behav = item["expected_behavior"]
        req_ev = item.get("required_evidence", [])
        forbid_ev = item.get("forbidden_evidence", [])

        chain.memory.clear()
        t0 = time.perf_counter()
        res = chain.run(q_text, update_memory=False)
        dur = (time.perf_counter() - t0) * 1000

        resp = res.validated_response
        cited_cids = resp.cited_chunk_ids
        registry = res.formatted_context.chunk_metadata_registry

        # Check actual behavior
        if resp.abstain:
            act_behav = "OUT_OF_SCOPE"
        elif resp.needs_clarification:
            act_behav = "CLARIFY"
        else:
            act_behav = "ANSWER"

        # Check decision correctness
        is_decision_correct = (act_behav == exp_behav)
        if is_decision_correct:
            correct_decisions += 1

        if exp_behav == "CLARIFY":
            expected_clarify_count += 1
            if act_behav == "ANSWER":
                premature_answers += 1
                print(f"  [PREMATURE ANSWER] {qid}: answered instead of clarify!")

        # Check forbidden evidence
        has_forbidden_violation = False
        for fb in forbid_ev:
            fb_doc = fb.get("doc_id", "")
            fb_art = str(fb.get("article", ""))
            for cid in cited_cids:
                meta = registry.get(cid, {})
                doc_m = meta.get("doc_id", "")
                art_m = str(meta.get("article_number", ""))
                if (fb_doc in doc_m or doc_m in fb_doc) and fb_art == art_m:
                    has_forbidden_violation = True
                    forbidden_evidence_violations += 1
                    wrong_intent_routing_count += 1
                    print(f"  [FORBIDDEN VIOLATION] {qid} cited forbidden: {cid}")

        # If answer behavior expected, evaluate citation support and completeness
        eval_metrics = {}
        if exp_behav == "ANSWER":
            answer_queries_count += 1
            if act_behav == "ANSWER" and req_ev:
                ev_res = OutputValidator.evaluate_multi_evidence(cited_cids, registry, req_ev)
                is_supp = (ev_res["completeness"] == 1.0)
                if is_supp:
                    answer_supported_count += 1
                total_required_items += ev_res["total_required"]
                total_supported_items += ev_res["supported_count"]

                # Precision
                for cid in cited_cids:
                    total_visible_citations += 1
                    meta = registry.get(cid, {})
                    is_supporting = False
                    for r in req_ev:
                        if OutputValidator.check_evidence_item_support(
                            [cid], {cid: meta}, r.get("doc_id"), r.get("article"), r.get("clause"), r.get("point")
                        ):
                            is_supporting = True
                            break
                    if is_supporting:
                        total_supporting_citations += 1

                eval_metrics = ev_res

        status_sym = "✅ PASS" if (is_decision_correct and not has_forbidden_violation) else "❌ FAIL"
        cites_summary = ", ".join(c.split('#')[-1] for c in cited_cids) if cited_cids else "(no citations)"
        print(f"[{i:02d}/{total_queries}] {status_sym} {qid} ({cat}): exp={exp_behav} act={act_behav} | Cites: {cites_summary} ({dur:.1f}ms)")

        results_detail.append({
            "id": qid,
            "question": q_text,
            "category": cat,
            "expected_behavior": exp_behav,
            "actual_behavior": act_behav,
            "is_decision_correct": is_decision_correct,
            "cited_chunk_ids": cited_cids,
            "has_forbidden_violation": has_forbidden_violation,
            "clarification_question": resp.clarification_question,
            "latency_ms": dur,
        })

    # Multi-turn conversational flow evaluation
    print("\n" + "-" * 70)
    print("RUNNING MULTI-TURN FACTUAL REFINEMENT FLOWS")
    print("-" * 70)

    multi_turn_results = {}

    # FLOW A: School Internship
    print("\n[Flow A: School Internship Agreement]")
    chain.memory.clear()
    fa_t1 = chain.run("tôi đi thực tập 7 tháng rồi mà ko có lương")
    fa_t1_clarify = fa_t1.validated_response.needs_clarification
    fa_t2 = chain.run("Em thực tập theo chương trình của trường, có giấy giới thiệu và thỏa thuận thực tập.")
    fa_t2_ans = not fa_t2.validated_response.needs_clarification
    fa_t2_no_d46 = not any("d46" in cid for cid in fa_t2.validated_response.cited_chunk_ids)
    flow_a_pass = fa_t1_clarify and fa_t2_ans and fa_t2_no_d46
    print(f"  T1 clarify: {fa_t1_clarify} | T2 answered: {fa_t2_ans} | Zero Điều 46: {fa_t2_no_d46} -> {'✅ PASS' if flow_a_pass else '❌ FAIL'}")
    multi_turn_results["FLOW_A"] = {
        "pass": flow_a_pass,
        "t1_clarify": fa_t1_clarify,
        "t2_answered": fa_t2_ans,
        "t2_citations": fa_t2.validated_response.cited_chunk_ids,
    }

    # FLOW B: De Facto Employment (Disguised Internship)
    print("\n[Flow B: De Facto Employment Disguised as Internship]")
    chain.memory.clear()
    fb_t1 = chain.run("tôi đi thực tập 7 tháng rồi mà ko có lương")
    fb_t2 = chain.run("Công ty tự tuyển em, ngày nào em cũng làm 8 tiếng, chấm công và làm việc như nhân viên, không có giấy của trường.")
    fb_t2_ans = not fb_t2.validated_response.needs_clarification
    fb_t2_has_d13 = any("d13" in cid or "d90" in cid for cid in fb_t2.validated_response.cited_chunk_ids) or "Điều 13" in fb_t2.validated_response.final_answer
    flow_b_pass = fb_t1.validated_response.needs_clarification and fb_t2_ans and fb_t2_has_d13
    print(f"  T1 clarify: {fb_t1.validated_response.needs_clarification} | T2 recognized employment: {fb_t2_has_d13} -> {'✅ PASS' if flow_b_pass else '❌ FAIL'}")
    multi_turn_results["FLOW_B"] = {
        "pass": flow_b_pass,
        "t2_answered": fb_t2_ans,
        "t2_citations": fb_t2.validated_response.cited_chunk_ids,
    }

    # FLOW C: Probation Transition -> Qualification Resolution
    print("\n[Flow C: Internship -> Probation -> Qualification Resolution]")
    chain.memory.clear()
    fc_t1 = chain.run("tôi đi thực tập 7 tháng rồi mà ko có lương")
    fc_t2 = chain.run("Thực ra công ty bảo đây là thử việc trước khi ký hợp đồng.")
    fc_t2_clarify = fc_t2.validated_response.needs_clarification
    fc_t3 = chain.run("Em làm lập trình viên, có bằng đại học.")
    fc_t3_ans = not fc_t3.validated_response.needs_clarification
    fc_t3_has_d25 = any("d25" in cid or "d26" in cid for cid in fc_t3.validated_response.cited_chunk_ids)
    flow_c_pass = fc_t1.validated_response.needs_clarification and fc_t2_clarify and fc_t3_ans and fc_t3_has_d25
    print(f"  T1 clarify: {fc_t1.validated_response.needs_clarification} | T2 asks qualification: {fc_t2_clarify} | T3 cites Điều 25/26: {fc_t3_has_d25} -> {'✅ PASS' if flow_c_pass else '❌ FAIL'}")
    multi_turn_results["FLOW_C"] = {
        "pass": flow_c_pass,
        "t2_clarify": fc_t2_clarify,
        "t3_answered": fc_t3_ans,
        "t3_citations": fc_t3.validated_response.cited_chunk_ids,
    }

    # Metric Calculations
    clarify_dec_acc = (correct_decisions / total_queries) * 100
    premature_rate = (premature_answers / expected_clarify_count * 100) if expected_clarify_count else 0.0
    wrong_intent_rate = (wrong_intent_routing_count / total_queries) * 100
    citation_support = (total_supported_items / total_required_items * 100) if total_required_items else 100.0
    citation_precision = (total_supporting_citations / total_visible_citations * 100) if total_visible_citations else 100.0

    multi_turn_passed = sum(1 for v in multi_turn_results.values() if v["pass"])
    conversation_state_acc = (multi_turn_passed / len(multi_turn_results)) * 100

    print("\n" + "=" * 70)
    print("PHASE 5F REAL-WORLD METRICS SUMMARY")
    print("=" * 70)
    print(f"Clarification Decision Accuracy:   {clarify_dec_acc:.2f}%  (Target: >= 90.00%)")
    print(f"Premature Answer Rate:             {premature_rate:.2f}%  (Target: <= 5.00%)")
    print(f"Wrong Intent Routing Rate:         {wrong_intent_rate:.2f}%  (Target: <= 5.00%)")
    print(f"Forbidden Evidence Violations:     {forbidden_evidence_violations}  (Target: 0)")
    print(f"Answer Query Citation Support:     {citation_support:.2f}%")
    print(f"Answer Query Citation Precision:   {citation_precision:.2f}%")
    print(f"Conversation State Accuracy:       {conversation_state_acc:.2f}%  (Target: >= 90.00%)")

    passed_all = (
        clarify_dec_acc >= 90.0
        and premature_rate <= 5.0
        and wrong_intent_rate <= 5.0
        and forbidden_evidence_violations == 0
        and conversation_state_acc >= 90.0
    )

    print(f"\nOVERALL PHASE 5F REAL-WORLD BENCHMARK: {'ACCEPTED ✅' if passed_all else 'REJECTED ❌'}")

    summary = {
        "total_queries": total_queries,
        "clarification_decision_accuracy": clarify_dec_acc,
        "premature_answer_rate": premature_rate,
        "wrong_intent_routing_rate": wrong_intent_rate,
        "forbidden_evidence_violations": forbidden_evidence_violations,
        "citation_support": citation_support,
        "citation_precision": citation_precision,
        "conversation_state_accuracy": conversation_state_acc,
        "passed_all": passed_all,
        "multi_turn_results": multi_turn_results,
        "results_detail": results_detail,
    }

    out_file = Path("evaluation/results/phase5f_realworld_results.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    return summary


if __name__ == "__main__":
    run_phase5f_realworld_benchmark()
