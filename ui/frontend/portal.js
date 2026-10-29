export default function(component) {
  const {parentElement, data, setTriggerValue} = component;
  const mount = parentElement.querySelector('.portal-mount');
  if (!mount) return;
  mount.__portalSaveFilters?.();
  // Streamlit can update component data without unmounting its DOM node. Retire
  // timers from the previous render before replacing its markup so an old
  // request timeout cannot cover a page that has already loaded successfully.
  const previousLifecycle = mount.__portalLifecycle;
  if (previousLifecycle) {
    if (previousLifecycle.cleanup) previousLifecycle.cleanup();
    else {
      clearTimeout(previousLifecycle.timeout);
      clearTimeout(previousLifecycle.pollTimeout);
      clearTimeout(previousLifecycle.busyTimer);
    }
  }
  const lifecycle = {timeout:null, pollTimeout:null, busyTimer:null, cleanup:null};
  mount.__portalLifecycle = lifecycle;
  mount.innerHTML = data.markup;
  mount.setAttribute('aria-busy', 'false');
  // Keep only filter choices in this component's memory, scoped to the account.
  // Never put forms, passwords, chat content or auth tokens into browser storage.
  let currentView = mount.querySelector('.admin-app')?.dataset.page || mount.querySelector('.profile-page')?.dataset.accountView || '';
  let currentSelectedId = data.selected || '';
  const owner = mount.querySelector('.admin-app')?.dataset.owner || 'account';
  if (!owner || mount.__portalFilterState?.owner !== owner) mount.__portalFilterState = {owner, views:{}};
  const filterSelector = '[data-search],[data-filter-column],[data-date-from],[data-date-to],[data-page-size],[data-feedback-status],[data-feedback-consent],[data-feedback-size]';
  const getActiveView = () => mount.querySelector('.admin-app')?.dataset.page || mount.querySelector('.profile-page')?.dataset.accountView || currentView || '';
  const restoreFilters = () => {
    const v = getActiveView();
    const savedFilters = mount.__portalFilterState?.views?.[v];
    if (savedFilters) {
      mount.querySelectorAll(filterSelector).forEach((field,i)=>{
        if (savedFilters.values[i] !== undefined) field.value = savedFilters.values[i];
      });
      mount.querySelectorAll('.data-table,.feedback-list').forEach((table,i)=>{
        table.dataset.page = String(savedFilters.pages[i] || 0);
      });
    }
  };
  const saveFilters = () => {
    const v = getActiveView();
    if (owner && v) mount.__portalFilterState.views[v] = {
      values:[...mount.querySelectorAll(filterSelector)].map(field=>field.value),
      pages:[...mount.querySelectorAll('.data-table,.feedback-list')].map(table=>Number(table.dataset.page || 0)),
    };
  };
  restoreFilters();
  mount.__portalSaveFilters = saveFilters;
  if (data.form_draft?.kind) {
    const form = mount.querySelector(`form[data-form="${CSS.escape(data.form_draft.kind)}"]`);
    for (const [name, value] of Object.entries(data.form_draft.fields || {})) {
      const field = form?.querySelector(`[name="${CSS.escape(name)}"]`);
      if (!field || ['password','file'].includes(field.type)) continue;
      if (field.type === 'checkbox') field.checked = value === true;
      else field.value = String(value ?? '');
    }
  }
  let sending = false;
  let confirmDialog;
  const errorMessage = text => {
    let box = mount.querySelector('.portal-client-error');
    if (!box) {
      box = document.createElement('div');
      box.className = 'portal-client-error';
      box.setAttribute('role', 'alert');
      mount.appendChild(box);
    }
    box.textContent = text;
  };
  const setBusy = (busy, showProgress = true) => {
    sending = busy;
    mount.setAttribute('aria-busy', String(busy));
    clearTimeout(lifecycle.busyTimer);
    mount.querySelectorAll('button[data-action], button[type="submit"]').forEach(button => {
      if (busy && !button.disabled) {button.dataset.portalBusy = 'true'; button.disabled = true;}
      else if (!busy && button.dataset.portalBusy) {delete button.dataset.portalBusy; button.disabled = false;}
    });
    const progress = mount.querySelector('.portal-progress');
    if (!busy) {
      if (progress) progress.hidden = true;
    } else if (showProgress && progress) {
      lifecycle.busyTimer = setTimeout(() => {
        if (sending && progress) progress.hidden = false;
      }, 200);
    }
  };
  const emit = payload => {
    if (sending) return false;
    try {
      const isRouteExit = payload.type === 'portal_route';
      setBusy(true, !isRouteExit);
      const actionId = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`;
      setTriggerValue('action', {
        ...payload,
        current_view: currentView,
        current_id: currentSelectedId,
        action_id: actionId,
      });
      lifecycle.timeout = setTimeout(() => {
        if (mount.__portalLifecycle !== lifecycle) return;
        lifecycle.timeout = null;
        setBusy(false);
        errorMessage('Chưa nhận được phản hồi từ máy chủ. Kiểm tra kết nối rồi tải lại trang để xem trạng thái thao tác.');
      }, 45000);
      return true;
    } catch (error) {
      setBusy(false);
      errorMessage('Không gửi được thao tác. Hãy tải lại trang và thử lại.');
      console.error('[VietLaborAI admin]', error);
      return false;
    }
  };
  const navigateClient = (nextRoute, nextId = '') => {
    const views = data.views || {};
    const key = nextId ? `${nextRoute}:${nextId}` : nextRoute;
    const nextMarkup = views[key] || (!nextId ? views[nextRoute] : null);
    if (!nextMarkup) return false;
    saveFilters();
    currentView = nextRoute;
    currentSelectedId = nextId || '';
    mount.innerHTML = nextMarkup;
    mount.setAttribute('aria-busy', 'false');
    restoreFilters();
    filter();
    filterFeedback();
    mount.querySelector('.detail-drawer button')?.focus();
    return true;
  };
  const confirmAction = message => new Promise(resolve => {
    confirmDialog = document.createElement('dialog');
    confirmDialog.className = 'portal-confirm';
    confirmDialog.setAttribute('aria-labelledby', 'portal-confirm-title');
    confirmDialog.innerHTML = '<h2 id="portal-confirm-title">Xác nhận thao tác</h2><p></p><div class="dialog-actions"><button type="button" class="btn" data-confirm-cancel>Hủy</button><button type="button" class="btn primary" data-confirm-accept>Xác nhận</button></div>';
    confirmDialog.querySelector('p').textContent = message;
    mount.appendChild(confirmDialog);
    const finish = accepted => {
      confirmDialog?.close();
      confirmDialog?.remove();
      confirmDialog = null;
      resolve(accepted);
    };
    confirmDialog.querySelector('[data-confirm-accept]').onclick = () => finish(true);
    confirmDialog.querySelector('[data-confirm-cancel]').onclick = () => finish(false);
    confirmDialog.addEventListener('cancel', event => {event.preventDefault(); finish(false);}, {once:true});
    confirmDialog.showModal();
    confirmDialog.querySelector('[data-confirm-cancel]').focus();
  });
  const toggleMenu = force => {
    const app = mount.querySelector('.admin-app');
    if (!app) return;
    const open = typeof force === 'boolean' ? force : !app.classList.contains('menu-open');
    app.classList.toggle('menu-open', open);
    app.querySelector('.menu-toggle')?.setAttribute('aria-expanded', String(open));
    const scrim = app.querySelector('.mobile-scrim');
    if (scrim) scrim.hidden = !open;
  };
  const click = async event => {
    const target = event.target instanceof Element ? event.target : event.target.parentElement;
    const button = target?.closest('button');
    if (!button || !mount.contains(button) || button.disabled) return;
    if (button.hasAttribute('data-menu')) {toggleMenu(); return;}
    if (button.hasAttribute('data-reset-filters')) {
      button.closest('.panel')?.querySelectorAll('[data-search],[data-filter-column],[data-date-from],[data-date-to]').forEach(field=>{field.value='';});
      filter(true); saveFilters(); return;
    }
    if (button.dataset.feedbackPage) {
      const list = button.closest('.feedback-list');
      if (list) {
        const controls = list.querySelector('.feedback-pagination');
        const size = Number(controls?.querySelector('[data-feedback-size]')?.value || 10);
        const matching = [...list.querySelectorAll('.feedback-item')].filter(item=>item.dataset.filtered !== 'true');
        const pageCount = Math.max(1, Math.ceil(matching.length / size));
        const current = Number(list.dataset.page || 0);
        list.dataset.page = String(button.dataset.feedbackPage === 'next' ? Math.min(pageCount - 1, current + 1) : Math.max(0, current - 1));
        filterFeedback();
        saveFilters();
      }
      return;
    }
    if (button.dataset.pageTurn) {
      const table = button.closest('.pagination')?.previousElementSibling?.querySelector('.data-table');
      if (table) {
        const pageCount = Math.max(1, Math.ceil([...table.querySelectorAll('tbody tr[data-search-row]')].filter(row=>row.dataset.filtered !== 'true').length / Number(table.dataset.pageSize || 25)));
        const current = Number(table.dataset.page || 0);
        table.dataset.page = String(button.dataset.pageTurn === 'next' ? Math.min(pageCount - 1, current + 1) : Math.max(0, current - 1));
        filter();
        saveFilters();
      }
      return;
    }
    if (button.hasAttribute('data-open-dialog')) {
      mount.querySelector(`#${CSS.escape(button.dataset.openDialog)}`)?.showModal(); return;
    }
    if (button.hasAttribute('data-close-dialog')) {button.closest('dialog')?.close(); return;}
    if (button.dataset.reveal) {
      const field = mount.querySelector(`[name="${CSS.escape(button.dataset.reveal)}"]`);
      if (field) {const shown = field.type === 'password'; field.type = shown ? 'text' : 'password'; button.textContent = shown ? 'Ẩn' : 'Hiện';}
      return;
    }
    if (button.dataset.route) {
      event.preventDefault();
      toggleMenu(false);
      const nextRoute = button.dataset.route;
      const nextId = button.dataset.id || '';
      if (navigateClient(nextRoute, nextId)) {
        return;
      }
      emit({type:'portal_route', view:nextRoute, id:nextId});
      return;
    }
    if (button.dataset.action) {
      event.preventDefault();
      if (sending || (button.dataset.confirm && !await confirmAction(button.dataset.confirm))) return;
      const payload = {type:button.dataset.action, id:button.dataset.id || ''};
      if (button.dataset.action === 'admin_audit_export') {
        const panel = button.closest('.panel');
        const start = panel.querySelector('[data-date-from]').value;
        const end = panel.querySelector('[data-date-to]').value;
        if (start && end && start > end) {
          panel.querySelector('.audit-filter-error').hidden=false; return;
        }
        payload.filters = {query:panel.querySelector('[data-search]').value,
          action:panel.querySelector('[data-filter-column="action"]').value, from:start, to:end};
      }
      emit(payload);
    }
  };
  const submit = async event => {
    const form = event.target;
    if (!form.matches('form[data-form]')) return;
    event.preventDefault();
    if (sending || !form.reportValidity()) return;
    const fields = {};
    for (const field of form.querySelectorAll('input[name],select[name],textarea[name]')) {
      if (field.type !== 'file' && !field.disabled) fields[field.name] = field.type === 'checkbox' ? field.checked : field.value;
    }
    const formError = text => {
      const box = form.querySelector('.form-error');
      if (box) {box.textContent = text; box.hidden = false;}
    };
    if (fields.confirm_password !== undefined && fields.password !== fields.confirm_password) {
      formError('Hai mật khẩu chưa khớp.'); return;
    }
    if (form.dataset.confirm && !await confirmAction(form.dataset.confirm)) return;
    try {
      let upload = null;
      const file = form.querySelector('input[type="file"]')?.files?.[0];
      if (file) {
        if (file.size > 10 * 1024 * 1024) {formError('Tệp tối đa 10 MB.'); return;}
        if (!file.name.toLowerCase().endsWith('.pdf')) {formError('Vui lòng chọn tệp PDF.'); return;}
        upload = await new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve({name:file.name, data:String(reader.result).split(',')[1]});
          reader.onerror = () => reject(new Error('Không đọc được tệp đã chọn.'));
          reader.readAsDataURL(file);
        });
      }
      if (emit({type:form.dataset.form, fields, upload})) {
        form.querySelectorAll('input[type="password"]').forEach(field => {field.value = '';});
      }
    } catch (error) {formError(error.message || 'Không đọc được tệp. Vui lòng chọn lại.');}
  };
  const normalize = text => String(text).normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/đ/g, 'd').replace(/Đ/g, 'D').toLocaleLowerCase('vi');
  const filterFeedback = (resetPage=false) => {
    const list = mount.querySelector('.feedback-list');
    if (!list) return;
    const controls = list.querySelector('.feedback-pagination');
    const items = [...list.querySelectorAll('.feedback-item')];
    const search = normalize(list.querySelector('[data-search]')?.value || '');
    const status = list.querySelector('[data-feedback-status]')?.value || '';
    const consent = list.querySelector('[data-feedback-consent]')?.value || '';
    const matching = items.filter(item=>normalize(item.textContent).includes(search)
      && (!status || item.dataset.status===status) && (!consent || item.dataset.consent===consent));
    const matchingSet = new Set(matching);
    items.forEach(item=>{const found=matchingSet.has(item); item.dataset.filtered=String(!found); if(!found) item.hidden=true;});
    const selected = list.querySelector('.feedback-item.selected');
    const outsideFilter = !!selected && !matchingSet.has(selected);
    const detailBody = mount.querySelector('[data-feedback-detail-body]');
    const detailEmpty = mount.querySelector('[data-feedback-detail-empty]');
    if (detailBody) detailBody.hidden = outsideFilter;
    if (detailEmpty) detailEmpty.hidden = !outsideFilter;
    const size = Math.max(1, Number(controls?.querySelector('[data-feedback-size]')?.value || 10));
    const pageCount = Math.max(1, Math.ceil(matching.length / size));
    const page = resetPage ? 0 : Math.min(Number(list.dataset.page || 0), pageCount - 1);
    list.dataset.page = String(page);
    matching.forEach((item,index)=>{item.hidden=index<page*size || index>=(page+1)*size;});
    const count = controls?.querySelector('[data-feedback-count]');
    const label = controls?.querySelector('[data-feedback-page-label]');
    const previous = controls?.querySelector('[data-feedback-page="prev"]');
    const next = controls?.querySelector('[data-feedback-page="next"]');
    if (count) count.textContent = matching.length ? `${page*size+1}–${Math.min((page+1)*size,matching.length)} / ${matching.length} phản hồi` : '0 phản hồi';
    if (label) label.textContent = `Trang ${page+1} / ${pageCount}`;
    if (previous) previous.disabled = page===0;
    if (next) next.disabled = page>=pageCount-1;
    const pageControls = controls?.querySelector('.page-controls');
    if (pageControls) pageControls.hidden = matching.length<=size;
    let empty = list.querySelector('.feedback-filter-empty');
    if (items.length && !empty) {
      empty = document.createElement('div');
      empty.className = 'empty-state feedback-filter-empty';
      empty.textContent = 'Không có phản hồi phù hợp. Thử từ khóa khác.';
      list.appendChild(empty);
    }
    if (empty) empty.hidden = matching.length > 0;
  };
  const filter = (resetPage=false) => {
    mount.querySelectorAll('.data-table').forEach(table=>{
      const scope = table.closest('.panel') || table.parentElement;
      const search = normalize((scope.querySelector('[data-search]')?.value || '').trim());
      const filters = [...scope.querySelectorAll('[data-filter-column]')];
      const start = scope.querySelector('[data-date-from]')?.value || '';
      const end = scope.querySelector('[data-date-to]')?.value || '';
      const invalidRange = !!(start && end && start > end);
      const rangeError = scope.querySelector('.audit-filter-error');
      if (rangeError) rangeError.hidden = !invalidRange;
      const rows = [...table.querySelectorAll('tbody tr[data-search-row]')];
      const matching = rows.filter(row=>!invalidRange
        && normalize(row.dataset.searchText || row.textContent).includes(search)
        && (!start || row.dataset.day >= start) && (!end || !!row.dataset.day && row.dataset.day <= end)
        && !filters.some(select=>select.value && row.dataset[select.dataset.filterColumn] !== undefined && row.dataset[select.dataset.filterColumn] !== select.value));
      const matchingSet = new Set(matching);
      rows.forEach(row=>{const found=matchingSet.has(row); row.dataset.filtered=String(!found); if(!found) row.hidden=true;});
      const controls = table.parentElement.nextElementSibling;
      const pageSize = Math.max(1, Number(controls?.querySelector('[data-page-size]')?.value || table.dataset.pageSize || 25));
      const pageCount = Math.max(1, Math.ceil(matching.length / pageSize));
      const page = resetPage ? 0 : Math.min(Number(table.dataset.page || 0), pageCount - 1);
      table.dataset.page = String(page);
      table.dataset.pageSize = String(pageSize);
      matching.forEach((row,index)=>{row.hidden=index<page*pageSize || index>=(page+1)*pageSize;});
      const firstResult = matching.length ? page * pageSize + 1 : 0;
      const lastResult = Math.min((page+1)*pageSize, matching.length);
      const count = controls?.querySelector('[data-result-count]');
      const label = controls?.querySelector('[data-page-label]');
      const previous = controls?.querySelector('[data-page-turn="prev"]');
      const next = controls?.querySelector('[data-page-turn="next"]');
      if (count) count.textContent = matching.length ? `${firstResult}–${lastResult} / ${matching.length} kết quả` : '0 kết quả';
      if (label) label.textContent = `Trang ${page+1} / ${pageCount}`;
      if (previous) previous.disabled = page===0;
      if (next) next.disabled = page>=pageCount-1;
      const pageControls = controls?.querySelector('.page-controls');
      if (pageControls) pageControls.hidden = matching.length<=pageSize;
      let empty = table.querySelector('.empty-filter-row');
      if (rows.length && !empty) {
        empty = document.createElement('tr');
        empty.className = 'empty-filter-row';
        const td = document.createElement('td');
        td.colSpan = table.querySelectorAll('thead th').length;
        td.innerHTML = '<div class="empty-state">Không có kết quả phù hợp. Thử từ khóa hoặc bộ lọc khác.</div>';
        empty.appendChild(td);
        table.querySelector('tbody')?.appendChild(empty);
      }
      if (empty) empty.hidden = matching.length > 0;
    });
  };
  const changeFilter = event => {
    if (event.target.matches('[data-search],[data-filter-column],[data-page-size],[data-date-from],[data-date-to]')) filter(true);
    if (event.target.matches('[data-search],[data-feedback-status],[data-feedback-consent]')) filterFeedback(true);
    if (event.target.matches('.feedback-pagination [data-feedback-size]')) filterFeedback(true);
    if (event.target.matches(filterSelector)) saveFilters();
  };
  const keydown = event => {
    if (event.key === 'Escape' && !mount.querySelector('dialog[open]')) {
      if (mount.querySelector('.detail-drawer')) {
        if (!navigateClient('admin-users', '')) emit({type:'portal_route', view:'admin-users'});
      }
      else toggleMenu(false);
    }
    const drawer = mount.querySelector('.detail-drawer');
    if (event.key === 'Tab' && drawer && !mount.querySelector('dialog[open]')) {
      const fields = [...drawer.querySelectorAll('button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled)')];
      const active = parentElement.activeElement || document.activeElement;
      if (event.shiftKey && active === fields[0]) {event.preventDefault(); fields.at(-1)?.focus();}
      else if (!event.shiftKey && active === fields.at(-1)) {event.preventDefault(); fields[0]?.focus();}
    }
  };
  mount.addEventListener('click', click);
  mount.addEventListener('submit', submit);
  mount.addEventListener('input', changeFilter);
  mount.addEventListener('change', changeFilter);
  mount.addEventListener('keydown', keydown);
  filter();
  filterFeedback();
  mount.querySelector('.detail-drawer button')?.focus();
  if (data.download) {
    const blob = new Blob([data.download.content], {type:data.download.mime || 'text/plain;charset=utf-8'});
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url; link.download = data.download.name;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  if (data.poll_after) lifecycle.pollTimeout = setTimeout(() => {
    if (mount.__portalLifecycle !== lifecycle) return;
    lifecycle.pollTimeout = null;
    if (!sending && !mount.querySelector('dialog[open],form:focus-within')) emit({type:'portal_refresh', background:true});
  }, data.poll_after);
  const cleanup = () => {
    clearTimeout(lifecycle.timeout);
    clearTimeout(lifecycle.pollTimeout);
    clearTimeout(lifecycle.busyTimer);
    if (mount.__portalLifecycle === lifecycle) mount.__portalLifecycle = null;
    confirmDialog?.remove();
    mount.removeEventListener('click', click);
    mount.removeEventListener('submit', submit);
    mount.removeEventListener('input', changeFilter);
    mount.removeEventListener('change', changeFilter);
    mount.removeEventListener('keydown', keydown);
  };
  lifecycle.cleanup = cleanup;
  return cleanup;
}
