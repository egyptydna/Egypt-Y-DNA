-- Additive: preserve every original row and all source payloads before linking duplicates.
create table ydna_backup.modern_before_identity_repair as table public."Modern_published_samples";
revoke all on ydna_backup.modern_before_identity_repair from public,anon,authenticated;

alter table public."Modern_published_samples"
  add column sync_merged_into bigint references public."Modern_published_samples"(id),
  add column sync_origin_conflict boolean not null default false,
  add constraint no_self_identity_merge check(sync_merged_into is distinct from id);

create table public.ydna_sync_identity_merges (
 retired_id bigint primary key references public."Modern_published_samples"(id),
 canonical_id bigint not null references public."Modern_published_samples"(id),
 merged_at timestamptz not null default now(), evidence_url text not null,
 original_canonical jsonb not null, original_retired jsonb not null,
 constraint different_merge_ids check(retired_id<>canonical_id)
);
alter table public.ydna_sync_identity_merges enable row level security;
revoke all on public.ydna_sync_identity_merges from public,anon,authenticated;
grant all on public.ydna_sync_identity_merges to service_role;

create function public.ydna_sync_merge_duplicate(p_keep bigint,p_retire bigint,p_evidence_url text)
returns jsonb language plpgsql security invoker set search_path=public,pg_temp as $$
declare
 a public."Modern_published_samples"%rowtype;
 b public."Modern_published_samples"%rowtype;
 ident record; origins_differ boolean; same_identity boolean;
begin
 perform pg_advisory_xact_lock(hashtextextended('egypt-ydna-sync',0));
 if p_keep=p_retire or p_evidence_url not like 'https://%' or p_evidence_url is null then
  raise exception 'Distinct IDs and a documented HTTPS source are required'; end if;
 if exists(select 1 from public.ydna_sync_identity_merges where retired_id=p_retire and canonical_id=p_keep) then
  return jsonb_build_object('status','unchanged','canonical_id',p_keep); end if;
 select * into strict a from public."Modern_published_samples" where id=p_keep for update;
 select * into strict b from public."Modern_published_samples" where id=p_retire for update;
 if a.sync_visibility<>'public' or b.sync_visibility<>'public' or a.sync_merged_into is not null or b.sync_merged_into is not null then
  raise exception 'Only two active public records can be consolidated'; end if;
 same_identity := (upper(trim(a.kit_number))=upper(trim(b.kit_number)) and trim(a.kit_number) ~* '^[A-Z]{0,3}[0-9]+$')
  or (upper(trim(a.yfull_id))=upper(trim(b.yfull_id)) and trim(a.yfull_id) ~* '^YF[0-9]+$');
 if not coalesce(same_identity,false) then raise exception 'No exact shared kit or YFull ID'; end if;
 -- Exact shared IDs never authorize merging conflicting IDs in the other namespace.
 if exists(select 1 from (
   select namespace,count(distinct external_id) n from (
    select namespace,upper(external_id) external_id from public.ydna_sync_identities where sample_id in (p_keep,p_retire)
    union all select 'ftdna',upper(trim(kit_number)) from public."Modern_published_samples" where id in (p_keep,p_retire) and trim(kit_number) ~* '^[A-Z]{0,3}[0-9]+$' and trim(kit_number) !~* '^YF[0-9]+$'
    union all select 'yfull',upper(trim(yfull_id)) from public."Modern_published_samples" where id in (p_keep,p_retire) and trim(yfull_id) ~* '^YF[0-9]+$'
    union all select 'yfull',upper(trim(kit_number)) from public."Modern_published_samples" where id in (p_keep,p_retire) and trim(kit_number) ~* '^YF[0-9]+$'
   ) ids group by namespace
  ) groups where n>1) then raise exception 'Conflicting verified external IDs'; end if;
 if coalesce(a.mt_dna,'') not in ('','—') and coalesce(b.mt_dna,'') not in ('','—') and a.mt_dna<>b.mt_dna then
  raise exception 'Conflicting mtDNA calls require manual review'; end if;
 if coalesce(a.y_dna,'') not in ('','—') and coalesce(b.y_dna,'') not in ('','—') and upper(a.y_dna)<>upper(b.y_dna) then
  if not exists(select 1 from unnest(string_to_array(upper(a.full_snp_path),'>')) marker
    where regexp_replace(trim(marker),'^[A-T]-','')=regexp_replace(upper(b.y_dna),'^[A-T]-','')) then
   raise exception 'Different terminal calls need a documented descendant path'; end if;
 end if;
 origins_differ := coalesce(a.governorate,'') not in ('','—') and coalesce(b.governorate,'') not in ('','—') and a.governorate<>b.governorate;
 insert into public.ydna_sync_identity_merges(retired_id,canonical_id,evidence_url,original_canonical,original_retired)
  values(p_retire,p_keep,p_evidence_url,to_jsonb(a),to_jsonb(b));
 if origins_differ then
  update public."Modern_published_samples" set sync_origin_conflict=true where id=p_keep;
  perform public.ydna_sync_review(p_keep,null,'merged_origin_conflict',jsonb_build_object('canonical_governorate',a.governorate,'other_governorate',b.governorate,'retired_id',p_retire,'evidence_url',p_evidence_url));
 end if;
 update public.ydna_sync_identities set sample_id=p_keep where sample_id=p_retire;
 update public.ydna_sync_observations set sample_id=p_keep where sample_id=p_retire;
 update public.ydna_sync_reviews set sample_id=p_keep where sample_id=p_retire;
 for ident in
  select distinct namespace,external_id from (
   select 'ftdna' namespace,upper(trim(kit_number)) external_id from public."Modern_published_samples" where id in (p_keep,p_retire) and trim(kit_number) ~* '^[A-Z]{0,3}[0-9]+$' and trim(kit_number) !~* '^YF[0-9]+$'
   union all select 'yfull',upper(trim(yfull_id)) from public."Modern_published_samples" where id in (p_keep,p_retire) and trim(yfull_id) ~* '^YF[0-9]+$'
   union all select 'yfull',upper(trim(kit_number)) from public."Modern_published_samples" where id in (p_keep,p_retire) and trim(kit_number) ~* '^YF[0-9]+$'
  ) ids
 loop
  insert into public.ydna_sync_identities(namespace,external_id,sample_id,evidence_url)
   values(ident.namespace,ident.external_id,p_keep,p_evidence_url) on conflict do nothing;
 end loop;
 update public."Modern_published_samples" set sync_visibility='merged',sync_merged_into=p_keep where id=p_retire;
 return jsonb_build_object('status','merged','canonical_id',p_keep,'retired_id',p_retire,'origin_review',origins_differ);
end;
$$;
revoke all on function public.ydna_sync_merge_duplicate(bigint,bigint,text) from public,anon,authenticated;
grant execute on function public.ydna_sync_merge_duplicate(bigint,bigint,text) to service_role;
