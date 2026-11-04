-- Additive country totals only. Existing tester records and archive tables are untouched.
create table public.ydna_sync_country_counts (
 id bigint generated always as identity primary key,
 source_id text not null references public.ydna_sync_sources(id),
 run_id uuid references public.ydna_sync_runs(id),
 namespace text not null check(namespace in ('ftdna','yfull')),
 node_label text not null check(node_label ~ '^[A-T][A-Z0-9*.+_-]*$'),
 country_code text not null check(country_code='EG'),
 count_scope text not null check(count_scope in ('direct','inclusive')),
 population text not null check(population in ('ftdna_big_y','yfull_modern','unknown')),
 reported_count integer not null check(reported_count>=0),
 observed_at timestamptz not null,
 source_url text not null check(source_url like 'https://%'),
 snp_path jsonb not null default '[]' check(jsonb_typeof(snp_path)='array'),
 path_source_url text,
 published boolean not null default false,
 is_current boolean not null default false,
 recorded_at timestamptz not null default now(),
 constraint country_count_population_matches_namespace check(
  population='unknown' or (namespace='ftdna' and population='ftdna_big_y') or (namespace='yfull' and population='yfull_modern')),
 unique(source_id,namespace,node_label,country_code,count_scope,population,observed_at)
);
create index country_counts_current_node on public.ydna_sync_country_counts(node_label) where published and is_current;
create index country_counts_run on public.ydna_sync_country_counts(run_id);
alter table public.ydna_sync_country_counts enable row level security;
revoke all on public.ydna_sync_country_counts from public,anon,authenticated;
grant all on public.ydna_sync_country_counts to service_role;
grant usage,select on sequence public.ydna_sync_country_counts_id_seq to service_role;
grant select on public.ydna_sync_country_counts to anon,authenticated;
create policy published_country_counts on public.ydna_sync_country_counts for select to anon,authenticated using(published and is_current);

create function public.ydna_sync_ingest_country_count(p_record jsonb,p_run uuid,p_dry_run boolean default true)
returns jsonb language plpgsql security invoker set search_path=public,pg_temp as $$
declare
 src text:=p_record->>'source_id'; ns text:=p_record->>'namespace'; label text:=p_record->>'node_label';
 scope_name text:=p_record->>'count_scope'; cohort text:=p_record->>'population';
 qty integer; at_time timestamptz; prior public.ydna_sync_country_counts%rowtype;
 latest_at timestamptz; saved_id bigint;
begin
 perform pg_advisory_xact_lock(hashtextextended('egypt-ydna-sync',0));
 if not coalesce((p_record->>'accepted')::boolean,false) then
  if not p_dry_run then perform public.ydna_sync_review(null,src,'country_count_requires_review',p_record); end if;
  return jsonb_build_object('status','review'); end if;
 if not exists(select 1 from public.ydna_sync_sources where id=src and publication_allowed) then
  raise exception 'Country count source not authorized'; end if;
 if p_record->>'country_code'<>'EG' or jsonb_typeof(p_record->'reported_count')<>'number' or p_record->>'reported_count' !~ '^\d+$' then
  raise exception 'Invalid Egyptian integer count'; end if;
 qty:=(p_record->>'reported_count')::integer;
 at_time:=(p_record->>'observed_at')::timestamptz;
 if at_time is null then raise exception 'Source observation time required'; end if;
 select * into prior from public.ydna_sync_country_counts where source_id=src and namespace=ns and node_label=label
  and count_scope=scope_name and population=cohort and country_code='EG' and observed_at=at_time;
 if prior.id is not null then
  if prior.reported_count<>qty then
   if not p_dry_run then perform public.ydna_sync_review(null,src,'conflicting_country_count',p_record); end if;
   return jsonb_build_object('status','review'); end if;
  return jsonb_build_object('status','unchanged','id',prior.id);
 end if;
 if p_dry_run then return jsonb_build_object('status','would_insert'); end if;
 select max(observed_at) into latest_at from public.ydna_sync_country_counts where source_id=src and namespace=ns and node_label=label
  and count_scope=scope_name and population=cohort and country_code='EG';
 if latest_at is null or latest_at<at_time then
  update public.ydna_sync_country_counts set is_current=false where source_id=src and namespace=ns and node_label=label
   and count_scope=scope_name and population=cohort and country_code='EG';
 end if;
 insert into public.ydna_sync_country_counts(source_id,run_id,namespace,node_label,country_code,count_scope,population,
  reported_count,observed_at,source_url,snp_path,path_source_url,published,is_current)
 values(src,p_run,ns,label,'EG',scope_name,cohort,qty,at_time,p_record->>'source_url',coalesce(p_record->'snp_path','[]'),
  p_record->>'path_source_url',true,latest_at is null or latest_at<at_time) returning id into saved_id;
 return jsonb_build_object('status',case when latest_at>at_time then 'historical' else 'inserted' end,'id',saved_id);
end $$;
revoke all on function public.ydna_sync_ingest_country_count(jsonb,uuid,boolean) from public,anon,authenticated;
grant execute on function public.ydna_sync_ingest_country_count(jsonb,uuid,boolean) to service_role;
