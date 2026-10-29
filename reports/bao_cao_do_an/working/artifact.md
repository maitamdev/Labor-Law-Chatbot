# Hợp đồng trình bày báo cáo

Nguồn tham chiếu bố cục là C:\Users\Asus\Desktop\Bao_cao_Do_an_co_so_POS_Quan_ly_kho_Canh_bao_ton_kho_thap_FINAL.docx. Hash và kiểm kê section nằm trong audit.json. Nguồn được giữ nguyên, không sửa. Tệp chỉ có 4 trang: hai bìa, lời cảm ơn và lời cam đoan; không có các chương POS để tái sử dụng.

Nguồn yêu cầu định dạng là C:\Users\Asus\Desktop\2 Biểu mẫu báo cáo.doc, đã đọc qua Word và lưu bản chuyển đổi nội bộ working/bieu_mau.docx. Mẫu có 12 trang. Yêu cầu chữ trong mẫu được ưu tiên hơn thuộc tính lề thực tế của tệp mẫu vì chúng mâu thuẫn nhau.

Tái sử dụng hai trang bìa từ bản sao của báo cáo POS, bao gồm logo trường và khung trang. Thay tên học phần, đề tài, sinh viên theo chỉ dẫn người dùng. Tên học phần BÁO CÁO HỌC PHẦN ỨNG DỤNG AI, đề tài XÂY DỰNG CHATBOT HỖ TRỢ TRA CỨU QUY ĐỊNH PHÁP LUẬT LAO ĐỘNG VIỆT NAM. Sinh viên MAI TRẦN THIỆN TÂM, MSSV 2305CT2070. Giảng viên, lớp, khóa chưa cung cấp nên ghi [CẦN ĐIỀN]. Không tái sử dụng tên giảng viên trong lời cảm ơn của báo cáo POS.

Hai bìa giữ phong cách font Times New Roman, logo chính giữa, khung và thông tin trình bày ở phần dưới. Phần sau bìa được thay nội dung toàn bộ. Trang phụ bìa là bản lặp theo mẫu. Phần mở đầu và thân bài dùng A4 21 x 29,7 cm; lề trên 3,5, dưới 3, trái 3,5 và phải 2 cm; Times New Roman 14; giãn dòng 1,5; Heading 1 16 đậm in hoa; Heading 2 14 đậm in hoa; Heading 3 14 đậm. Chữ trong bảng và caption 14 pt; bảng giãn dòng 1,12 để không nén chữ. Ghi chú nguồn hình 11 pt và mã lệnh 10 pt là ngoại lệ đã ghi trong phụ lục đối chiếu. Trang 1 bắt đầu tại MỞ ĐẦU, đánh giữa đầu trang; phần đầu không có số trang. Trang bìa 25 pt cho đề tài, xuống dòng tự nhiên, không kéo giãn hoặc nén chữ.

Mục lục, danh mục hình và bảng là field Word, làm mới bằng Word COM. Tạo caption và bookmark tương ứng. Hình do phân tích mã nguồn được ghi là tác giả tổng hợp từ mã nguồn; hình approved-homepage.png chỉ là ảnh tham chiếu có sẵn, không là minh chứng chạy thử ngày rà soát.

Tái sử dụng package của báo cáo POS qua python-docx vì thay đổi kết cấu toàn bộ thân báo cáo là chủ đích. Giữ lại ảnh logo và page border của bìa, không có custom XML, footnote hoặc rich control cần bảo tồn. Section bổ sung để có đánh số trang độc lập. Thay đổi lề thân bài theo quy định bằng chữ là chủ đích. Không đòi giữ số section, số trang hoặc heading POS.

Chưa thể tuyên bố đạt 70–100 trang văn bản thuần theo mẫu khi chưa có đủ minh chứng thực nghiệm. Đếm số trang sau render, công bố trung thực. Không thêm trang trắng hoặc lời văn lặp để đủ độ dày.

Renderer gói render_docx.py đã thử và không chạy vì thiếu LibreOffice soffice.exe trên Windows. Dùng Microsoft Word cài sẵn để cập nhật field và xuất PDF nội bộ, sau đó PyMuPDF của runtime gói để render từng trang PNG và kiểm tra bố cục. PDF/PNG chỉ là QA.
