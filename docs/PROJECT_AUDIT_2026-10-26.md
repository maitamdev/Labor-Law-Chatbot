# Rà soát dự án — 26/10/2026

Đã rà soát mã nguồn, chạy kiểm thử Python, gọi Ollama thực tế, kiểm tra giao diện bằng Chromium, chạy SQL phân quyền trong PostgreSQL/PGlite và kiểm tra bản đóng gói. Công việc được thực hiện trực tiếp, không dùng sub-agent; không commit, push, publish hoặc deploy.

Kho làm việc đã có nhiều thay đổi và tệp chưa được theo dõi trước đợt rà soát. Các thay đổi đó được giữ lại. Bản chụp mã nguồn trước khi sửa nằm tại `storage/audit_20261026/before/`; dữ liệu pháp luật và chỉ mục production không được tái tạo hoặc thay thế trong đợt này.

## Các lỗi đã sửa

| Khu vực | Vấn đề và thay đổi |
|---|---|
| Giao diện Streamlit | Bỏ monkeypatch asyncio bị thực thi lặp khi rerun; sửa nhánh lưu tệp đính kèm có tên biến chưa định nghĩa; lưu metadata đính kèm đúng một lần. |
| Lịch sử trò chuyện | Sao chép sâu snapshot để bên gọi không sửa ngầm dữ liệu cache; dùng thời gian sửa tệp ở độ chính xác nanosecond; thông báo lỗi ghi tệp thay vì báo lưu thành công. |
| Cache câu trả lời | Tạo lại câu trả lời sẽ loại bỏ bản cache cũ, kể cả khi kết quả mới không đủ căn cứ để đưa vào cache. |
| Embedding | Dùng chung model theo tên, thiết bị và thư mục cache; khóa nạp/suy luận; cache truy vấn LRU tối đa 512 mục và trả bản sao vector. Không tự thay model khác khi model yêu cầu bị thiếu. |
| Corpus và chỉ mục | Tách cache theo đường dẫn và phiên bản tệp; ContextBuilder và QA anchor theo đúng corpus của retriever được truyền vào; BM25 cập nhật lookup khi xây lại chỉ mục cùng số lượng chunk. |
| Vector store | Kiểm tra ID trùng và kích thước batch trước thao tác rebuild; ngừng tái sử dụng pickle vector cũ không có thông tin chứng minh model và nội dung tương ứng; đóng kết nối SQLite và đọc ở chế độ chỉ đọc. |
| Bộ chọn căn cứ | Chia hàm chấm điểm lớn thành các phần nhỏ; xử lý metadata null và số điều/khoản không chuyển được thành số nguyên. Đối chiếu 3.000 phép chấm điểm để kiểm tra refactor giữ nguyên kết quả trên dữ liệu hợp lệ. |
| Ngữ cảnh trả lời | Ưu tiên căn cứ ngoại lệ khi câu hỏi về nghỉ việc do bố trí sai công việc. Trước sửa, các điều khoản báo trước lấn hết ngân sách ngữ cảnh và ca Ollama có sẵn bị trượt; sau sửa, ca đó đạt. Không thay các assertion kết luận cũ. |
| Quản trị và tài khoản | Thực hiện đầy đủ preload của các trang quản trị với transport được truyền vào; phát hiện JSON/row response sai cấu trúc; xử lý con trỏ chỉ mục lỗi; chỉ đọc tối đa ba trang PDF khi tạo preview. |
| Cấu hình và health check | Đường dẫn tương đối độc lập với thư mục khởi chạy; báo riêng lỗi cấu hình và lỗi kho dữ liệu; đếm đúng collection Chroma cần kiểm tra. |
| Đóng gói và môi trường | Sửa phát hiện package của setuptools; bổ sung dependency và tài nguyên giao diện còn thiếu; đồng bộ requirements với pyproject; chuyển DeepEval sang nhóm tùy chọn. |
| Container | Loại thông tin bí mật khỏi build context; app chờ tác vụ tải model Ollama hoàn thành. Chỉ kiểm tra cấu hình, chưa build/chạy Docker trên máy này. |
| Chất lượng mã | Sửa lỗi lint trong nguồn ứng dụng, scripts, evaluation, tests và notebook. Pyright kiểm tra 136 tệp nguồn, không quét các bản sao báo cáo, dữ liệu sinh ra và fixture kiểm thử động. |

Các cải thiện hiệu năng ở đây gồm giảm nạp model lặp, giới hạn bộ nhớ cache, giảm số trang PDF phải đọc và tránh đọc lại corpus giữa các phiên cùng phiên bản. Chưa thực hiện benchmark tải đồng thời để kết luận phần trăm tăng tốc.

## Kết quả kiểm chứng

- Trước sửa: 465 kiểm thử Python đạt, 6 ca Ollama bị bỏ qua theo cấu hình mặc định.
- Lượt đầy đủ có Ollama sau sửa: **503 đạt**, không bỏ qua, 330,69 giây.
- Lượt ngoại tuyến cuối cùng, sau khi thêm hai ca metadata null: **499 đạt, 6 ca Ollama được bỏ qua đúng cấu hình**, 52,50 giây. Toàn bộ bộ kiểm thử hiện có **505 ca**, tăng 34 ca so với ban đầu; sáu ca Ollama đã đạt ở lượt đầy đủ phía trên.
- **9/9** kiểm tra tương tác DOM đạt.
- **30/30** kiểm tra SQL về RLS, quyền quản trị, quyền riêng tư, thu hồi chia sẻ và ngăn hồi sinh lịch sử đã xóa đạt trong PostgreSQL/PGlite.
- **21/21** kịch bản trình duyệt quản trị đạt, không có lỗi JavaScript; có kiểm tra desktop, điện thoại, PDF, bảng dữ liệu, quyền hạn và thao tác lịch sử.
- Trang chính thực tế hiển thị trên Chromium ở 1440×1000 và 390×844; không có exception hoặc tràn ngang trên điện thoại. Đã xem ảnh chụp.
- Ruff không có lỗi; Pyright: **0 lỗi, 0 cảnh báo** trên 136 tệp; compileall đạt; pip check không có dependency hỏng.
- Corpus, BM25 và Chroma có cùng **9.390 ID chunk**, không chỉ cùng số lượng.
- Build wheel thành công; có 188 tệp, bao gồm JS/CSS/ảnh/YAML cần thiết, không chứa dữ liệu runtime, báo cáo, tests hoặc tệp secrets.

Nhật ký và bằng chứng cục bộ:

- `storage/audit_20261026/pytest-final.txt` và `pytest-final.xml`: lượt đầy đủ có Ollama.
- `storage/audit_20261026/pytest-offline-final.txt` và `pytest-offline-final.xml`: lượt ngoại tuyến cuối cùng sau khi thêm hai ca metadata null.
- `storage/audit_20261026/pyright-final.json`, `frontend-final.txt`, `rls-final.txt`.
- `storage/audit_20261026/browser/verification.json` và các ảnh giao diện quản trị.
- `storage/audit_20261026/main-ui-verification.json`, `main-ui-desktop.png`, `main-ui-mobile.png`.
- `storage/audit_20261026/scoring_equivalence.json`, `index-integrity.json`, `wheel-verification.json`.
- `storage/audit_wheels/vietlabor_ai-0.1.0-py3-none-any.whl`.

## Môi trường và giới hạn

Dùng Python 3.11 trong `.venv` hiện có và Ollama với `qwen2.5:7b-instruct-q4_0`. Đã cài Pyright để kiểm tra kiểu; môi trường được đưa về PyYAML 6.0.2 và Kubernetes client 35.0.0 để giải quyết xung đột dependency với Paddlex/Chroma. Playwright và py-spy phục vụ kiểm chứng được đặt trong vùng công cụ bỏ qua bởi Git.

Các kiểm tra SQL và quản trị chạy trên fixture/PGlite, không xác nhận kết nối Supabase production, gửi email hay cấu hình Auth của dịch vụ thật. Chưa kiểm thử trực tiếp Neo4j hoặc Docker vì các dịch vụ/công cụ tương ứng không sẵn sàng. Chưa có kiểm thử tải lớn nhiều người dùng hoặc thẩm định độc lập toàn bộ nội dung pháp luật. Kết quả trên xác nhận những tình huống đã thực thi, không chứng minh hệ thống không còn mọi lỗi có thể xảy ra.

## Chạy lại

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest --run-ollama -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pyright
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts/health_check.py
.\.venv\Scripts\python.exe scripts/render_account_fixtures.py
node scripts/test_account_frontend.mjs
node scripts/test_supabase_rls.mjs
```

Các lệnh Node cần các package kiểm thử ở `storage/test_tools/node_modules` như môi trường kiểm chứng này; chúng không phải dependency runtime của ứng dụng.
