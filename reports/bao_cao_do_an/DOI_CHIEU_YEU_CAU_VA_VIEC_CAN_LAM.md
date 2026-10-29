# Đối chiếu báo cáo học phần Ứng dụng AI

Sinh viên: **Mai Trần Thiện Tâm — 2305CT2070**. Đề tài: **Xây dựng chatbot hỗ trợ tra cứu quy định pháp luật lao động Việt Nam**. Ngày đọc mã nguồn, kiểm kê và kiểm thử: 12/10/2026.

## Những gì đã làm

Đã đọc các thành phần chính của dự án `D:\chatbot-law`: giao diện, dịch vụ hội thoại, pipeline RAG, retriever, schema và builder Neo4j, ingestion/OCR, cấu hình triển khai, notebook và dữ liệu SFT, kiểm thử và các báo cáo thực nghiệm đã lưu. Đã đối chiếu khung sáu chương được dán, biểu mẫu `.doc` và báo cáo POS `.docx`.

Đã soạn bản Word hoàn chỉnh về cấu trúc: hai bìa, trang nhận xét, lời cảm ơn, lời cam đoan, tóm tắt Việt–Anh, mục lục, danh mục viết tắt, danh mục hình/bảng, Mở đầu, sáu chương, tài liệu tham khảo và sáu phụ lục. Họ tên, MSSV, học phần và đề tài đã thay theo thông tin bạn cung cấp. Giảng viên, lớp, khóa và ngày ký để `[CẦN ĐIỀN]`.

Đã vẽ 7 sơ đồ kỹ thuật và 2 biểu đồ từ mã nguồn/số liệu có thật. Đã chạy mới bộ kiểm thử mặc định: **366 passed, 6 skipped, 46,40 giây**. Đã khởi động ứng dụng, thử hỏi đáp có nguồn, yêu cầu làm rõ, lựa chọn nối tiếp và từ chối ngoài phạm vi; lưu 6 ảnh màn hình cùng các tệp đầu ra. Kết quả lỗi cũng được ghi, không chỉ chọn các ảnh thành công.

Các nguồn Word ban đầu được giữ nguyên. Báo cáo POS thực tế chỉ có 4 trang, nên chỉ dùng để tham chiếu bìa, logo và khung; không lấy nội dung POS làm nội dung chatbot. Biểu mẫu ghi Trường Đại học Hùng Vương TP.HCM. Cụm “chuẩn ĐH Bách Khoa 100%” trong văn bản dán không phải căn cứ xác nhận quy chuẩn của trường.

## Cần viết gì và đã viết ở đâu

| Phần | Nội dung đã viết | Việc cần bổ sung bằng minh chứng thật |
|---|---|---|
| Mở đầu | Lý do chọn đề tài, lịch sử hướng tiếp cận, mục tiêu, đối tượng, phạm vi, phương pháp | Rà lại yêu cầu riêng của giảng viên |
| Chương 1 | Bài toán tra cứu luật lao động; yêu cầu về nguồn, dữ liệu và giới hạn sản phẩm | Chốt tiêu chí nghiệm thu học phần |
| Chương 2 | LLM, attention, BM25, embedding, RRF, RAG, đồ thị, kiểm soát tiền đề và trích dẫn, LoRA/QLoRA | Bổ sung nghiên cứu liên quan nếu giảng viên yêu cầu số lượng nguồn lớn hơn |
| Chương 3 | Tác nhân, yêu cầu chức năng/phi chức năng, kiến trúc, pipeline, dữ liệu, đồ thị, trình tự, cache, giao diện, triển khai | Cập nhật sơ đồ khi code thay đổi |
| Chương 4 | Môi trường, tổ chức mã, ingestion, corpus, chỉ mục, Neo4j, OCR, hội thoại, cache, cấu hình SFT, Docker | Log nạp Neo4j và minh chứng tài liệu đính kèm; log huấn luyện nếu thực hiện |
| Chương 5 | Ablation đã lưu; pytest mới; phân tích độ trễ; giới hạn rubric; tình huống điển hình; phân loại lỗi; demo mới | Chạy benchmark có kiểm soát, chấm căn cứ/kết luận chặt hơn; khắc phục lỗi demo |
| Chương 6 | Kết quả, đóng góp, hạn chế, hướng hoàn thiện | Chỉ nâng mức kết luận sau khi có thực nghiệm tương ứng |
| Phụ lục A–F | Danh mục corpus và SFT; 15 ca rubric; ánh xạ mã; lệnh/rubric tái lập; đối chiếu mẫu; ảnh demo | Thêm hồ sơ đầu vào/đầu ra đầy đủ cho đợt đánh giá tiếp theo |

## Cần vẽ gì và đã vẽ

| Tệp trong `so_do` | Nội dung | Ghi chú sử dụng |
|---|---|---|
| 01_use_cases | Ca sử dụng người tra cứu và người vận hành | Vai trò vận hành qua script, chưa khẳng định có tài khoản admin |
| 02_architecture | Kiến trúc tổng thể | Neo4j tùy chọn; cache trong tiến trình |
| 03_pipeline | Luồng xử lý câu hỏi theo mã thực thi | Tiền đề trước retrieval; graph mở rộng sau hybrid |
| 04_graph_schema | Lược đồ được builder nạp | LegalDocument và Article; Article định danh theo chunk_id |
| 05_sequence | Trình tự hỏi đáp | UI → ChatService → RAG → Retriever/Ollama |
| 06_deployment | Triển khai cục bộ và kho dữ liệu | Tiến trình/container, Ollama, Neo4j, volume |
| 07_ingestion | Chuỗi đọc nguồn, OCR, parser và lập chỉ mục | BM25, Chroma và graph tùy chọn |
| 08_retrieval_chart | Hit@10 và Recall@10 | Số liệu ablation đã lưu; graph offline; trục bắt đầu 0,75 có ghi rõ |
| 09_latency_chart | Độ trễ 11 câu đã lưu | Không phải benchmark sinh mới |

Mỗi hình có PNG để chèn Word, SVG để chỉnh sửa và PDF riêng để in. Bảy sơ đồ có thêm Mermaid `.mmd` biểu diễn quan hệ. Mã tạo hình lưu trong `working/build_diagrams.py`; Mermaid và bản vẽ vector là các cách thể hiện cùng thiết kế, không bảo đảm bố cục giống nhau từng pixel. Sơ đồ kỹ thuật không thay cho ảnh runtime Neo4j hoặc log truy vấn.

## Đối chiếu yêu cầu biểu mẫu

| Yêu cầu | Trạng thái bản Word |
|---|---|
| Hai bìa và thông tin đề tài | Đã có, còn giảng viên/lớp/khóa |
| Lời cảm ơn, cam đoan | Đã soạn dự thảo; bạn đọc lại theo trải nghiệm thật và ký |
| TNR 14, thân bài 1,5 dòng | Đã áp dụng; chữ bảng và caption 14; bảng 1,12 dòng; ghi chú nguồn 11 và mã lệnh 10 là ngoại lệ được công bố |
| A4; trên/trái 3,5 cm; phải 2 cm; dưới 3 cm | Đã áp dụng thân bài; hai bìa giữ bố cục tham chiếu |
| Số trang giữa đầu, bắt đầu 1 tại Mở đầu | Đã áp dụng bằng section và field Word |
| Mục lục và danh mục hình/bảng | Đã tạo 3 field tự động và cập nhật bằng Microsoft Word |
| Đánh số chương, mục, bảng và hình | Đã có; hình phụ lục F đánh số F.1–F.5 |
| Tài liệu tham khảo | Có nguồn kỹ thuật gốc, nguồn văn bản chính thức và hồ sơ dự án; tách Việt/Anh/hồ sơ |
| 70–100 trang, không kể hình/bảng/đồ thị/tài liệu tham khảo | **Chưa đạt nguyên văn yêu cầu này**: phần Mở đầu đến hết Chương 6 chưa tới 70 trang ngay cả khi tính hình/bảng. Tổng số trang toàn tệp không chứng minh đạt yêu cầu. Xem số trang kiểm kê trong `minh_chung/kiem_tra_ban_giao.json`. Nếu học phần AI áp dụng quy định khác, chốt với giảng viên; nếu giữ nguyên, cần thêm thực nghiệm và phân tích có bằng chứng |
| In một mặt, bìa cứng và chữ vàng | Là công đoạn in/nộp; cần xác định có áp dụng cho học phần AI hay chỉ mẫu đồ án tốt nghiệp |

## Các việc cần làm trước khi nộp

1. **Điền thông tin học vụ**: giảng viên, lớp, khóa, ngày ký. Kiểm tra tên trường theo đơn vị đang học. Đọc lại lời cảm ơn/cam đoan và chỉ ký khi nội dung đúng thực tế.
2. **Sửa luồng nối tiếp sau khi làm rõ**: phiên mới → hỏi “Tôi muốn nghỉ việc thì phải báo trước bao nhiêu ngày?” → chọn hợp đồng 12–36 tháng. Demo hiện trả thông báo không xử lý được. Cần ghi traceback tại nhánh `except Exception` ở `ui/streamlit_app.py`, xác định lỗi, sửa và chạy lại cả thao tác UI lẫn ca hồi quy. Chưa xác định nguyên nhân gốc từ thông báo chung. Rà lại cụm “36 BLLĐ” trong câu làm rõ.
3. **Rà metadata hiệu lực**: 2.393 bản ghi chưa có status; registry thời gian riêng chưa đồng bộ corpus. Đồng thời rà mục văn bản nổi bật trên giao diện còn giới thiệu Nghị định 12/2022. Xác minh theo nguồn chính thức và điều khoản chuyển tiếp, rồi đồng bộ dữ liệu/lọc retrieval/chỉ mục.
4. **Chấm lại rubric**: đặc biệt TC_PAR_01, TC_MUL_01, TC_MUL_03. Chấm đúng vấn đề, chủ thể, điều/khoản/điểm, kết luận và ngoại lệ; không dùng một từ khóa rộng để kết luận PASS. Lưu toàn văn đầu ra.
5. **Bổ sung demo đọc tệp**: dùng hợp đồng giả lập DOCX/PDF có chữ và PDF scan ngắn. Chụp tên tệp, nội dung đã đọc, câu hỏi và phản hồi. Đánh giá lỗi OCR; ghi giới hạn 10 trang OCR. Không coi tài liệu người dùng là căn cứ pháp luật có hiệu lực.
6. **Thực nghiệm graph nếu thuộc mục tiêu bắt buộc**: chuẩn bị Neo4j, nạp dữ liệu và bật cấu hình; ghi số nút/cạnh, trạng thái kết nối và số đoạn mở rộng. So sánh hybrid với hybrid+graph trên cùng corpus/model/câu hỏi/context. Bảng hiện có ghi graph offline nên chưa chứng minh đóng góp đồ thị.
7. **Huấn luyện nếu thuộc mục tiêu bắt buộc**: khử trùng và tách train/validation/test theo nhóm; chạy notebook; lưu cấu hình, trainer_state, loss thật, thời gian, VRAM và checkpoint. Đánh giá trước/sau trên cùng RAG và tập giữ lại. Notebook hiện không có execution_count/output, nên báo cáo chưa công bố đã tinh chỉnh thành công.
8. **Đo lại hiệu năng và chất lượng**: tách model lạnh/ấm, cache miss/hit, thời gian token đầu và hoàn thành. Lưu median/P95, cấu hình máy, seed/phiên bản/hash corpus. Chấm faithfulness và citation precision bằng nhãn có căn cứ. Các con số 100% và dưới 3 giây trong khung chưa được minh chứng.
9. **Hoàn thiện độ dài bằng kết quả thật**: thêm phương pháp, thiết kế bộ test, kết quả đối chứng, phân tích từng loại lỗi, tác động tham số top-k/context/graph và thảo luận. Không cộng phụ lục, ảnh hay trang trắng để thay cho 70–100 trang văn bản yêu cầu trong mẫu.
10. **Chốt bản nộp**: cập nhật toàn bộ field trong Word sau chỉnh sửa, rà ngắt trang/caption, kiểm tra lại tên/mã/số liệu, xuất bản dùng để in và thực hiện yêu cầu đóng bìa theo hướng dẫn giảng viên.

## Những khẳng định đã sửa so với khung dán

- Cache thực tế dùng **SHA-256**, không phải MD5.
- Notebook đặt **LoRA alpha 16**, không phải 32; 150 max_steps chưa chứng minh đã chạy đủ số epoch nào.
- Builder dùng **LegalDocument, Article, HAS_ARTICLE, GUIDES, PENALIZES, REFERENCES**. Chapter/Clause/Point chưa được nạp thành nút riêng; 8 mục cầu dẫn cấu hình không phải số cạnh online.
- Giao diện hiện có nền sáng, đỏ/vàng; không mô tả thành Dark Theme Glassmorphism.
- Kết quả pytest mới là **366 passed, 6 skipped**, thay các số cũ không cùng snapshot.
- Không chuyển “15/15 PASS” của script cũ thành “100% chính xác pháp lý”; không khẳng định fine-tuning hoàn tất hay graph tăng điểm khi chưa có minh chứng.

## Cách dùng các tệp bàn giao

Mở `Bao_cao_Hoc_phan_Ung_dung_AI_Mai_Tran_Thien_Tam.docx` để đọc và chỉnh sửa. `noi_dung_bao_cao.md` là nguồn nội dung có các chỉ thị tạo bảng/hình. ZIP chứa sơ đồ, ảnh demo, kết quả pytest, bản thống kê, nguồn nội dung và mã tạo tài liệu; không chứa dữ liệu hội thoại cũ của bạn, mật khẩu, model hoặc corpus đầy đủ. Thư mục `working` gồm tệp trung gian phục vụ đối chiếu và kiểm tra dàn trang, không cần nộp cho giảng viên.

PDF và ảnh từng trang trong `working` chỉ phục vụ kiểm tra nội bộ. Bản Word đã được Microsoft Word cập nhật field và dàn trang; số trang có thể thay đổi khi đổi font, máy in hoặc chỉnh sửa.
