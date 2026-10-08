# 📦 VietLabor AI - Archive Repository

Thư mục này lưu trữ các tài liệu, kịch bản (scripts), bộ đánh giá (benchmarks), và các bài kiểm thử (tests) thuộc các giai đoạn phát triển lịch sử (Phases 3E, 5B - 5G) nhằm giữ cho cây thư mục chính của dự án gọn gàng, nhẹ nhàng và dễ bảo trì.

## Cấu trúc Archive:

* **`scripts_legacy/`**: Các kịch bản nạp dữ liệu một lần (one-off ingestion), audit corpus và lập chỉ mục phiên bản cũ (v1, v2).
  *(Thư mục `scripts/` chính hiện tại chỉ tập trung vào các công cụ cốt lõi: `build_index_v3.py`, `build_graph_index.py`, `validate_processed_data.py`, `download_labor_laws.py`, `chat.py`, `search.py`, cùng thư viện `qa_source_normalizations.py` được `tests/test_qa_anchor.py` sử dụng)*.
* **`evaluation_legacy/`**: Các file benchmark trung gian của các Phase 5C - 5G1.
* **`tests_legacy/`**: Các bài kiểm thử hồi quy cũ của từng Phase lịch sử.
* **`data_backup/`**: File sao lưu tạm thời trước đợt refresh dữ liệu chính thức.

> **Lưu ý:** Toàn bộ mã nguồn cốt lõi và các chỉ mục hiện hành (ChromaDB v3, BM25 v3, Neo4j GraphRAG) vẫn hoạt động độc lập và đầy đủ chức năng.
