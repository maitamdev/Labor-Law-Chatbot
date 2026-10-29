// Actual PostgreSQL RLS/PLpgSQL tests in an ephemeral PGlite database.
// Install dev dependency: npm install --prefix storage/test_tools @electric-sql/pglite
import {PGlite} from '../storage/test_tools/node_modules/@electric-sql/pglite/dist/index.js';
import {readFile} from 'node:fs/promises';
import assert from 'node:assert/strict';

const db=new PGlite();
await db.exec(`create role anon; create role authenticated;
create schema auth; create schema storage;
create table auth.users(id uuid primary key,email text,email_confirmed_at timestamptz,raw_user_meta_data jsonb default '{}');
create function auth.uid() returns uuid language sql stable as $$select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid$$;
grant usage on schema auth to authenticated,anon;grant execute on function auth.uid() to authenticated,anon;
create table storage.buckets(id text primary key,name text,public boolean,file_size_limit bigint,allowed_mime_types text[]);
create table storage.objects(id uuid primary key default gen_random_uuid(),bucket_id text,name text);
alter table storage.objects enable row level security;
grant usage on schema storage to authenticated;grant select,insert,delete on storage.objects to authenticated;
`);
await db.exec(await readFile(new URL('../supabase/migrations/202610220001_accounts_admin.sql',import.meta.url),'utf8'));
await db.exec(await readFile(new URL('../supabase/migrations/202610220002_admin_workflows.sql',import.meta.url),'utf8'));
const ids={alice:'00000000-0000-0000-0000-000000000001',bob:'00000000-0000-0000-0000-000000000002',admin:'00000000-0000-0000-0000-000000000003'};
for(const [name,id] of Object.entries(ids)) await db.query(`insert into auth.users(id,email,email_confirmed_at,raw_user_meta_data) values($1,$2,now(),$3)`,[id,name+'@example.com',JSON.stringify({full_name:name,role:'admin'})]);
await db.query(`update public.profiles set role='admin' where id=$1`,[ids.admin]);
async function as(name){await db.exec('reset role');await db.query(`select set_config('request.jwt.claim.sub',$1,false)`,[ids[name]||'']);await db.exec(`set role ${name==='anon'?'anon':'authenticated'}`);}
let passed=0;
async function test(name,fn){await fn();passed++;console.log('PASS '+name);}
async function denied(sql,params=[]){await assert.rejects(()=>db.query(sql,params));}

await test('signup metadata cannot grant admin',async()=>{await as('alice'); const {rows}=await db.query(`select role from profiles where id=$1`,[ids.alice]);assert.equal(rows[0].role,'user');});
await test('user stores and reads own private chat',async()=>{await as('alice');await db.query(`select save_my_conversations($1::jsonb,$2::text[])`,[JSON.stringify([{id:'chat-a',title:'PRIVATE TITLE',messages:[{role:'user',content:'PRIVATE QUESTION'}]}]),[]]);assert.equal((await db.query('select * from conversations')).rows.length,1);});
await test('other user cannot read or overwrite private chat',async()=>{await as('bob');assert.equal((await db.query('select * from conversations')).rows.length,0);await denied(`insert into conversations(owner_id,id,payload) values($1,'chat-a','{}')`,[ids.alice]);});
await test('admin also cannot read another persons chat',async()=>{await as('admin');assert.equal((await db.query('select * from conversations')).rows.length,0);});
await test('anon cannot read or execute privileged RPC',async()=>{await as('anon');await denied('select * from conversations');await denied('select admin_dashboard()');});
await test('user cannot escalate own profile or run admin RPC',async()=>{await as('alice');await denied(`update profiles set role='admin' where id=$1`,[ids.alice]);await denied('select admin_dashboard()');await denied(`select admin_update_account($1,'admin','active','promote')`,[ids.alice]);});
await test('feedback without consent cannot carry private text',async()=>{await as('alice');await denied(`insert into feedback(rating,question) values('down','PRIVATE QUESTION')`);await db.query(`insert into feedback(rating,comment) values('down','Needs source')`);});
await test('user cannot set admin notes or resolve own feedback',async()=>{await as('alice');await db.query(`update feedback set admin_note='fake',status='resolved'`);const {rows}=await db.query('select admin_note,status from feedback');assert.equal(rows[0].admin_note,'');assert.equal(rows[0].status,'pending');});
await test('admin sees feedback but no private chat text',async()=>{await as('admin');const {rows}=await db.query('select * from feedback');assert.equal(rows.length,1);assert.equal(rows[0].question,'');assert.equal(rows[0].answer,'');});
await test('user cannot access private legal storage',async()=>{await as('alice');await denied(`insert into storage.objects(bucket_id,name) values('legal-documents','bad.pdf')`);});
await test('admin can lock user and audit event is recorded',async()=>{await as('admin');await db.query(`select admin_update_account($1,'user','blocked','Access suspended')`,[ids.alice]);assert.ok((await db.query('select * from admin_audit')).rows.length>0);});
await test('blocked user token cannot access own chat or submit feedback',async()=>{await as('alice');assert.equal((await db.query('select * from conversations')).rows.length,0);await denied(`select save_my_conversations('[]'::jsonb,array['chat-a'])`);await denied(`insert into feedback(rating) values('up')`);});
await test('admin cannot self lock or demote',async()=>{await as('admin');await denied(`select admin_update_account($1,'user','active','demote self')`,[ids.admin]);await denied(`select admin_update_account($1,'admin','blocked','lock self')`,[ids.admin]);});
await test('admin dashboard aggregates without granting chat access',async()=>{await as('admin');const {rows}=await db.query('select admin_dashboard() as dashboard');assert.equal(rows[0].dashboard.users,3);assert.equal((await db.query('select * from conversations')).rows.length,0);});
await test('invitation only applies to verified matching email',async()=>{await as('admin');await db.query(`select invite_administrator('alice@example.com')`);await as('bob');await denied('select accept_administrator_invitation()');await as('admin');await db.query(`select admin_update_account($1,'user','active','Reinstate user')`,[ids.alice]);await as('alice');await db.query('select accept_administrator_invitation()');assert.equal((await db.query(`select role from profiles where id=$1`,[ids.alice])).rows[0].role,'admin');});
await test('admin jobs use a single active lease and reject stale workers',async()=>{
  await as('admin');
  const {rows}=await db.query(`insert into admin_jobs(kind) values('health') returning id`);
  const job=rows[0].id, lease='00000000-0000-0000-0000-0000000000aa';
  const claimed=await db.query('select claim_admin_job($1,$2) as job',[job,lease]);
  assert.equal(claimed.rows[0].job.lease_token,lease);
  await db.query('select assert_admin_job_lease($1,$2)',[job,lease]);
  await db.query('select touch_admin_job($1,$2)',[job,lease]);
  await denied('select claim_admin_job($1,$2)',[job,'00000000-0000-0000-0000-0000000000bb']);
  await db.query('select finish_admin_job($1,$2,true,$3)',[job,lease,'completed']);
  await denied('select finish_admin_job($1,$2,true,$3)',[job,lease,'stale completion']);
  const saved=await db.query('select status,result from admin_jobs where id=$1',[job]);
  assert.equal(saved.rows[0].status,'succeeded');
  assert.equal(saved.rows[0].result,'completed');
});
await test('document approval checks current version and queues indexing atomically',async()=>{
  await as('admin');
  const {rows}=await db.query(`insert into legal_documents(title,validity,effective_from,storage_path,sha256,file_name,size_bytes,page_count,status)
    values('Reviewed law','CURRENT','2026-01-01','law.pdf','hash','law.pdf',1,1,'review') returning id,updated_at`);
  await denied('select approve_legal_document($1,$2)',[rows[0].id,'2000-01-01T00:00:00Z']);
  const approved=await db.query('select approve_legal_document($1,$2) as job_id',[rows[0].id,rows[0].updated_at]);
  assert.ok(approved.rows[0].job_id);
  assert.equal((await db.query('select status from legal_documents where id=$1',[rows[0].id])).rows[0].status,'approved');
  assert.equal((await db.query(`select count(*)::int as total from admin_jobs where document_id=$1 and kind='index'`,[rows[0].id])).rows[0].total,1);
});
await test('administrator invitation cancellation is audited and one-way',async()=>{
  await as('admin');
  await db.query(`select invite_administrator('cancel-me@example.com')`);
  const invitation=(await db.query(`select id from admin_invitations where email='cancel-me@example.com'`)).rows[0].id;
  await as('bob');
  await denied('select cancel_administrator_invitation($1)',[invitation]);
  await as('admin');
  await db.query('select cancel_administrator_invitation($1)',[invitation]);
  assert.equal((await db.query('select cancelled from admin_invitations where id=$1',[invitation])).rows[0].cancelled,true);
  await denied('select cancel_administrator_invitation($1)',[invitation]);
  assert.ok((await db.query(`select * from admin_audit where action='administrator.cancel_invitation'`)).rows.length>0);
});
await test('only administrators can delete private legal files',async()=>{
  await as('admin');
  const {rows}=await db.query(`insert into storage.objects(bucket_id,name) values('legal-documents','law.pdf') returning id`);
  await as('bob');
  assert.equal((await db.query('delete from storage.objects where id=$1 returning id',[rows[0].id])).rows.length,0);
  await as('admin');
  assert.equal((await db.query('select id from storage.objects where id=$1',[rows[0].id])).rows.length,1);
  await db.query('delete from storage.objects where id=$1',[rows[0].id]);
});
await test('user cannot restore arbitrary business data',async()=>{await as('bob');await denied(`select restore_business_metadata('{"format":"vietlabor-business-v1","documents":[]}'::jsonb)`);});
await db.exec('reset role');
await db.exec(await readFile(new URL('../supabase/migrations/202610240003_privacy_permissions.sql',import.meta.url),'utf8'));
// Seed the designated permission as database owner, never through a user RPC.
await db.query(`insert into admin_capabilities(admin_id,manage_administrators) values($1,true)`,[ids.admin]);
await test('ordinary admin cannot promote, lock an admin, invite or assign capabilities',async()=>{
  await as('alice');
  assert.equal((await db.query('select my_admin_permissions() as p')).rows[0].p.manage_admins,false);
  await denied(`select admin_update_account($1,'admin','active','Try promoting')`,[ids.bob]);
  await denied(`select admin_update_account($1,'admin','blocked','Try locking admin')`,[ids.admin]);
  await denied(`select invite_administrator('untrusted@example.com')`);
  await denied(`insert into admin_capabilities(admin_id,manage_administrators) values($1,true)`,[ids.alice]);
  assert.equal((await db.query('select * from admin_invitations')).rows.length,0);
});
await test('ordinary admin can moderate user status but not read chats',async()=>{
  await as('alice');
  await db.query(`select admin_update_account($1,'user','blocked','Moderation')`,[ids.bob]);
  await db.query(`select admin_update_account($1,'user','active','Reinstate')`,[ids.bob]);
  assert.equal((await db.query('select * from conversations where owner_id<>$1',[ids.alice])).rows.length,0);
});
await test('primary admin can promote but primary capability is not inherited',async()=>{
  await as('admin');
  await db.query(`select admin_update_account($1,'admin','active','Grant admin')`,[ids.bob]);
  await as('bob');assert.equal((await db.query('select my_admin_permissions() as p')).rows[0].p.manage_admins,false);
  await as('admin');await db.query(`select admin_update_account($1,'user','active','Return to user')`,[ids.bob]);
});
let sharedFeedback;
await test('users cannot read internal notes; admin cannot query feedback owner',async()=>{
  await as('bob');
  await db.query(`insert into feedback(rating,comment,share_consent,question,answer) values('down','Shared feedback',true,'MY PRIVATE QUESTION','MY SHARED ANSWER')`);
  const own=(await db.query('select * from my_feedback()')).rows;
  sharedFeedback=own.find(row=>row.comment==='Shared feedback').id;
  assert.equal(own[0].admin_note,undefined);
  assert.equal((await db.query('select id,admin_note from feedback')).rows.length,0);
  await as('admin');await denied('select owner_id from feedback');
  assert.equal((await db.query('select question from feedback where id=$1',[sharedFeedback])).rows[0].question,'MY PRIVATE QUESTION');
  await db.query('select review_feedback_safe($1,$2,$3,0)',[sharedFeedback,'reviewing','Internal review note']);
});
await test('another user and admin cannot withdraw or delete someone elses feedback',async()=>{
  for(const user of ['alice','admin']) {
    await as(user);await denied('select withdraw_my_feedback_consent($1)',[sharedFeedback]);
    await denied('select delete_my_feedback($1)',[sharedFeedback]);
  }
});
await test('owner can withdraw shared text; stale admin edits cannot restore it',async()=>{
  await as('bob');await db.query('select withdraw_my_feedback_consent($1)',[sharedFeedback]);
  await as('admin');
  const row=(await db.query('select share_consent,question,answer,admin_note,privacy_version from feedback where id=$1',[sharedFeedback])).rows[0];
  assert.deepEqual(row,{share_consent:false,question:'',answer:'',admin_note:'',privacy_version:1});
  await denied('select review_feedback_safe($1,$2,$3,0)',[sharedFeedback,'resolved','Old copied content']);
  await denied(`update feedback set admin_note='bypass' where id=$1`,[sharedFeedback]);
  await db.query('select review_feedback_safe($1,$2,$3,1)',[sharedFeedback,'resolved','Reviewed without shared content']);
  assert.equal((await db.query(`select * from admin_audit where actor_id=$1 and target_id=$2`,[ids.bob,sharedFeedback])).rows.length,0);
});
await test('only owner can delete a feedback record',async()=>{
  await as('bob');await db.query('select delete_my_feedback($1)',[sharedFeedback]);
  assert.equal((await db.query('select * from my_feedback()')).rows.length,0);
  await as('admin');assert.equal((await db.query('select id from feedback where id=$1',[sharedFeedback])).rows.length,0);
});
await test('deleting own history never deletes another accounts chat',async()=>{
  await as('bob');await db.query(`select save_my_conversations('[{"id":"bob-private","messages":[]}]'::jsonb,'{}'::text[],0)`);
  await as('admin');await db.query('select delete_my_conversations()');
  await as('bob');assert.equal((await db.query('select * from conversations')).rows.length,1);
  await db.query('select delete_my_conversations()');assert.equal((await db.query('select * from conversations')).rows.length,0);
});
await test('stale browser cannot resurrect erased history',async()=>{
  await as('bob');
  assert.equal(Number((await db.query('select my_history_version() as v')).rows[0].v),1);
  await denied(`select save_my_conversations('[{"id":"old-copy","messages":[]}]'::jsonb,'{}'::text[],0)`);
  await db.query(`select save_my_conversations('[{"id":"new-chat","messages":[]}]'::jsonb,'{}'::text[],1)`);
  assert.equal((await db.query('select * from conversations')).rows.length,1);
});
await test('guest cannot use privacy or administrator permission RPCs',async()=>{
  await as('anon');for(const sql of ['select my_admin_permissions()','select my_feedback()','select delete_my_conversations()']) await denied(sql);
});
console.log(`${passed} PostgreSQL security checks passed.`);
await db.close();
