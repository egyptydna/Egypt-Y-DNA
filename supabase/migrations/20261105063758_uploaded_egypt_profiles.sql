-- Owner-supplied source records without external IDs. Never counted as newly
-- identified people and never merged into archive profiles by names alone.
create table public.ydna_uploaded_files (
 file_hash text primary key check(file_hash ~ '^[0-9a-f]{64}$'),
 file_name text not null, row_count integer not null check(row_count>=0),
 imported_at timestamptz not null default now(), published boolean not null default true
);
create table public.ydna_uploaded_profiles (
 record_key text primary key check(record_key ~ '^[0-9a-f]{64}$'),
 file_hash text not null references public.ydna_uploaded_files(file_hash),
 sheet_name text not null,row_number integer not null check(row_number>1),
 name text not null,ancestor_name text not null default '',
 country_code text not null check(country_code='EG'),y_dna text not null check(y_dna ~ '^[A-T]-[A-Z0-9*.+_-]+$'),
 y_dna_alias text,yfull_reference_url text,origin_raw text not null default '',governorate text,governorate_iso text,
 location_status text not null check(location_status in ('unknown','resolved','ambiguous','conflict')),
 location_evidence jsonb not null default '{}',
 snp_path jsonb not null default '[]', tree_path jsonb not null default '[]',path_source_url text,
 path_kind text not null check(path_kind in ('ftdna_archived_reference','yfull_reference','terminal_only')),
 identity_state text not null default 'unlinked' check(identity_state='unlinked'),
 imported_at timestamptz not null default now(),published boolean not null default true,
 check(jsonb_typeof(snp_path)='array' and jsonb_typeof(tree_path)='array'),
 check(location_status='resolved' or (governorate is null and governorate_iso is null))
);
create index uploaded_profiles_file on public.ydna_uploaded_profiles(file_hash);
create index uploaded_profiles_terminal on public.ydna_uploaded_profiles(y_dna) where published;
alter table public.ydna_uploaded_files enable row level security;
alter table public.ydna_uploaded_profiles enable row level security;
revoke all on public.ydna_uploaded_files,public.ydna_uploaded_profiles from public,anon,authenticated;
grant select on public.ydna_uploaded_files,public.ydna_uploaded_profiles to anon,authenticated;
grant all on public.ydna_uploaded_files,public.ydna_uploaded_profiles to service_role;
create policy published_upload_files on public.ydna_uploaded_files for select to anon,authenticated using(published);
create policy published_upload_profiles on public.ydna_uploaded_profiles for select to anon,authenticated
 using(published and exists(select 1 from public.ydna_uploaded_files f where f.file_hash=ydna_uploaded_profiles.file_hash and f.published));

create function public.ydna_import_uploaded_profiles(p_payload jsonb,p_dry_run boolean default true)
returns jsonb language plpgsql security invoker set search_path=public,pg_temp as $$
declare f jsonb:=p_payload->'file'; r jsonb; inserted_count integer:=0; one_count integer; conflicts integer:=0;
begin
 perform pg_advisory_xact_lock(hashtextextended('egypt-ydna-uploaded-profiles',0));
 if coalesce(f->>'file_hash','') !~ '^[0-9a-f]{64}$' or coalesce(f->>'file_name','')='' or f->>'file_name' ~ '[/\\]'
  or coalesce(f->>'row_count','') !~ '^[0-9]+$' or jsonb_typeof(p_payload->'rows') is distinct from 'array'
  or jsonb_array_length(p_payload->'rows')>100 then raise exception 'Invalid uploaded workbook batch'; end if;
 for r in select * from jsonb_array_elements(p_payload->'rows') loop
  if coalesce(r->>'record_key','') !~ '^[0-9a-f]{64}$' or r->>'country_code' is distinct from 'EG'
   or coalesce(r->>'name','')='' or coalesce(r->>'y_dna','') !~ '^[A-T]-[A-Z0-9*.+_-]+$'
   or coalesce(r->>'row_number','') !~ '^[0-9]+$' or (r->>'row_number')::int<2
   or jsonb_typeof(r->'snp_path') is distinct from 'array' or jsonb_typeof(r->'tree_path') is distinct from 'array'
   or (jsonb_array_length(r->'tree_path')>0 and r->'tree_path'->>-1 is distinct from r->>'y_dna')
   or (jsonb_array_length(r->'snp_path')>0 and (coalesce(r->>'path_source_url','') not like 'https://%'
    or (r->'snp_path'->>-1 is distinct from r->>'y_dna' and r->'snp_path'->>-1 is distinct from r->>'y_dna_alias')))
   or (r->>'y_dna_alias' is not null and coalesce(r->>'yfull_reference_url','') not like 'https://github.com/YFullTeam/YTree/%')
   or exists(select 1 from jsonb_object_keys(r) k where k not in ('record_key','sheet_name','row_number','name','ancestor_name','country_code','y_dna','y_dna_alias','yfull_reference_url','origin_raw','governorate','governorate_iso','location_status','location_evidence','snp_path','tree_path','path_source_url','path_kind','candidate_ids'))
  then raise exception 'Invalid or excessive fields in uploaded profile'; end if;
 end loop;
 if p_dry_run then return jsonb_build_object('status','dry_run','rows',jsonb_array_length(p_payload->'rows'),'archive_profiles_modified',0); end if;
 insert into public.ydna_uploaded_files(file_hash,file_name,row_count) values(f->>'file_hash',f->>'file_name',(f->>'row_count')::int) on conflict do nothing;
 insert into public.ydna_sync_sources(id,url,adapter,publication_allowed,permission_url,metadata)
 values('owner-egypt-workbook','https://github.com/egyptydna/Egypt-Y-DNA','owner_uploaded_workbook',true,
 'https://github.com/egyptydna/Egypt-Y-DNA/blob/main/docs/WORKBOOK-IMPORT.md','{"scope":"Owner-provided source records; no external kit identity asserted"}') on conflict do nothing;
 for r in select * from jsonb_array_elements(p_payload->'rows') loop
  insert into public.ydna_uploaded_profiles(record_key,file_hash,sheet_name,row_number,name,ancestor_name,country_code,y_dna,y_dna_alias,yfull_reference_url,origin_raw,governorate,governorate_iso,location_status,location_evidence,snp_path,tree_path,path_source_url,path_kind)
  values(r->>'record_key',f->>'file_hash',r->>'sheet_name',(r->>'row_number')::int,r->>'name',r->>'ancestor_name','EG',r->>'y_dna',r->>'y_dna_alias',r->>'yfull_reference_url',r->>'origin_raw',r->>'governorate',r->>'governorate_iso',r->>'location_status',r->'location_evidence',r->'snp_path',r->'tree_path',r->>'path_source_url',r->>'path_kind') on conflict do nothing;
  get diagnostics one_count=row_count;inserted_count:=inserted_count+one_count;
  if jsonb_array_length(coalesce(r->'candidate_ids','[]'))>0 then
   perform public.ydna_sync_review(null,'owner-egypt-workbook','uploaded_profile_possible_identity',jsonb_build_object('record_key',r->>'record_key','candidate_ids',r->'candidate_ids','policy','Name similarity only; no identity merge'));
   conflicts:=conflicts+1;
  end if;
  if r->>'location_status' in ('ambiguous','conflict') then
   perform public.ydna_sync_review(null,'owner-egypt-workbook','uploaded_profile_location',jsonb_build_object('record_key',r->>'record_key','status',r->>'location_status'));
  end if;
 end loop;
 return jsonb_build_object('status','completed','inserted_source_records',inserted_count,'retained_source_records',jsonb_array_length(p_payload->'rows')-inserted_count,'possible_identity_reviews',conflicts,'archive_profiles_modified',0);
end $$;
revoke all on function public.ydna_import_uploaded_profiles(jsonb,boolean) from public,anon,authenticated;
grant execute on function public.ydna_import_uploaded_profiles(jsonb,boolean) to service_role;
