# Kiểm chứng sửa lỗi chat và điều hướng — 29/10/2026

## Các lỗi đã xử lý

### Menu tự quay về mục trước

Máy chủ từng dựng giao diện trước khi áp dụng sự kiện điều hướng. Ngoài ra,
phản hồi của lần bấm trước có thể đến sau lần bấm tiếp theo và ghi đè lựa chọn
mới trong trình duyệt. Điều hướng hiện được áp dụng trước khi dựng giao diện;
trình duyệt giữ mã hành động đang chờ cho đến khi nhận đúng xác nhận từ máy chủ.
Phản hồi cũ không được thay đổi mục đang chọn. Thao tác mở cuộc chat khác hoặc
gửi câu hỏi mới giải phóng trạng thái điều hướng đang chờ.

Đã bổ sung bộ chọn CSS còn thiếu cho trang đồ thị tri thức.

### Câu hỏi về an toàn lao động bị từ chối sai

Bộ lọc bỏ dấu đã biến cụm “lở đe” trong “sạt lở đe dọa” thành “lo de”, trùng
với tín hiệu về lô đề. Bộ lọc hiện phân biệt chữ có dấu, vẫn nhận dạng câu hỏi
không dấu và không chặn nhầm ngữ cảnh lao động có ngày tháng hoặc hệ quả kỷ luật.

Đã kiểm tra 1.000 câu hỏi lao động trong bộ dữ liệu: không có câu bị từ chối
nhầm bởi bộ lọc phạm vi. Đây là kiểm tra phân loại phạm vi, không phải đánh giá
độ đúng của 1.000 câu trả lời do mô hình sinh ra.

### Trả lời quá ngắn, phần căn cứ quá dài

Ngữ cảnh của một số khoản trước đây chỉ chứa câu dẫn và thiếu các điểm con.
Hiện đã bổ sung điểm con khi lấy toàn khoản, đồng thời giữ phạm vi riêng khi
chỉ lấy một điểm. Câu hỏi tổng quan về sa thải được cung cấp đủ bốn khoản của
Điều 125, thủ tục tại khoản 1 Điều 122 và các thời gian được bảo vệ tại khoản 4.

Câu hỏi tổng quan được yêu cầu giải thích trường hợp áp dụng, thủ tục và ngoại
lệ. Câu trả lời quá sơ sài được bổ sung tối đa một lần. Nếu vẫn thiếu, hệ thống
dựng phần trình bày có cấu trúc từ các nguồn đã có trong ngữ cảnh và kiểm tra
lại căn cứ, quyền sở hữu chứng cứ theo vấn đề và các ràng buộc pháp luật.
Một điểm riêng lẻ không được coi là đã bao phủ toàn bộ khoản có nhiều điểm.
Các yêu cầu trả lời ngắn gọn vẫn được tôn trọng.

Cấu hình mặc định dùng JSON schema chặt chẽ, ngữ cảnh 8.192 token và tối đa
1.800 token sinh; giá trị môi trường do người vận hành đặt vẫn có hiệu lực.

Giao diện gom trích dẫn theo văn bản, đóng mặc định và mở từng điều/khoản để
xem toàn bộ nội dung nguồn. Việc xuất PDF vẫn giữ câu trả lời và các trích dẫn.
Không cắt nội dung phân tích chỉ vì mô hình sử dụng tiêu đề “CĂN CỨ PHÁP LÝ”.

## Kết quả kiểm chứng

- Bộ kiểm thử Python: **584 đạt, 6 bỏ qua có điều kiện**.
- Kiểm thử tương tác JavaScript: **10 đạt**, gồm phản hồi điều hướng đến muộn.
- Trình duyệt thật: **24 tình huống điều hướng đạt**, gồm bấm nhanh, màn hình
  điện thoại và chuyển mục trong lúc AI xử lý câu hỏi.
- Câu hỏi sạt lở/cắt thưởng được trả lời trên ứng dụng chạy thật với Ollama.
- Câu hỏi sa thải đã được kiểm tra trên ứng dụng thật: đủ các nhóm trường hợp,
  thủ tục và thời gian được bảo vệ; tám trích dẫn gom thành một mục văn bản;
  mở nguồn, xuất PDF và bố cục điện thoại hoạt động.
- Ruff, Pyright, kiểm tra cú pháp JavaScript và kiểm tra khoảng trắng của diff đạt.

Chứng cứ chạy thử nằm trong `storage/scope_fix_20261029/` và
`storage/answer_quality_20261029/`, gồm JSON kết quả, ảnh giao diện và bản PDF.
Các thư mục này là dữ liệu kiểm chứng cục bộ, không được đưa lên kho mã nguồn.

Sau khi tải lại trang, cần tạo lại câu trả lời cũ để áp dụng cách trả lời mới.
Nội dung đã lưu trong lịch sử không tự được viết lại. Không thực hiện push,
publish hoặc deploy.
