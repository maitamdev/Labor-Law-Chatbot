from pathlib import Path
p=Path(r'D:\chatbot-law\reports\bao_cao_do_an\noi_dung_bao_cao.md')
s=p.read_text(encoding='utf-8')
s=s.replace('Bản nộp cuối nên bổ sung ảnh màn hình thực tế gồm trang hỏi đáp, câu trả lời có căn cứ, yêu cầu làm rõ, tài liệu đính kèm và trang đồ thị, kèm đầu vào có thể tái lập.','Phụ lục F đã bổ sung ảnh chạy thực tế của trang chủ, câu trả lời có căn cứ, yêu cầu làm rõ và câu hỏi ngoài phạm vi. Minh chứng tài liệu đính kèm và đồ thị online vẫn cần bổ sung cùng đầu vào có thể tái lập.')
s=s.replace('trong lần soạn báo cáo này chỉ bộ pytest mặc định đã được chạy mới.','trong lần soạn báo cáo này bộ pytest mặc định đã được chạy mới, đồng thời một số luồng giao diện được kiểm tra và lưu ảnh ở Phụ lục F. Các bộ benchmark định lượng cũ chưa được chạy lại.')
demo='''## 5.16 Kiểm tra giao diện thực tế bổ sung

Ứng dụng được khởi động bằng python -m app.main tại 127.0.0.1:8501 ngày 12/10/2026. Ollama tại 127.0.0.1:11434 có model qwen2.5:7b-instruct-q4_0. Không có dịch vụ Neo4j lắng nghe tại 7474 hoặc 7687 trong lúc kiểm tra, nên lần demo này không dùng để chứng minh hoạt động đồ thị online. Trình duyệt hiển thị ở vùng xem 734 × 884 pixel; ảnh giữ bố cục đáp ứng của ứng dụng và không được chỉnh thành mockup.

Ca thứ nhất hỏi về người lao động có hợp đồng xác định thời hạn 24 tháng, đơn phương chấm dứt trong trường hợp thông thường. Giao diện trả lời ít nhất 30 ngày và hiển thị Điều 35 khoản 1 điểm b. Khi mở thẻ căn cứ, nội dung đoạn nguồn và liên kết văn bản hiện ra. Đây là minh chứng thao tác được luồng hỏi đáp và xem nguồn của ca này; chưa phải phép đo Citation Precision trên toàn bộ câu trả lời.

Ca thứ hai chỉ hỏi thời hạn báo trước khi nghỉ việc. Hệ thống yêu cầu chọn loại hợp đồng, thể hiện hành vi làm rõ. Tuy nhiên, khi chọn phương án hợp đồng xác định thời hạn 12–36 tháng, lượt tiếp theo hiện thông báo “Hệ thống chưa thể xử lý câu hỏi này”. Nhánh except Exception trong ui/streamlit_app.py tạo thông báo chung và không lưu traceback ở vị trí được kiểm tra, nên chưa đủ bằng chứng xác định nguyên nhân gốc. Lỗi phải được tái lập, ghi log và xử lý trước khi xem luồng làm rõ là hoàn chỉnh. Nội dung làm rõ cũng hiển thị cụm “36 BLLĐ”; cần rà lại quá trình chuẩn hóa căn cứ để tránh làm mất hoặc đổi thông tin điều luật.

Ca thứ ba hỏi thủ tục chia di sản thừa kế là quyền sử dụng đất nông nghiệp. Hệ thống thông báo câu hỏi ngoài phạm vi và chuyển hướng về chủ đề lao động. Ảnh, đầu vào và đầu ra quan sát của các ca được lưu ở Phụ lục F và thư mục minh_chung trong gói bàn giao. Không tính tỷ lệ chính xác tổng thể từ các ca chọn để demo, không lấy thời gian thao tác trình duyệt làm độ trễ mô hình và không sửa số liệu ablation cũ thành kết quả chạy mới.

'''
s=s.replace('# CHƯƠNG 6 KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN',demo+'# CHƯƠNG 6 KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN')
s=s.replace('Chưa có đánh giá tải, bảo vệ dữ liệu nhiều người dùng hoặc nghiên cứu trải nghiệm người dùng.','Chưa có đánh giá tải, bảo vệ dữ liệu nhiều người dùng hoặc nghiên cứu trải nghiệm người dùng. Demo giao diện bổ sung còn phát hiện lỗi ở lượt chọn loại hợp đồng sau yêu cầu làm rõ; lỗi này không được xem là đã sửa chỉ vì bộ pytest mặc định đạt.')
s += '''

# PHỤ LỤC F MINH CHỨNG CHẠY ỨNG DỤNG

## F.1 Trang chủ thực tế

Ảnh được chụp ngày 12/10/2026 sau khi khởi động python -m app.main. Địa chỉ truy cập 127.0.0.1:8501; Ollama sử dụng model qwen2.5:7b-instruct-q4_0. Vùng xem 734 × 884 pixel khiến menu trái được thu gọn và khối văn bản chuyển xuống dưới. Ảnh này là minh chứng giao diện đang chạy, khác ảnh tham chiếu ở Hình 3.6.

@figure F.1 Trang chủ ứng dụng trong lần demo thực tế | UI01_trang_chu.jpg

## F.2 Hỏi đáp có căn cứ

Đầu vào: “Tôi ký hợp đồng lao động xác định thời hạn 24 tháng. Nếu tôi đơn phương chấm dứt hợp đồng theo trường hợp thông thường thì phải báo trước bao nhiêu ngày?”. Giao diện trả lời ít nhất 30 ngày và có thẻ Điều 35 khoản 1 điểm b. Nội dung đầu ra được lưu trong UI02_ket_qua.txt; ảnh mở nguồn bổ sung là UI03_can_cu.jpg.

@figure F.2 Câu hỏi, câu trả lời và căn cứ của ca hợp đồng 24 tháng | UI02_cau_tra_loi.jpg

## F.3 Yêu cầu làm rõ

Đầu vào trong phiên mới: “Tôi muốn nghỉ việc thì phải báo trước bao nhiêu ngày?”. Giao diện yêu cầu chọn loại hợp đồng và có các phương án để người dùng bổ sung dữ kiện. Lần quan sát này chứng minh có bước hỏi lại ở ca được thử, chưa chứng minh mọi tình huống thiếu tiền đề đều được nhận diện.

@figure F.3 Phản hồi yêu cầu người dùng bổ sung loại hợp đồng | UI04_lam_ro.jpg

## F.4 Lỗi quan sát ở lượt tiếp theo

Thao tác: bấm phương án “Hợp đồng xác định thời hạn 12 - 36 tháng (báo trước ít nhất 30 ngày)”. Kết quả hiển thị thông báo chưa thể xử lý câu hỏi. Cần giữ ca này trong danh sách hồi quy, bổ sung log ngoại lệ rồi kiểm tra cả ChatService, bộ nhớ và bước viết lại truy vấn. Báo cáo không suy đoán thành phần gây lỗi khi chưa có traceback.

@figure F.4 Thông báo lỗi sau khi chọn dữ kiện bổ sung | UI05_noi_tiep_loi.jpg

## F.5 Câu hỏi ngoài phạm vi

Đầu vào trong phiên mới: “Thủ tục phân chia di sản thừa kế là quyền sử dụng đất nông nghiệp như thế nào?”. Giao diện phản hồi ngoài phạm vi tra cứu lao động và gợi ý các câu hỏi phù hợp. Ca này được lưu riêng trong UI06_ket_qua.txt; không gộp thành kết quả của bộ 15 rubric cũ.

@figure F.5 Phản hồi từ chối câu hỏi ngoài phạm vi lao động | UI06_ngoai_pham_vi.jpg
'''
p.write_text(s,encoding='utf-8')
