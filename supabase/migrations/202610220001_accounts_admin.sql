-- Run once in the Supabase SQL Editor. No demo users, passwords or chats.
begin;
create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null, full_name text not null default '',
  role text not null default 'user' check (role in ('user','admin')),
  status text not null default 'active' check (status in ('active','blocked')),
  email_verified boolean not null default false,
  created_at timestamptz not null default now()
);
create function public.is_active_user() returns boolean language sql stable security definer set search_path = '' as $$
  select exists(select 1 from public.profiles where id=auth.uid() and status='active' and email_verified);
$$;
create function public.is_administrator() returns boolean language sql stable security definer set search_path = '' as $$
  select exists(select 1 from public.profiles where id=auth.uid() and role='admin' and status='active' and email_verified);
$$;
create function public.sync_auth_profile() returns trigger language plpgsql security definer set search_path='' as $$
begin
  insert into public.profiles(id,email,full_name,email_verified)
  values(new.id,coalesce(new.email,''),left(coalesce(new.raw_user_meta_data->>'full_name',''),100),new.email_confirmed_at is not null)
  on conflict(id) do update set email=excluded.email,email_verified=excluded.email_verified;
  return new;
end;
$$;
create trigger sync_auth_profile after insert or update of email,email_confirmed_at on auth.users for each row execute function public.sync_auth_profile();
insert into public.profiles(id,email,full_name,email_verified)
select id,coalesce(email,''),left(coalesce(raw_user_meta_data->>'full_name',''),100),email_confirmed_at is not null from auth.users;

create table public.conversations (
  owner_id uuid not null references auth.users(id) on delete cascade,
  id text not null check(length(id) between 1 and 100),
  payload jsonb not null check(jsonb_typeof(payload)='object' and octet_length(payload::text)<5242880),
  created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  primary key(owner_id,id)
);
create index conversations_owner_updated on public.conversations(owner_id,updated_at desc);
create table public.feedback (
  id uuid primary key default gen_random_uuid(), owner_id uuid default auth.uid() references auth.users(id) on delete set null,
  rating text not null check(rating in ('up','down')),
  comment text not null default '' check(length(comment)<=2000),
  share_consent boolean not null default false,
  question text not null default '' check(length(question)<=4000),
  answer text not null default '' check(length(answer)<=12000),
  status text not null default 'pending' check(status in ('pending','reviewing','resolved')),
  admin_note text not null default '' check(length(admin_note)<=4000),
  created_at timestamptz not null default now(),
  check(share_consent or (question='' and answer=''))
);
create index feedback_status_created on public.feedback(status,created_at desc);
create table public.legal_documents (
  id uuid primary key default gen_random_uuid(), title text not null check(length(title) between 2 and 300),
  document_no text not null default '', issuer text not null default '', effective_from date,
  validity text not null default 'unverified' check(validity in ('unverified','CURRENT','PARTIALLY_EFFECTIVE','REPEALED','HISTORICAL')),
  source_url text not null default '', storage_path text not null, sha256 text not null,
  file_name text not null, size_bytes integer not null check(size_bytes between 1 and 10485760),
  page_count integer not null, preview_text text not null default '',
  status text not null default 'draft' check(status in ('draft','review','approved','indexed')),
  review_note text not null default '', reviewed_by uuid references auth.users(id), reviewed_at timestamptz,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create table public.admin_jobs (
  id uuid primary key default gen_random_uuid(), kind text not null check(kind in ('index','health','backup','restore')),
  document_id uuid references public.legal_documents(id),
  status text not null default 'pending' check(status in ('pending','running','succeeded','failed')),
  result text not null default '', payload jsonb not null default '{}',
  created_by uuid not null default auth.uid() references auth.users(id),
  created_at timestamptz not null default now(), started_at timestamptz, finished_at timestamptz
);
create table public.admin_audit (
  id uuid primary key default gen_random_uuid(), actor_id uuid references auth.users(id) on delete set null,
  action text not null, target_id text not null default '', details jsonb not null default '{}',
  created_at timestamptz not null default now()
);
create table public.app_settings (
  id text primary key check(id='general'), app_name text not null default 'VietLaborAI' check(length(app_name) between 2 and 60),
  workspace_name text not null default 'Quản trị VietLaborAI' check(length(workspace_name) between 2 and 80),
  updated_at timestamptz not null default now()
);
insert into public.app_settings(id) values('general');
create table public.admin_invitations (
  id uuid primary key default gen_random_uuid(), email text not null,
  invited_by uuid not null references auth.users(id), expires_at timestamptz not null default now()+interval '24 hours',
  accepted_at timestamptz, cancelled boolean not null default false, created_at timestamptz not null default now()
);
create table public.query_metrics (
  id uuid primary key default gen_random_uuid(), owner_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  duration_ms integer not null check(duration_ms between 0 and 3600000),
  success boolean not null, created_at timestamptz not null default now()
);
create index query_metrics_created on public.query_metrics(created_at desc);

alter table public.profiles enable row level security;
alter table public.conversations enable row level security;
alter table public.feedback enable row level security;
alter table public.legal_documents enable row level security;
alter table public.admin_jobs enable row level security;
alter table public.admin_audit enable row level security;
alter table public.app_settings enable row level security;
alter table public.admin_invitations enable row level security;
alter table public.query_metrics enable row level security;

revoke all on public.profiles,public.conversations,public.feedback,public.legal_documents,public.admin_jobs,public.admin_audit,public.app_settings,public.admin_invitations,public.query_metrics from anon,authenticated;
grant select on public.profiles,public.admin_audit,public.app_settings,public.admin_invitations to authenticated;
grant select,insert,update,delete on public.conversations to authenticated;
grant select,insert on public.feedback to authenticated;
grant update(status,admin_note) on public.feedback to authenticated;
grant select,insert,update on public.legal_documents,public.admin_jobs to authenticated;
grant update(app_name,workspace_name,updated_at) on public.app_settings to authenticated;
grant insert on public.query_metrics to authenticated;

create policy profile_read on public.profiles for select to authenticated using(id=auth.uid() or public.is_administrator());
-- Deliberately NO administrator override for conversations.
create policy chat_owner_only on public.conversations for all to authenticated using(owner_id=auth.uid() and public.is_active_user()) with check(owner_id=auth.uid() and public.is_active_user());
create policy feedback_read on public.feedback for select to authenticated using((owner_id=auth.uid() and public.is_active_user()) or public.is_administrator());
create policy feedback_submit on public.feedback for insert to authenticated with check(owner_id=auth.uid() and public.is_active_user() and status='pending' and admin_note='');
create policy feedback_review on public.feedback for update to authenticated using(public.is_administrator()) with check(public.is_administrator());
create policy documents_admin on public.legal_documents for all to authenticated using(public.is_administrator()) with check(public.is_administrator());
create policy jobs_admin on public.admin_jobs for all to authenticated using(public.is_administrator()) with check(public.is_administrator() and created_by=auth.uid());
create policy audit_admin on public.admin_audit for select to authenticated using(public.is_administrator());
create policy settings_admin_read on public.app_settings for select to authenticated using(public.is_administrator());
create policy settings_admin_write on public.app_settings for update to authenticated using(public.is_administrator()) with check(public.is_administrator());
create policy invitations_admin on public.admin_invitations for select to authenticated using(public.is_administrator());
create policy metrics_self on public.query_metrics for insert to authenticated with check(owner_id=auth.uid() and public.is_active_user());

create function public.save_my_conversations(changed jsonb,deleted text[]) returns void language plpgsql security invoker set search_path='' as $$
declare item jsonb;
begin
  if not public.is_active_user() or jsonb_typeof(changed)<>'array' or jsonb_array_length(changed)>5000 or cardinality(deleted)>5000 then raise exception 'not permitted'; end if;
  for item in select value from jsonb_array_elements(changed) loop
    if jsonb_typeof(item->'messages')<>'array' then raise exception 'invalid conversation'; end if;
    insert into public.conversations(owner_id,id,payload) values(auth.uid(),item->>'id',item)
    on conflict(owner_id,id) do update set payload=excluded.payload,updated_at=now();
  end loop;
  delete from public.conversations where owner_id=auth.uid() and id=any(deleted);
end;
$$;
create function public.update_my_profile(new_name text) returns void language plpgsql security definer set search_path='' as $$
begin
  if not public.is_active_user() or length(trim(new_name)) not between 2 and 100 then raise exception 'not permitted'; end if;
  update public.profiles set full_name=trim(new_name) where id=auth.uid();
end;
$$;
create function public.admin_update_account(target_id uuid,new_role text,new_status text,reason text) returns void language plpgsql security definer set search_path='' as $$
begin
  if not public.is_administrator() or new_role not in ('user','admin') or new_status not in ('active','blocked') or length(trim(reason)) not between 3 and 500 then raise exception 'not permitted'; end if;
  perform pg_advisory_xact_lock(20261022);
  if not public.is_administrator() then raise exception 'not permitted'; end if;
  if target_id=auth.uid() and (new_role<>'admin' or new_status<>'active') then raise exception 'cannot lock or demote yourself'; end if;
  if not exists(select 1 from public.profiles where id=target_id) then raise exception 'not found'; end if;
  update public.profiles set role=new_role,status=new_status where id=target_id;
  insert into public.admin_audit(actor_id,action,target_id,details) values(auth.uid(),'account.update',target_id::text,jsonb_build_object('role',new_role,'status',new_status,'reason',left(reason,500)));
end;
$$;
create function public.invite_administrator(target_email text) returns uuid language plpgsql security definer set search_path='' as $$
declare result uuid;
begin
  if not public.is_administrator() or length(target_email)>254 or target_email not like '%@%.%' then raise exception 'not permitted'; end if;
  insert into public.admin_invitations(email,invited_by) values(lower(trim(target_email)),auth.uid()) returning id into result;
  insert into public.admin_audit(actor_id,action,target_id) values(auth.uid(),'administrator.invite',result::text);
  return result;
end;
$$;
create function public.cancel_administrator_invitation(invitation_id uuid) returns void language plpgsql security definer set search_path='' as $$
begin
  if not public.is_administrator() then raise exception 'not permitted'; end if;
  update public.admin_invitations set cancelled=true where id=invitation_id and accepted_at is null;
end;
$$;
create function public.accept_administrator_invitation() returns void language plpgsql security definer set search_path='' as $$
declare invitation uuid;
begin
  if not public.is_active_user() then raise exception 'not permitted'; end if;
  select i.id into invitation from public.admin_invitations i join auth.users u on lower(u.email)=i.email
  where u.id=auth.uid() and u.email_confirmed_at is not null and not i.cancelled and i.accepted_at is null and i.expires_at>now() order by i.created_at desc limit 1 for update of i;
  if invitation is null then raise exception 'invitation not found'; end if;
  update public.profiles set role='admin' where id=auth.uid();
  update public.admin_invitations set accepted_at=now() where id=invitation;
  insert into public.admin_audit(actor_id,action,target_id) values(auth.uid(),'administrator.accept_invitation',invitation::text);
end;
$$;
create function public.audit_admin_change() returns trigger language plpgsql security definer set search_path='' as $$
begin
  insert into public.admin_audit(actor_id,action,target_id,details)
  values(auth.uid(),tg_table_name||'.'||lower(tg_op),new.id::text,jsonb_build_object('operation',tg_op));
  return new;
end;
$$;
create trigger audit_documents after insert or update on public.legal_documents for each row execute function public.audit_admin_change();
create trigger audit_jobs after insert or update on public.admin_jobs for each row execute function public.audit_admin_change();
create trigger audit_settings after update on public.app_settings for each row execute function public.audit_admin_change();
create trigger audit_feedback_review after update on public.feedback for each row execute function public.audit_admin_change();
create function public.claim_admin_job(job_id uuid) returns jsonb language plpgsql security invoker set search_path='' as $$
declare result public.admin_jobs;
begin
  update public.admin_jobs set status='running',started_at=now(),finished_at=null,result='' where id=job_id and created_by=auth.uid() and status in ('pending','failed') returning * into result;
  if result.id is null then raise exception 'job already claimed or inaccessible'; end if;
  return to_jsonb(result);
end;
$$;
create function public.restore_business_metadata(snapshot jsonb) returns void language plpgsql security definer set search_path='' as $$
declare item jsonb;
begin
  if not public.is_administrator() or snapshot->>'format'<>'vietlabor-business-v1' or jsonb_typeof(snapshot->'documents')<>'array' then raise exception 'not permitted'; end if;
  for item in select value from jsonb_array_elements(snapshot->'documents') loop
    -- Never restore storage paths, source files, access rights, or private chats.
    update public.legal_documents set title=item->>'title',document_no=coalesce(item->>'document_no',''),issuer=coalesce(item->>'issuer',''),
      effective_from=(item->>'effective_from')::date,validity='unverified',source_url=coalesce(item->>'source_url',''),
      status='review',reviewed_by=null,reviewed_at=null,updated_at=now()
    where id=(item->>'id')::uuid and sha256=item->>'sha256';
  end loop;
  if jsonb_array_length(snapshot->'settings')=1 then
    item=snapshot->'settings'->0;
    update public.app_settings set app_name=item->>'app_name',workspace_name=item->>'workspace_name',updated_at=now() where id='general';
  end if;
  insert into public.admin_audit(actor_id,action) values(auth.uid(),'business_metadata.restore');
end;
$$;
revoke all on function public.restore_business_metadata(jsonb) from public,anon;
grant execute on function public.restore_business_metadata(jsonb) to authenticated;

create function public.admin_dashboard() returns jsonb language plpgsql stable security definer set search_path='' as $$
declare result jsonb;
begin
  if not public.is_administrator() then raise exception 'not permitted'; end if;
  select jsonb_build_object(
    'users',(select count(*) from public.profiles),
    'active_users',(select count(*) from public.profiles where status='active'),
    'queries',(select count(*) from public.query_metrics where created_at>now()-interval '7 days'),
    'pending_feedback',(select count(*) from public.feedback where status<>'resolved'),
    'documents',(select count(*) from public.legal_documents),
    'pending_documents',(select count(*) from public.legal_documents where status in ('draft','review')),
    'median_ms',(select percentile_cont(0.5) within group(order by duration_ms) from public.query_metrics where created_at>now()-interval '7 days'),
    'p95_ms',(select percentile_cont(0.95) within group(order by duration_ms) from public.query_metrics where created_at>now()-interval '7 days'),
    'daily',(select coalesce(jsonb_agg(x),'[]') from (select d::date as day,count(m.id) as count from generate_series(current_date-6,current_date,interval '1 day') d left join public.query_metrics m on m.created_at>=d and m.created_at<d+interval '1 day' group by d order by d) x)
  ) into result;
  return result;
end;
$$;

insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types)
values('legal-documents','legal-documents',false,10485760,array['application/pdf']) on conflict(id) do nothing;
create policy legal_files_read on storage.objects for select to authenticated using(bucket_id='legal-documents' and public.is_administrator());
create policy legal_files_insert on storage.objects for insert to authenticated with check(bucket_id='legal-documents' and public.is_administrator());

-- Revoke the default PUBLIC function execution grant, including helpers.
revoke all on function public.is_active_user(),public.is_administrator(),public.sync_auth_profile(),public.save_my_conversations(jsonb,text[]),public.update_my_profile(text),public.admin_update_account(uuid,text,text,text),public.invite_administrator(text),public.cancel_administrator_invitation(uuid),public.accept_administrator_invitation(),public.audit_admin_change(),public.claim_admin_job(uuid),public.admin_dashboard() from public,anon;
grant execute on function public.is_active_user(),public.is_administrator(),public.save_my_conversations(jsonb,text[]),public.update_my_profile(text),public.admin_update_account(uuid,text,text,text),public.invite_administrator(text),public.cancel_administrator_invitation(uuid),public.accept_administrator_invitation(),public.claim_admin_job(uuid),public.admin_dashboard() to authenticated;
commit;
