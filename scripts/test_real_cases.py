# -*- coding: utf-8 -*-
"""
VietLabor AI - Mandatory 7 Real-World Case Test Runner
Executes the 7 mandatory queries specified in Phase 5 requirements:
1. "Công ty bắt tôi thử việc 3 tháng có đúng không?"
2. "Điều 25 Bộ luật Lao động quy định gì?"
3. "Tôi ký hợp đồng 2 năm, nghỉ việc phải báo trước bao lâu?"
4. "Cty quỵt lương thì sao?"
5. "Làm ngày lễ thì được trả bao nhiêu?"
6. "Công ty giữ bằng đại học gốc của tôi có được không?"
7. "Tôi ly hôn thì chia tài sản thế nào?"
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure Windows terminal prints Vietnamese UTF-8 cleanly
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from rag.chain import VietLaborRAGChain

TEST_QUERIES = [
    {
        "id": "CASE_1_PROBATION_3_MONTHS",
        "query": "Công ty bắt tôi thử việc 3 tháng có đúng không?",
        "expected_topic": "Thời gian thử việc (Điều 25 BLLĐ / 18/VBHN-VPQH). Thử việc tối đa 180 ngày đối với người quản lý doanh nghiệp, 60 ngày đối với trình độ CĐ trở lên, 30 ngày TC/CN, 03 ngày làm việc khác. Nếu không phải người quản lý thì 3 tháng là sai luật hoặc cần hỏi rõ vị trí.",
    },
    {
        "id": "CASE_2_EXACT_ARTICLE_25",
        "query": "Điều 25 Bộ luật Lao động quy định gì?",
        "expected_topic": "Quy định về thời gian thử việc trong Bộ luật Lao động.",
    },
    {
        "id": "CASE_3_NOTICE_PERIOD_2_YEARS",
        "query": "Tôi ký hợp đồng 2 năm, nghỉ việc phải báo trước bao lâu?",
        "expected_topic": "Hợp đồng xác định thời hạn từ 12-36 tháng: báo trước ít nhất 30 ngày theo Điều 35 Khoản 1 Điểm b BLLĐ.",
    },
    {
        "id": "CASE_3B_SPECIAL_OCCUPATION_FLIGHT_CREW",
        "query": "Tôi là thành viên tổ lái tàu bay, hợp đồng 2 năm, muốn đơn phương nghỉ thì báo trước bao lâu?",
        "expected_topic": "Ngành nghề đặc thù (Điều 7 Nghị định 145/2020/NĐ-CP): báo trước ít nhất 120 ngày đối với HĐLĐ từ 12 tháng trở lên.",
    },
    {
        "id": "CASE_4_UNPAID_SALARY",
        "query": "Cty quỵt lương thì sao?",
        "expected_topic": "Nguyên tắc trả lương, trả lương chậm, quyền đơn phương chấm dứt HĐLĐ không cần báo trước khi không được trả đủ lương (Điều 35), tiền lãi trả chậm hoặc xử phạt NĐ 12/2022.",
    },
    {
        "id": "CASE_5_HOLIDAY_OVERTIME_PAY",
        "query": "Làm ngày lễ thì được trả bao nhiêu?",
        "expected_topic": "Tiền lương làm thêm giờ vào ngày nghỉ lễ, tết, ngày nghỉ có hưởng lương ít nhất bằng 300% chưa kể tiền lương ngày lễ (Điều 98 BLLĐ).",
    },
    {
        "id": "CASE_6_RETENTION_OF_DEGREE",
        "query": "Công ty giữ bằng đại học gốc của tôi có được không?",
        "expected_topic": "Hành vi người sử dụng lao động không được làm khi giao kết/thực hiện HĐLĐ: Giữ bản chính giấy tờ tùy thân, văn bằng, chứng chỉ của người lao động (Điều 17 BLLĐ).",
    },
    {
        "id": "CASE_7_OUT_OF_SCOPE_DIVORCE",
        "query": "Tôi ly hôn thì chia tài sản thế nào?",
        "expected_topic": "Out of scope: Thuộc Luật Hôn nhân và Gia đình, chatbot phải từ chối và nói rõ hệ thống chỉ tập trung vào pháp luật lao động.",
    },
]


def main():
    print("=" * 80)
    print("       VIETLABOR AI - PHASE 5 MANDATORY 7 REAL-WORLD CASES AUDIT")
    print("=" * 80)

    chain = VietLaborRAGChain()
    results = []

    for i, item in enumerate(TEST_QUERIES, start=1):
        print(f"\n[{i}/7] Testing: \"{item['query']}\"")
        chain.memory.clear()  # Clear memory for isolated query testing

        t0 = time.perf_counter()
        res = chain.run(item["query"])
        elapsed = time.perf_counter() - t0

        print(f"  -> Route strategy   : {res.route_decision.strategy.upper()} ({res.retrieval_method})")
        print(f"  -> Retrieval latency: {res.retrieval_latency_ms:.2f} ms")
        print(f"  -> LLM latency      : {res.llm_latency_ms:.2f} ms")
        print(f"  -> Total latency    : {elapsed*1000:.2f} ms")
        print(f"  -> Cited Chunks     : {res.validated_response.cited_chunk_ids}")
        print(f"  -> Rejected Chunks  : {res.validated_response.rejected_chunk_ids}")
        print(f"  -> Needs Clarify    : {res.validated_response.needs_clarification}")
        print(f"  -> Abstain          : {res.validated_response.abstain} ({res.validated_response.abstain_reason})")
        print(f"  -> Answer snippet   : {res.answer[:180]}...")

        results.append({
            "case_id": item["id"],
            "query": item["query"],
            "expected_topic": item["expected_topic"],
            "strategy": res.route_decision.strategy,
            "retrieval_method": res.retrieval_method,
            "retrieval_latency_ms": res.retrieval_latency_ms,
            "llm_latency_ms": res.llm_latency_ms,
            "total_latency_ms": elapsed * 1000,
            "cited_chunk_ids": res.validated_response.cited_chunk_ids,
            "rejected_chunk_ids": res.validated_response.rejected_chunk_ids,
            "abstain": res.validated_response.abstain,
            "abstain_reason": res.validated_response.abstain_reason,
            "needs_clarification": res.validated_response.needs_clarification,
            "clarification_question": res.validated_response.clarification_question,
            "is_fully_grounded": res.validated_response.is_fully_grounded,
            "full_answer": res.answer,
        })

    with open("evaluation/results/phase5_7_cases_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 80)
    print("Audit completed! Results saved to evaluation/results/phase5_7_cases_results.json")
    print("=" * 80)


if __name__ == "__main__":
    main()
