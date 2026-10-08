# 📋 TỔNG HỢP CÁC LỆNH CHẠY DỰ ÁN VIETLABOR AI

Tài liệu này tổng hợp toàn bộ các câu lệnh cần thiết để thiết lập, khởi chạy, kiểm thử và đánh giá dự án **VietLabor AI (Chatbot Pháp luật Lao động)** trên hệ điều hành Windows.

---

## ⚡ 1. Khởi Chạy Nhanh (Quick Start)

Nếu máy đã cài sẵn môi trường và đã tải model Ollama, bạn chỉ cần mở Terminal tại thư mục dự án `d:\chatbot-law` và chạy:

```powershell
# 1. Kích hoạt môi trường ảo
.\.venv\Scripts\Activate.ps1

# 2. Khởi chạy giao diện Web (Streamlit)
python -m app.main
```
> Trình duyệt sẽ tự động mở trang web tại địa chỉ: `http://localhost:8501`

---

## 🛠️ 2. Chuẩn Bị Môi Trường (Setup)

### 2.1. Kích hoạt môi trường ảo Python (`.venv`)

- **Trên PowerShell**:
  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```
  *(Nếu gặp lỗi `Execution_Policies`, chạy lệnh sau một lần: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

- **Trên Command Prompt (CMD)**:
  ```cmd
  .\.venv\Scripts\activate.bat
  ```

### 2.2. Cài đặt / Cập nhật thư viện
```powershell
pip install -r requirements.txt
```

---

## 🧠 3. Quản Lý Mô Hình AI Local (Ollama)

Hệ thống hoạt động 100% offline thông qua Ollama.

### 3.1. Kiểm tra trạng thái Ollama
```powershell
ollama list
```

### 3.2. Tải và chạy mô hình ngôn ngữ khuyến nghị
```powershell
# Mô hình chuẩn mặc định của dự án (khớp với config/settings.py):
ollama pull qwen2.5:7b-instruct-q4_0

# Đã có sẵn qwen2.5:7b? Hệ thống tự dùng bản Qwen 2.5 7B đã cài (có cảnh báo trong log).

# Dùng mô hình khác (ví dụ qwen2.5-coder:7b) thì chỉ định qua biến môi trường:
ollama pull qwen2.5-coder:7b
$env:OLLAMA_MODEL="qwen2.5-coder:7b"
```

---

## 🚀 4. Các Lệnh Khởi Chạy Ứng Dụng (Running the App)

### 4.1. Giao diện Web (Streamlit UI)
```powershell
python -m app.main
```
*Tùy chọn chỉ định cổng nếu cổng 8501 bị chiếm:*
```powershell
$env:VIETLABOR_PORT=8502
python -m app.main
```

### 4.2. Giao diện Chat trực tiếp trong Terminal (CLI)
Dành cho việc kiểm tra nhanh phản hồi của trợ lý không cần bật trình duyệt:
```powershell
# Chế độ chat thông thường
python scripts/chat.py

# Chế độ chat kèm hiển thị chi tiết chỉ số (thời gian, router, citation audit)
python scripts/chat.py --debug
```

### 4.3. Tra cứu nhanh văn bản luật trong Terminal (Search Test)
Tìm kiếm trực tiếp các điều khoản theo từ khóa / câu hỏi:
```powershell
python scripts/search.py "thời gian thử việc trình độ đại học"
```

---

## 📚 5. Quản Lý Dữ Liệu & Xây Dựng Chỉ Mục (Data & Indexing)

Dùng khi cần làm mới hoặc cập nhật văn bản pháp luật vào cơ sở dữ liệu:

### 5.1. Tải các văn bản pháp luật chính thức
```powershell
python scripts/download_labor_laws.py
```

### 5.2. Chạy pipeline xử lý, làm sạch và chunking văn bản
```powershell
python scripts/run_ingestion.py
```

### 5.3. Kiểm tra tính hợp lệ của dữ liệu đã xử lý
```powershell
python scripts/validate_processed_data.py

# Đồng bộ và xác minh Chroma index với corpus production
python scripts/sync_index_v3.py
```

### 5.4. Xây dựng chỉ mục tìm kiếm (BM25 + ChromaDB)
```powershell
# Xây dựng cả 2 chỉ mục (BM25 và Chroma Vectorstore)
python scripts/build_index_v3.py

# Bắt buộc xây dựng lại từ đầu (Force Rebuild)
python scripts/build_index_v3.py --force

# Chỉ xây dựng lại chỉ mục BM25
python scripts/build_index_v3.py --target bm25 --force

# Chỉ xây dựng lại chỉ mục Vector ChromaDB
python scripts/build_index_v3.py --target chroma
```

Chroma được đồng bộ tăng dần và có thể tiếp tục sau khi bị ngắt. Trong lúc
chưa đồng bộ xong, chatbot dùng chỉ mục BM25 đã cập nhật và không đọc vector
cũ hoặc thiếu. Để kiểm tra riêng bộ 1.000 câu:

```powershell
python scripts/prepare_qa_bank.py
python scripts/audit_qa_bank.py --bank data/evaluation/labor_qa_corrected.jsonl --report data/evaluation/labor_qa_audit.json
python scripts/semantic_review_qa_bank.py --limit 50
```

Lệnh cuối tạo hàng đợi rà soát bằng Ollama và tự tiếp tục từ dòng chưa chạy.
Nhãn PASS/FAIL/UNCLEAR của model chỉ là gợi ý; đối chiếu văn bản gốc trước khi
sửa Sheet hoặc đưa đáp án vào dữ liệu huấn luyện.

---

## 🧪 6. Kiểm Thử Tự Động (Testing)

VietLabor AI có bộ kiểm thử tự động toàn diện bằng `pytest`:

### 6.1. Chạy toàn bộ bài kiểm thử
```powershell
pytest
```
*Chạy hiển thị chi tiết tên từng bài test:*
```powershell
pytest -v

# Bao gồm các bài end-to-end cần Ollama đang chạy
pytest --run-ollama
```

### 6.2. Chạy từng nhóm bài kiểm thử cụ thể
```powershell
# Kiểm thử 15 ca chuẩn theo Rubric Đại học (Fast Unit Tests)
pytest tests/test_rubric_15_cases.py -v

# Kiểm thử trải nghiệm hội thoại thực tế (Colloquial & Edge Cases)
pytest tests/test_chatbot_experience.py -v

# Kiểm thử giao diện và tương tác UI
pytest tests/test_ui_service.py -v

# Kiểm thử toàn diện RAG Chain & Ingestion
pytest tests/test_chain.py tests/test_ingestion.py
```

---

## 📊 7. Đánh Giá & Đo Đạc Hiệu Năng (Benchmark & Evaluation)

### 7.1. Chạy đánh giá toàn diện 15 ca kiểm thử theo Rubric Chấm điểm Đại học (Mục IV & Tiêu chí E2)
```powershell
python scripts/run_rubric_evaluation.py
```
> Kết quả đánh giá chi tiết và tỷ lệ đạt sẽ được tự động xuất ra file Markdown tại: `reports/rubric_15_test_cases.md`.

### 7.2. Đánh giá chất lượng truy hồi và cắt giảm độ trễ (Ablation Benchmark)
```powershell
python scripts/evaluate_ablation.py
```

---

## 🔧 8. Khắc Phục Lỗi Thường Gặp (Troubleshooting)

| Lỗi | Nguyên nhân | Cách khắc phục |
| :--- | :--- | :--- |
| **`Execution_Policies` khi bật `.venv`** | Windows chặn chạy script PowerShell chưa ký | Chạy lệnh: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |
| **`ConnectionRefusedError` hoặc lỗi kết nối Ollama** | Ollama chưa được bật trên máy | Mở ứng dụng Ollama hoặc chạy lệnh: `ollama serve` |
| **`Ollama model 'qwen2.5:7b-instruct-q4_0' is not installed`** | Chưa tải mô hình Qwen 2.5 7B nào về máy | Chạy lệnh: `ollama pull qwen2.5:7b-instruct-q4_0` hoặc đặt `OLLAMA_MODEL` sang mô hình đã cài |
| **Lỗi cổng `8501` bị chiếm khi chạy Streamlit** | Tiến trình Streamlit cũ chưa tắt | Đổi cổng: `streamlit run ui/streamlit_app.py --server.port 8502` |
