-- Additive only. The four archive tables are copied before any alteration.
create schema if not exists ydna_backup;
revoke all on schema ydna_backup from public, anon, authenticated;
create table if not exists ydna_backup.modern_before_sync as table public."Modern_published_samples";
create table if not exists ydna_backup.ancient_before_sync as table public."Ancient_published_samples";
create table if not exists ydna_backup.study_before_sync as table public."Modern_study_samples";
create table if not exists ydna_backup.related_before_sync as table public.ancient_related_samples;
revoke all on all tables in schema ydna_backup from public, anon, authenticated;

alter table public."Modern_published_samples"
  add column if not exists sync_managed boolean not null default false,
  add column if not exists sync_primary_source text,
  add column if not exists sync_published jsonb not null default '{}'::jsonb,
  add column if not exists origin_raw text,
  add column if not exists governorate_iso text,
  add column if not exists yfull_id text,
  add column if not exists test_status text,
  add column if not exists haplogroup_status text,
  add column if not exists sync_updated_at timestamptz,
  add column if not exists sync_first_seen_run uuid,
  add column if not exists sync_visibility text not null default 'public';

create table public.ydna_sync_runs (
 id uuid primary key default gen_random_uuid(), started_at timestamptz not null default now(),
 finished_at timestamptz, status text not null default 'running', report jsonb not null default '{}'
);
create table public.ydna_sync_sources (
 id text primary key, url text not null, adapter text not null, publication_allowed boolean not null default false,
 permission_url text, last_success_at timestamptz, last_status text, etag text, metadata jsonb not null default '{}'
);
create table public.ydna_sync_identities (
 namespace text not null check(namespace in ('ftdna','yfull')), external_id text not null,
 sample_id bigint not null references public."Modern_published_samples"(id), evidence_url text not null,
 primary key(namespace,external_id)
);
create index on public.ydna_sync_identities(sample_id);
create table public.ydna_sync_observations (
 id bigint generated always as identity primary key,
 source_id text not null references public.ydna_sync_sources(id),
 namespace text not null, external_id text not null, checksum text not null,
 sample_id bigint references public."Modern_published_samples"(id),
 first_seen_at timestamptz not null default now(), last_seen_at timestamptz not null default now(),
 payload jsonb not null, published boolean not null default false, is_current boolean not null default true,
 unique(source_id, namespace, external_id, checksum)
);
create index on public.ydna_sync_observations(sample_id);
create table public.ydna_sync_str_values (
 observation_id bigint not null references public.ydna_sync_observations(id) on delete cascade,
 position integer not null, marker text not null, source_label text not null, allele text,
 primary key(observation_id,position)
);
create table public.ydna_sync_reviews (
 fingerprint text primary key, sample_id bigint references public."Modern_published_samples"(id),
 source_id text, reason text not null, details jsonb not null, status text not null default 'pending',
 created_at timestamptz not null default now(), resolved_at timestamptz
);
create index on public.ydna_sync_reviews(sample_id);
create table public.ydna_sync_places (
 id text primary key, name text not null, aliases jsonb not null, governorate_iso text not null,
 district text, source_url text not null, metadata jsonb not null default '{}'
);
create table public.ydna_sync_tree_nodes (
 source_id text not null references public.ydna_sync_sources(id), label text not null,
 parent_label text, aliases jsonb not null default '[]', source_url text not null,
 updated_at timestamptz not null default now(), primary key(source_id,label)
);
create table public.ydna_sync_optouts (
 identity_hash text primary key, created_at timestamptz not null default now()
);

-- Explicit grants are needed on projects with opt-in Data API exposure.
do $$ declare t text; begin
 foreach t in array array['ydna_sync_runs','ydna_sync_sources','ydna_sync_identities','ydna_sync_observations',
 'ydna_sync_str_values','ydna_sync_reviews','ydna_sync_places','ydna_sync_tree_nodes','ydna_sync_optouts'] loop
  execute format('alter table public.%I enable row level security',t);
  execute format('revoke all on public.%I from public,anon,authenticated',t);
  execute format('grant all on public.%I to service_role',t);
 end loop;
end $$;
grant usage, select on sequence public.ydna_sync_observations_id_seq to service_role;
grant select on public.ydna_sync_observations,public.ydna_sync_str_values,public.ydna_sync_tree_nodes to anon,authenticated;
create policy public_current_evidence on public.ydna_sync_observations for select to anon,authenticated
 using(published and exists(select 1 from public."Modern_published_samples" s where s.id=sample_id and s.sync_visibility='public'));
create policy public_str_evidence on public.ydna_sync_str_values for select to anon,authenticated
 using(exists(select 1 from public.ydna_sync_observations o where o.id=observation_id and o.published));
create policy public_tree_nodes on public.ydna_sync_tree_nodes for select to anon,authenticated using(true);
create policy sync_visibility_guard on public."Modern_published_samples" as restrictive for select to anon,authenticated
 using(sync_visibility='public');

create function public.ydna_sync_review(p_sample bigint,p_source text,p_reason text,p_details jsonb)
returns void language sql security invoker set search_path=public,pg_temp as $$
 insert into public.ydna_sync_reviews(fingerprint,sample_id,source_id,reason,details)
 values(md5(coalesce(p_sample::text,'')||coalesce(p_source,'')||p_reason||p_details::text),p_sample,p_source,p_reason,p_details)
 on conflict(fingerprint) do nothing;
$$;

-- One record, one transaction, with an advisory lock across all sync writers.
-- Only service_role may call this invoker function; no browser write privilege.
create function public.ydna_sync_ingest(p_record jsonb,p_run uuid,p_dry_run boolean default true)
returns jsonb language plpgsql security invoker set search_path=public,pg_temp as $$
declare
 sid bigint; ids bigint[]; candidate integer; oid bigint; old_ob public.ydna_sync_observations%rowtype;
 s public."Modern_published_samples"%rowtype; ns text:=p_record->>'namespace';
 eid text:=upper(p_record->>'external_id'); src text:=p_record->>'source_id';
 v_checksum text:=md5(p_record::text); identity jsonb; v_marker jsonb; field text; val text;
 projection jsonb; current_val text; changed boolean:=false; conflicts integer:=0; outcome text:='unchanged';
begin
 perform pg_advisory_xact_lock(hashtextextended('egypt-ydna-sync',0));
 if exists(select 1 from public.ydna_sync_optouts where identity_hash=encode(sha256(convert_to(ns||':'||eid,'UTF8')),'hex')) then
  return jsonb_build_object('status','opted_out'); end if;
 select array_agg(distinct d.sample_id) into ids from public.ydna_sync_identities d
 where (d.namespace=ns and d.external_id=eid) or (p_record->>'identity_evidence_url' like 'https://%' and
 exists(select 1 from jsonb_array_elements(coalesce(p_record->'verified_ids','[]')) i
 where i->>'namespace'=d.namespace and upper(i->>'external_id')=d.external_id));
 if cardinality(ids)>1 then
  if not p_dry_run then perform public.ydna_sync_review(null,src,'identity_collision',p_record); end if;
  return jsonb_build_object('status','review','reason','identity_collision');
 end if;
 sid:=ids[1];
 if sid is null then
  select array_agg(id) into ids from public."Modern_published_samples"
   where upper(trim(kit_number))=eid or (ns='yfull' and upper(yfull_id)=eid);
  if cardinality(ids)>1 then
   if not p_dry_run then perform public.ydna_sync_review(null,src,'duplicate_existing_identity',p_record); end if;
   return jsonb_build_object('status','review','reason','duplicate_existing_identity');
  end if;
  sid:=ids[1];
 end if;
 if not coalesce((p_record->>'accepted')::boolean,false) then
  if not p_dry_run then perform public.ydna_sync_review(sid,src,'candidate_requires_review',p_record); end if;
  return jsonb_build_object('status','review'); end if;
 if not exists(select 1 from public.ydna_sync_sources where id=src and publication_allowed) then
  raise exception 'Source not authorized for publication'; end if;
 if sid is null then
  outcome:='inserted';
  if not p_dry_run then
   insert into public."Modern_published_samples"(sync_managed,sync_primary_source,sync_first_seen_run)
    values(true,src,p_run) returning id into sid;
  end if;
 end if;
 if p_dry_run then return jsonb_build_object('status',case when sid is null then 'would_insert' else 'would_reconcile' end,'sample_id',sid); end if;
 select * into s from public."Modern_published_samples" where id=sid for update;
 if s.sync_visibility<>'public' then return jsonb_build_object('status','suppressed'); end if;
 insert into public.ydna_sync_identities(namespace,external_id,sample_id,evidence_url)
 values(ns,eid,sid,p_record->>'source_url') on conflict do nothing;
 if p_record->>'identity_evidence_url' like 'https://%' then
  for identity in select * from jsonb_array_elements(coalesce(p_record->'verified_ids','[]')) loop
   if exists(select 1 from public.ydna_sync_optouts where identity_hash=encode(sha256(convert_to((identity->>'namespace')||':'||upper(identity->>'external_id'),'UTF8')),'hex')) then
    raise exception 'Linked identity opted out'; end if;
   insert into public.ydna_sync_identities(namespace,external_id,sample_id,evidence_url)
   values(identity->>'namespace',upper(identity->>'external_id'),sid,p_record->>'identity_evidence_url') on conflict do nothing;
  end loop;
 end if;
 select * into old_ob from public.ydna_sync_observations where source_id=src and namespace=ns and external_id=eid and is_current order by id desc limit 1;
 update public.ydna_sync_observations set is_current=false where source_id=src and namespace=ns and external_id=eid;
 insert into public.ydna_sync_observations(source_id,namespace,external_id,checksum,sample_id,payload,published)
 values(src,ns,eid,v_checksum,sid,p_record,true)
 on conflict(source_id,namespace,external_id,checksum) do update set last_seen_at=now(),is_current=true
 returning id into oid;
 for v_marker in select * from jsonb_array_elements(coalesce(p_record->'str_markers','[]')) loop
  insert into public.ydna_sync_str_values(observation_id,position,marker,source_label,allele)
   values(oid,(v_marker->>'position')::integer,v_marker->>'marker',v_marker->>'source_label',v_marker->>'value') on conflict do nothing;
  if v_marker->>'value' is not null and exists(select 1 from public.ydna_sync_str_values v join public.ydna_sync_observations o on o.id=v.observation_id
    where o.sample_id=sid and v.marker=v_marker->>'marker' and v.allele is not null and v.allele<>v_marker->>'value' and v.observation_id<>oid) then
   perform public.ydna_sync_review(sid,src,'str_conflict',v_marker); conflicts:=conflicts+1; end if;
 end loop;
 projection:=jsonb_build_object('name',p_record->>'name','kit_number',case when ns='ftdna' then eid end,
 'yfull_id',case when ns='yfull' then eid end,'test_type',p_record->>'test_type','test_status',p_record->>'test_status',
 'haplogroup_status',p_record->>'haplogroup_status','y_dna',nullif(p_record->>'y_dna',''),
 'y_dna_alias',nullif(p_record->>'y_dna_alias',''),'origin_raw',p_record->>'origin_raw',
 'governorate',p_record->'origin'->>'governorate','governorate_iso',p_record->'origin'->>'governorate_iso',
 'y_link_1',p_record->>'source_url');
 if jsonb_array_length(coalesce(p_record->'snp_path','[]'))>0 then
  projection:=projection||jsonb_build_object('full_snp_path',(select string_agg(x,'>' order by ord) from jsonb_array_elements_text(p_record->'snp_path') with ordinality a(x,ord)));
 end if;
 for field,val in select key,value #>> '{}' from jsonb_each(projection) loop
  if val is null or trim(val) in ('','—','-') then continue; end if;
  execute format('select %I::text from public."Modern_published_samples" where id=$1',field) into current_val using sid;
  if current_val=val then continue; end if;
  if current_val is null or trim(current_val) in ('','—','-') or
    (s.sync_managed and s.sync_primary_source=src and s.sync_published->>field=current_val) then
   execute format('update public."Modern_published_samples" set %I=$1 where id=$2',field) using val,sid;
   update public."Modern_published_samples" set sync_published=sync_published||jsonb_build_object(field,val) where id=sid;
   changed:=true;
  else
   perform public.ydna_sync_review(sid,src,'field_conflict',jsonb_build_object('field',field,'existing',current_val,'proposed',val,'observation_id',oid));
   conflicts:=conflicts+1;
  end if;
 end loop;
 -- Do not retain a previous verified path after a terminal move without a replacement path.
 if s.sync_managed and s.sync_primary_source=src and s.y_dna is distinct from p_record->>'y_dna'
  and s.sync_published->>'y_dna'=s.y_dna and jsonb_array_length(coalesce(p_record->'snp_path','[]'))=0
  and s.sync_published->>'full_snp_path'=s.full_snp_path then
  update public."Modern_published_samples" set full_snp_path=null,sync_published=sync_published-'full_snp_path' where id=sid;
 end if;
 if p_record->>'path_source_url' like 'https://%' then
  for candidate in select generate_series(0,jsonb_array_length(coalesce(p_record->'snp_path','[]'))-1) loop
   insert into public.ydna_sync_tree_nodes(source_id,label,parent_label,aliases,source_url)
   values(src,p_record->'snp_path'->>candidate,case when candidate>0 then p_record->'snp_path'->>(candidate-1) end,
   coalesce(p_record->'snp_aliases'->(p_record->'snp_path'->>candidate),'[]'),p_record->>'path_source_url')
   on conflict(source_id,label) do update set parent_label=excluded.parent_label,aliases=excluded.aliases,source_url=excluded.source_url,updated_at=now();
  end loop;
 end if;
 if p_record->>'location_review'='true' then perform public.ydna_sync_review(sid,src,'location_ambiguous',p_record->'origin'); end if;
 if changed or old_ob.checksum is distinct from v_checksum then
  update public."Modern_published_samples" set sync_updated_at=now() where id=sid;
  if outcome<>'inserted' then outcome:='updated'; end if;
 end if;
 return jsonb_build_object('status',outcome,'sample_id',sid,'conflicts',conflicts,'duplicate',old_ob.id is not null);
end $$;

-- Explicit opt-out: hide the legacy archive row, purge identifying source payloads, and prevent reimport.
-- Legacy fields remain in the private backup; the maintainer must process backup erasure separately.
create function public.ydna_sync_opt_out(p_sample bigint) returns void
language plpgsql security invoker set search_path=public,pg_temp as $$
begin
 perform pg_advisory_xact_lock(hashtextextended('egypt-ydna-sync',0));
 insert into public.ydna_sync_optouts(identity_hash)
 select encode(sha256(convert_to(namespace||':'||external_id,'UTF8')),'hex') from public.ydna_sync_identities where sample_id=p_sample on conflict do nothing;
 update public."Modern_published_samples" set sync_visibility='opted_out',name=null,kit_number=null,yfull_id=null,
 origin_raw=null,y_link_1=null,y_link_2=null,sync_published='{}' where id=p_sample;
 delete from public.ydna_sync_reviews where sample_id=p_sample;
 delete from public.ydna_sync_observations where sample_id=p_sample;
 delete from public.ydna_sync_identities where sample_id=p_sample;
end $$;

revoke all on function public.ydna_sync_review(bigint,text,text,jsonb) from public,anon,authenticated;
revoke all on function public.ydna_sync_ingest(jsonb,uuid,boolean) from public,anon,authenticated;
revoke all on function public.ydna_sync_opt_out(bigint) from public,anon,authenticated;
grant execute on function public.ydna_sync_review(bigint,text,text,jsonb),public.ydna_sync_ingest(jsonb,uuid,boolean),public.ydna_sync_opt_out(bigint) to service_role;

-- Run summaries contain counts and source status only, never candidate identities.
grant select on public.ydna_sync_runs to anon,authenticated;
create policy public_sync_summary on public.ydna_sync_runs for select to anon,authenticated using(status in ('completed','partial'));
