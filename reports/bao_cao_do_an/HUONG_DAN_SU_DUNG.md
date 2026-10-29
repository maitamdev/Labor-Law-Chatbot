# Hồ sơ bàn giao báo cáo học phần Ứng dụng AI

Mai Trần Thiện Tâm — 2305CT2070. Đề tài: Xây dựng chatbot hỗ trợ tra cứu quy định pháp luật lao động Việt Nam.

Báo cáo Word có 103 trang sau khi dàn bằng Microsoft Word: 14 trang đầu, 66 trang từ Mở đầu đến hết Chương 6 (có hình/bảng), 2 trang tham khảo và 21 trang phụ lục. Chưa đạt yêu cầu 70–100 trang văn bản loại trừ hình/bảng/tham khảo nếu áp dụng nguyên văn biểu mẫu.

- Bao_cao_Hoc_phan_Ung_dung_AI_Mai_Tran_Thien_Tam.docx: bản báo cáo để đọc/chỉnh sửa; còn [CẦN ĐIỀN].
- DOI_CHIEU_YEU_CAU_VA_VIEC_CAN_LAM.md: phần đã làm, các yêu cầu và việc cần hoàn thiện.
- so_do/: 7 sơ đồ và 2 biểu đồ, có PNG/SVG/PDF; bảy sơ đồ có Mermaid .mmd.
- minh_chung/: 6 ảnh runtime, 4 tệp đầu ra của ca demo, kết quả pytest và kiểm kê dữ liệu. Demo có một lỗi nối tiếp chưa được sửa.
- nguon_benchmark/: các bảng/CSV đã có trước, không phải số liệu chạy mới trong lần soạn báo cáo.
- noi_dung_bao_cao.md và ma_tao_tai_lieu/: nguồn nội dung và mã tạo; chạy lại yêu cầu workspace gốc, báo cáo POS tham chiếu, python-docx, Pillow, ReportLab, PyMuPDF và Microsoft Word trên Windows. add_demo_content.py là thao tác biên soạn đã áp dụng, không chạy lặp.

Các bản PDF của sơ đồ dùng để in hình riêng. Không kèm PDF báo cáo và PNG từng trang phục vụ QA, corpus đầy đủ, model, thông tin kết nối hoặc lịch sử hội thoại cũ.

Kết quả pytest: 366 passed, 6 skipped in 46.40s. Notebook SFT chưa có output xác nhận; Neo4j chưa online trong demo; không công bố độ chính xác pháp lý 100%.
