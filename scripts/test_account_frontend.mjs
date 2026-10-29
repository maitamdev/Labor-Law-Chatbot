// DOM interaction tests, no browser or external account is used.
import {JSDOM} from '../storage/test_tools/node_modules/jsdom/lib/api.js';
import {readFile} from 'node:fs/promises';
import assert from 'node:assert/strict';

const fixtures=JSON.parse(await readFile(new URL('../storage/test_tools/ui-fixtures.json',import.meta.url),'utf8'));
const source=await readFile(new URL('../ui/frontend/approved.js',import.meta.url),'utf8');
const portalSource=await readFile(new URL('../ui/frontend/portal.js',import.meta.url),'utf8');
const approved=(await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'))).default;
const portal=(await import('data:text/javascript;base64,'+Buffer.from(portalSource).toString('base64'))).default;
let passed=0;
function setup(markup,widget=approved,messages=[]) {
  const dom=new JSDOM('<div id="host"><div class="portal-mount"></div></div>',{url:'http://localhost/',pretendToBeVisual:true});
  const win=dom.window;
  win.HTMLDialogElement.prototype.showModal=function(){this.open=true;};
  win.HTMLDialogElement.prototype.close=function(){this.open=false;};
  win.HTMLElement.prototype.scrollTo=function(){};
  win.confirm=()=>true;
  globalThis.document=win.document;globalThis.window=win;globalThis.sessionStorage=win.sessionStorage;
  globalThis.NodeFilter=win.NodeFilter;
  globalThis.CSS={escape:s=>String(s).replace(/[^a-zA-Z0-9_-]/g,'_')};
  const calls=[];
  const cleanup=widget({parentElement:win.document.querySelector('#host'),data:{markup,messages,conversation_id:'test'},setTriggerValue:(name,value)=>calls.push(value)});
  return {win,doc:win.document,calls,dispose:cleanup,cleanup:()=>{cleanup();dom.window.close();}};
}
function test(name,fn){fn();passed++;console.log('PASS '+name);}
function submit(ctx,form){form.dispatchEvent(new ctx.win.Event('submit',{bubbles:true,cancelable:true}));}

test('AI appears first; login opens only on click',()=>{
  const ctx=setup(fixtures.home);assert.equal(ctx.doc.querySelector('.auth-dialog').open,false);
  ctx.doc.querySelector('[data-auth-open=login]').click();assert.equal(ctx.doc.querySelector('.auth-dialog').open,true);ctx.cleanup();
});
test('forgot-password requires email but no hidden password',()=>{
  const ctx=setup(fixtures.home);ctx.doc.querySelector('[data-auth-open=login]').click();ctx.doc.querySelector('[data-auth-mode=forgot]').click();
  const form=ctx.doc.querySelector('.auth-form');assert.equal(form.elements.password.disabled,true);form.elements.username.value='user@example.com';
  submit(ctx,form);assert.equal(ctx.calls[0].mode,'forgot');assert.equal(ctx.calls[0].username,'user@example.com');ctx.cleanup();
});
test('registration rejects mismatching passwords without sending credentials',()=>{
  const ctx=setup(fixtures.home);ctx.doc.querySelector('[data-auth-open=register]').click();const form=ctx.doc.querySelector('.auth-form');
  form.elements.username.value='user@example.com';form.elements.full_name.value='Test User';form.elements.password.value='password-one';form.elements.confirm_password.value='password-two';submit(ctx,form);
  assert.equal(ctx.calls.length,0);assert.equal(ctx.doc.querySelector('.auth-error').hidden,false);ctx.cleanup();
});
test('registration sends email/name and clears password fields',()=>{
  const ctx=setup(fixtures.home);ctx.doc.querySelector('[data-auth-open=register]').click();const form=ctx.doc.querySelector('.auth-form');
  form.elements.username.value='user@example.com';form.elements.full_name.value='Test User';form.elements.password.value='password-one';form.elements.confirm_password.value='password-one';submit(ctx,form);
  assert.equal(ctx.calls[0].mode,'register');assert.equal(ctx.calls[0].full_name,'Test User');assert.equal(form.elements.password.value,'');ctx.cleanup();
});
test('answer report consent starts unchecked and sends no chat text',()=>{
  const ctx=setup(fixtures.chat,approved,[{id:'q1',role:'user',content:'Private question'},{id:'a1',role:'assistant',content:'Private answer'}]);
  ctx.doc.querySelector('[data-feedback=down]').click();const form=ctx.doc.querySelector('.feedback-form');assert.equal(form.elements.share_consent.checked,false);submit(ctx,form);
  assert.equal(ctx.calls[0].share_consent,false);assert.equal(ctx.calls[0].id,'a1');assert.equal(ctx.calls[0].question,undefined);ctx.cleanup();
});
test('answer report only sends consent flag when explicitly checked',()=>{
  const ctx=setup(fixtures.chat,approved,[{id:'q1',role:'user',content:'Private question'},{id:'a1',role:'assistant',content:'Private answer'}]);
  ctx.doc.querySelector('[data-feedback=down]').click();const form=ctx.doc.querySelector('.feedback-form');form.elements.share_consent.checked=true;submit(ctx,form);assert.equal(ctx.calls[0].share_consent,true);ctx.cleanup();
});
test('password change submits current/new password without persisting fields',()=>{
  const ctx=setup(fixtures['account-password'],portal);const form=ctx.doc.querySelector('form');
  form.elements.current_password.value='old-test-password';form.elements.password.value='new-test-password';form.elements.confirm_password.value='new-test-password';submit(ctx,form);
  assert.equal(ctx.calls[0].type,'account_change_password');assert.equal(ctx.calls[0].fields.current_password,'old-test-password');assert.equal(form.elements.password.value,'');ctx.cleanup();
});
test('admin user search hides unmatched rows',()=>{
  const ctx=setup(fixtures['admin-users'],portal);const input=ctx.doc.querySelector('[data-search]');input.value='no such account';input.dispatchEvent(new ctx.win.Event('input',{bubbles:true}));assert.equal(ctx.doc.querySelector('tr[data-search-row]').hidden,true);ctx.cleanup();
});
test('a stale admin timeout cannot cover a newly rendered page',()=>{
  const dom=new JSDOM('<div id="host"><div class="portal-mount"></div></div>',{url:'http://localhost/',pretendToBeVisual:true});
  const win=dom.window;globalThis.document=win.document;globalThis.window=win;globalThis.Element=win.Element;globalThis.CSS={escape:s=>String(s).replace(/[^a-zA-Z0-9_-]/g,'_')};
  const parentElement=win.document.querySelector('#host');
  const originalSetTimeout=globalThis.setTimeout, originalClearTimeout=globalThis.clearTimeout;
  const timers=new Map();let nextTimer=0;let staleCallback;
  globalThis.setTimeout=(callback,delay,...args)=>{const id=++nextTimer;timers.set(id,{callback,delay,args});if(delay===45000)staleCallback=()=>callback(...args);return id;};
  globalThis.clearTimeout=id=>timers.delete(id);
  try {
    const render=data=>portal({parentElement,data:{markup:data},setTriggerValue:()=>{}});
    render(fixtures['admin-users']);
    win.document.querySelector('.admin-nav[data-route]').click();
    assert.equal(win.document.querySelector('.portal-mount').getAttribute('aria-busy'),'true');
    render(fixtures['admin-documents']);
    staleCallback(); // Simulate a timeout already queued when Streamlit replaces the view.
    assert.equal(win.document.querySelector('.portal-mount').getAttribute('aria-busy'),'false');
    assert.equal(win.document.querySelector('.portal-client-error'),null);
    const progress=win.document.querySelector('.portal-progress');if(progress)assert.equal(progress.hidden,true);
  } finally {
    globalThis.setTimeout=originalSetTimeout;globalThis.clearTimeout=originalClearTimeout;
    dom.window.close();
  }
});
test('late navigation renders cannot replace the latest selected view',()=>{
  const ctx=setup(fixtures.home);
  const parentElement=ctx.doc.querySelector('#host');
  let dispose=ctx.dispose;
  // Keep one mount, just as Streamlit does while replacing component data.
  const rerender=(view,ack)=>{
    dispose();
    const template=ctx.doc.createElement('template');
    template.innerHTML=fixtures.home;
    template.content.querySelector('.vl-app').dataset.view=view;
    template.content.querySelectorAll('.nav-item').forEach(button=>{
      const active=button.dataset.view===view;
      button.classList.toggle('active',active);
      if(active)button.setAttribute('aria-current','page');else button.removeAttribute('aria-current');
    });
    const markup=template.innerHTML;
    dispose=approved({parentElement,data:{markup,messages:[],conversation_id:'test',navigation_ack:ack},
      setTriggerValue:(_name,value)=>ctx.calls.push(value)});
  };
  ctx.doc.querySelector('.nav-item[data-view="documents"]').click();
  const first=ctx.calls.at(-1);
  ctx.doc.querySelector('.nav-item[data-view="faq"]').click();
  const latest=ctx.calls.at(-1);
  rerender('documents',first.action_id);
  assert.equal(ctx.doc.querySelector('.vl-app').dataset.view,'faq');
  assert.equal(ctx.doc.querySelector('.nav-item.active').dataset.view,'faq');
  assert.equal(ctx.calls.at(-1).action_id,latest.action_id);
  const callCount=ctx.calls.length;
  rerender('documents',first.action_id);
  assert.equal(ctx.calls.length,callCount,'Do not resend for the same stale acknowledgement');
  rerender('faq',latest.action_id);
  assert.equal(ctx.doc.querySelector('.vl-mount').dataset.pendingNavigationId,undefined);
  ctx.doc.querySelector('.nav-item[data-view="topics"]').click();
  ctx.doc.querySelector('[data-event="new_chat"]').click();
  assert.equal(ctx.doc.querySelector('.vl-mount').dataset.pendingNavigationId,undefined);
  rerender('chat',latest.action_id);
  assert.equal(ctx.doc.querySelector('.vl-app').dataset.view,'chat');
  dispose();ctx.cleanup();
});
console.log(`${passed} frontend interaction checks passed.`);
