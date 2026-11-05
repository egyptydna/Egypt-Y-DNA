-- Aggregate facts only. Existing archive profiles, identities and alleles are untouched.
create table public.ydna_tracker_snapshots (
 id uuid primary key default gen_random_uuid(),
 source_id text not null references public.ydna_sync_sources(id),
 snapshot_key text not null check(snapshot_key ~ '^[0-9a-f]{64}$'),
 provider text not null default 'ftdna' check(provider='ftdna'),
 country_code text not null default 'EG' check(country_code='EG'),
 observed_at timestamptz not null, checked_at timestamptz not null default now(),
 total_count integer not null check(total_count>=0),
 nodes jsonb not null check(jsonb_typeof(nodes)='array'),
 source_url text not null check(source_url like 'https://%'),
 details jsonb not null default '{}', published boolean not null default true,
 unique(source_id,snapshot_key)
);
create index tracker_snapshot_latest on public.ydna_tracker_snapshots(observed_at desc,checked_at desc) where published;
create table public.ydna_tracker_changes (
 snapshot_id uuid not null references public.ydna_tracker_snapshots(id),
 change_key text not null, branch_label text,
 kind text not null check(kind in ('baseline','total_increase','total_decrease','branch_change','reference_update')),
 before_count integer, after_count integer not null check(after_count>=0),
 primary key(snapshot_id,change_key)
);
create table public.ydna_tracker_status (
 provider text primary key check(provider='ftdna'),
 snapshot_id uuid references public.ydna_tracker_snapshots(id),
 checked_at timestamptz not null default now(), last_success_at timestamptz,
 primary_status text not null check(primary_status in ('ok','unavailable','not_checked')),
 message text not null default ''
);
do $$ declare t text; begin
 foreach t in array array['ydna_tracker_snapshots','ydna_tracker_changes','ydna_tracker_status'] loop
  execute format('alter table public.%I enable row level security',t);
  execute format('revoke all on public.%I from public,anon,authenticated',t);
  execute format('grant all on public.%I to service_role',t);
  execute format('grant select on public.%I to anon,authenticated',t);
 end loop;
end $$;
create policy published_tracker_snapshots on public.ydna_tracker_snapshots for select to anon,authenticated using(published);
create policy published_tracker_changes on public.ydna_tracker_changes for select to anon,authenticated
 using(exists(select 1 from public.ydna_tracker_snapshots s where s.id=snapshot_id and s.published));
create policy public_tracker_status on public.ydna_tracker_status for select to anon,authenticated using(true);

create function public.ydna_tracker_publish(p_snapshot jsonb,p_dry_run boolean default true)
returns jsonb language plpgsql security invoker set search_path=public,pg_temp as $$
declare
 src text:=p_snapshot->>'source_id'; payload_key text:=p_snapshot->>'snapshot_key';
 qty integer; at_time timestamptz; sid uuid; total_delta integer:=0; n record;
 prior public.ydna_tracker_snapshots%rowtype; already public.ydna_tracker_snapshots%rowtype; newest public.ydna_tracker_snapshots%rowtype;
 before_nodes jsonb; after_nodes jsonb;
begin
 perform pg_advisory_xact_lock(hashtextextended('egypt-ydna-country-tracker',0));
 if src not in ('ftdna-aggregate-github','owner-observatory-export') or src is null
  or not exists(select 1 from public.ydna_sync_sources where id=src and publication_allowed) then raise exception 'Approved aggregate source required'; end if;
 if payload_key is null or payload_key !~ '^[0-9a-f]{64}$' or p_snapshot->>'country_code' is distinct from 'EG'
  or p_snapshot->>'provider' is distinct from 'ftdna' or coalesce(p_snapshot->>'source_url','') not like 'https://%'
  or jsonb_typeof(p_snapshot->'nodes') is distinct from 'array'
  or coalesce(p_snapshot->>'total_count','') !~ '^[0-9]+$' then raise exception 'Invalid country snapshot'; end if;
 qty:=(p_snapshot->>'total_count')::integer;at_time:=(p_snapshot->>'observed_at')::timestamptz;
 if at_time is null or at_time>now()+interval '1 day' or jsonb_array_length(p_snapshot->'nodes')>10000 then raise exception 'Invalid snapshot date or size'; end if;
 if exists(select 1 from jsonb_array_elements(p_snapshot->'nodes') x where
  coalesce(x->>'label','') !~ '^[A-T][A-Za-z0-9*.+_-]*$' or coalesce(x->>'count','') !~ '^[0-9]+$' or jsonb_typeof(x->'count') is distinct from 'number'
  or jsonb_typeof(x->'path') is distinct from 'array'
  or exists(select 1 from jsonb_object_keys(x) k where k not in ('label','count','path','path_source_url','path_kind','path_observed_at'))
  or exists(select 1 from jsonb_array_elements(x->'path') p where jsonb_typeof(p)<>'string' or (p#>>'{}') !~ '^[A-Za-z0-9*.+_-]+$')
  or (jsonb_array_length(x->'path')>0 and
   (upper(x->'path'->>-1)<>upper(x->>'label') or coalesce(x->>'path_source_url','') not like 'https://%')))
 then raise exception 'Snapshot must contain anonymous branch counts and documented paths only'; end if;
 if (select count(distinct upper(x->>'label')) from jsonb_array_elements(p_snapshot->'nodes') x)<>jsonb_array_length(p_snapshot->'nodes')
  or coalesce((select sum((x->>'count')::bigint) from jsonb_array_elements(p_snapshot->'nodes') x),0)<>qty then
  raise exception 'Duplicate branches or incomplete country total'; end if;
 select * into already from public.ydna_tracker_snapshots where source_id=src and snapshot_key=payload_key;
 if already.id is not null then
  if not p_dry_run then update public.ydna_tracker_snapshots set checked_at=now() where id=already.id; end if;
  return jsonb_build_object('status','unchanged','snapshot_id',already.id,'new_results',0); end if;
 select * into prior from public.ydna_tracker_snapshots where source_id=src and published order by observed_at desc,checked_at desc limit 1;
 select * into newest from public.ydna_tracker_snapshots where published order by observed_at desc,checked_at desc limit 1;
 if newest.id is not null and at_time>=newest.observed_at and qty<newest.total_count*0.5 then
  if not p_dry_run then perform public.ydna_sync_review(null,src,'tracker_unexpected_country_drop',jsonb_build_object('before',newest.total_count,'proposed',qty,'observed_at',at_time)); end if;
  return jsonb_build_object('status','review','reason','unexpected_country_drop'); end if;
 select coalesce(jsonb_object_agg(x->>'label',x->'count'),'{}') into before_nodes from jsonb_array_elements(coalesce(prior.nodes,'[]')) x;
 select coalesce(jsonb_object_agg(x->>'label',x->'count'),'{}') into after_nodes from jsonb_array_elements(p_snapshot->'nodes') x;
 if prior.id is not null and at_time=prior.observed_at and before_nodes<>after_nodes then
  return jsonb_build_object('status','review','reason','conflicting_snapshot_date'); end if;
 if p_dry_run then return jsonb_build_object('status','would_publish','total_count',qty); end if;
 insert into public.ydna_tracker_snapshots(source_id,snapshot_key,observed_at,total_count,nodes,source_url,details)
 values(src,payload_key,at_time,qty,p_snapshot->'nodes',p_snapshot->>'source_url',coalesce(p_snapshot->'details','{}')) returning id into sid;
 if prior.id is null then
  insert into public.ydna_tracker_changes values(sid,'country',null,'baseline',null,qty);
 elsif at_time>=prior.observed_at then
  total_delta:=qty-prior.total_count;
  if total_delta<>0 then insert into public.ydna_tracker_changes values(sid,'country',null,case when total_delta>0 then 'total_increase' else 'total_decrease' end,prior.total_count,qty); end if;
  for n in select coalesce(b.key,a.key) label,coalesce((b.value#>>'{}')::int,0) before_count,coalesce((a.value#>>'{}')::int,0) after_count
    from jsonb_each(before_nodes) b full join jsonb_each(after_nodes) a on a.key=b.key
    where b.value is distinct from a.value loop
   insert into public.ydna_tracker_changes values(sid,'branch:'||n.label,n.label,'branch_change',n.before_count,n.after_count);
  end loop;
  if before_nodes=after_nodes then insert into public.ydna_tracker_changes values(sid,'reference',null,'reference_update',qty,qty); end if;
 end if;
 return jsonb_build_object('status',case when prior.id is not null and at_time<prior.observed_at then 'historical' else 'published' end,'snapshot_id',sid,'new_results',greatest(total_delta,0));
end $$;

create function public.ydna_tracker_select(p_primary_status text,p_message text default '')
returns jsonb language plpgsql security invoker set search_path=public,pg_temp as $$
declare chosen public.ydna_tracker_snapshots%rowtype; direct public.ydna_tracker_snapshots%rowtype; chosen_counts jsonb; direct_counts jsonb;
begin
 perform pg_advisory_xact_lock(hashtextextended('egypt-ydna-country-tracker',0));
 if p_primary_status is null or p_primary_status not in ('ok','unavailable','not_checked') then raise exception 'Invalid source status'; end if;
 select * into chosen from public.ydna_tracker_snapshots where published
 order by observed_at desc,(source_id='ftdna-aggregate-github') desc,checked_at desc limit 1;
 if p_primary_status='ok' and chosen.source_id='owner-observatory-export' then
  select * into direct from public.ydna_tracker_snapshots where published and source_id='ftdna-aggregate-github' order by observed_at desc,checked_at desc limit 1;
  select jsonb_object_agg(x->>'label',x->'count') into chosen_counts from jsonb_array_elements(chosen.nodes) x;
  select jsonb_object_agg(x->>'label',x->'count') into direct_counts from jsonb_array_elements(coalesce(direct.nodes,'[]')) x;
  if direct.id is not null and chosen_counts=direct_counts then chosen:=direct; end if;
 end if;
 insert into public.ydna_tracker_status(provider,snapshot_id,primary_status,message,last_success_at)
 values('ftdna',chosen.id,p_primary_status,left(p_message,500),case when p_primary_status='ok' then now() end)
 on conflict(provider) do update set snapshot_id=excluded.snapshot_id,primary_status=excluded.primary_status,
  message=excluded.message,checked_at=now(),last_success_at=coalesce(excluded.last_success_at,ydna_tracker_status.last_success_at);
 return jsonb_build_object('snapshot_id',chosen.id,'total_count',chosen.total_count,'source_id',chosen.source_id);
end $$;
revoke all on function public.ydna_tracker_publish(jsonb,boolean),public.ydna_tracker_select(text,text) from public,anon,authenticated;
grant execute on function public.ydna_tracker_publish(jsonb,boolean),public.ydna_tracker_select(text,text) to service_role;
