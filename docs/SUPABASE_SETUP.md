# Kết nối Supabase cho VietLaborAI

Mã nguồn đã có tài khoản email, lịch sử riêng, trung tâm quyền riêng tư, khu quản trị
và khôi phục mật khẩu. Ứng dụng không tạo project, tài khoản hoặc mật khẩu mặc định.
Khi chưa cấu hình, trang AI vẫn chạy ở chế độ khách; chức năng tài khoản thông báo cần kết nối.

## 1. Tạo project và chạy tuần tự các bản migration

1. Vào [Supabase Dashboard](https://supabase.com/dashboard), tạo project mới hoặc mở project hiện có (`kczjokppaxuzdhdanghr`).
2. Đặt mật khẩu cơ sở dữ liệu và lưu ở nơi riêng. Không dán mật khẩu đó vào chat.
3. Mở **SQL Editor** và chạy tuần tự 3 migration theo đúng thứ tự:
   - **Bước 1 (`001`)**: `supabase/migrations/202610220001_accounts_admin.sql` — Tạo bảng `profiles`, `conversations`, `feedback`, `legal_documents`, `admin_jobs`, `admin_audit`, `admin_invitations`, RLS, RPC cơ bản và bucket PDF riêng tư. *(Nếu project đã chạy migration 001 trước đó thì bỏ qua bước này).*
   - **Bước 2 (`002`)**: `supabase/migrations/202610220002_admin_workflows.sql` — Bật duyệt văn bản an toàn (`approve_legal_document`), cơ chế lease cho worker (`claim_admin_job`, `assert_admin_job_lease`, `touch_admin_job`, `finish_admin_job`) và hủy lời mời có ghi nhật ký (`cancel_admin_invitation`). *(Nếu project đã chạy migration 002 trước đó thì bỏ qua bước này).*
   - **Bước 3 (`003` — Bắt buộc cho bản v5.3)**: `supabase/migrations/202610240003_privacy_permissions.sql` — Bổ sung bảng `admin_capabilities` (tách quyền Quản trị viên chính `is_security_administrator()`), ẩn cột `owner_id` của bảng `feedback` khỏi admin, thêm các RPC quyền riêng tư của người dùng (`my_admin_permissions`, `my_feedback`, `withdraw_my_feedback_consent`, `delete_my_feedback`, `review_feedback_safe`, `my_history_version`, `delete_my_conversations`) và nâng cấp `save_my_conversations(changed, deleted, expected_history_version)` chống thiết bị cũ ghi đè lịch sử đã xóa.
4. **Trạng thái kiểm tra thực tế trên project `kczjokppaxuzdhdanghr` (ngày 25/10/2026)**:
   - Cả 3 bản migration `001`, `002` và `003` (`supabase/migrations/202610240003_privacy_permissions.sql`) **đều đã được cài đặt và xác minh hoạt động** trên project cloud.
5. Trong phần API của project, lấy **Project URL** và **publishable key** (hoặc anon key).

## 2. Cấu hình trên máy

Sao chép `.streamlit/secrets.toml.example` thành `.streamlit/secrets.toml`.
Điền giá trị thật:

```toml
[supabase]
SUPABASE_URL = "https://PROJECT_ID.supabase.co"
SUPABASE_PUBLISHABLE_KEY = "PUBLISHABLE_KEY"
SUPABASE_SERVICE_ROLE_KEY = ""
APP_PUBLIC_URL = "http://127.0.0.1:8501"
```

Khóa publishable/anon dùng cho các yêu cầu gắn với quyền của người dùng.
`SUPABASE_SERVICE_ROLE_KEY` là tùy chọn, chỉ cần khi **gửi email mời admin**.
Lấy khóa này từ Supabase và chỉ đặt ở tệp máy chủ trên; không đưa vào HTML/JS,
ảnh chụp, Git hoặc tin nhắn. Chức năng còn lại không sử dụng khóa này để truy cập dữ liệu.
Tệp secrets đã được thêm vào `.gitignore`. Có thể dùng biến môi trường cùng tên thay thế.

Khởi động lại ứng dụng:

```powershell
.venv\Scripts\python.exe -m streamlit run ui/streamlit_app.py
```

## 3. Xác minh email, SMTP và liên kết khôi phục

Trong **Authentication**, bật phương thức Email và yêu cầu xác minh email.
Đặt Site URL là `http://127.0.0.1:8501` khi chạy trên máy.
Khai báo địa chỉ này trong danh sách redirect URL được cho phép.
Khi triển khai lên mạng, thay bằng tên miền HTTPS thực tế trong cả Supabase lẫn
`APP_PUBLIC_URL`. Liên kết localhost chỉ mở đúng trên máy chạy ứng dụng.

Cấu hình SMTP riêng tại phần SMTP của Authentication và thử gửi email.
Dịch vụ gửi mail mặc định bị giới hạn, không nên dùng cho người dùng thật.
Các tên mục trong Dashboard có thể thay đổi theo phiên bản giao diện.

Ứng dụng Streamlit dùng liên kết `token_hash` được xác minh ở máy chủ.
Trong **Email Templates**, dùng các liên kết sau (chỉnh nội dung email tiếng Việt tùy ý):

Các luồng trong ứng dụng truyền URL chuyển hướng đã cấu hình, nên dùng
`{{ .RedirectTo }}` để email mở lại đúng ứng dụng.

**Confirm signup**:

```html
<a href="{{ .RedirectTo }}/?token_hash={{ .TokenHash }}&amp;type=email">Xác minh email</a>
```

**Reset password**:

```html
<a href="{{ .RedirectTo }}/?token_hash={{ .TokenHash }}&amp;type=recovery">Đặt mật khẩu mới</a>
```

**Invite user**:

```html
<a href="{{ .RedirectTo }}/?token_hash={{ .TokenHash }}&amp;type=invite">Chấp nhận lời mời và đặt mật khẩu</a>
```

Giữ liên kết có thời hạn ngắn; không chuyển tiếp email xác thực. Ứng dụng xóa
tham số xác thực khỏi URL, sau đó chỉ kiểm tra token với Supabase khi người dùng
bấm nút xác nhận trên trang VietLaborAI. Cách này tránh để trình quét bảo mật
email dùng mất liên kết một lần khi tự động mở trước. Token không được gửi sang
component giao diện. Sau khi đổi mẫu email, yêu cầu một liên kết mới; thư cũ vẫn
có định dạng trước đó.

## 4. Cấp tài khoản Quản trị viên chính đầu tiên

1. Mở ứng dụng, đăng ký bằng email `maitamit062005@gmail.com` và tên hiển thị
   **Mai Trần Thiện Tâm**.
2. Xác minh email qua liên kết nhận được.
3. Mở tệp `storage/setup/admin-first.sql` (hoặc chạy trực tiếp migration `202610240003_privacy_permissions.sql` nếu tài khoản đã tồn tại), sao chép toàn bộ
   nội dung vào Supabase **SQL Editor**, rồi chạy một lần:
   - Đặt `profiles.role = 'admin'`, `status = 'active'`, `email_verified = true`.
   - Cấp quyền Quản trị viên chính `admin_capabilities(admin_id, manage_administrators) = (target_user, true)` cho `maitamit062005@gmail.com`.
   - Ghi nhận vào nhật ký quản trị `admin_audit`.
4. Đăng nhập lại: tài khoản sẽ vào **Tổng quan quản trị** với đầy đủ quyền Quản trị viên chính.
5. Tài khoản khác đăng ký thông thường luôn nhận vai trò `user`.
6. Các tài khoản được nâng lên `admin` thông qua giao diện quản trị là **Admin nghiệp vụ** (quản lý văn bản, phản hồi, khóa/mở khóa `user`), không tự động có quyền Quản trị viên chính (`manage_administrators = false`).

## 5. Các màn hình đã triển khai

| Demo | Màn hình / hành vi |
|---|---|
| 01 | Tổng quan: tài khoản, lượt hỏi, phản hồi, độ trễ và biểu đồ từ dữ liệu thật |
| 02 | Người dùng: tìm tên/email, lọc vai trò/trạng thái, mời admin (chỉ Quản trị viên chính) |
| 03 | Chi tiết: khóa/mở khóa `user`, cấp/hạ quyền admin (chỉ Quản trị viên chính); không mở lịch sử chat |
| 04 | Kho văn bản: PDF riêng tư, metadata, nguồn chính thức, trạng thái duyệt |
| 05 | Phản hồi: ẩn `owner_id`, chỉ đọc nội dung được chia sẻ; kiểm tra `privacy_version` khi lưu ghi chú |
| 06 | Vận hành: kiểm tra Ollama, số đo độ trễ, tiến trình lập chỉ mục và chạy lại khi lỗi |
| 07 | Nhật ký/sao lưu: lọc sự kiện, xuất CSV an toàn công thức, sao lưu/khôi phục cấu hình và metadata |
| 08 | Cài đặt: tên khu quản trị (chỉ Quản trị viên chính), bảng phân quyền; Auth/SMTP cấu hình tại Supabase |
| 09 | Hồ sơ/bảo mật: đổi tên, thông tin email, thu hồi phiên đăng nhập khác |
| 10 | Đổi mật khẩu: xác minh mật khẩu hiện tại trước khi đổi |
| 11 | Quên mật khẩu: email khôi phục; thông báo không tiết lộ email có tài khoản hay không |
| 12 | Đặt mật khẩu mới: xác minh liên kết một lần, đổi mật khẩu và trở lại đăng nhập |
| 13 | Quản lý dữ liệu của tôi (`account-privacy`): xuất JSON lịch sử, xóa toàn bộ lịch sử (`history_versions`), xem phản hồi đã gửi, thu hồi chia sẻ câu hỏi/câu trả lời hoặc xóa phản hồi |

## 6. Văn bản, tiến trình và sao lưu

- Chỉ nhận PDF có lớp văn bản đọc được, tối đa 10 MB/500 trang. Tệp scan cần OCR
  và kiểm tra trước. Nguồn phải là HTTPS thuộc tên miền `gov.vn` hoặc `chinhphu.vn`.
- Admin lưu bản nháp, xác minh hiệu lực/ngày hiệu lực rồi xác nhận duyệt.
  Thay đổi metadata làm mất trạng thái duyệt trước đó.
- Lập chỉ mục chạy nền trên máy chủ Streamlit: tạo bản corpus và chỉ mục BM25/Chroma
  mới trong `storage/admin_indexes/`, giữ nguyên corpus nền tảng. Chỉ kích hoạt khi
  cả hai chỉ mục hoàn tất. Neo4j tiếp tục dùng đồ thị hiện có; tính năng này không tự
  tạo quan hệ pháp lý cho tài liệu mới.
- Worker chạy trong tiến trình máy chủ, còn trạng thái và lease được lưu ở Supabase.
  Sau khi máy chủ khởi động lại và một admin mở **Vận hành AI** hoặc **Nhật ký**, các
  tác vụ chờ sẽ được tiếp tục; tác vụ đang chạy chỉ được nhận lại khi lease cũ đã quá
  hạn. Với nhiều tiến trình ứng dụng, Supabase chỉ cho một worker giữ lease tại một thời điểm.
- Sao lưu nghiệp vụ chỉ gồm cấu hình và metadata văn bản, **không chứa tài khoản,
  mật khẩu hoặc lịch sử chat**. PDF nằm riêng ở Supabase Storage; cần phương án sao
  lưu Storage và PostgreSQL riêng khi triển khai thực tế.
- Khôi phục metadata không thay đổi tài khoản/lịch sử, đưa văn bản về chờ duyệt,
  không tự thay chỉ mục đang phục vụ. Chỉ mục đã kích hoạt có thể vẫn chứa bản văn bản
  trước đó cho đến khi bạn duyệt và xuất bản phiên bản tiếp theo.

## 7. Quyền riêng tư, phiên đăng nhập và danh mục bảo mật bổ sung

- **Lịch sử trò chuyện (`conversations`)**: chỉ cho chủ tài khoản đọc/sửa/xóa. Không có ngoại lệ cho bất kỳ admin hay Quản trị viên chính nào.
- **Chống phục hồi lịch sử từ thiết bị cũ (`history_versions`)**: khi người dùng xóa toàn bộ lịch sử, phiên bản lịch sử tăng lên; mọi yêu cầu lưu từ tab/thiết bị cũ mang `expected_history_version` thấp hơn đều bị từ chối ở PostgreSQL.
- **Ẩn danh hóa và thu hồi phản hồi (`feedback`)**: admin không có quyền đọc cột `owner_id`. Khi người dùng thu hồi sự đồng ý chia sẻ, câu hỏi/câu trả lời và ghi chú nội bộ bị xóa ngay và tăng `privacy_version`, đồng thời không ghi nhận ID người dùng vào nhật ký quản trị.
- **Giới hạn hạ tầng và danh mục bảo mật vận hành**:
  - Chủ project Supabase (người giữ quyền chủ sở hữu cơ sở dữ liệu hoặc `service_role` key) có quyền quản trị hạ tầng; hệ thống thực thi phân quyền ở tầng ứng dụng/RLS, không phải mã hóa đầu cuối (E2EE).
  - Các bản xuất JSONL phản hồi đã được tải về máy tính cá nhân của admin trước thời điểm người dùng bấm thu hồi chia sẻ nằm ngoài cơ sở dữ liệu nên cần quản lý theo quy trình nội bộ.
  - Thu hồi phiên ngăn làm mới token (`refresh_token`); access token JWT đã cấp có thể còn hiệu lực ngắn hạn cho tới khi hết hạn, nhưng tài khoản bị khóa (`status = 'locked'`) sẽ bị chặn ngay lập tức bởi RLS trên mọi bảng dữ liệu.
  - Khuyến nghị bật thêm MFA (xác thực đa yếu tố) cho tài khoản Quản trị viên chính, cấu hình giới hạn tần suất (Rate Limiting) cho Auth/SMTP trên Supabase Dashboard và rà soát định kỳ nhật ký kiểm toán.

## 8. Kiểm tra sau cấu hình

1. Chạy `supabase/migrations/202610240003_privacy_permissions.sql` trên Supabase SQL Editor.
2. Đăng ký hoặc đăng nhập tài khoản `maitamit062005@gmail.com`, chạy `storage/setup/admin-first.sql` nếu cần và kiểm tra cột `is_primary_admin = true`.
3. Đăng nhập một tài khoản người dùng thường, tạo lịch sử chat và phản hồi có chia sẻ nội dung; sau đó mở **Quản lý dữ liệu của tôi** để kiểm tra thu hồi chia sẻ, xóa phản hồi và xóa toàn bộ lịch sử.
4. Kiểm tra một tài khoản Admin nghiệp vụ: xác nhận quản lý được văn bản/phản hồi và khóa được tài khoản `user`, nhưng không thể thăng cấp admin hoặc sửa tài khoản admin khác.

Tài liệu chính thức:
[Password Auth](https://supabase.com/docs/guides/auth/passwords),
[Email templates](https://supabase.com/docs/guides/auth/auth-email-templates),
[Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security).

## 9. Chạy kiểm thử mã nguồn

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_privacy_boundaries.py tests/test_admin_audit_filters.py tests/test_accounts_admin.py tests/test_account_app.py tests/test_approved_layout.py tests/unit/test_session_manager.py -q
npm install --prefix storage/test_tools @electric-sql/pglite jsdom --no-audit --no-fund
node scripts/test_supabase_rls.mjs
.\.venv\Scripts\python.exe scripts/render_account_fixtures.py
node scripts/test_account_frontend.mjs
node scripts/check_admin_ui.cjs
```

PostgreSQL kiểm thử chạy tạm trong bộ nhớ bằng PGlite, không kết nối project thật.
Kiểm thử Auth sử dụng phản hồi HTTP giả lập; email/SMTP, đường dẫn xác thực và việc
lập chỉ mục đầy đủ cần kiểm thử tích hợp sau khi cấu hình Supabase và dịch vụ trên máy.
