# VietLaborAI — bản thiết kế quản trị v4

Ảnh gốc: `00-generated-reference.png`.

Tạo bằng công cụ tích hợp `image_gen.imagegen`, chế độ tạo ảnh mới, nền đục.
Ảnh được chép vào dự án từ thư mục generated_images của Codex. Đây là ảnh
định hướng thiết kế, không phải ảnh chụp phần mềm đang chạy.

Các ảnh còn lại trong thư mục được chụp bằng Playwright từ component thật
trong ứng dụng Streamlit kiểm thử. Số liệu và tài khoản trong ảnh chụp là
dữ liệu kiểm thử; ứng dụng chính tiếp tục dùng dữ liệu Supabase được cấp quyền.

## Prompt đã dùng

Create one pixel-crisp high-fidelity desktop admin dashboard UI mockup for Vietnamese legal AI app VietLaborAI. This image will be coded faithfully. Single complete landscape screenshot, 1600x1000 layout, straight on, no laptop frame, no collage.
A genuinely NEW premium modern light productivity-app design: WHITE sidebar 236px, warm offwhite main canvas #F7F8FA, charcoal text #17212F, deep burgundy #981B35 primary, gold #C7A36B brand accent. Spacious but purposeful, excellent contrast, 14-15px body text, 34px titles, 38px metric numbers. Segoe UI style sans typography, 12px radii, fine neutral borders. No dark sidebar, no washed-out pink text, no purple gradients.
Sidebar top: gold scales icon in small burgundy square, wordmark VietLaborAI, small 'KHÔNG GIAN QUẢN TRỊ'. Menu: 'Tổng quan' active pale burgundy, 'Người dùng', 'Kho văn bản', 'Phản hồi', 'Vận hành AI', 'Nhật ký & sao lưu', 'Cài đặt & bảo mật'. Bottom: compact privacy note 'Lịch sử luôn riêng tư', 'Chỉ xem nội dung được chia sẻ'; link 'Trở về trợ lý AI'; TT avatar, 'Thiện Tâm', 'Quản trị viên', logout icon.
Main topbar height72px: breadcrumb 'Quản trị / Tổng quan', right outlined 'Bảo mật tài khoản' and circular TT avatar. Main content padding36px. Heading 'Tổng quan', subtitle 'Theo dõi hoạt động và chất lượng trợ lý của bạn.', right burgundy '+ Quản lý người dùng' button and bordered refresh icon button.
Four metric tiles in one row. FIRST tile burgundy filled with white type and subtle tonal corner arc; remaining tiles white: 'Người dùng' value2, 'Lượt tra cứu' value27, 'Phản hồi chờ xử lý' value2, 'Thời gian trả lời' value '15,3 s'. Each has a coherent outlined icon top right and small clear caption.
Next row: left white chart card65% width titled 'Hoạt động tra cứu', subtitle 'Lượt sử dụng trong 7 ngày gần đây'. Actual burgundy vertical BAR chart, 7 rounded bars values2,5,3,0,6,7,4, faint horizontal grid, date labels16/10 through22/10. Right white card35% titled 'Cần bạn xử lý' with 3 spacious task rows: '2 phản hồi chờ xử lý', '1 văn bản chờ duyệt', 'Vận hành hệ thống'. Each has icon, explanatory subtitle and right chevron. Compact burgundy 'Xem tất cả hoạt động' link below.
Bottom full-width white card 'Hoạt động gần đây', right outlined 'Xem nhật ký'. Clear 4-column table 'Thời gian', 'Hoạt động', 'Đối tượng', 'Trạng thái'. Three rows of plausible Vietnamese admin operations with small green/amber status badges. Small muted privacy footer. Professional production software, beautiful hierarchy, impeccable aligned spacing, readable accurate Vietnamese diacritics. No decorative photos or illustrations, no mascot, no giant empty holes. Make this noticeably more refined and lighter than a basic dark-sidebar Bootstrap admin.

## Chuyển thành mã nguồn

Ảnh tạo ra có năm thẻ chỉ số; bản triển khai theo năm thẻ thực tế trong ảnh.
Không sao chép dữ liệu cá nhân, ngày tháng và trạng thái giả trong ảnh vào
ứng dụng chính. Thời gian trả lời được ghi rõ là trung vị theo API hiện có.
Đối tượng nhật ký dùng mã rút gọn, không suy diễn email hay nội dung chat.
Biểu tượng SVG dùng bộ Tabler chính thức, giấy phép MIT trong
`ui/static/icons/LICENSE`.
