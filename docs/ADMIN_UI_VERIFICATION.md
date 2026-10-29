# Kiểm tra khu quản trị VietLaborAI

Ngày cập nhật: 24/10/2026.

## Bảo vệ quyền riêng tư và phân quyền quản trị (v5.3)

Phiên bản v5.3 hoàn thiện ranh giới phân quyền giữa **Khách**, **Người dùng**, **Admin nghiệp vụ** và **Quản trị viên chính**, đồng thời bổ sung trung tâm quyền riêng tư `account-privacy` ("Quản lý dữ liệu của tôi") được cưỡng chế trực tiếp tại tầng PostgreSQL/RLS và máy chủ Python:

- **Tách quyền Quản trị viên chính (`admin_capabilities`)**:
  - `profiles.role` vẫn giữ `user` và `admin`; quyền quản trị viên chính (`manage_administrators = true`) được lưu trong bảng `public.admin_capabilities`, kiểm tra qua hàm `public.is_security_administrator()` và RPC `public.my_admin_permissions()`.
  - Không bao giờ tin quyền từ `user_metadata` hay tham số do trình duyệt gửi lên.
  - Admin nghiệp vụ quản lý được kho văn bản, xử lý phản hồi, vận hành AI và khóa/mở khóa tài khoản `user`, nhưng **không được** cấp/thu hồi quyền admin, không được khóa/quản lý tài khoản admin khác và không được quản lý lời mời admin.
  - Quản trị viên chính (`maitamit062005@gmail.com`) có quyền cấp/thu hồi quyền admin và quản lý tài khoản admin khác, nhưng vẫn bị chặn tự khóa/tự hạ quyền chính mình và vẫn **không được đọc lịch sử chat riêng của người khác**.
- **Ẩn danh hóa người gửi phản hồi đối với Admin**:
  - Cột `owner_id` của `public.feedback` bị thu hồi quyền `SELECT` khỏi vai trò `authenticated`. Admin chỉ đọc được các cột nghiệp vụ (`id, category, rating, comment, share_Consent, shared_question, shared_answer, status, admin_note, privacy_version, created_at, reviewed_by, reviewed_at`).
  - Người dùng đọc phản hồi của chính mình qua RPC `public.my_feedback()` (ẩn hoàn toàn `admin_note` và `reviewed_by` nội bộ của admin).
- **Thu hồi chia sẻ và xóa phản hồi chống ghi đè (`privacy_version`)**:
  - Người dùng thu hồi nội dung câu hỏi/câu trả lời đã chia sẻ qua `public.withdraw_my_feedback_consent(target_id)` (xóa `shared_question`, `shared_answer`, `admin_note`, tăng `privacy_version` và không ghi `actor_id` vào nhật ký quản trị để tránh lộ danh tính người gửi).
  - Người dùng xóa hẳn phản hồi của mình qua `public.delete_my_feedback(target_id)` (chỉ xóa khi `owner_id = auth.uid()`).
  - Admin lưu xử lý qua `public.review_feedback_safe(target_id, next_status, note_text, expected_privacy_version)`. Nếu người dùng vừa thu hồi chia sẻ hoặc xóa phản hồi khi admin đang mở màn hình cũ, cơ sở dữ liệu từ chối ghi chú cũ với lỗi `feedback privacy changed`.
- **Xóa toàn bộ lịch sử trò chuyện và chống phục hồi từ phiên cũ (`history_versions`)**:
  - Người dùng xóa toàn bộ lịch sử qua `public.delete_my_conversations()`, đồng thời tăng bộ đếm `public.history_versions.version`.
  - RPC lưu lịch sử `public.save_my_conversations(changed, deleted, expected_history_version)` bắt buộc đối chiếu `expected_history_version`. Nếu một tab hoặc thiết bị cũ còn giữ bản chụp lịch sử trong bộ nhớ thử ghi đè sau khi người dùng đã xóa lịch sử, PostgreSQL từ chối với lỗi `history erased; reload required` và buộc đồng bộ lại trạng thái trống.

Đã vượt qua **75 kiểm tra Python (`pytest`)**, **30 kiểm tra bảo mật PostgreSQL/RLS (`PGlite`)**, **9 kiểm tra tương tác frontend (`JSDOM`)** và **21 nhóm thao tác trình duyệt (`Playwright Chromium`)**. Bộ ảnh chụp thực tế và báo cáo `verification.json` nằm tại `reports/ui-preview/admin-privacy-2026-10-24/`.

## Đồng bộ màu với chatbot (v5.2)

Admin dùng cùng màu với giao diện chatbot: đỏ `#A5121B`, vàng `#D6A43B`,
nền kem `#FAF7F0`, đường viền `#eee3d3`. Thanh bên sáng, mục đang chọn
nền kem và chữ đỏ; thanh đầu trang dùng `#fffefa` như trang chatbot.
Nút, biểu đồ, biểu mẫu, trang tài khoản và các panel dùng bảng màu tương ứng.
Bố cục và các luồng quản trị v5.1 được giữ nguyên.

Đã chạy lại 18 nhóm thao tác trình duyệt và khởi động lại ứng dụng chính 8501.
Ảnh hiện tại trong `reports/ui-preview/admin-upgrade-2026-10-24/` dùng bảng màu
mới; ảnh AI v5 chỉ còn làm tham khảo bố cục với màu cũ.

## Nâng cấp chức năng 24/10/2026 (v5.1)

- Giữ giao diện v5, bổ sung lọc nhật ký theo thao tác, từ khóa không dấu và
  khoảng ngày theo giờ Việt Nam (UTC+7). Nút xóa bộ lọc khôi phục danh sách.
- Chi tiết sự kiện hiển thị mã đầy đủ, người thực hiện, đối tượng và các trường
  audit được cho phép: thao tác dữ liệu, vai trò, trạng thái, lý do thay đổi.
  Không dựng toàn bộ JSON tùy ý trong audit lên giao diện hay CSV.
- Xuất CSV áp dụng bộ lọc ở máy chủ và kiểm tra lại quyền admin. Khoảng ngày
  sai được từ chối; ngăn công thức bảng tính kể cả khi có khoảng trắng trước.
- Phản hồi có lọc trạng thái và quyền chia sẻ nội dung. Nếu phản hồi đang mở
  không khớp bộ lọc, vùng chi tiết hướng dẫn chọn lại, tránh hiển thị nhầm mục.
- Bộ lọc và trang hiện tại được giữ trong bộ nhớ component, tách theo tài khoản
  và trang. Không lưu biểu mẫu, mật khẩu hoặc token vào browser storage.
- Mỗi bảng chỉ áp dụng bộ lọc trong panel của mình. Lọc nhật ký không làm mất
  các hàng ở bảng tiến trình sao lưu.
- Không cần migration mới cho các bổ sung này; dùng schema audit/feedback hiện có.

Đã qua **59 kiểm tra Python** và **18 nhóm thao tác trình duyệt**, gồm màn hình
390px, lỗi ngày, chi tiết audit, CSV đã lọc, giữ bộ lọc và quyền chia sẻ phản hồi.
Ảnh và `verification.json`: `reports/ui-preview/admin-upgrade-2026-10-24/`.
Các thao tác ghi/email dùng fixture cô lập; không khẳng định đã kiểm tra SMTP
hoặc ghi dữ liệu trên Supabase thật. Ứng dụng chính đã được khởi động lại ở 8501.

## Thiết kế v5 theo ảnh mới

- Ảnh AI tham chiếu và prompt: `reports/ui-preview/admin-redesign-v5/GENERATION.md`.
- Sidebar burgundy tối `#2b151f` rộng 20vw (248–300px), điểm nhấn `#971b3b`, nền `#f6f7f9`,
  bộ chữ Segoe UI và biểu tượng Tabler MIT được lưu cục bộ.
- Bốn thẻ chỉ số theo ảnh tạo ra, bỏ chỉ số lượt tra cứu bị trùng. Biểu đồ có trục và giá trị từng cột,
  khối việc cần xử lý và bảng nhật ký bốn cột. Không điền số liệu mẫu vào
  môi trường thật. Mục thời gian ghi đúng trung vị do backend cung cấp.
- Cùng bộ kiểu áp dụng cho tài khoản, văn bản, phản hồi, vận hành, nhật ký,
  cài đặt và đổi/khôi phục mật khẩu; menu thu gọn trên điện thoại.
- Gallery có nút chuyển ảnh AI / ảnh chạy thật cùng kích thước để đối chiếu.
- CSS riêng của admin nằm trong `ui/frontend/admin.css`, nạp sau kiểu chung của tài khoản.
- Đã kiểm tra bằng 49 kiểm tra Python và 14 nhóm thao tác trình duyệt.
- Ảnh đối chiếu cùng kích thước 1505 × 1045; có cả trạng thái dữ liệu trống và có dữ liệu.
- Đã khởi động lại ứng dụng chính ở cổng 8501 để nạp component v5 và CSS mới.
  Endpoint `/_stcore/health` trả `ok`; trang chính dựng `.vl-app` không có lỗi Streamlit.
  Kiểm tra bố cục thêm ở 390, 768, 1024, 1280 và 1505px không phát hiện tràn trang
  hoặc chữ chỉ số đè lên biểu tượng.

## Những thay đổi chính

- Dùng chung bộ kiểu hiển thị cho sidebar, thanh đầu trang, chỉ số, bảng, biểu mẫu,
  hộp thoại và màn hình điện thoại. Giữ thương hiệu VietLaborAI đỏ burgundy.
- Hiển thị số 0 chính xác. Biểu đồ dùng cùng tên lớp CSS với mã dựng giao diện;
  dữ liệu trống có giải thích, không tự điền số liệu mẫu.
- Đưa sự kiện component vào hàng đợi trước khi tải dữ liệu trang. Mỗi lần dựng
  giao diện có mã xác nhận riêng để nút không bị kẹt khi dữ liệu không thay đổi.
- Thao tác có trạng thái chờ, thông báo kết quả và lỗi. Xác nhận nhạy cảm dùng
  hộp thoại trong trang thay cho `window.confirm` của trình duyệt nhúng.
- Giữ nội dung biểu mẫu khi máy chủ từ chối lưu. Mật khẩu không nằm trong dữ
  liệu khôi phục biểu mẫu.
- Chấp nhận nguồn HTTPS thuộc `gov.vn` và `chinhphu.vn`. Vẫn từ chối tên miền
  giả dạng, HTTP và URL chứa thông tin đăng nhập.
- Tìm kiếm tài khoản/văn bản/phản hồi không bắt buộc dấu tiếng Việt; bảng có
  phân trang và bộ lọc báo khi không tìm thấy kết quả. Chi tiết tài khoản hỗ trợ
  đóng bằng Escape.
- Tác vụ vận hành/sao lưu tự cập nhật khi đang xử lý, không tự làm mới lúc người
  dùng đang nhập biểu mẫu hoặc mở hộp thoại. Sau khởi động lại, tác vụ chờ và
  tác vụ có lease hết hạn được tiếp tục; nhiều admin có thể nhận việc trong hàng đợi.

## Các thao tác được nối với máy chủ

| Khu vực | Thao tác |
|---|---|
| Người dùng | Tìm kiếm/lọc, mở chi tiết, khóa/mở khóa tài khoản `user` (Admin nghiệp vụ); cấp/hạ quyền admin và quản lý tài khoản admin (chỉ Quản trị viên chính) |
| Lời mời admin | Auth Admin API khi có khóa máy chủ, danh sách lời mời còn hạn, hủy lời mời có ghi nhật ký (chỉ Quản trị viên chính) |
| Kho văn bản | Tải PDF, lưu metadata, xem trích xuất, duyệt và tạo tác vụ lập chỉ mục |
| Phản hồi | Tìm kiếm/phân trang, đổi trạng thái, lưu ghi chú qua `review_feedback_safe` (kiểm tra `privacy_version`), xuất đoạn được người dùng cho phép chia sẻ |
| Vận hành | Kiểm tra mô hình, xem tiến trình và chạy lại tác vụ lỗi |
| Nhật ký/sao lưu | Xuất CSV, tạo sao lưu nghiệp vụ, yêu cầu khôi phục metadata |
| Cài đặt | Lưu tên ứng dụng/khu quản trị (chỉ Quản trị viên chính), mở cấu hình email/SMTP Supabase |
| Tài khoản & Quyền riêng tư | Lưu hồ sơ, đổi mật khẩu, thu hồi phiên khác, đặt mật khẩu qua liên kết khôi phục, xuất JSON lịch sử, xóa toàn bộ lịch sử (`delete_my_conversations`), thu hồi chia sẻ phản hồi (`withdraw_my_feedback_consent`) và xóa phản hồi của mình (`delete_my_feedback`) |

## Cách kiểm tra

Các kiểm tra Python và PostgreSQL/JSDOM:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_privacy_boundaries.py tests/test_admin_audit_filters.py tests/test_accounts_admin.py tests/test_account_app.py tests/test_approved_layout.py -q
node scripts/test_supabase_rls.mjs
.\.venv\Scripts\python.exe scripts/render_account_fixtures.py
node scripts/test_account_frontend.mjs
```

Ứng dụng kiểm thử trình duyệt là `tests/fixtures/admin_portal_app.py`, chạy riêng
trên cổng 8510. Nó dùng bộ lưu trữ trong bộ nhớ, không kết nối Supabase, không
gửi email, không xuất bản chỉ mục và không thay đổi dữ liệu người dùng thật.
Kiểm tra đi qua JavaScript component, callback Streamlit, bộ điều khiển và
`AdminService` đang dùng trong ứng dụng chính.

```powershell
.\.venv\Scripts\python.exe -m streamlit run tests\fixtures\admin_portal_app.py --server.port 8510 --server.headless true
```

Chạy `scripts/check_admin_ui.cjs` bằng Node với gói Playwright trong `NODE_PATH`.
Gói runtime của Codex có sẵn Playwright; Chrome kiểm thử nằm trong bộ nhớ đệm
Playwright của tài khoản Windows. Có thể chỉ định `PLAYWRIGHT_CHROMIUM_EXECUTABLE`.

```powershell
node scripts/check_admin_ui.cjs
```

Ảnh được chụp tại 1440px, 1505px, 1874px và 390px. Bộ kiểm tra bao gồm 21 kịch bản:
luồng thành công, hủy xác nhận, lưu lỗi, khôi phục nội dung nhập, tải lại liên tiếp,
xuất file, giới hạn của Admin nghiệp vụ (`21-ordinary-admin-restrictions.png`),
trung tâm quyền riêng tư người dùng (`22-user-privacy.png`, `23-user-privacy-mobile.png`),
chặn ghi đè ghi chú phản hồi sau khi người dùng thu hồi chia sẻ và chặn thiết bị cũ
ghi lại lịch sử đã xóa. Kết quả/ảnh nằm trong `reports/ui-preview/admin-privacy-2026-10-24/`.

## Phạm vi xác nhận và giới hạn vận hành

75 kiểm tra Python, 30 kiểm tra RLS PostgreSQL (PGlite), 9 kiểm tra JSDOM và 21 kiểm tra
trình duyệt Playwright đã qua. Báo cáo `verification.json` ghi kết quả kiểm tra
trình duyệt độc lập. Các kiểm tra này không chứng minh việc gửi thư SMTP hoặc
ghi dữ liệu trên project Supabase thật nếu chưa chạy migration `003` trên cloud.

Các lưu ý bảo mật và vận hành cần nắm rõ:
- Ứng dụng chính dùng quyền tài khoản Supabase thật và RLS. Lời mời admin qua email
  cần `SUPABASE_SECRET_KEY` hoặc `SUPABASE_SERVICE_ROLE_KEY` ở phía máy chủ; khóa
  publishable không đủ để gọi Auth Admin API.
- Khi người dùng thu hồi chia sẻ hoặc xóa phản hồi, dữ liệu trong PostgreSQL bị xóa
  ngay lập tức, nhưng các tệp JSONL mà admin đã tải xuống máy cá nhân trước thời điểm
  thu hồi nằm ngoài phạm vi kiểm soát của cơ sở dữ liệu.
- Tính năng trong `account-privacy` hiện xóa toàn bộ lịch sử trò chuyện và thu hồi/xóa
  phản hồi của người dùng; việc xóa hoàn toàn tài khoản (`auth.users`) vẫn cần quy trình
  quản trị hoặc Auth Admin API riêng.
- Chủ sở hữu hạ tầng Supabase (người giữ mật khẩu Postgres `postgres` hoặc `service_role` key)
  có quyền truy cập cấp hạ tầng; hệ thống áp dụng phân quyền và RLS ở tầng ứng dụng/CSDL,
  không phải mã hóa đầu cuối (E2EE) phía trình duyệt.
