# Báo Cáo Đánh Giá Thực Nghiệm Bộ 11 Câu Hỏi Pháp Lý Vàng (Benchmark 11 Gold Questions)

**Hệ thống**: VietLabor AI – Hybrid GraphRAG Pipeline  
**Model**: `qwen2.5:7b-instruct-q4_0` (Local Ollama, GPU Accelerated)  
**Thời gian thực nghiệm**: 12/10/2026 13:20  
**Tập câu hỏi**: 11 tình huống pháp lý phức tạp / đa vấn đề / có bẫy xung đột pháp luật.

---

## 📊 1. BẢNG TỔNG HỢP KẾT QUẢ THỰC NGHIỆM

| STT | Tình huống pháp lý kiểm thử | Latency | Grounding Status | Căn cứ luật định cốt lõi | Kết luận pháp lý đạt chuẩn |
| :---: | :--- | :---: | :---: | :--- | :---: |
| **Q0** | Nữ nuôi con dưới 1 tuổi, vị trí hết việc; chuyển việc khác không đồng ý; thỏa thuận báo trước 45 ngày; nhận cả 2 trợ cấp thôi việc & mất việc? | **42.6s** | **100% Grounded** (2/2 issues) | BLLĐ 2019 Điều 37k3, Điều 137k3, Điều 39, Điều 46k1, Điều 47k1, Điều 29k1 | **ĐẠT XUẤT SẮC** (Không được đơn phương chấm dứt; 2 trợ cấp loại trừ nhau) |
| **Q1** | Lao động mang thai 5 tháng hay nghỉ đi khám thai, công ty báo chấm dứt HĐLĐ. | **25.3s** | **Grounded** | BLLĐ 2019 Điều 37k3, Điều 137k3, Điều 122k4d, Điều 39, Điều 41 | **ĐẠT** (Cấm sa thải / đơn phương chấm dứt; bồi thường theo Điều 41) |
| **Q2** | Bắt làm thêm 4 tiếng/ngày không trả lương tăng ca, từ chối thì bị trừ lương. | **23.5s** | **Grounded** | BLLĐ 2019 Điều 127k2, Điều 102k1, Điều 107k2a, Điều 107k2b, Điều 98 | **ĐẠT** (Cấm phạt tiền/cắt lương; làm thêm phải có thỏa thuận) |
| **Q3** | Bị tai nạn giao thông nằm viện 2 tuần thì nhận quyết định cho nghỉ việc. | **19.7s** | **Grounded** | BLLĐ 2019 Điều 37k1, Điều 36k1b, Điều 122k4a, Điều 39, Điều 41 | **ĐẠT** (Đang điều trị được bảo vệ; 2 tuần chưa đủ hạn Điều 36k1b) |
| **Q4** | Thử việc công nhân đứng máy 3 tháng và chỉ trả 70% lương. | **19.1s** | **Grounded** | BLLĐ 2019 Điều 25k3, Điều 26 | **ĐẠT** (Lương thử việc tối thiểu 85%; thời gian tối đa 30 ngày) |
| **Q5** | Đã ký 2 HĐLĐ 1 năm liên tiếp, công ty muốn ký tiếp HĐ 1 năm lần thứ 3. | **13.8s** | **Grounded** | BLLĐ 2019 Điều 20k2b, Điều 20k2c | **ĐẠT** (Chỉ được ký thêm 1 lần; lần 3 bắt buộc là HĐLĐ không xác định thời hạn) |
| **Q6** | Công ty nợ lương 2 tháng, người lao động muốn nghỉ việc ngay không báo trước. | **20.9s** | **Grounded** | BLLĐ 2019 Điều 35k2b, Điều 94, Điều 97k4 | **ĐẠT** (Được quyền nghỉ ngay không cần báo trước theo Điều 35k2b) |
| **Q7** | Đi làm trễ 10 phút công ty phạt 200.000 đồng trừ thẳng vào lương. | **11.7s** | **Grounded** | BLLĐ 2019 Điều 127k2, Điều 102k1, Điều 102k3 | **ĐẠT** (Hành vi trừ lương trái pháp luật; cấm phạt tiền thay kỷ luật) |
| **Q8** | Tái cơ cấu cắt giảm nhân sự, làm được 5 năm nhận những khoản gì? | **17.4s** | **Grounded** | BLLĐ 2019 Điều 42k3, Điều 47k1 | **ĐẠT** (Hưởng trợ cấp mất việc làm, mỗi năm 1 tháng lương, tối thiểu 2 tháng) |
| **Q9** | Nghỉ việc riêng 3 ngày không xin phép vì việc gấp, công ty có được sa thải? | **7.8s** | **Grounded** | BLLĐ 2019 Điều 125k4 | **ĐẠT** (Chưa đủ điều kiện sa thải; Điều 125 yêu cầu 5 ngày cộng dồn trong 30 ngày) |
| **Q10** | Công ty chuyển sang bộ phận kho 4 tháng không đồng ý có đúng không? | **11.1s** | **Grounded** | BLLĐ 2019 Điều 29k1 | **ĐẠT** (Tạm thời chuyển tối đa 60 ngày/năm; quá 60 ngày phải có thỏa thuận bằng văn bản) |

---

## 🛠️ 2. CHI TIẾT CÁC CẢI TIẾN ĐÃ NÂNG CẤP HÔM NAY

1. **Khắc phục triệt để lỗi "Chưa đủ căn cứ do dùng nhầm căn cứ của vấn đề khác"**:
   - Tối ưu `rag/context_builder.py`: Bảo toàn đúng `owner` quy định trong `priority_chunk_ids` từ `StatutoryConstraintEngine`, không để danh sách ứng viên ban đầu của vấn đề khác chiếm đoạt quyền sở hữu căn cứ bảo vệ đặc biệt (như Điều 137k3).
   - Tối ưu `rag/output_validator.py`: Khi phát hiện một citation token ngoài danh mục của sub-issue, hệ thống bóc tách và loại bỏ token đó khỏi văn bản nhưng **vẫn giữ nguyên lập luận pháp lý chính xác** nếu danh sách `clean_tokens` vẫn chứa các căn cứ đúng của vấn đề, không còn xóa sạch câu trả lời để thay bằng câu fallback nữa.

2. **Khắc phục lỗi mất nội dung kết luận khi LLM trả về tiêu đề rỗng**:
   - Khi mô hình LLM cục bộ chỉ sinh tiêu đề Markdown `### Vấn đề...` ở trường `"answer"` và đặt toàn bộ lập luận chi tiết trong mảng `"findings"`, `OutputValidator.parse_llm_json` và `validate_and_format` tự động kích hoạt bộ tổng hợp `synthesize_answer_from_findings` để đưa toàn bộ nội dung phán quyết vào văn bản trả lời cho người dùng.

3. **Khử trùng lặp cú pháp trích dẫn điều khoản**:
   - Trong `rag/evidence_mapper.py`: Tự động nhận diện và gộp các cụm từ điều khoản bị lặp lại do mô hình đã viết trước khi điền token (ví dụ: `Khoản 3 Điều 37 Khoản 3 Điều 37` $\rightarrow$ `Khoản 3 Điều 37 Bộ luật Lao động 2019`).

4. **Kiểm thử hồi quy toàn diện**:
   - Chạy toàn bộ bộ test `pytest tests/`: **345 test passed tuyệt đối 100%**.
