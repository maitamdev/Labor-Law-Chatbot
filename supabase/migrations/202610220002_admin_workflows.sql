-- Safer admin workflows: atomic document approval, job leases and invitation audit.
begin;

alter table public.admin_jobs add column lease_token uuid;
alter table public.admin_jobs add column claimed_by uuid references auth.users(id);

create or replace function public.cancel_administrator_invitation(invitation_id uuid)
returns void language plpgsql security definer set search_path='' as $$
declare cancelled_id uuid;
begin
  if not public.is_administrator() then raise exception 'not permitted'; end if;
  update public.admin_invitations
  set cancelled=true
  where id=invitation_id and accepted_at is null and not cancelled and expires_at>now()
  returning id into cancelled_id;
  if cancelled_id is null then raise exception 'invitation unavailable'; end if;
  insert into public.admin_audit(actor_id,action,target_id)
  values(auth.uid(),'administrator.cancel_invitation',cancelled_id::text);
end;
$$;

create or replace function public.approve_legal_document(
  target_document uuid,
  expected_updated_at timestamptz
) returns uuid language plpgsql security invoker set search_path='' as $$
declare
  item public.legal_documents;
  job_id uuid;
begin
  if not public.is_administrator() then raise exception 'not permitted'; end if;
  select * into item from public.legal_documents where id=target_document for update;
  if not found then raise exception 'document not found'; end if;
  if item.updated_at is distinct from expected_updated_at then raise exception 'document changed'; end if;
  if item.status not in ('draft','review') then raise exception 'document is not awaiting review'; end if;
  if item.validity not in ('CURRENT','PARTIALLY_EFFECTIVE') or item.effective_from is null then
    raise exception 'document effectivity is not verified';
  end if;

  update public.legal_documents
  set status='approved',reviewed_by=auth.uid(),reviewed_at=now(),updated_at=now()
  where id=target_document;
  insert into public.admin_jobs(kind,document_id)
  values('index',target_document) returning id into job_id;
  return job_id;
end;
$$;

drop function public.claim_admin_job(uuid);
create function public.claim_admin_job(job_id uuid, requested_lease uuid)
returns jsonb language plpgsql security definer set search_path='' as $$
declare result public.admin_jobs;
begin
  if requested_lease is null or not public.is_administrator() then raise exception 'not permitted'; end if;
  update public.admin_jobs
  set status='running',started_at=now(),finished_at=null,result='',lease_token=requested_lease,claimed_by=auth.uid()
  where id=job_id
    and (status in ('pending','failed') or (status='running' and started_at<now()-interval '10 minutes'))
  returning * into result;
  if result.id is null then raise exception 'job already claimed or inaccessible'; end if;
  return to_jsonb(result);
end;
$$;

create function public.assert_admin_job_lease(job_id uuid, requested_lease uuid)
returns void language plpgsql security definer set search_path='' as $$
begin
  if not public.is_administrator() then raise exception 'not permitted'; end if;
  perform 1 from public.admin_jobs
  where id=job_id and claimed_by=auth.uid() and status='running' and lease_token=requested_lease
  for update;
  if not found then raise exception 'job lease expired'; end if;
end;
$$;

create function public.touch_admin_job(job_id uuid, requested_lease uuid)
returns void language plpgsql security definer set search_path='' as $$
begin
  if not public.is_administrator() then raise exception 'not permitted'; end if;
  update public.admin_jobs set started_at=now()
  where id=job_id and claimed_by=auth.uid() and status='running' and lease_token=requested_lease;
  if not found then raise exception 'job is no longer active'; end if;
end;
$$;

create function public.finish_admin_job(
  job_id uuid, requested_lease uuid, succeeded boolean, job_result text
) returns void language plpgsql security definer set search_path='' as $$
begin
  if not public.is_administrator() then raise exception 'not permitted'; end if;
  update public.admin_jobs set
    status=case when succeeded then 'succeeded' else 'failed' end,
    finished_at=now(),result=left(coalesce(job_result,''),4000)
  where id=job_id and claimed_by=auth.uid() and status='running' and lease_token=requested_lease;
  if not found then raise exception 'job lease expired'; end if;
end;
$$;

create function public.restore_business_metadata_for_job(
  job_id uuid,requested_lease uuid,snapshot jsonb
) returns void language plpgsql security definer set search_path='' as $$
declare
  item jsonb;
  executor uuid;
begin
  select claimed_by into executor from public.admin_jobs
  where id=job_id and status='running' and lease_token=requested_lease for update;
  if executor is null or executor<>auth.uid() or not public.is_administrator()
     or snapshot->>'format' is distinct from 'vietlabor-business-v1'
     or jsonb_typeof(snapshot->'documents') is distinct from 'array'
     or jsonb_typeof(snapshot->'settings') is distinct from 'array' then
    raise exception 'not permitted';
  end if;
  for item in select value from jsonb_array_elements(snapshot->'documents') loop
    update public.legal_documents set
      title=item->>'title',document_no=coalesce(item->>'document_no',''),
      issuer=coalesce(item->>'issuer',''),effective_from=(item->>'effective_from')::date,
      validity='unverified',source_url=coalesce(item->>'source_url',''),
      status='review',reviewed_by=null,reviewed_at=null,updated_at=now()
    where id=(item->>'id')::uuid and sha256=item->>'sha256';
  end loop;
  if jsonb_array_length(snapshot->'settings')=1 then
    item=snapshot->'settings'->0;
    update public.app_settings set app_name=item->>'app_name',
      workspace_name=item->>'workspace_name',updated_at=now() where id='general';
  end if;
  insert into public.admin_audit(actor_id,action) values(auth.uid(),'business_metadata.restore');
end;
$$;

create or replace function public.audit_admin_change()
returns trigger language plpgsql security definer set search_path='' as $$
begin
  if tg_table_name='admin_jobs' and tg_op='UPDATE' then
    if old.status='running' and new.status='running'
       and old.result=new.result and old.lease_token=new.lease_token then return new; end if;
  end if;
  insert into public.admin_audit(actor_id,action,target_id,details)
  values(auth.uid(),tg_table_name||'.'||lower(tg_op),new.id::text,jsonb_build_object('operation',tg_op));
  return new;
end;
$$;

revoke all on function public.cancel_administrator_invitation(uuid),
  public.approve_legal_document(uuid,timestamptz),
  public.claim_admin_job(uuid,uuid),public.assert_admin_job_lease(uuid,uuid),
  public.touch_admin_job(uuid,uuid),public.finish_admin_job(uuid,uuid,boolean,text),
  public.restore_business_metadata_for_job(uuid,uuid,jsonb),
  public.audit_admin_change()
  from public,anon;
grant execute on function public.cancel_administrator_invitation(uuid),
  public.approve_legal_document(uuid,timestamptz),
  public.claim_admin_job(uuid,uuid),public.assert_admin_job_lease(uuid,uuid),
  public.touch_admin_job(uuid,uuid),public.finish_admin_job(uuid,uuid,boolean,text),
  public.restore_business_metadata_for_job(uuid,uuid,jsonb)
  to authenticated;

create policy legal_files_delete on storage.objects for delete to authenticated
  using(bucket_id='legal-documents' and public.is_administrator());

commit;
