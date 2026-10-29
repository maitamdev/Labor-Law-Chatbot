"""Build review-only screens. This never calls Supabase or the live app backend."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from ui.components.approved_layout import layout_markup, auth_dialog_markup, icon, sprite

OUT = Path(__file__).parent


def button(label, route='', kind='secondary', glyph='', action=''):
    target = f'data-route="{route}"' if route else f'data-action="{action or label}"'
    return f'<button class="btn {kind}" {target}>{icon(glyph) if glyph else ""}{label}</button>'


def badge(text, tone='neutral'):
    return f'<span class="badge {tone}">{text}</span>'


def brand():
    return f'<div class="demo-brand">{sprite(56,8,86,61,"brand-symbol","VietLaborAI")}<span>VietLabor<span>AI</span><small>Trợ lý pháp luật lao động</small></span></div>'


def input_field(label, placeholder='', value='', kind='text', extra=''):
    return f'<label class="field"><span>{label}</span><input type="{kind}" placeholder="{placeholder}" value="{value}" {extra}></label>'


def table(headers, rows, cls=''):
    return f'<div class="table-scroll"><table class="data-table {cls}"><thead><tr>{"".join(f"<th>{h}</th>" for h in headers)}</tr></thead><tbody>{"".join("<tr>"+"".join(f"<td>{c}</td>" for c in row)+"</tr>" for row in rows)}</tbody></table></div>'


def panel(title, subtitle, content, actions='', cls=''):
    return f'<section class="panel {cls}"><div class="panel-head"><div><h2>{title}</h2><p>{subtitle}</p></div>{actions}</div>{content}</section>'


NAV = [
    ('admin-dashboard', 'Tổng quan', 'home-filled'),
    ('admin-users', 'Người dùng', 'user'),
    ('admin-documents', 'Kho văn bản', 'books'),
    ('admin-feedback', 'Phản hồi', 'thumb-down'),
    ('admin-operations', 'Vận hành AI', 'refresh'),
    ('admin-audit', 'Nhật ký & sao lưu', 'history'),
    ('admin-settings', 'Cài đặt & phân quyền', 'hierarchy'),
]


def admin_shell(active, title, description, content, actions=''):
    nav = ''.join(f'<button class="admin-nav {"active" if key == active else ""}" data-route="{key}">{icon(glyph)}<span>{label}</span>{badge("18", "count") if key == "admin-feedback" else ""}</button>' for key, label, glyph in NAV)
    return f'''<div class="admin-app">
      <aside class="admin-sidebar">{brand()}<div class="workspace-label">Không gian quản trị</div><nav>{nav}</nav>
      <div class="sidebar-bottom"><button class="back-ai" data-route="home">{icon('message-circle')}Trở về trợ lý AI{icon('external-link')}</button><div class="admin-identity"><span class="avatar">TT</span><div><strong>Thiện Tâm</strong><small>Quản trị viên</small></div><button data-action="Đăng xuất bản mẫu" aria-label="Đăng xuất">{icon('chevron-right')}</button></div></div></aside>
      <div class="admin-main"><header class="admin-topbar"><button class="menu-toggle" data-menu aria-label="Mở menu">{icon('menu')}</button><div class="breadcrumb">Quản trị <span>/</span> {title}</div><div class="topbar-end">{badge('Dữ liệu minh họa','demo')}<a href="gallery.html" class="gallery-link">Bộ ảnh duyệt</a><span class="avatar small">TT</span></div></header>
      <main class="admin-content"><div class="page-heading"><div><h1>{title}</h1><p>{description}</p></div><div class="page-actions">{actions}</div></div>{content}<div class="prototype-foot">Bản mẫu giao diện để duyệt. Chưa kết nối Supabase và chưa áp dụng thao tác vào dữ liệu thật.</div></main></div>
      <div class="demo-toast" role="status" hidden></div><dialog class="demo-action-dialog"><button class="close-action" data-close aria-label="Đóng">{icon('x')}</button><div class="action-content"></div></dialog>
    </div>'''


def metric(label, value, note, glyph, cls=''):
    return f'<article class="metric {cls}"><div class="metric-label">{label}<span>{icon(glyph)}</span></div><strong>{value}</strong><small>{note}</small></article>'


def dashboard():
    metrics = metric('Người dùng', '128', 'Tài khoản đang hoạt động', 'user') + metric('Lượt tra cứu', '1.284', 'Trong 7 ngày gần đây', 'message-circle') + metric('Cần xem xét', '18', 'Phản hồi đang chờ xử lý', 'thumb-down', 'attention') + metric('Thời gian trả lời', '12,6 s', 'Trung vị của lượt hỏi mẫu', 'refresh')
    bars = ''.join(f'<div class="chart-column"><span>{v}</span><div class="chart-bar" style="height:{v/2}px"></div><small>{d}</small></div>' for d, v in zip(['T2','T3','T4','T5','T6','T7','CN'], [118, 172, 146, 234, 208, 186, 220]))
    chart = panel('Hoạt động tra cứu', 'Số câu hỏi theo ngày · dữ liệu minh họa', f'<div class="bar-chart">{bars}</div><div class="chart-caption"><i></i>Lượt hỏi của người dùng và khách</div>', '<select aria-label="Khoảng thời gian"><option>7 ngày gần đây</option><option>30 ngày gần đây</option></select>')
    tasks = ''.join(f'<button class="task-row" data-route="{route}"><span class="task-icon">{icon(glyph)}</span><span><strong>{title}</strong><small>{detail}</small></span>{icon("chevron-right")}</button>' for title, detail, glyph, route in [('9 phản hồi thiếu căn cứ','Ưu tiên kiểm tra câu trả lời và nguồn','thumb-down','admin-feedback'),('2 văn bản chờ duyệt','Kiểm tra trước khi cập nhật kho tri thức','file-text','admin-documents'),('1 tiến trình cần chạy lại','Xem lỗi xử lý và phiên bản chỉ mục','refresh','admin-operations')])
    activity_rows = [['10:42', 'Tài liệu mới được đưa vào hàng chờ', 'Kho văn bản', badge('Chờ duyệt','warning')], ['10:30', 'Đã xử lý một phản hồi về trích dẫn', 'Chất lượng', badge('Hoàn tất','success')], ['09:58', 'Tài khoản người dùng được mở khóa', 'Người dùng', badge('Đã cập nhật')]]
    content = f'<div class="metrics-grid">{metrics}</div><div class="dashboard-middle">{chart}{panel("Cần bạn xử lý", "Những việc nên ưu tiên hôm nay", tasks)}</div>' + panel('Hoạt động gần đây', 'Theo dõi các thay đổi trong hệ thống', table(['Thời gian','Hoạt động','Phạm vi','Trạng thái'], activity_rows), button('Xem nhật ký','admin-audit'))
    return admin_shell('admin-dashboard','Tổng quan','Chào Thiện Tâm, đây là tình hình của VietLaborAI hôm nay.',content,button('Xem phản hồi','admin-feedback','primary'))


USERS = [
    ('TT','Mai Trần Thiện Tâm','tam@example.com','Quản trị viên','Hoạt động','Hôm nay, 10:42','18'),
    ('MA','Trần Minh Anh','minhanh@example.com','Người dùng','Hoạt động','Hôm nay, 10:15','7'),
    ('NL','Nguyễn Thảo Linh','thaolinh@example.com','Người dùng','Hoạt động','Hôm qua, 19:08','12'),
    ('QH','Lê Quốc Huy','quochuy@example.com','Người dùng','Tạm khóa','20/10, 14:25','4'),
    ('HN','Phạm Hoài Nam','hoainam@example.com','Người dùng','Chờ xác minh','21/10, 09:10','0'),
]


def users(detail=False):
    rows=[]
    for initials,name,email,role,status,last,count in USERS:
        person=f'<div class="person"><span class="avatar {"rose" if initials=="TT" else "pale"}">{initials}</span><div><strong>{name}</strong><small>{email}</small></div></div>'
        rows.append([person,badge(role,'role' if role=='Quản trị viên' else 'neutral'),badge(status,{'Hoạt động':'success','Tạm khóa':'danger','Chờ xác minh':'warning'}[status]),last,count,button('Chi tiết','admin-user-detail','table-action')])
    toolbar='<div class="table-toolbar"><label class="search-box">'+icon('search')+'<input data-filter placeholder="Tìm theo tên hoặc email" aria-label="Tìm người dùng"></label><select aria-label="Lọc vai trò"><option>Tất cả vai trò</option><option>Quản trị viên</option><option>Người dùng</option></select><select aria-label="Lọc trạng thái"><option>Tất cả trạng thái</option><option>Hoạt động</option><option>Tạm khóa</option></select></div>'
    content='<div class="tab-row"><button class="selected">Tất cả <b>128</b></button><button data-action="Lọc tài khoản hoạt động">Hoạt động <b>121</b></button><button data-action="Lọc tài khoản bị khóa">Tạm khóa <b>3</b></button><button data-action="Lọc tài khoản chờ xác minh">Chờ xác minh <b>4</b></button></div>'
    content+=panel('Danh sách tài khoản','Quản lý quyền truy cập, trạng thái và hỗ trợ tài khoản.',toolbar+table(['Người dùng','Vai trò','Trạng thái','Hoạt động gần nhất','Cuộc chat',''],rows)+'<div class="pagination"><span>Hiển thị 1–5 trong 128 tài khoản</span><div><button data-action="Trang trước">‹</button><button class="current">1</button><button data-action="Trang 2">2</button><button data-action="Trang tiếp">›</button></div></div>')
    result=admin_shell('admin-users','Người dùng','Mỗi tài khoản có lịch sử và quyền truy cập riêng.',content,button('Mời quản trị viên',action='invite-admin',kind='primary',glyph='plus'))
    if detail:
        drawer=f'''<div class="drawer-scrim"></div><aside class="detail-drawer"><div class="drawer-heading"><div><small>Chi tiết tài khoản</small><h2>Trần Minh Anh</h2></div><button data-route="admin-users" aria-label="Đóng chi tiết">{icon('x')}</button></div><div class="person-profile"><span class="avatar large pale">MA</span><strong>Trần Minh Anh</strong><span>minhanh@example.com</span>{badge('Email đã xác minh','success')}</div><dl class="definition-list"><div><dt>Ngày tham gia</dt><dd>12/10/2026</dd></div><div><dt>Cuộc trò chuyện</dt><dd>7 cuộc</dd></div><div><dt>Đăng nhập gần nhất</dt><dd>Hôm nay, 10:15</dd></div></dl><section class="drawer-section"><h3>Quyền truy cập</h3><label class="field"><span>Vai trò</span><select><option>Người dùng</option><option>Quản trị viên</option></select></label><p>Thay đổi vai trò chỉ được thực hiện bởi quản trị viên có thẩm quyền.</p>{button('Lưu thay đổi',action='Lưu quyền tài khoản',kind='primary')}</section><section class="drawer-section"><h3>Hỗ trợ tài khoản</h3>{button('Gửi liên kết đặt lại mật khẩu',action='reset-user')}{button('Tạm khóa tài khoản',action='lock-user',kind='danger-ghost')}<p class="privacy-note">Lịch sử chat cá nhân không hiển thị tại khu vực quản trị tài khoản.</p></section></aside>'''
        result+=drawer
    return result


def documents(add=False):
    if add:
        fields=input_field('Tên văn bản','', 'Bộ luật Lao động 2019')+input_field('Số hiệu văn bản','', '45/2019/QH14')+input_field('Cơ quan ban hành','', 'Quốc hội')+input_field('Ngày có hiệu lực','Chọn ngày',kind='date')
        form=f'<div class="steps"><span class="done">1. Tệp văn bản</span><span class="active">2. Kiểm tra thông tin</span><span>3. Duyệt & lập chỉ mục</span></div><div class="document-form-grid">'+panel('Thông tin văn bản','Xác minh nguồn và metadata trước khi đưa vào kho.',f'<div class="sample-upload">{icon("file-text")}<div><strong>bo_luat_lao_dong_2019.pdf</strong><small>Tệp minh họa · PDF · 2,4 MB</small></div>{badge("Đã đọc tệp","success")}</div><div class="form-grid">{fields}<label class="field full"><span>Đường dẫn nguồn chính thức</span><input value="https://congbao.chinhphu.vn/…" readonly></label><label class="field full"><span>Ghi chú rà soát</span><textarea placeholder="Ghi chú về phạm vi áp dụng hoặc văn bản liên quan"></textarea></label></div>')+panel('Kiểm tra trước khi duyệt','Tài liệu chưa được đưa vào chỉ mục đang sử dụng.','<div class="check-row">'+badge('Đã kiểm tra','success')+'Định dạng và khả năng đọc văn bản</div><div class="check-row">'+badge('Đã kiểm tra','success')+'Số hiệu và nguồn văn bản</div><div class="check-row">'+badge('Cần xác nhận','warning')+'Hiệu lực và văn bản thay thế</div><div class="extracted-preview"><h3>Xem trước cấu trúc trích xuất</h3><p>Chương I. Những quy định chung</p><p>Chương II. Việc làm, tuyển dụng và quản lý lao động</p><p>Chương III. Hợp đồng lao động</p><small>Đây là bố cục xem trước. Nội dung và nguồn cần được người quản trị duyệt.</small></div><label class="check-label"><input type="checkbox">Tôi đã kiểm tra thông tin và nguồn văn bản.</label>')+'</div><div class="form-bottom">'+button('Hủy','admin-documents')+button('Lưu bản nháp',action='Lưu bản nháp')+button('Duyệt & đưa vào hàng chờ',kind='primary',action='Duyệt tài liệu mẫu')+'</div>'
        return admin_shell('admin-documents','Thêm văn bản','Tải lên, kiểm tra và phê duyệt trước khi cập nhật kho tri thức.',form,button('Về kho văn bản','admin-documents'))
    records=[('Bộ luật Lao động 2019','45/2019/QH14','Văn bản nền tảng','Đã duyệt','22/10/2026'),('Nghị định 145/2020/NĐ-CP','145/2020/NĐ-CP','Văn bản hướng dẫn','Đã duyệt','21/10/2026'),('Luật Bảo hiểm xã hội','Tệp cập nhật mẫu','Bảo hiểm xã hội','Chờ duyệt','22/10/2026'),('Văn bản bổ sung về lao động','Tệp mẫu 04','Bổ sung dữ liệu','Bản nháp','20/10/2026')]
    rows=[]
    for title,num,group,status,date in records:
        rows.append([f'<div class="document-name">{icon("file-description")}<div><strong>{title}</strong><small>{num}</small></div></div>',group,badge(status,{'Đã duyệt':'success','Chờ duyệt':'warning','Bản nháp':'neutral'}[status]),date,button('Kiểm tra','admin-document-add','table-action')])
    summary='<div class="compact-stats"><span><b>36</b> Văn bản trong kho</span><span><b>2</b> Đang chờ duyệt</span><span><b>v3</b> Chỉ mục đang sử dụng</span></div>'
    toolbar='<div class="table-toolbar"><label class="search-box">'+icon('search')+'<input data-filter placeholder="Tìm tên hoặc số hiệu văn bản"></label><select><option>Tất cả loại văn bản</option><option>Bộ luật / Luật</option><option>Nghị định</option></select><select><option>Tất cả trạng thái</option><option>Chờ duyệt</option></select></div>'
    return admin_shell('admin-documents','Kho văn bản','Quản lý nguồn tri thức và kiểm soát các lần cập nhật dữ liệu.',summary+panel('Danh mục văn bản','Trạng thái duyệt là dữ liệu minh họa, không xác nhận hiệu lực pháp lý.',toolbar+table(['Văn bản','Nhóm nội dung','Xử lý dữ liệu','Cập nhật',''],rows)),button('Thêm văn bản','admin-document-add','primary','plus'))


def feedback():
    items=''.join(f'<button class="feedback-item {"selected" if i==0 else ""}" data-action="Chọn phản hồi mẫu"><div><span>#{code}</span>{badge(tag,"warning" if i==0 else "neutral")}</div><strong>{q}</strong><small>{time}</small></button>' for i,(code,tag,q,time) in enumerate([('FB-018','Cần kiểm tra','Câu trả lời về thời gian thử việc thiếu căn cứ','Hôm nay · 10:26'),('FB-017','Chờ xử lý','Chưa tìm thấy nguồn khi hỏi về hợp đồng','Hôm nay · 09:40'),('FB-016','Chờ xử lý','Câu trả lời còn quá dài và khó theo dõi','Hôm qua · 16:18'),('FB-015','Đã xử lý','Đề nghị bổ sung liên kết văn bản gốc','Hôm qua · 14:05')]))
    detail=f'''<div class="feedback-detail-head"><div><h2>Kiểm tra phản hồi #FB-018</h2><p>Người dùng đã gửi kèm đoạn trao đổi để quản trị viên xem xét.</p></div>{badge('Đang xem xét','warning')}</div><div class="reported-question"><small>Câu hỏi được báo cáo</small><p>Tôi muốn tra cứu thời gian thử việc theo quy định hiện hành.</p></div><div class="reported-answer"><small>Câu trả lời minh họa</small><p>Để xác định quy định áp dụng, cần biết nhóm công việc và trình độ chuyên môn yêu cầu.</p><p>Câu trả lời cần bổ sung căn cứ trích dẫn rõ ràng để người dùng tự đối chiếu.</p><div class="source-warning">{icon('file-text')}Điểm cần rà soát: nguồn trích dẫn và mức độ đầy đủ của câu trả lời.</div></div><div class="user-comment"><strong>Góp ý của người dùng</strong><p>“Tôi muốn có điều khoản và đường dẫn văn bản để kiểm tra lại.”</p></div><label class="field"><span>Ghi chú xử lý</span><textarea placeholder="Ghi lại nguyên nhân, tài liệu cần bổ sung hoặc hướng cải thiện"></textarea></label><div class="feedback-actions">{button('Tạo ca đánh giá',action='Tạo ca đánh giá từ phản hồi')}{button('Đánh dấu đã xử lý',kind='primary',action='Đã đánh dấu phản hồi xử lý')}</div>'''
    content='<div class="notice subtle">'+icon('info-circle')+'Chỉ hiển thị nội dung người dùng gửi kèm phản hồi. Không mở toàn bộ lịch sử chat cá nhân.</div><div class="feedback-workspace"><section class="feedback-list"><div class="feedback-list-title"><h2>Phản hồi cần xem</h2>'+badge('18','count')+'</div>'+items+'</section><section class="panel feedback-detail">'+detail+'</section></div>'
    return admin_shell('admin-feedback','Phản hồi','Rà soát chất lượng câu trả lời và theo dõi việc khắc phục.',content,'<select><option>Chờ xử lý</option><option>Đã xử lý</option><option>Tất cả</option></select>')


def operations():
    health='<div class="health-grid">'+panel('Mô hình AI','Ollama · mô hình cục bộ',f'<div class="health-main">{badge("Sẵn sàng","success")}<strong>qwen2.5:7b</strong></div><dl class="definition-list"><div><dt>Ngữ cảnh</dt><dd>4.096 tokens</dd></div><div><dt>Giới hạn sinh</dt><dd>800 tokens</dd></div></dl>')+panel('Kho truy hồi','Phiên bản đang phục vụ',f'<div class="health-main">{badge("Đang sử dụng","success")}<strong>Chỉ mục v3</strong></div><dl class="definition-list"><div><dt>Vector / từ khóa</dt><dd>ChromaDB / BM25</dd></div><div><dt>Lần kiểm tra mẫu</dt><dd>Hôm nay, 10:40</dd></div></dl>')+panel('Hiệu năng','Số liệu ví dụ để duyệt giao diện','<div class="performance"><span><strong>12,6 s</strong><small>Trung vị</small></span><span><strong>28,5 s</strong><small>P95</small></span></div><p class="muted">Tách thời gian truy hồi và sinh câu trả lời để xác định điểm chậm.</p>')+'</div>'
    jobs=[['JOB-024','Cập nhật dữ liệu văn bản mẫu',badge('Đang xử lý','warning'),'2 / 3 bước','Thiện Tâm','10:35'],['JOB-023','Xây lại chỉ mục từ bản nháp',badge('Cần xử lý','danger'),'Lỗi đọc một tệp PDF','Thiện Tâm','09:50'],['JOB-022','Kiểm tra chỉ mục hiện hành',badge('Hoàn tất','success'),'Đã kiểm tra dữ liệu mẫu','Thiện Tâm','Hôm qua']]
    content=health+panel('Hàng đợi cập nhật','Phiên bản mới chỉ được kích hoạt sau khi kiểm tra thành công.',table(['Tiến trình','Công việc','Trạng thái','Kết quả / tiến độ','Người tạo','Bắt đầu'],jobs),button('Tạo tiến trình',action='Tạo tiến trình mẫu',glyph='plus'))+'<div class="notice warning-notice">'+icon('info-circle')+'JOB-023: không đọc được một tệp PDF. Chỉ mục v3 vẫn tiếp tục phục vụ người dùng. '+button('Xem chi tiết lỗi',action='Xem lỗi đọc PDF')+'</div>'
    return admin_shell('admin-operations','Vận hành AI','Theo dõi mô hình, độ trễ và các lần cập nhật kho tri thức.',content,button('Kiểm tra trạng thái',action='Kiểm tra trạng thái mẫu',glyph='refresh'))


def audit():
    rows=[['Hôm nay, 10:42','Thiện Tâm','Duyệt văn bản','Tài liệu #DOC-036',badge('Thành công','success')],['Hôm nay, 10:30','Thiện Tâm','Xử lý phản hồi','Phản hồi #FB-015',badge('Thành công','success')],['Hôm nay, 09:58','Thiện Tâm','Mở khóa tài khoản','Tài khoản #USR-024',badge('Thành công','success')],['Hôm nay, 09:50','Hệ thống','Cập nhật chỉ mục','Tiến trình #JOB-023',badge('Lỗi','danger')]]
    backups='<div class="backup-summary"><span class="backup-icon">'+icon('history')+'</span><div><strong>Bản sao lưu gần nhất</strong><p>22/10/2026 · 02:00 · Bản sao minh họa</p></div>'+badge('Hoàn tất','success')+'</div><div class="backup-options"><div><strong>Dữ liệu nghiệp vụ</strong><p>Hồ sơ, lịch sử chat, phản hồi và nhật ký quản trị.</p></div>'+button('Tạo bản sao lưu',action='Tạo bản sao lưu mẫu',kind='primary')+'</div><div class="backup-options"><div><strong>Khôi phục dữ liệu</strong><p>Cần kiểm tra bản sao lưu và xác nhận trước khi áp dụng.</p></div>'+button('Chọn bản khôi phục',action='restore-backup',kind='danger-ghost')+'</div>'
    content=panel('Nhật ký hoạt động','Theo dõi ai đã thực hiện thay đổi và kết quả thao tác.',table(['Thời gian','Người thực hiện','Thao tác','Đối tượng','Kết quả'],rows),button('Xuất nhật ký',action='Xuất nhật ký mẫu'))+panel('Sao lưu & khôi phục','Bản mẫu mô tả quy trình. Chưa tạo hoặc khôi phục dữ liệu thật.',backups)
    return admin_shell('admin-audit','Nhật ký & sao lưu','Truy vết thay đổi và chuẩn bị phương án phục hồi dữ liệu.',content)


def settings():
    auth=f'<div class="integration-title"><span class="integration-icon">{icon("user")}</span><div><strong>Supabase Auth</strong><small>Nền tảng xác thực đã được chọn</small></div>{badge("Chưa tích hợp","warning")}</div><div class="setting-row"><div><strong>Xác minh email</strong><p>Yêu cầu xác minh email khi tạo tài khoản.</p></div><input class="switch" type="checkbox" checked aria-label="Xác minh email"></div><div class="setting-row"><div><strong>Khôi phục mật khẩu qua email</strong><p>Liên kết sử dụng một lần và có thời hạn.</p></div><input class="switch" type="checkbox" checked aria-label="Khôi phục mật khẩu"></div><div class="setting-row"><div><strong>Email gửi thông báo</strong><p>Kết nối SMTP khi triển khai chức năng thật.</p></div>{badge("Chờ cấu hình")}</div>'
    roles=table(['Quyền','Người dùng','Admin'],[['Lưu và xem lịch sử của mình','Có','Có'],['Gửi phản hồi câu trả lời','Có','Có'],['Quản lý người dùng','Không','Có'],['Duyệt văn bản và cập nhật chỉ mục','Không','Có'],['Xem nhật ký quản trị','Không','Có']])
    content='<div class="settings-grid">'+panel('Xác thực & tài khoản','Thiết lập đề xuất cho phiên bản dùng Supabase.',auth)+panel('Phân quyền','Một cửa đăng nhập, giao diện được chọn theo vai trò.',roles+'<div class="notice subtle">Không có đăng ký admin công khai. Quyền quản trị được cấp qua quy trình riêng.</div>')+'</div>'+panel('Hiển thị ứng dụng','Thông tin chung hiển thị với người dùng.','<div class="form-grid">'+input_field('Tên ứng dụng',value='VietLaborAI')+input_field('Tên không gian quản trị',value='Quản trị VietLaborAI')+'</div><p class="muted">Khóa quản trị và thông tin SMTP không được hiển thị trong bản mẫu.</p>')
    return admin_shell('admin-settings','Cài đặt & phân quyền','Quản lý cấu hình nghiệp vụ và quyền truy cập theo vai trò.',content,button('Lưu cấu hình',action='Lưu cấu hình bản mẫu',kind='primary'))


def public_base(member=False):
    conversations=[]
    messages=[]
    if member:
        conversations=[{'id':'demo-chat','title':'Tìm hiểu quyền lợi thử việc','display_time':'Hôm nay 10:20'}, {'id':'old-1','title':'Tra cứu hợp đồng lao động','display_time':'Hôm qua'}, {'id':'old-2','title':'Nghỉ phép và thời giờ làm việc','display_time':'20/10'}]
        messages=[{'id':'u1','role':'user','content':'Tôi đang thử việc và muốn hiểu quyền lợi của mình.'},{'id':'a1','role':'assistant','content':'Mình có thể giúp bạn tra cứu và đối chiếu với văn bản trong kho pháp luật.\n\n**Để xác định nội dung cần tra cứu**, bạn cho biết thêm:\n\n- Vị trí công việc và yêu cầu chuyên môn.\n- Thời gian đã thử việc.\n- Nội dung thỏa thuận hoặc hợp đồng đang có.\n\nBạn có thể đính kèm văn bản để mình hỗ trợ đọc và xác định các điểm cần đối chiếu.','structured_data':{'needs_clarification':True,'suggested_followups':['Tôi làm nhân viên văn phòng','Tôi muốn kiểm tra hợp đồng']}}]
    markup=layout_markup('chat' if member else 'home',messages,conversations,False,'demo-chat',username='Thiện Tâm' if member else '')
    markup=markup.replace(auth_dialog_markup(),'').replace('/app/static/approved-homepage.png','/ui/static/approved-homepage.png')
    if member:
        markup=markup.replace('<span class="account-name" title="Thiện Tâm">','<button data-route="user-profile" class="account-name" title="Thiện Tâm">').replace('Thiện Tâm</span><button class="account-logout"','Thiện Tâm</button><button class="account-logout"')
    return markup


def auth_screen(mode):
    titles={'login':'Chào mừng trở lại','register':'Tạo tài khoản của bạn','forgot':'Quên mật khẩu?','reset-sent':'Kiểm tra hộp thư của bạn','reset-password':'Đặt mật khẩu mới','reset-success':'Mật khẩu đã được cập nhật'}
    desc={'login':'Đăng nhập để lưu và tiếp tục cuộc trò chuyện.','register':'Lưu lịch sử riêng và tra cứu thuận tiện hơn.','forgot':'Nhập email đã đăng ký để nhận liên kết đặt lại.','reset-sent':'Nếu email khớp với tài khoản, liên kết khôi phục sẽ được gửi tới hộp thư của bạn.','reset-password':'Chọn mật khẩu mới để bảo vệ tài khoản của bạn.','reset-success':'Bạn có thể đăng nhập lại bằng mật khẩu mới.'}
    content=''
    if mode in {'login','register'}:
        content=(input_field('Họ và tên','Nhập họ và tên',extra='required') if mode=='register' else '')+input_field('Email','ban@example.com',kind='email',extra='required autocomplete="email"')+input_field('Mật khẩu','Ít nhất 8 ký tự',kind='password',extra='required minlength="8" autocomplete="new-password"')
        if mode=='register': content+=input_field('Nhập lại mật khẩu','Nhập lại mật khẩu',kind='password',extra='required minlength="8"')
        if mode=='login': content+='<button type="button" class="forgot-link" data-route="forgot">Quên mật khẩu?</button>'
        content+=f'<button class="btn primary wide" type="submit">{"Đăng nhập" if mode=="login" else "Tạo tài khoản"}{icon("chevron-right")}</button>'
        content+=f'<p class="auth-cross">{"Chưa có tài khoản?" if mode=="login" else "Đã có tài khoản?"}<button type="button" data-route="{"register" if mode=="login" else "login"}">{"Tạo tài khoản" if mode=="login" else "Đăng nhập"}</button></p>'
    elif mode=='forgot':
        content=input_field('Email','Nhập email đã đăng ký',kind='email',extra='required')+'<button class="btn primary wide" type="submit">Gửi liên kết khôi phục</button><p class="auth-cross"><button type="button" data-route="login">Quay lại đăng nhập</button></p>'
    elif mode=='reset-sent':
        content='<div class="mail-illustration">'+icon('file-text')+'</div><div class="instruction-box"><strong>Bước tiếp theo</strong><p>1. Mở email từ VietLaborAI.</p><p>2. Chọn liên kết đặt lại mật khẩu.</p><p>3. Tạo mật khẩu mới và đăng nhập lại.</p></div><small class="muted centered">Chưa thấy email? Hãy kiểm tra thư mục spam.</small>'+button('Mở màn đặt mật khẩu mẫu','reset-password','primary wide')+button('Nhập email khác','forgot','text wide')
    elif mode=='reset-password':
        content=input_field('Mật khẩu mới','Ít nhất 8 ký tự',kind='password',extra='required minlength="8"')+input_field('Nhập lại mật khẩu mới','Nhập lại mật khẩu mới',kind='password',extra='required minlength="8"')+'<p class="form-help">Sau khi đổi, các phiên đăng nhập cũ sẽ cần xác thực lại.</p><button class="btn primary wide" type="submit">Lưu mật khẩu mới</button>'
    else:
        content='<div class="success-mark">'+icon('thumb-up')+'</div>'+button('Quay lại đăng nhập','login','primary wide')
    target={'login':'user-chat','register':'login','forgot':'reset-sent','reset-password':'reset-success'}.get(mode,'')
    note=''
    return f'<div class="auth-scene"><div class="auth-underlay" inert>{public_base()}</div><div class="auth-shade"></div><section class="review-auth-card {"register-card" if mode=="register" else ""}" role="dialog" aria-modal="true" aria-labelledby="review-auth-title"><button class="review-auth-close" data-route="home" aria-label="Đóng">{icon("x")}</button>{brand()}<h1 id="review-auth-title">{titles[mode]}</h1><p class="auth-description">{desc[mode]}</p><form data-submit="{target}" class="review-auth-form">{content}</form>{note}<div class="auth-review-note">Bản mẫu để duyệt · Không gửi email hoặc lưu mật khẩu thật</div></section></div>'


def profile():
    form='<div class="profile-person"><span class="avatar extra rose">TT</span><div><h2>Mai Trần Thiện Tâm</h2><p>tam@example.com</p>'+badge('Email đã xác minh','success')+'</div></div><div class="form-grid">'+input_field('Họ và tên',value='Mai Trần Thiện Tâm')+input_field('Email',value='tam@example.com',kind='email')+'</div><div class="align-right">'+button('Lưu hồ sơ',action='Lưu hồ sơ bản mẫu',kind='primary')+'</div>'
    security='<div class="setting-row"><div><strong>Mật khẩu</strong><p>Đổi mật khẩu để bảo vệ tài khoản.</p></div>'+button('Đổi mật khẩu','reset-password')+'</div><div class="setting-row"><div><strong>Các phiên đăng nhập</strong><p>Thiết bị hiện tại · Windows · Phiên minh họa</p></div>'+badge('Phiên hiện tại','success')+'</div><div class="setting-row"><div><strong>Đăng xuất các thiết bị khác</strong><p>Giữ lại phiên trên thiết bị hiện tại.</p></div>'+button('Đăng xuất phiên khác',action='Thu hồi phiên mẫu')+'</div>'
    return f'<div class="profile-page"><header class="profile-header">{brand()}{button("Trở về trợ lý AI","user-chat",glyph="message-circle")}</header><main class="profile-main"><div class="page-heading"><div><h1>Tài khoản của bạn</h1><p>Quản lý thông tin cá nhân, bảo mật và quyền riêng tư.</p></div>{badge("Người dùng","role")}</div>{panel("Hồ sơ cá nhân","Thông tin được dùng để hiển thị trong ứng dụng.",form)}{panel("Bảo mật & đăng nhập","Các thao tác tài khoản do Supabase Auth quản lý khi tích hợp thật.",security)}<div class="profile-footer"><p>Lịch sử chat chỉ thuộc về tài khoản của bạn.</p>{button("Đăng xuất","home")}</div><div class="prototype-foot">Bản mẫu để duyệt · Dữ liệu minh họa · Chưa kết nối Supabase</div></main><div class="demo-toast" role="status" hidden></div></div>'


def denied():
    return f'<div class="denied-page"><header class="profile-header">{brand()}{badge("Tài khoản người dùng")}</header><main><span class="denied-icon">{icon("scale")}</span><span class="error-code">403</span><h1>Bạn không có quyền truy cập</h1><p>Khu vực này chỉ dành cho quản trị viên.<br>Bạn vẫn có thể sử dụng trợ lý AI và lịch sử của mình.</p>{button("Về trợ lý AI","user-chat","primary")}{button("Đăng nhập tài khoản khác","login","text")}</main><div class="prototype-foot centered">Bản mẫu minh họa trường hợp tài khoản thường mở trang quản trị.</div></div>'


def build():
    screens=[
        ('home','01','Trang AI · Chế độ khách',public_base()),
        ('login','02','Đăng nhập bằng email',auth_screen('login')),
        ('register','03','Tạo tài khoản người dùng',auth_screen('register')),
        ('forgot','04','Quên mật khẩu',auth_screen('forgot')),
        ('reset-sent','05','Thông báo gửi email khôi phục',auth_screen('reset-sent')),
        ('reset-password','06','Đặt mật khẩu mới',auth_screen('reset-password')),
        ('reset-success','07','Đặt lại mật khẩu thành công',auth_screen('reset-success')),
        ('user-chat','08','Chat & lịch sử của người dùng',public_base(True)),
        ('user-profile','09','Hồ sơ & bảo mật tài khoản',profile()),
        ('admin-dashboard','10','Admin · Tổng quan',dashboard()),
        ('admin-users','11','Admin · Người dùng',users()),
        ('admin-user-detail','12','Admin · Chi tiết tài khoản',users(True)),
        ('admin-documents','13','Admin · Kho văn bản',documents()),
        ('admin-document-add','14','Admin · Kiểm tra & duyệt văn bản',documents(True)),
        ('admin-feedback','15','Admin · Xử lý phản hồi',feedback()),
        ('admin-operations','16','Admin · Vận hành AI',operations()),
        ('admin-audit','17','Admin · Nhật ký & sao lưu',audit()),
        ('admin-settings','18','Admin · Cài đặt & phân quyền',settings()),
        ('access-denied','19','Từ chối truy cập trái quyền',denied()),
    ]
    pages={key:{'number':num,'title':title,'html':html} for key,num,title,html in screens}
    (OUT/'screens.json').write_text(json.dumps(pages,ensure_ascii=False),encoding='utf-8')
    manifest=[{'id':key,'number':num,'title':title,'file':f'{num}-{key}.jpg','width':1440,'height':1080} for key,num,title,_ in screens]
    manifest.append({'id':'admin-dashboard','number':'20','title':'Admin · Giao diện điện thoại','file':'20-admin-mobile.jpg','width':390,'height':844})
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Generated {len(screens)} review screens + mobile variant in {OUT}')


if __name__=='__main__':
    build()
