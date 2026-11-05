-- Owner-only curation. Existing public read rules are retained; hidden records
-- get an additional restrictive guard. No email, password or participant data here.
create schema if not exists ydna_editor;
revoke all on schema ydna_editor from public,anon,authenticated;
grant usage on schema ydna_editor to authenticated,service_role;
create table ydna_editor.administrators(email text primary key check(email=lower(email)),user_id uuid,enabled boolean not null default true);
create table ydna_editor.audit(sequence bigint generated always as identity unique,id uuid primary key,actor uuid not null,action text not null,kind text not null,record_key text not null,
 request_hash text not null,before_state jsonb not null,after_state jsonb not null,reason text not null default '',created_at timestamptz not null default now(),undone_at timestamptz);
alter table ydna_editor.administrators enable row level security;
alter table ydna_editor.audit enable row level security;
revoke all on all tables in schema ydna_editor from public,anon,authenticated;
grant all on all tables in schema ydna_editor to service_role;
alter table public."Modern_study_samples" add column if not exists governorate text;
create index editor_audit_subject on ydna_editor.audit(kind,record_key,created_at desc);

create function ydna_editor.assert_owner() returns uuid language plpgsql security definer set search_path='' as $$
declare actor uuid:=auth.uid(); session_text text:=auth.jwt()->>'session_id';
begin
 if actor is null or not exists(select 1 from auth.users u join ydna_editor.administrators a on a.email=lower(u.email)
  where u.id=actor and a.enabled and (a.user_id is null or a.user_id=actor) and u.email_confirmed_at is not null
  and u.deleted_at is null and (u.banned_until is null or u.banned_until<now()))
 then raise exception 'Administrator sign-in required' using errcode='42501'; end if;
 if session_text is null or not exists(select 1 from auth.sessions s where s.id::text=session_text and s.user_id=actor)
 then raise exception 'Active administrator session required' using errcode='42501'; end if;
 return actor;
end $$;

create function ydna_editor.table_for(kind text) returns regclass language plpgsql immutable set search_path='' as $$
begin return case kind when 'modern' then 'public."Modern_published_samples"'::regclass when 'collected' then 'public.ydna_uploaded_profiles'::regclass
 when 'study' then 'public."Modern_study_samples"'::regclass when 'ancient' then 'public."Ancient_published_samples"'::regclass
 when 'related' then 'public.ancient_related_samples'::regclass else null end;
end $$;
create function ydna_editor.key_for(kind text) returns text language sql immutable set search_path='' as $$select case when kind='collected' then 'record_key' else 'id' end$$;
create function ydna_editor.version(row_data jsonb) returns text language sql immutable set search_path='' as $$select encode(sha256(convert_to(row_data::text,'UTF8')),'hex')$$;

do $$ declare t regclass;k text;begin
 foreach k in array array['modern','collected','study','ancient','related'] loop
 t:=ydna_editor.table_for(k);
 execute format('alter table %s add column owner_active boolean not null default true, add column owner_modified_at timestamptz, add column owner_merged_kind text, add column owner_merged_key text',t);
 execute format('create policy owner_visibility_guard on %s as restrictive for select to anon,authenticated using(owner_active)',t);
 end loop;
end $$;

create function ydna_editor.row_data(kind text,key text,lock_row boolean default false) returns jsonb language plpgsql set search_path='' as $$
declare t regclass:=ydna_editor.table_for(kind);r jsonb;
begin
 if t is null then raise exception 'Unsupported sample category'; end if;
 execute format('select to_jsonb(t) from %s t where %I::text=$1%s',t,ydna_editor.key_for(kind),case when lock_row then ' for update' else '' end) into r using key;
 if r is null then raise exception 'Sample not found'; end if;return r;
end $$;

create function ydna_editor.put_row(kind text,key text,patch jsonb) returns jsonb language plpgsql set search_path='' as $$
declare t regclass:=ydna_editor.table_for(kind);assignments text;r jsonb;
begin
 select string_agg(format('%I=(jsonb_populate_record(null::%s,$1)).%I',x.key,t,x.key),',') into assignments
 from jsonb_each(patch) x where x.key<>ydna_editor.key_for(kind)
 and exists(select 1 from pg_attribute a where a.attrelid=t and a.attname=x.key and a.attnum>0 and not a.attisdropped);
 if assignments is null then raise exception 'No editable fields';end if;
 execute format('update %s as t set %s where %I::text=$2 returning to_jsonb(t)',t,assignments,ydna_editor.key_for(kind)) into r using patch,key;
 return r;
end $$;

create function ydna_editor.check_patch(kind text,patch jsonb) returns jsonb language plpgsql set search_path='' as $$
declare k text;v jsonb;allowed text[];t regclass:=ydna_editor.table_for(kind);
begin
 if t is null or jsonb_typeof(patch)<>'object' or octet_length(patch::text)>60000 then raise exception 'Invalid sample fields';end if;
 allowed:=case kind when 'modern' then array['name','kit_number','yfull_id','test_type','ethnic_group','origin_raw','governorate','y_dna','mt_dna','snp_path','full_snp_path','full_mtDNA_path','y_link_1','y_link_2','mt_link_1','mt_link_2','y_dna_alias']
 when 'collected' then array['name','ancestor_name','origin_raw','governorate','y_dna']
 when 'study' then array['sample_id','governorate','ethnic_group','y_dna','mt_dna','snp_path','full_snp_path','full_mtDNA_path','y_link_1','y_link_2','mt_link_1','mt_link_2','study_link','y_dna_alias']
 else array['name','sample_id','period','site','country','governorate','cultural_group','y_dna','mt_dna','snp_path','full_snp_path','full_mtDNA_path','full_mtdna_path','y_link_1','y_link_2','mt_link_1','mt_link_2','study_reference','Description','y_dna_alias'] end;
 for k,v in select * from jsonb_each(patch) loop
 if not k=any(allowed) or jsonb_typeof(v) not in ('string','null') or length(coalesce(v#>>'{}',''))>8000
 or not exists(select 1 from pg_attribute a where a.attrelid=t and a.attname=k and a.attnum>0 and not a.attisdropped)
 then raise exception 'Invalid or unavailable field: %',k;end if;
 if k ~ '^(y_link_|mt_link_|study_link)' and coalesce(v#>>'{}','') not in ('','—') and v#>>'{}' !~ '^https://' then raise exception 'Source links require HTTPS';end if;
 end loop;
 if patch ? 'governorate' and coalesce(patch->>'governorate','') not in ('','—','Al Bahr al Ahmar','Al Buhayrah','Ad Daqahlīyah','Al Fayyūm','Al Gharbīyah','Al Iskandarīyah','Al Ismā`īlīyah','Al Minūfīyah','Al Minyā','Al Qalyūbīyah','As Suways','Ash Sharqīyah','Aswān','Asyūt','Banī Suwayf','Cairo','Dumyāt','Al Jīzah','Janūb Sīnā''','Kafr ash Shaykh','Luxor','Matrouh','Qinā','Shamal Sīnā''','Sūhāj','Port Said','New Valley') then raise exception 'Choose a listed governorate';end if;
 if coalesce(patch->>'y_dna','') not in ('','—') and patch->>'y_dna' !~ '^[A-T][A-Za-z0-9*.+_-]*$' then raise exception 'Invalid Y-DNA branch';end if;
 if coalesce(patch->>'kit_number','') not in ('','—') and (upper(patch->>'kit_number') !~ '^[A-Z]{0,3}[0-9]+$' or upper(patch->>'kit_number') ~ '^YF[0-9]+$') then raise exception 'Enter a FamilyTreeDNA kit in the kit field';end if;
 if coalesce(patch->>'yfull_id','') not in ('','—') and upper(patch->>'yfull_id') !~ '^YF[0-9]+$' then raise exception 'Invalid YFull ID';end if;
 if patch ? 'kit_number' then patch:=jsonb_set(patch,'{kit_number}',to_jsonb(upper(coalesce(patch->>'kit_number',''))));end if;
 if patch ? 'yfull_id' then patch:=jsonb_set(patch,'{yfull_id}',to_jsonb(upper(coalesce(patch->>'yfull_id',''))));end if;
 return patch;
end $$;

create function ydna_editor.check_ids(data jsonb,self_key text) returns void language plpgsql set search_path='' as $$
declare kit text:=upper(trim(coalesce(data->>'kit_number','')));yf text:=upper(trim(coalesce(data->>'yfull_id','')));
begin
 if kit ~ '^[A-Z]{0,3}[0-9]+$' and exists(select 1 from public.ydna_sync_optouts where identity_hash=encode(sha256(convert_to('ftdna:'||kit,'UTF8')),'hex')) then raise exception 'This kit has an opt-out';end if;
 if yf ~ '^YF[0-9]+$' and exists(select 1 from public.ydna_sync_optouts where identity_hash=encode(sha256(convert_to('yfull:'||yf,'UTF8')),'hex')) then raise exception 'This YFull ID has an opt-out';end if;
 if exists(select 1 from public.ydna_sync_identities i where i.sample_id::text is distinct from self_key and ((i.namespace='ftdna' and i.external_id=kit) or (i.namespace='yfull' and i.external_id=yf))) then raise exception 'An existing identity link uses that ID. Review or merge the existing sample';end if;
 if exists(select 1 from public."Modern_published_samples" s where s.id::text is distinct from self_key and s.sync_visibility='public' and
 ((kit ~ '^[A-Z]{0,3}[0-9]+$' and upper(trim(s.kit_number))=kit) or (yf ~ '^YF[0-9]+$' and (upper(trim(s.yfull_id))=yf or upper(trim(s.kit_number))=yf)))) then raise exception 'An existing sample has that ID. Edit or merge that sample instead';end if;
end $$;

create function ydna_editor.context() returns jsonb language plpgsql security definer set search_path='' as $$
declare actor uuid:=ydna_editor.assert_owner();begin return jsonb_build_object('administrator',true,'actor',actor);end $$;
create function ydna_editor.list_samples(p_kind text,p_query text default '',p_governorate text default '',p_visibility text default 'active',p_offset integer default 0)
returns jsonb language plpgsql security definer set search_path='' as $$
declare actor uuid:=ydna_editor.assert_owner();t regclass:=ydna_editor.table_for(p_kind);rows jsonb;n bigint;filter text;
begin
 if t is null or p_offset<0 or p_offset>1000000 or length(p_query)>200 then raise exception 'Invalid list request';end if;
 filter:='($1='''' or concat_ws('' '',to_jsonb(t)->>''name'',to_jsonb(t)->>''sample_id'',to_jsonb(t)->>''kit_number'',to_jsonb(t)->>''yfull_id'',to_jsonb(t)->>''ancestor_name'',to_jsonb(t)->>''y_dna'',to_jsonb(t)->>''mt_dna'') ilike ''%''||$1||''%'') and ($2='''' or case when $2=''—'' then coalesce(to_jsonb(t)->>''governorate'','''') in ('''',''—'',''-'') else to_jsonb(t)->>''governorate''=$2 end) and ($3=''all'' or t.owner_active=($3=''active''))';
 execute format('select count(*) from %s t where %s',t,filter) into n using p_query,p_governorate,p_visibility;
 execute format('select coalesce(jsonb_agg(v),''[]''::jsonb) from (select to_jsonb(t)||jsonb_build_object(''__key'',%I::text,''__kind'',$4,''__version'',ydna_editor.version(to_jsonb(t))) v from %s t where %s order by %I limit 60 offset $5) q',ydna_editor.key_for(p_kind),t,filter,ydna_editor.key_for(p_kind)) into rows using p_query,p_governorate,p_visibility,p_kind,p_offset;
 return jsonb_build_object('rows',rows,'total',n,'offset',p_offset);
end $$;

create function ydna_editor.save_sample(p_kind text,p_key text,p_patch jsonb,p_version text,p_request uuid)
returns jsonb language plpgsql security definer set search_path='' as $$
declare actor uuid:=ydna_editor.assert_owner();t regclass:=ydna_editor.table_for(p_kind);old jsonb:='{}';data jsonb;result jsonb;k text:=p_key;
 h text:=ydna_editor.version(jsonb_build_array('save',p_kind,p_key,p_patch,p_version));prior ydna_editor.audit%rowtype;cols text;vals text;manual_hash text;is_new boolean:=p_key is null;
begin
 perform pg_advisory_xact_lock(hashtextextended('egypt-ydna-sync',0));
 select * into prior from ydna_editor.audit where id=p_request;
 if found then if prior.actor<>actor or prior.request_hash<>h then raise exception 'Request already used';end if;return prior.after_state;end if;
 p_patch:=ydna_editor.check_patch(p_kind,p_patch);
 if not is_new then old:=ydna_editor.row_data(p_kind,k,true);if ydna_editor.version(old) is distinct from p_version then raise exception 'Sample changed since loading. Reload before saving';end if;end if;
 data:=old||p_patch;
 if p_kind<>'study' and coalesce(nullif(trim(data->>'name'),''),nullif(data->>'kit_number',''),nullif(data->>'yfull_id',''),nullif(data->>'sample_id','')) is null then raise exception 'A sample name or ID is required';end if;
 if p_kind='study' and coalesce(data->>'sample_id','')='' then raise exception 'Study sample ID is required';end if;
 if p_kind='modern' then perform ydna_editor.check_ids(data,k);p_patch:=p_patch||jsonb_build_object('sync_managed',false,'sync_updated_at',now(),'sync_origin_conflict',false);end if;
 if p_kind='collected' then
 if coalesce(data->>'name','')='' or coalesce(data->>'y_dna','') !~ '^[A-T]-[A-Z0-9*.+_-]+$' then raise exception 'Collected samples require a name and terminal Y-DNA branch';end if;
 if p_patch ? 'governorate' then
 if coalesce(p_patch->>'governorate','') in ('','—') then p_patch:=jsonb_set(p_patch,'{governorate}','null'::jsonb);end if;
 p_patch:=p_patch||jsonb_build_object('location_status',case when coalesce(p_patch->>'governorate','') in ('','—') then 'unknown' else 'resolved' end,'location_evidence',jsonb_build_object('basis','owner_curation'),'governorate_iso',null);end if;
 if p_patch ? 'y_dna' and p_patch->>'y_dna' is distinct from old->>'y_dna' then p_patch:=p_patch||jsonb_build_object('snp_path','[]'::jsonb,'tree_path','[]'::jsonb,'path_kind','terminal_only','path_source_url',null,'y_dna_alias',null,'yfull_reference_url',null);end if;
 end if;
 p_patch:=p_patch||jsonb_build_object('owner_modified_at',now());
 if is_new then
 if p_kind='collected' then
 manual_hash:=encode(sha256(convert_to('owner-manual-collected-samples','UTF8')),'hex');k:=encode(sha256(convert_to(p_request::text,'UTF8')),'hex');
 insert into public.ydna_uploaded_files(file_hash,file_name,row_count,published) values(manual_hash,'Manual collected samples',0,true) on conflict do nothing;
 p_patch:=p_patch||jsonb_build_object('record_key',k,'file_hash',manual_hash,'sheet_name','Manual','row_number',2,'country_code','EG','identity_state','unlinked','location_status',coalesce(p_patch->>'location_status','unknown'),'path_kind','terminal_only','published',true);
 else
 if (select a.attidentity='' and a.atthasdef=false from pg_attribute a where a.attrelid=t and a.attname='id') then execute format('select coalesce(max(id),0)+1 from %s',t) into k;p_patch:=p_patch||jsonb_build_object('id',k::bigint);end if;
 end if;
 select string_agg(format('%I',x.key),','),string_agg(format('(jsonb_populate_record(null::%s,$1)).%I',t,x.key),',') into cols,vals from jsonb_each(p_patch) x;
 execute format('insert into %s as t(%s) select %s returning to_jsonb(t)',t,cols,vals) into data using p_patch;
 k:=data->>ydna_editor.key_for(p_kind);
 else data:=ydna_editor.put_row(p_kind,k,p_patch);end if;
 if p_kind='modern' then
 if coalesce(data->>'kit_number','') ~ '^[A-Z]{0,3}[0-9]+$' then
 insert into public.ydna_sync_identities(namespace,external_id,sample_id,evidence_url) values('ftdna',data->>'kit_number',k::bigint,'https://egyptydna.github.io/Egypt-Y-DNA/') on conflict do nothing;
 insert into public.ydna_project_targets(target_key,kind,sample_id) values('kit:'||k,'kit',k::bigint) on conflict do nothing;
 end if;
 if coalesce(data->>'yfull_id','') ~ '^YF[0-9]+$' then insert into public.ydna_sync_identities(namespace,external_id,sample_id,evidence_url) values('yfull',data->>'yfull_id',k::bigint,'https://egyptydna.github.io/Egypt-Y-DNA/') on conflict do nothing;end if;
 if is_new then insert into public.ydna_project_profile_activity(sample_id,new_until) values(k::bigint,now()+interval '30 days') on conflict do nothing;end if;
 end if;
 result:=jsonb_build_object('kind',p_kind,'key',k,'version',ydna_editor.version(data),'data',data);
 insert into ydna_editor.audit(id,actor,action,kind,record_key,request_hash,before_state,after_state) values(p_request,actor,case when is_new then 'create' else 'update' end,p_kind,k,h,old,result);
 return result;
end $$;

create function ydna_editor.visibility(p_kind text,p_key text,p_active boolean,p_version text,p_reason text,p_request uuid)
returns jsonb language plpgsql security definer set search_path='' as $$
declare actor uuid:=ydna_editor.assert_owner();old jsonb;data jsonb;r jsonb;h text:=ydna_editor.version(jsonb_build_array('visibility',p_kind,p_key,p_active,p_version,p_reason));prior ydna_editor.audit%rowtype;
begin
 perform pg_advisory_xact_lock(hashtextextended('egypt-ydna-sync',0));
 select * into prior from ydna_editor.audit where id=p_request;if found then if prior.actor<>actor or prior.request_hash<>h then raise exception 'Request already used';end if;return prior.after_state;end if;
 old:=ydna_editor.row_data(p_kind,p_key,true);
 if ydna_editor.version(old) is distinct from p_version then raise exception 'Sample changed since loading. Reload first';end if;
 if length(trim(p_reason))<3 then raise exception 'Please provide a reason';end if;
 if p_active and (old->>'owner_merged_key' is not null or (p_kind='modern' and old->>'sync_visibility'<>'public')) then raise exception 'A merged or opted-out sample requires identity review before restoring';end if;
 data:=ydna_editor.put_row(p_kind,p_key,jsonb_build_object('owner_active',p_active,'owner_modified_at',now()));
 r:=jsonb_build_object('kind',p_kind,'key',p_key,'version',ydna_editor.version(data),'data',data);
 insert into ydna_editor.audit(id,actor,action,kind,record_key,request_hash,before_state,after_state,reason) values(p_request,actor,case when p_active then 'restore' else 'remove' end,p_kind,p_key,h,old,r,p_reason);return r;
end $$;

create function ydna_editor.merge_samples(p_keep_kind text,p_keep_key text,p_other_kind text,p_other_key text,p_keep_version text,p_other_version text,p_reason text,p_confirm boolean,p_request uuid)
returns jsonb language plpgsql security definer set search_path='' as $$
declare actor uuid:=ydna_editor.assert_owner();a jsonb;b jsonb;patch jsonb:='{}';k text;v jsonb;after_a jsonb;after_b jsonb;r jsonb;
 h text:=ydna_editor.version(jsonb_build_array('merge',p_keep_kind,p_keep_key,p_other_kind,p_other_key,p_keep_version,p_other_version,p_reason));prior ydna_editor.audit%rowtype;before_meta jsonb:='{}';
begin
 perform pg_advisory_xact_lock(hashtextextended('egypt-ydna-sync',0));
 select * into prior from ydna_editor.audit where id=p_request;if found then if prior.actor<>actor or prior.request_hash<>h then raise exception 'Request already used';end if;return prior.after_state;end if;
 if not p_confirm or length(trim(p_reason))<5 or (p_keep_kind=p_other_kind and p_keep_key=p_other_key) then raise exception 'Confirm the same person and document the reason';end if;
 if p_keep_kind<>p_other_kind and not(p_keep_kind='modern' and p_other_kind='collected') then raise exception 'Cross-category links keep a modern sample and attach a collected sample. Choose that order';end if;
 a:=ydna_editor.row_data(p_keep_kind,p_keep_key,true);b:=ydna_editor.row_data(p_other_kind,p_other_key,true);
 if ydna_editor.version(a) is distinct from p_keep_version or ydna_editor.version(b) is distinct from p_other_version then raise exception 'A sample changed. Reload the merge preview';end if;
 if a->>'owner_active'<>'true' or b->>'owner_active'<>'true' or (p_keep_kind='modern' and a->>'sync_visibility'<>'public') or (p_other_kind='modern' and b->>'sync_visibility'<>'public') then raise exception 'Only active public samples can be merged';end if;
 if coalesce(a->>'kit_number','') ~ '^[A-Z]{0,3}[0-9]+$' and coalesce(b->>'kit_number','') ~ '^[A-Z]{0,3}[0-9]+$' and a->>'kit_number' !~ '^YF[0-9]+$' and b->>'kit_number' !~ '^YF[0-9]+$' and a->>'kit_number'<>b->>'kit_number' then raise exception 'Different kit IDs require identity review; they are not automatically discarded';end if;
 if coalesce(a->>'yfull_id','') ~ '^YF[0-9]+$' and coalesce(b->>'yfull_id','') ~ '^YF[0-9]+$' and a->>'yfull_id'<>b->>'yfull_id' then raise exception 'Different YFull IDs require identity review';end if;
 for k,v in select * from jsonb_each(b) loop
 if k in ('name','kit_number','yfull_id','test_type','ethnic_group','origin_raw','governorate','y_dna','mt_dna','snp_path','full_snp_path','full_mtDNA_path','full_mtdna_path','y_link_1','y_link_2','mt_link_1','mt_link_2','ancestor_name','Description','study_reference','period','site','country','cultural_group')
 and coalesce(a->>k,'') in ('','—','-') and coalesce(v#>>'{}','') not in ('','—','-') then patch:=patch||jsonb_build_object(k,v);end if;
 end loop;
 if p_keep_kind='modern' then
 if coalesce(a->>'kit_number','') ~ '^YF[0-9]+$' then
  if coalesce(a->>'yfull_id','') in ('','—') then patch:=patch||jsonb_build_object('yfull_id',a->>'kit_number');end if;
  if coalesce(b->>'kit_number','') ~ '^[A-Z]{0,3}[0-9]+$' and b->>'kit_number' !~ '^YF[0-9]+$' then patch:=patch||jsonb_build_object('kit_number',b->>'kit_number');end if;
 elsif coalesce(b->>'kit_number','') ~ '^YF[0-9]+$' and coalesce(a->>'yfull_id','') in ('','—') then patch:=patch||jsonb_build_object('yfull_id',b->>'kit_number');end if;
 patch:=patch||jsonb_build_object('sync_managed',false,'sync_updated_at',now());end if;
 after_a:=ydna_editor.put_row(p_keep_kind,p_keep_key,patch||jsonb_build_object('owner_modified_at',now()));
 if p_keep_kind='modern' and p_other_kind='modern' then
 before_meta:=jsonb_build_object('identities',(select coalesce(jsonb_agg(to_jsonb(i)),'[]') from public.ydna_sync_identities i where sample_id=p_other_key::bigint),
 'observations',(select coalesce(jsonb_agg(jsonb_build_object('id',id,'sample_id',sample_id)),'[]') from public.ydna_sync_observations where sample_id=p_other_key::bigint),
 'memberships',(select coalesce(jsonb_agg(to_jsonb(m)),'[]') from public.ydna_project_memberships m where sample_id in (p_keep_key::bigint,p_other_key::bigint)));
 insert into public.ydna_sync_identity_merges(retired_id,canonical_id,evidence_url,original_canonical,original_retired) values(p_other_key::bigint,p_keep_key::bigint,'https://github.com/egyptydna/Egypt-Y-DNA/blob/main/docs/OWNER-ADMIN.md',a,b);
 update public.ydna_sync_identities set sample_id=p_keep_key::bigint where sample_id=p_other_key::bigint;
 update public.ydna_sync_observations set sample_id=p_keep_key::bigint where sample_id=p_other_key::bigint;
 insert into public.ydna_project_memberships(sample_id,project_key,observation_id,evidence_url,first_seen_at,last_seen_at,is_baseline)
 select p_keep_key::bigint,project_key,observation_id,evidence_url,first_seen_at,last_seen_at,is_baseline from public.ydna_project_memberships where sample_id=p_other_key::bigint on conflict(sample_id,project_key) do nothing;
 delete from public.ydna_project_memberships where sample_id=p_other_key::bigint;
 after_b:=ydna_editor.put_row(p_other_kind,p_other_key,jsonb_build_object('owner_active',false,'owner_merged_kind',p_keep_kind,'owner_merged_key',p_keep_key,'owner_modified_at',now(),'sync_visibility','merged','sync_merged_into',p_keep_key::bigint));
 else after_b:=ydna_editor.put_row(p_other_kind,p_other_key,jsonb_build_object('owner_active',false,'owner_merged_kind',p_keep_kind,'owner_merged_key',p_keep_key,'owner_modified_at',now()));end if;
 r:=jsonb_build_object('kind',p_keep_kind,'key',p_keep_key,'version',ydna_editor.version(after_a),'data',after_a,'other_kind',p_other_kind,'other_key',p_other_key,'other_version',ydna_editor.version(after_b));
 insert into ydna_editor.audit(id,actor,action,kind,record_key,request_hash,before_state,after_state,reason) values(p_request,actor,'merge',p_keep_kind,p_keep_key,h,jsonb_build_object('keep',a,'other',b,'metadata',before_meta),r,p_reason);
 return r;
end $$;

create function ydna_editor.history() returns jsonb language plpgsql security definer set search_path='' as $$
declare actor uuid:=ydna_editor.assert_owner();r jsonb;
begin select coalesce(jsonb_agg(x),'[]') into r from (select id,action,kind,record_key,reason,created_at,undone_at from ydna_editor.audit order by sequence desc limit 60)x;return r;end $$;
create function ydna_editor.undo_change(p_id uuid,p_request uuid) returns jsonb language plpgsql security definer set search_path='' as $$
declare actor uuid:=ydna_editor.assert_owner();a ydna_editor.audit%rowtype;current_row jsonb;r jsonb;other jsonb;x jsonb;
begin
 perform pg_advisory_xact_lock(hashtextextended('egypt-ydna-sync',0));
 select * into strict a from ydna_editor.audit where id=p_id for update;
 if a.undone_at is not null then raise exception 'This change is already restored';end if;
 current_row:=ydna_editor.row_data(a.kind,a.record_key,true);
 if ydna_editor.version(current_row) is distinct from a.after_state->>'version' then raise exception 'A newer change exists; restore it first';end if;
 if a.kind='modern' and current_row->>'sync_visibility'='opted_out' then raise exception 'An opt-out cannot be restored';end if;
 if a.action='create' then r:=ydna_editor.put_row(a.kind,a.record_key,jsonb_build_object('owner_active',false,'owner_modified_at',now()));
 elsif a.action='merge' then
 other:=ydna_editor.row_data(a.after_state->>'other_kind',a.after_state->>'other_key',true);
 if ydna_editor.version(other) is distinct from a.after_state->>'other_version' then raise exception 'The linked sample changed after the merge';end if;
 r:=ydna_editor.put_row(a.kind,a.record_key,a.before_state->'keep');
 perform ydna_editor.put_row(a.after_state->>'other_kind',a.after_state->>'other_key',a.before_state->'other');
 if a.kind='modern' and a.after_state->>'other_kind'='modern' then
 for x in select * from jsonb_array_elements(a.before_state#>'{metadata,identities}') loop update public.ydna_sync_identities set sample_id=(x->>'sample_id')::bigint where namespace=x->>'namespace' and external_id=x->>'external_id';end loop;
 for x in select * from jsonb_array_elements(a.before_state#>'{metadata,observations}') loop update public.ydna_sync_observations set sample_id=(x->>'sample_id')::bigint where id=(x->>'id')::bigint;end loop;
 -- Remove only transferred memberships that had no original keeper record and
 -- still match the copied evidence. Later independent evidence is preserved.
 delete from public.ydna_project_memberships m using jsonb_array_elements(a.before_state#>'{metadata,memberships}') original
 where original->>'sample_id'=a.after_state->>'other_key' and m.sample_id=a.record_key::bigint
 and m.project_key=original->>'project_key' and m.observation_id is not distinct from (original->>'observation_id')::bigint
 and m.last_seen_at is not distinct from (original->>'last_seen_at')::timestamptz
 and not exists(select 1 from jsonb_array_elements(a.before_state#>'{metadata,memberships}') keeper
 where keeper->>'sample_id'=a.record_key and keeper->>'project_key'=m.project_key);
 -- Restore original membership ownership without deleting later evidence.
 for x in select * from jsonb_array_elements(a.before_state#>'{metadata,memberships}') loop
 insert into public.ydna_project_memberships select * from jsonb_populate_record(null::public.ydna_project_memberships,x) on conflict(sample_id,project_key) do nothing;end loop;
 delete from public.ydna_sync_identity_merges where retired_id=(a.after_state->>'other_key')::bigint and canonical_id=a.record_key::bigint;
 end if;
 else r:=ydna_editor.put_row(a.kind,a.record_key,a.before_state);end if;
 update ydna_editor.audit set undone_at=now() where id=p_id;
 insert into ydna_editor.audit(id,actor,action,kind,record_key,request_hash,before_state,after_state,reason)
 values(p_request,actor,'undo',a.kind,a.record_key,ydna_editor.version(jsonb_build_array('undo',p_id)),current_row,jsonb_build_object('kind',a.kind,'key',a.record_key,'version',ydna_editor.version(r),'data',r),'Restore prior saved state');
 return jsonb_build_object('kind',a.kind,'key',a.record_key,'version',ydna_editor.version(r),'data',r);
end $$;

-- Private helpers are never a public API. Every exposed entry checks a live,
-- verified owner session and runs with a fixed empty search_path.
revoke all on all functions in schema ydna_editor from public,anon,authenticated;
grant execute on function ydna_editor.context(),ydna_editor.list_samples(text,text,text,text,integer),ydna_editor.save_sample(text,text,jsonb,text,uuid),ydna_editor.visibility(text,text,boolean,text,text,uuid),ydna_editor.merge_samples(text,text,text,text,text,text,text,boolean,uuid),ydna_editor.history(),ydna_editor.undo_change(uuid,uuid) to authenticated;
create function public.ydna_editor_context() returns jsonb language sql security invoker set search_path='' as $$select ydna_editor.context()$$;
create function public.ydna_editor_list(p_kind text,p_query text default '',p_governorate text default '',p_visibility text default 'active',p_offset integer default 0) returns jsonb language sql security invoker set search_path='' as $$select ydna_editor.list_samples(p_kind,p_query,p_governorate,p_visibility,p_offset)$$;
create function public.ydna_editor_save(p_kind text,p_key text,p_patch jsonb,p_version text,p_request uuid) returns jsonb language sql security invoker set search_path='' as $$select ydna_editor.save_sample(p_kind,p_key,p_patch,p_version,p_request)$$;
create function public.ydna_editor_visibility(p_kind text,p_key text,p_active boolean,p_version text,p_reason text,p_request uuid) returns jsonb language sql security invoker set search_path='' as $$select ydna_editor.visibility(p_kind,p_key,p_active,p_version,p_reason,p_request)$$;
create function public.ydna_editor_merge(p_keep_kind text,p_keep_key text,p_other_kind text,p_other_key text,p_keep_version text,p_other_version text,p_reason text,p_confirm boolean,p_request uuid) returns jsonb language sql security invoker set search_path='' as $$select ydna_editor.merge_samples(p_keep_kind,p_keep_key,p_other_kind,p_other_key,p_keep_version,p_other_version,p_reason,p_confirm,p_request)$$;
create function public.ydna_editor_history() returns jsonb language sql security invoker set search_path='' as $$select ydna_editor.history()$$;
create function public.ydna_editor_undo(p_id uuid,p_request uuid) returns jsonb language sql security invoker set search_path='' as $$select ydna_editor.undo_change(p_id,p_request)$$;
revoke all on function public.ydna_editor_context(),public.ydna_editor_list(text,text,text,text,integer),public.ydna_editor_save(text,text,jsonb,text,uuid),public.ydna_editor_visibility(text,text,boolean,text,text,uuid),public.ydna_editor_merge(text,text,text,text,text,text,text,boolean,uuid),public.ydna_editor_history(),public.ydna_editor_undo(uuid,uuid) from public,anon,authenticated;
grant execute on function public.ydna_editor_context(),public.ydna_editor_list(text,text,text,text,integer),public.ydna_editor_save(text,text,jsonb,text,uuid),public.ydna_editor_visibility(text,text,boolean,text,text,uuid),public.ydna_editor_merge(text,text,text,text,text,text,text,boolean,uuid),public.ydna_editor_history(),public.ydna_editor_undo(uuid,uuid) to authenticated;

-- Existing opt-outs must also redact private curation snapshots.
create function ydna_editor.purge_optout_audit() returns trigger language plpgsql security invoker set search_path='' as $$
begin
 if new.sync_visibility='opted_out' then
 update ydna_editor.audit set before_state='{}'::jsonb,after_state='{}'::jsonb,reason='Redacted following opt-out'
 where (kind='modern' and record_key=new.id::text) or (after_state->>'other_kind'='modern' and after_state->>'other_key'=new.id::text);
 end if;return new;
end $$;
revoke all on function ydna_editor.purge_optout_audit() from public,anon,authenticated;
create trigger editor_optout_redaction after update of sync_visibility on public."Modern_published_samples" for each row when(new.sync_visibility='opted_out') execute function ydna_editor.purge_optout_audit();
