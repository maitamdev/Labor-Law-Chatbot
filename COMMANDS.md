# 📋 TỔNG HỢP CÁC LỆNH CHẠY DỰ ÁN VIETLABOR AI

Tài liệu này tổng hợp toàn bộ các câu lệnh cần thiết để thiết lập, khởi chạy, kiểm thử và đánh giá dự án **VietLabor AI (Chatbot Pháp luật Lao động)** trên hệ điều hành Windows.

---

## ⚡ 1. Khởi Chạy Nhanh (Quick Start)

Nếu máy đã cài sẵn môi trường và đã tải model Ollama, bạn chỉ cần mở Terminal tại thư mục dự án `d:\chatbot-law` và chạy:

```powershell
# 1. Kích hoạt môi trường ảo
.\.venv\Scripts\Activate.ps1

# 2. Khởi chạy giao diện Web (Streamlit)
streamlit run ui/streamlit_app.py
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
# Mô hình chuẩn mặc định của dự án:
ollama run qwen2.5:7b

# Hoặc mô hình chuyên xuất JSON và định dạng:
ollama run qwen2.5-coder:7b
```

---

## 🚀 4. Các Lệnh Khởi Chạy Ứng Dụng (Running the App)

### 4.1. Giao diện Web (Streamlit UI)
```powershell
streamlit run ui/streamlit_app.py
```
*Tùy chọn chỉ định cổng nếu cổng 8501 bị chiếm:*
```powershell
streamlit run ui/streamlit_app.py --server.port 8502
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
```

### 5.4. Xây dựng chỉ mục tìm kiếm (BM25 + ChromaDB)
```powershell
# Xây dựng cả 2 chỉ mục (BM25 và Chroma Vectorstore)
python scripts/build_index.py

# Bắt buộc xây dựng lại từ đầu (Force Rebuild)
python scripts/build_index.py --force

# Chỉ xây dựng lại chỉ mục BM25
python scripts/build_index.py --target bm25 --force

# Chỉ xây dựng lại chỉ mục Vector ChromaDB
python scripts/build_index.py --target chroma --force
```

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
```

### 6.2. Chạy từng nhóm bài kiểm thử cụ thể
```powershell
# Kiểm thử giao diện và định dạng Markdown (xuống dòng, tiêu đề)
pytest tests/test_ui_service.py tests/test_format_markdown.py

# Kiểm thử chống ảo giác trích dẫn (Zero Phantom Citations)
pytest tests/test_phase5d_regression.py

# Kiểm thử bộ chọn căn cứ pháp lý then chốt (Evidence Selector)
pytest tests/test_phase5e_evidence_selector.py

# Kiểm thử hồi quy các giai đoạn trước
pytest tests/test_phase5b_regression.py tests/test_phase5c_regression.py
```

---

## 📊 7. Đánh Giá & Đo Đạc Hiệu Năng (Benchmark & Evaluation)

### 7.1. Đánh giá chất lượng truy hồi (Retrieval Benchmark)
```powershell
python evaluation/benchmark_phase5c_retrieval.py
```

### 7.2. Đánh giá chất lượng sinh văn bản & độ chính xác trích dẫn (Generation Benchmark)
```powershell
python evaluation/benchmark_phase5d_generation.py
```

### 7.3. Đánh giá kịch bản thực tế phức tạp (Real-World Benchmark)
```powershell
python evaluation/benchmark_phase5f_realworld.py
```

### 7.4. Kiểm thử các tình huống thực tế mẫu
```powershell
python scripts/test_real_cases.py
```

---

## 🔧 8. Khắc Phục Lỗi Thường Gặp (Troubleshooting)

| Lỗi | Nguyên nhân | Cách khắc phục |
| :--- | :--- | :--- |
| **`Execution_Policies` khi bật `.venv`** | Windows chặn chạy script PowerShell chưa ký | Chạy lệnh: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |
| **`ConnectionRefusedError` hoặc lỗi kết nối Ollama** | Ollama chưa được bật trên máy | Mở ứng dụng Ollama hoặc chạy lệnh: `ollama serve` |
| **`Model 'qwen2.5:7b' not found`** | Chưa tải mô hình về máy | Chạy lệnh: `ollama pull qwen2.5:7b` |
| **Lỗi cổng `8501` bị chiếm khi chạy Streamlit** | Tiến trình Streamlit cũ chưa tắt | Đổi cổng: `streamlit run ui/streamlit_app.py --server.port 8502` |
