-- Apply after 001 and 002. No private conversations are read or exported here.
begin;

create table if not exists public.admin_capabilities (
  admin_id uuid primary key references auth.users(id) on delete cascade,
  manage_administrators boolean not null default false
);
alter table public.admin_capabilities enable row level security;
revoke all on public.admin_capabilities from public,anon,authenticated;
-- The project owner requested this verified account as the primary admin.
-- No account is created or promoted by this migration.
insert into public.admin_capabilities(admin_id,manage_administrators)
select id,true from public.profiles
where lower(email)='maitamit062005@gmail.com' and role='admin'
  and status='active' and email_verified
on conflict(admin_id) do update set manage_administrators=true;

create or replace function public.is_security_administrator()
returns boolean language sql stable security definer set search_path='' as $$
  select public.is_administrator() and exists(
    select 1 from public.admin_capabilities
    where admin_id=auth.uid() and manage_administrators
  );
$$;
create or replace function public.my_admin_permissions()
returns jsonb language plpgsql stable security definer set search_path='' as $$
begin
  if not public.is_administrator() then raise exception 'not permitted'; end if;
  return jsonb_build_object('manage_admins',public.is_security_administrator());
end;
$$;

create or replace function public.admin_update_account(target_id uuid,new_role text,new_status text,reason text)
returns void language plpgsql security definer set search_path='' as $$
declare target public.profiles;
begin
  if not public.is_administrator() or new_role is null or new_status is null
     or new_role not in ('user','admin') or new_status not in ('active','blocked')
     or reason is null or length(trim(reason)) not between 3 and 500 then
    raise exception 'not permitted';
  end if;
  perform pg_advisory_xact_lock(20261022);
  if not public.is_administrator() then raise exception 'not permitted'; end if;
  select * into target from public.profiles where id=target_id for update;
  if not found then raise exception 'not found'; end if;
  if (target.role='admin' or new_role='admin') and not public.is_security_administrator() then
    raise exception 'security administrator required';
  end if;
  if target_id=auth.uid() and (new_role<>'admin' or new_status<>'active') then
    raise exception 'cannot lock or demote yourself';
  end if;
  if exists(select 1 from public.admin_capabilities where admin_id=target_id and manage_administrators)
     and target_id<>auth.uid() then raise exception 'protected administrator'; end if;
  update public.profiles set role=new_role,status=new_status where id=target_id;
  insert into public.admin_audit(actor_id,action,target_id,details)
  values(auth.uid(),'account.update',target_id::text,
    jsonb_build_object('role',new_role,'status',new_status,'reason',trim(reason)));
end;
$$;

create or replace function public.invite_administrator(target_email text)
returns uuid language plpgsql security definer set search_path='' as $$
declare result uuid;
begin
  if not public.is_security_administrator() or target_email is null
     or length(target_email)>254 or target_email not like '%@%.%' then raise exception 'not permitted'; end if;
  insert into public.admin_invitations(email,invited_by)
  values(lower(trim(target_email)),auth.uid()) returning id into result;
  insert into public.admin_audit(actor_id,action,target_id)
  values(auth.uid(),'administrator.invite',result::text);
  return result;
end;
$$;
create or replace function public.cancel_administrator_invitation(invitation_id uuid)
returns void language plpgsql security definer set search_path='' as $$
declare cancelled_id uuid;
begin
  if not public.is_security_administrator() then raise exception 'not permitted'; end if;
  update public.admin_invitations set cancelled=true
  where id=invitation_id and accepted_at is null and not cancelled and expires_at>now()
  returning id into cancelled_id;
  if cancelled_id is null then raise exception 'invitation unavailable'; end if;
  insert into public.admin_audit(actor_id,action,target_id)
  values(auth.uid(),'administrator.cancel_invitation',cancelled_id::text);
end;
$$;
create or replace function public.accept_administrator_invitation()
returns void language plpgsql security definer set search_path='' as $$
declare invitation uuid;
begin
  if not public.is_active_user() then raise exception 'not permitted'; end if;
  select i.id into invitation from public.admin_invitations i
  join auth.users u on lower(u.email)=i.email
  join public.admin_capabilities c on c.admin_id=i.invited_by and c.manage_administrators
  join public.profiles p on p.id=i.invited_by and p.role='admin' and p.status='active' and p.email_verified
  where u.id=auth.uid() and u.email_confirmed_at is not null and not i.cancelled
    and i.accepted_at is null and i.expires_at>now()
  order by i.created_at desc limit 1 for update of i;
  if invitation is null then raise exception 'invitation not found'; end if;
  update public.profiles set role='admin' where id=auth.uid();
  update public.admin_invitations set accepted_at=now() where id=invitation;
  insert into public.admin_audit(actor_id,action,target_id)
  values(auth.uid(),'administrator.accept_invitation',invitation::text);
end;
$$;
drop policy if exists invitations_admin on public.admin_invitations;
create policy invitations_admin on public.admin_invitations for select to authenticated
using(public.is_security_administrator());

-- Admins can review a submitted excerpt, but cannot query its owner_id.
-- Users read their own submissions through a dedicated RPC without internal notes.
alter table public.feedback add column if not exists privacy_version integer not null default 0;
drop policy if exists feedback_submit on public.feedback;
create policy feedback_submit on public.feedback for insert to authenticated
with check(owner_id=auth.uid() and public.is_active_user() and status='pending' and admin_note='' and privacy_version=0);
revoke select on public.feedback from authenticated;
grant select(id,rating,comment,share_consent,question,answer,status,admin_note,created_at,privacy_version)
  on public.feedback to authenticated;
revoke update(status,admin_note) on public.feedback from authenticated;
drop policy if exists feedback_read on public.feedback;
create policy feedback_read on public.feedback for select to authenticated using(public.is_administrator());
drop policy if exists feedback_review on public.feedback;

create or replace function public.my_feedback()
returns table(id uuid,rating text,comment text,share_consent boolean,status text,created_at timestamptz)
language plpgsql stable security definer set search_path='' as $$
begin
  if not public.is_active_user() then raise exception 'not permitted'; end if;
  return query select f.id,f.rating,f.comment,f.share_consent,f.status,f.created_at
    from public.feedback f where f.owner_id=auth.uid() order by f.created_at desc;
end;
$$;
create or replace function public.withdraw_my_feedback_consent(feedback_id uuid)
returns void language plpgsql security definer set search_path='' as $$
begin
  if not public.is_active_user() then raise exception 'not permitted'; end if;
  update public.feedback set share_consent=false,question='',answer='',admin_note='',privacy_version=privacy_version+1
    where id=feedback_id and owner_id=auth.uid();
  if not found then raise exception 'feedback unavailable'; end if;
end;
$$;
create or replace function public.delete_my_feedback(feedback_id uuid)
returns void language plpgsql security definer set search_path='' as $$
begin
  if not public.is_active_user() then raise exception 'not permitted'; end if;
  delete from public.feedback where id=feedback_id and owner_id=auth.uid();
  if not found then raise exception 'feedback unavailable'; end if;
end;
$$;
create or replace function public.review_feedback_safe(
  target_feedback uuid,new_status text,new_note text,expected_privacy_version integer
) returns void language plpgsql security definer set search_path='' as $$
declare current_version integer;
begin
  if not public.is_administrator() or new_status is null or new_status not in ('pending','reviewing','resolved')
     or new_note is null or length(new_note)>4000 or expected_privacy_version is null then
    raise exception 'not permitted';
  end if;
  select privacy_version into current_version from public.feedback where id=target_feedback for update;
  if not found or current_version<>expected_privacy_version then raise exception 'feedback privacy changed'; end if;
  update public.feedback set status=new_status,admin_note=new_note where id=target_feedback;
end;
$$;
create table if not exists public.history_versions (
  owner_id uuid primary key references auth.users(id) on delete cascade,
  version bigint not null default 0
);
alter table public.history_versions enable row level security;
revoke all on public.history_versions from public,anon,authenticated;
create or replace function public.my_history_version()
returns bigint language plpgsql stable security definer set search_path='' as $$
begin
  if not public.is_active_user() then raise exception 'not permitted'; end if;
  return coalesce((select version from public.history_versions where owner_id=auth.uid()),0);
end;
$$;
-- A stale browser must not recreate chats deleted from a different device.
drop function if exists public.save_my_conversations(jsonb,text[]);
revoke insert,update on public.conversations from authenticated;
create or replace function public.save_my_conversations(changed jsonb,deleted text[],expected_history_version bigint)
returns void language plpgsql security definer set search_path='' as $$
declare item jsonb; current_version bigint;
begin
  if not public.is_active_user() or changed is null or jsonb_typeof(changed)<>'array'
     or jsonb_array_length(changed)>5000 or deleted is null or cardinality(deleted)>5000
     or expected_history_version is null then raise exception 'not permitted'; end if;
  insert into public.history_versions(owner_id) values(auth.uid()) on conflict do nothing;
  select version into current_version from public.history_versions where owner_id=auth.uid() for update;
  if current_version<>expected_history_version then raise exception 'history erased; reload required'; end if;
  for item in select value from jsonb_array_elements(changed) loop
    if jsonb_typeof(item)<>'object' or item->>'id' is null or item->'messages' is null or jsonb_typeof(item->'messages')<>'array' then
      raise exception 'invalid conversation';
    end if;
    insert into public.conversations(owner_id,id,payload) values(auth.uid(),item->>'id',item)
    on conflict(owner_id,id) do update set payload=excluded.payload,updated_at=now();
  end loop;
  delete from public.conversations where owner_id=auth.uid() and id=any(deleted);
end;
$$;
create or replace function public.delete_my_conversations()
returns void language plpgsql security definer set search_path='' as $$
begin
  if not public.is_active_user() then raise exception 'not permitted'; end if;
  insert into public.history_versions(owner_id,version) values(auth.uid(),1)
  on conflict(owner_id) do update set version=public.history_versions.version+1;
  delete from public.conversations where owner_id=auth.uid();
end;
$$;

-- Withdrawal must not identify the feedback author through the audit log.
create or replace function public.audit_admin_change()
returns trigger language plpgsql security definer set search_path='' as $$
begin
  if tg_table_name='feedback' then
    if old.privacy_version is distinct from new.privacy_version then return new; end if;
    insert into public.admin_audit(actor_id,action,target_id,details)
    values(auth.uid(),'feedback.update',new.id::text,jsonb_build_object('operation',tg_op));
    return new;
  end if;
  if tg_table_name='admin_jobs' and tg_op='UPDATE' then
    if old.status='running' and new.status='running'
       and old.result=new.result and old.lease_token=new.lease_token then return new; end if;
  end if;
  insert into public.admin_audit(actor_id,action,target_id,details)
  values(auth.uid(),tg_table_name||'.'||lower(tg_op),new.id::text,jsonb_build_object('operation',tg_op));
  return new;
end;
$$;

revoke all on function public.is_security_administrator(),public.my_admin_permissions(),
 public.my_feedback(),public.withdraw_my_feedback_consent(uuid),public.delete_my_feedback(uuid),
 public.review_feedback_safe(uuid,text,text,integer),public.delete_my_conversations(),
 public.my_history_version(),public.save_my_conversations(jsonb,text[],bigint)
 from public,anon;
grant execute on function public.is_security_administrator(),public.my_admin_permissions(),
 public.my_feedback(),public.withdraw_my_feedback_consent(uuid),public.delete_my_feedback(uuid),
 public.review_feedback_safe(uuid,text,text,integer),public.delete_my_conversations(),
 public.my_history_version(),public.save_my_conversations(jsonb,text[],bigint)
 to authenticated;
notify pgrst, 'reload schema';
commit;
