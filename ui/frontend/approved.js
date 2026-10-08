export default function(component) {
  const {parentElement, data, setTriggerValue} = component;
  const mount = parentElement.querySelector('.vl-mount');
  const oldInput = mount.querySelector('#vl-question');
  const previousDraft = oldInput ? oldInput.value : '';
  const oldConversation = mount.dataset.conversation;
  // Markup is constructed and escaped by the server. User text is never
  // concatenated into DOM markup here.
  mount.innerHTML = data.markup;
  mount.dataset.conversation = data.conversation_id;
  const app = mount.querySelector('.vl-app');
  const input = app.querySelector('#vl-question');
  const busy = app.dataset.busy === 'true';
  let sent = false;
  let toastTimer;
  const emit = action => {
    if (action.type === 'query') {
      if (sent || busy) return;
      sent = true;
      setTimeout(() => { sent = false; }, 2500);
    }
    setTriggerValue('action', action);
  };
  const toast = text => {
    const node = app.querySelector('.toast');
    node.textContent = text;
    node.classList.add('visible');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => node.classList.remove('visible'), 3200);
  };
  // Auto-scroll message-feed internally to latest message
  const scrollToLatest = (smooth = true) => {
    try {
      const feed = app.querySelector('.message-feed');
      if (feed) {
        feed.scrollTo({ top: feed.scrollHeight, behavior: smooth ? 'smooth' : 'auto' });
      }
    } catch (_) {
      try {
        const feed = app.querySelector('.message-feed');
        if (feed) feed.scrollTop = feed.scrollHeight;
      } catch (_) {}
    }
  };
  if (app.dataset.view === 'chat') {
    setTimeout(() => scrollToLatest(false), 40);
    setTimeout(() => scrollToLatest(false), 150);
  }

  // Dynamic progress cycling while assistant is busy
  let thinkingTimer;
  if (busy) {
    setTimeout(() => scrollToLatest(true), 150);
    const thinkingText = app.querySelector('#vl-thinking-text');
    if (thinkingText) {
      const steps = [
        "Đang tra cứu cơ sở dữ liệu pháp luật lao động...",
        "Đang phân tích và đối soát căn cứ pháp lý...",
        "Đang trích xuất điều khoản và chế tài...",
        "Đang tổng hợp lập luận và soạn thảo tư vấn...",
      ];
      let stepIdx = 0;
      thinkingTimer = setInterval(() => {
        stepIdx = (stepIdx + 1) % steps.length;
        if (thinkingText && app.contains(thinkingText)) {
          thinkingText.textContent = steps[stepIdx];
        } else {
          clearInterval(thinkingTimer);
        }
      }, 2400);
    }
  }

  const formatBytes = bytes => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const draftKey = 'vietlaborai-draft:' + data.conversation_id;
  const composers = app.querySelectorAll('.composer');

  composers.forEach(form => {
    const input = form.querySelector('#vl-question') || form.querySelector('textarea');
    const counter = form.querySelector('.counter');
    const fileInput = form.querySelector('.vl-file-input');
    const attachBtn = form.querySelector('[data-attach-btn]');
    const bar = form.querySelector('.composer-attachment-bar');
    const previewName = form.querySelector('.preview-name');
    const previewSize = form.querySelector('.preview-size');
    const previewRemove = form.querySelector('.preview-remove');

    let formAttachment = null;

    if (input) {
      try {
        if (oldConversation === data.conversation_id && previousDraft) {
          input.value = previousDraft;
        } else {
          input.value = sessionStorage.getItem(draftKey) || '';
        }
      } catch (_) {}

      const updateCounter = () => {
        if (counter) counter.textContent = input.value.length + '/2000';
        try { sessionStorage.setItem(draftKey, input.value); } catch (_) {}
      };
      input.addEventListener('input', updateCounter);
      updateCounter();

      const submit = event => {
        if (event) event.preventDefault();
        const text = input.value.trim();
        const att = formAttachment;
        if ((!text && !att) || sent || busy) {
          if (!text && !att) input.focus();
          return;
        }
        input.value = '';
        formAttachment = null;
        if (fileInput) fileInput.value = '';
        if (bar) bar.style.display = 'none';
        updateCounter();

        // Switch to chat view if on home or another view
        app.dataset.view = 'chat';
        app.querySelectorAll('.nav-item').forEach(btn => {
          const isActive = btn.dataset.view === 'chat';
          btn.classList.toggle('active', isActive);
          if (isActive) btn.setAttribute('aria-current', 'page');
          else btn.removeAttribute('aria-current');
        });

        scrollToLatest(true);
        emit({type: 'query', text, attachment: att});
      };

      form.addEventListener('submit', submit);
      input.addEventListener('keydown', event => {
        if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
          submit(event);
        }
      });
    }

    if (attachBtn && fileInput) {
      attachBtn.addEventListener('click', e => {
        e.preventDefault();
        if (!busy) fileInput.click();
      });

      fileInput.addEventListener('change', () => {
        const file = fileInput.files && fileInput.files[0];
        if (!file) return;

        if (file.size > 15 * 1024 * 1024) {
          toast('Tệp đính kèm vượt quá giới hạn 15MB. Vui lòng chọn tệp nhỏ hơn.');
          fileInput.value = '';
          return;
        }

        const nameLower = file.name.toLowerCase();
        const allowed = ['.pdf', '.docx', '.doc', '.txt'];
        if (!allowed.some(ext => nameLower.endsWith(ext))) {
          toast('Chỉ hỗ trợ tệp văn bản .PDF, .DOCX, .DOC hoặc .TXT');
          fileInput.value = '';
          return;
        }

        const reader = new FileReader();
        reader.onload = () => {
          formAttachment = {
            name: file.name,
            size: file.size,
            type: file.type || 'application/octet-stream',
            data: reader.result,
          };
          if (previewName) previewName.textContent = file.name;
          if (previewSize) previewSize.textContent = formatBytes(file.size);
          if (bar) bar.style.display = 'block';
          toast('Đã đính kèm: ' + file.name);
          if (input) input.focus();
        };
        reader.onerror = () => {
          toast('Không thể đọc tệp đã chọn. Vui lòng thử lại.');
        };
        reader.readAsDataURL(file);
      });
    }

    if (previewRemove) {
      previewRemove.addEventListener('click', e => {
        e.preventDefault();
        formAttachment = null;
        if (fileInput) fileInput.value = '';
        if (bar) bar.style.display = 'none';
      });
    }
  });

  const dialog = app.querySelector('.info-dialog');
  const showDialog = (title, markup) => {
    dialog.querySelector('h2').textContent = title;
    dialog.querySelector('.dialog-body').innerHTML = markup;
    dialog.showModal();
  };
  const dialogs = {
    guide:['Hướng dẫn sử dụng','<p>Nhập câu hỏi về luật lao động hoặc tải lên hợp đồng (.pdf, .docx, .txt) rồi bấm <strong>Gửi câu hỏi</strong>. Enter để gửi, Shift + Enter để xuống dòng.</p><p>Bạn cũng có thể chọn câu hỏi gợi ý. Nếu trợ lý cần thêm dữ kiện, chọn câu trả lời phù hợp hoặc nhập thông tin bổ sung.</p><p>Mở <strong>Căn cứ pháp lý</strong> để xem điều khoản và nguồn văn bản. Trong trang Trợ lý AI, mở <strong>Lịch sử</strong> để tiếp tục trò chuyện.</p>'],
    login:['Đăng nhập','<p>Ứng dụng đang chạy cục bộ. Bạn có thể sử dụng trợ lý và lưu lịch sử trên máy này mà không cần tài khoản.</p><p>Chức năng đăng nhập tài khoản chưa được cấu hình.</p>'],
    attachment:['Đính kèm văn bản','<p>Trợ lý hỗ trợ đọc trực tiếp các tệp hợp đồng, quyết định, thỏa thuận dạng <strong>.PDF, .DOCX, .DOC hoặc .TXT</strong> (tối đa 15MB).</p><p>Bấm vào nút <strong>Đính kèm văn bản</strong> (biểu tượng kẹp giấy) tại ô nhập liệu để tải tệp lên đối chiếu và rà soát pháp luật.</p>'],
    policy:['Chính sách sử dụng','<p>VietLabor AI hỗ trợ tra cứu thông tin pháp luật lao động từ các văn bản trong cơ sở dữ liệu. Nội dung cung cấp mang tính tham khảo và không thay thế ý kiến tư vấn chuyên môn cho tình huống pháp lý cụ thể.</p>'],
    terms:['Điều khoản','<p>VietLabor AI hỗ trợ tra cứu thông tin pháp luật lao động từ các văn bản trong cơ sở dữ liệu. Nội dung cung cấp mang tính tham khảo và không thay thế ý kiến tư vấn chuyên môn cho tình huống pháp lý cụ thể.</p>'],
    contact:['Liên hệ','<p>Thông tin liên hệ chưa được cấu hình.</p><p>Bạn có thể gửi góp ý qua mục <strong>Phản hồi</strong> của ứng dụng.</p>'],
    feedback:['Phản hồi','<form class="feedback-form"><label for="vl-feedback">Góp ý về giao diện hoặc câu trả lời</label><textarea id="vl-feedback" required maxlength="1000" placeholder="Nhập góp ý của bạn..."></textarea><button class="send" type="submit">Gửi phản hồi</button></form>'],
  };
  const onClick = async event => {
    const button = event.target.closest('button');
    if (!button || !app.contains(button)) return;
    if (button.hasAttribute('data-view')) {
      const targetView = button.dataset.view;
      app.dataset.view = targetView;
      app.querySelectorAll('.nav-item').forEach(btn => {
        const isActive = btn.dataset.view === targetView;
        btn.classList.toggle('active', isActive);
        if (isActive) btn.setAttribute('aria-current', 'page');
        else btn.removeAttribute('aria-current');
      });
      emit({type:'navigate', view:targetView});
    }
    else if (button.hasAttribute('data-query')) {
      app.dataset.view = 'chat';
      app.querySelectorAll('.nav-item').forEach(btn => {
        const isActive = btn.dataset.view === 'chat';
        btn.classList.toggle('active', isActive);
        if (isActive) btn.setAttribute('aria-current', 'page');
        else btn.removeAttribute('aria-current');
      });
      scrollToLatest(true);
      emit({type:'query', text:button.dataset.query});
    }
    else if (button.hasAttribute('data-event')) {
      if (button.dataset.event === 'new_chat') {
        app.dataset.view = 'chat';
        app.querySelectorAll('.sidebar-conv-row').forEach(row => row.classList.remove('active'));
      }
      emit({type:button.dataset.event});
    }
    else if (button.hasAttribute('data-conversation')) {
      const targetConv = button.dataset.conversation;
      app.querySelectorAll('.sidebar-conv-row').forEach(row => {
        const hasBtn = row.querySelector(`[data-conversation="${targetConv}"]`);
        row.classList.toggle('active', Boolean(hasBtn));
      });
      app.dataset.view = 'chat';
      setTimeout(() => scrollToLatest(false), 50);
      emit({type:'switch', id:targetConv});
    }
    else if (button.hasAttribute('data-delete')) {
      event.preventDefault();
      event.stopPropagation();
      emit({type:'delete', id:button.dataset.delete});
    }
    else if (button.hasAttribute('data-feedback')) emit({type:'feedback', rating:button.dataset.feedback, id:button.dataset.message});
    else if (button.hasAttribute('data-mobile-menu')) app.classList.toggle('menu-open');
    else if (button.classList.contains('dialog-close')) {
      dialog.close();
      dialog.classList.remove('template-dialog-view');
    }
    else if (button.hasAttribute('data-template')) {
      const templateId = button.dataset.template;
      const templatesScript = app.querySelector('#vl-templates-data');
      if (templatesScript) {
        try {
          const templates = JSON.parse(templatesScript.textContent);
          const item = templates.find(t => t.id === templateId);
          if (item) {
            const safeContent = item.content
              .replace(/&/g, '&amp;')
              .replace(/</g, '&lt;')
              .replace(/>/g, '&gt;');
            const modalMarkup = `
              <div class="template-modal-body">
                <div class="template-modal-meta">
                  <span class="template-modal-tag">${item.tag}</span>
                  <span class="template-modal-basis">${item.basis}</span>
                </div>
                <p class="template-modal-desc">${item.summary}</p>
                <div class="template-modal-toolbar">
                  <button class="btn-copy-template" data-tpl-copy="${item.id}">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 4v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V7.242a2 2 0 0 0-.602-1.43L16.083 2.57A2 2 0 0 0 14.685 2H10a2 2 0 0 0-2 2z"/><path d="M16 18v2a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2h2"/></svg>
                    <span>Sao chép toàn bộ mẫu</span>
                  </button>
                  <button class="btn-ai-fill" data-query="${item.query.replace(/"/g, '&quot;')}">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
                    <span>Nhờ AI điền thông tin</span>
                  </button>
                </div>
                <div class="template-pre-wrapper">
                  <pre class="template-pre">${safeContent}</pre>
                </div>
              </div>
            `;
            dialog.classList.add('template-dialog-view');
            showDialog(item.title, modalMarkup);
          }
        } catch (e) {
          console.error(e);
        }
      }
    }
    else if (button.hasAttribute('data-tpl-copy')) {
      const pre = dialog.querySelector('.template-pre');
      if (pre) {
        try {
          await navigator.clipboard.writeText(pre.textContent);
          toast('Đã sao chép toàn bộ mẫu văn bản vào bộ nhớ tạm!');
        } catch (_) {
          const range = document.createRange();
          range.selectNodeContents(pre);
          const sel = window.getSelection();
          sel.removeAllRanges();
          sel.addRange(range);
          toast('Đã bôi đen toàn bộ mẫu. Nhấn Ctrl+C để sao chép.');
        }
      }
    }
    else if (button.classList.contains('btn-ai-fill')) {
      dialog.close();
      dialog.classList.remove('template-dialog-view');
      app.dataset.view = 'chat';
      app.querySelectorAll('.nav-item').forEach(btn => {
        const isActive = btn.dataset.view === 'chat';
        btn.classList.toggle('active', isActive);
        if (isActive) btn.setAttribute('aria-current', 'page');
        else btn.removeAttribute('aria-current');
      });
      scrollToLatest(true);
      emit({type:'query', text:button.dataset.query});
    }
    else if (button.hasAttribute('data-copy')) {
      const message = data.messages.find(msg => msg.id === button.dataset.copy);
      if (message) {
        try { await navigator.clipboard.writeText(message.content); toast('Đã sao chép câu trả lời.'); }
        catch (_) { toast('Trình duyệt chưa cho phép sao chép. Bạn có thể chọn nội dung và sao chép trực tiếp.'); }
      }
    } else if (button.hasAttribute('data-dialog')) {
      const key = button.dataset.dialog;
      if (key === 'history') showDialog('Lịch sử trò chuyện', app.querySelector('#history-content').innerHTML);
      else if (dialogs[key]) showDialog(...dialogs[key]);
    }
  };
  app.addEventListener('click', onClick);
  dialog.addEventListener('click', event => {
    if (event.target === dialog) {
      dialog.close();
      dialog.classList.remove('template-dialog-view');
    }
  });
  dialog.addEventListener('submit', event => {
    if (!event.target.classList.contains('feedback-form')) return;
    event.preventDefault();
    const text = dialog.querySelector('#vl-feedback').value.trim();
    if (text) emit({type:'general_feedback', text});
  });
  const search = app.querySelector('#document-search');
  if (search) search.addEventListener('input', () => {
    const query = search.value.toLocaleLowerCase('vi').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d');
    let visible = 0;
    app.querySelectorAll('.searchable-documents .document-row').forEach(row => {
      const title = row.textContent.toLocaleLowerCase('vi').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d');
      row.hidden = !title.includes(query);
      if (!row.hidden) visible++;
    });
    app.querySelector('.no-results').hidden = visible > 0;
  });
  if (data.notice) toast(data.notice);
  return () => { 
    app.removeEventListener('click', onClick); 
    clearTimeout(toastTimer); 
    if (thinkingTimer) clearInterval(thinkingTimer);
  };
}
