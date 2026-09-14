# -*- coding: utf-8 -*-
"""
VietLabor AI - Interactive Terminal Chat CLI
Allows interactive conversation with the grounded VietLabor AI assistant.
Supports --debug flag to show detailed retrieval routing, latencies, chunk scores,
and citation validation status.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure Windows terminal prints Vietnamese UTF-8 cleanly
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        getattr(sys.stdout, "reconfigure")(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        getattr(sys.stderr, "reconfigure")(encoding="utf-8")

from rag.chain import VietLaborRAGChain


def print_banner():
    banner = """
========================================================================
             VIETLABOR AI - TRỢ LÝ PHÁP LUẬT LAO ĐỘNG VIỆT NAM
              Local Inference via Ollama (Qwen 2.5) + LangChain
========================================================================
- Gõ câu hỏi của bạn và nhấn Enter.
- Gõ 'clear' để xóa ngữ cảnh hội thoại.
- Gõ 'exit' hoặc 'quit' để thoát.
------------------------------------------------------------------------
"""
    print(banner)


def main():
    parser = argparse.ArgumentParser(description="VietLabor AI Terminal Chat")
    parser.add_argument("--debug", action="store_true", help="Display retrieval telemetry, latencies, and citation audit details")
    args = parser.parse_args()

    print("[VietLabor AI] Khởi động hệ thống RAG local...")
    t_start = time.perf_counter()
    try:
        chain = VietLaborRAGChain()
    except Exception as e:
        print(f"[LỖI] Không thể khởi tạo VietLabor RAG Chain: {e}")
        sys.exit(1)

    init_sec = time.perf_counter() - t_start
    print(f"[VietLabor AI] Hệ thống sẵn sàng! (Khởi tạo mất {init_sec:.2f}s)")
    if args.debug:
        print(">>> DEBUG MODE: BẬT (Hiển thị chi tiết telemetry, routing, và validation) <<<\n")

    print_banner()

    while True:
        try:
            user_input = input("\n[Bạn] > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n[VietLabor AI] Tạm biệt!")
            break

        if not user_input:
            continue

        if user_input.lower() in ["exit", "quit", "q"]:
            print("\n[VietLabor AI] Tạm biệt!")
            break

        if user_input.lower() == "clear":
            chain.memory.clear()
            print("[VietLabor AI] Đã xóa lịch sử hội thoại.")
            continue

        print("\n[VietLabor AI đang suy nghĩ và tra cứu căn cứ...]")
        try:
            result = chain.run(user_input)
        except Exception as e:
            print(f"\n[LỖI THỰC THI]: {e}")
            continue

        if args.debug:
            print("\n" + "=" * 60)
            print("                       DEBUG TELEMETRY")
            print("=" * 60)
            print(f"Query chuẩn hóa   : {result.normalized_query}")
            print(f"Query sau context : {result.resolved_query}")
            print(f"Chiến lược Route  : {result.route_decision.strategy.upper()}")
            print(f"Lý do định tuyến  : {result.route_decision.reason}")
            print(f"Phương thức tra cứu: {result.retrieval_method}")
            print(f"Thời gian tra cứu : {result.retrieval_latency_ms:.2f} ms")
            print(f"Thời gian LLM     : {result.llm_latency_ms:.2f} ms")
            print(f"Tổng thời gian    : {result.total_latency_ms:.2f} ms")
            print(f"Tổng chunks tìm   : {len(result.retrieved_chunks)}")
            print("-" * 60)
            print("Top chunks được truy xuất:")
            for idx, c in enumerate(result.retrieved_chunks[:5], start=1):
                score = c.get("score") or c.get("rrf_score", 0.0)
                meta = c.get("metadata", {})
                print(f"  #{idx} [{c.get('chunk_id')}] (Điểm: {score:.4f}) -> {meta.get('document_no', '')} Điều {meta.get('article_number')}")
            print("-" * 60)
            print(f"Chunk IDs trích dẫn: {result.validated_response.cited_chunk_ids}")
            print(f"Chunk IDs bị từ chối: {result.validated_response.rejected_chunk_ids}")
            print(f"Trạng thái Grounded: {'CHUẨN XÁC 100%' if result.validated_response.is_fully_grounded else 'CẦN CHÚ Ý'}")
            print(f"Yêu cầu làm rõ    : {result.validated_response.needs_clarification}")
            print(f"Từ chối (Abstain) : {result.validated_response.abstain} ({result.validated_response.abstain_reason})")
            print("=" * 60 + "\n")

        print(f"\n[VietLabor AI]:\n{result.answer}\n")


if __name__ == "__main__":
    main()
