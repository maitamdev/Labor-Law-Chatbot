/* Review prototype only: no authentication, database, email, or external requests. */
(() => {
  let screens = {}, toastTimer;
  const root = document.getElementById('preview-root');
  function render(id, push = true) {
    if (!screens[id]) id = 'admin-dashboard';
    if (push) history.pushState({}, '', '?screen=' + encodeURIComponent(id));
    root.innerHTML = screens[id].html;
    document.body.dataset.screen = id;
    document.title = screens[id].title + ' · VietLaborAI · Bản mẫu';
    window.scrollTo(0, 0);
  }
  function toast(message) {
    let box = document.querySelector('.demo-toast');
    if (!box) { box = document.createElement('div'); box.className = 'demo-toast'; box.setAttribute('role', 'status'); root.append(box); }
    clearTimeout(toastTimer); box.textContent = message; box.hidden = false;
    toastTimer = setTimeout(() => { box.hidden = true; }, 4200);
  }
  const dialogs = {
    'invite-admin': ['Mời quản trị viên', 'Chỉ cấp quyền cho email đã được xác minh. Khi triển khai, việc cấp quyền được kiểm tra ở máy chủ và ghi nhật ký.', '<label class="field"><span>Email người được mời</span><input type="email" required placeholder="quantri@example.com"></label>', 'Gửi lời mời mẫu'],
    'reset-user': ['Gửi liên kết khôi phục', 'Gửi hướng dẫn đến email đã đăng ký. Quản trị viên không xem hoặc đặt mật khẩu thay người dùng.', '<div class="notice subtle">Tài khoản mẫu: minh.anh@example.com</div>', 'Xác nhận gửi mẫu'],
    'lock-user': ['Khóa tài khoản', 'Tạm ngừng quyền truy cập của tài khoản. Khi triển khai, thao tác cần được kiểm tra ở máy chủ và ghi nhật ký.', '<label class="field"><span>Lý do khóa</span><textarea required placeholder="Nhập lý do để ghi nhật ký"></textarea></label>', 'Khóa tài khoản mẫu'],
    'restore-backup': ['Kiểm tra bản khôi phục', 'Chọn bản sao lưu và kiểm tra phạm vi dữ liệu trước khi xác nhận. Bản mẫu không khôi phục dữ liệu thật.', '<label class="field"><span>Bản sao lưu</span><select><option>22/10/2026 · 02:00 · Bản sao minh họa</option></select></label><label class="consent"><input type="checkbox" required> Tôi đã kiểm tra bản sao lưu được chọn.</label>', 'Xác nhận bản mẫu']
  };
  root.addEventListener('click', e => {
    const el = e.target.closest('button, a'); if (!el) return;
    if (el.dataset.route) { e.preventDefault(); render(el.dataset.route); return; }
    if (el.hasAttribute('data-auth-open')) { render(el.dataset.authOpen === 'register' ? 'register' : 'login'); return; }
    if (el.hasAttribute('data-menu')) { document.querySelector('.admin-app').classList.toggle('menu-open'); return; }
    if (el.hasAttribute('data-close')) { el.closest('dialog').close(); return; }
    if (el.hasAttribute('data-mobile-menu')) { document.querySelector('.vl-app').classList.toggle('menu-open'); return; }
    if (el.dataset.event === 'logout') { render('home'); return; }
    if (el.dataset.event === 'new_chat' || el.dataset.query || el.dataset.conversation) { render('user-chat'); return; }
    if (el.hasAttribute('data-view')) {
      if (['home', 'chat'].includes(el.dataset.view)) render(el.dataset.view === 'chat' ? 'user-chat' : 'home');
      else toast('Màn này giữ theo ứng dụng hiện tại. Bộ demo tập trung vào tài khoản và quản trị.');
      return;
    }
    if (el.dataset.action) {
      if (el.dataset.action === 'Đăng xuất bản mẫu') { render('home'); return; }
      const spec = dialogs[el.dataset.action], dialog = document.querySelector('.demo-action-dialog');
      if (spec && dialog) {
        dialog.querySelector('.action-content').innerHTML = '<h2>' + spec[0] + '</h2><p class="muted">' + spec[1] + '</p><form class="action-demo-form">' + spec[2] + '<button type="submit" class="btn primary wide">' + spec[3] + '</button></form>';
        dialog.showModal();
      } else toast('Bản mẫu: ' + el.textContent.trim() + '. Chưa thay đổi dữ liệu thật.');
      return;
    }
    if (el.dataset.tab !== undefined) { el.parentElement.querySelectorAll('button').forEach(b => b.classList.remove('active')); el.classList.add('active'); toast('Đã chọn bộ lọc trong bản mẫu.'); return; }
    if (!el.closest('form') && !el.href) toast('Thao tác minh họa. Chưa kết nối chức năng thật.');
  });
  root.addEventListener('input', e => {
    if (!e.target.hasAttribute('data-filter')) return;
    const query = e.target.value.toLocaleLowerCase('vi').trim();
    root.querySelectorAll('.data-table tbody tr').forEach(row => { row.hidden = !row.textContent.toLocaleLowerCase('vi').includes(query); });
  });
  root.addEventListener('submit', e => {
    e.preventDefault(); const form = e.target;
    if (form.classList.contains('action-demo-form')) { form.closest('dialog').close(); toast('Đã mô phỏng xác nhận. Không có thao tác trên dữ liệu thật.'); return; }
    if (form.classList.contains('composer')) { render('user-chat'); return; }
    if (form.hasAttribute('data-submit')) {
      const passwords = [...form.querySelectorAll('input[type=password]')];
      if (passwords.length === 2 && passwords[0].value !== passwords[1].value) { passwords[1].setCustomValidity('Hai mật khẩu chưa trùng khớp.'); passwords[1].reportValidity(); passwords[1].oninput = () => passwords[1].setCustomValidity(''); return; }
      const target = form.dataset.submit;
      if (target) { const current = document.body.dataset.screen; const email = form.querySelector('input[type=email]')?.value; render(current === 'login' && email === 'admin@example.com' ? 'admin-dashboard' : target); if(current === 'register') toast('Bản mẫu: hãy xác minh email trước khi đăng nhập. Chưa tạo tài khoản hoặc gửi email thật.'); }
    }
  });
  window.addEventListener('popstate', () => render(new URLSearchParams(location.search).get('screen'), false));
  fetch('screens.json').then(r => { if (!r.ok) throw Error('Không tải được bộ màn hình'); return r.json(); }).then(data => { screens = data; render(new URLSearchParams(location.search).get('screen'), false); }).catch(err => { root.textContent = err.message; });
})();
