-- Owner workbench, persistent SNP aliases and reversible curation.
-- No administrator identities or participant records are embedded.
create or replace function ydna_editor.sort_key(variadic items text[]) returns text[] language sql immutable parallel safe set search_path='' as $$
 with chosen as (select regexp_replace(normalize(lower(btrim(value)),NFKD),U&'[\0300-\036f]','','g') value from unnest(items) with ordinality v(value,position) where btrim(value) not in ('','—','-') order by position limit 1),
 tokens as (select parts[1] value,position from chosen,lateral regexp_matches(chosen.value,'[0-9]+|[^0-9]+','g') with ordinality r(parts,position))
 select array_agg(case when value ~ '^[0-9]+$' then '0'||lpad(length(coalesce(nullif(ltrim(value,'0'),''),'0'))::text,8,'0')||coalesce(nullif(ltrim(value,'0'),''),'0') else '1'||value end order by position) from tokens
$$;
revoke all on function ydna_editor.sort_key(text[]) from public,anon,authenticated;
create table public.ydna_owner_lineages(
 record_key text primary key,dna_type text not null check(dna_type in ('y','mt')),canonical_label text not null,canonical_key text not null,
 aliases text[] not null default '{}',match_labels text[] not null,source_url text not null default '',note text not null default '',
 owner_active boolean not null default true,owner_modified_at timestamptz not null default now(),unique(dna_type,canonical_key)
);
create index on public.ydna_owner_lineages using gin(match_labels);
alter table public.ydna_owner_lineages enable row level security;
revoke all on public.ydna_owner_lineages from public,anon,authenticated;
grant select on public.ydna_owner_lineages to anon,authenticated;
create policy lineage_reference_read on public.ydna_owner_lineages for select to anon,authenticated using(owner_active);

create function ydna_editor.identifiers(j jsonb) returns text[] language sql immutable set search_path='' as $$
 select array_remove(array[
 case when upper(btrim(j->>'kit_number')) ~ '^[A-Z]{0,3}[0-9]+$' and upper(btrim(j->>'kit_number')) !~ '^YF[0-9]+$' then 'ftdna:'||upper(btrim(j->>'kit_number')) end,
 case when upper(btrim(j->>'yfull_id')) ~ '^YF[0-9]+$' then 'yfull:'||upper(btrim(j->>'yfull_id')) when upper(btrim(j->>'kit_number')) ~ '^YF[0-9]+$' then 'yfull:'||upper(btrim(j->>'kit_number')) end],null)
$$;
create function ydna_editor.branch_key(p_type text,p_label text) returns text language sql stable set search_path='' as $$
 select case when btrim(coalesce(p_label,'')) in ('','—','-') then null else coalesce((select canonical_key from public.ydna_owner_lineages where dna_type=p_type and owner_active and match_labels @> array[upper(btrim(p_label))] limit 1),upper(btrim(p_label))) end
$$;
create function ydna_editor.lineage_terms(p_type text,p_label text) returns text language sql stable set search_path='' as $$
 select coalesce((select canonical_label||' '||array_to_string(aliases,' ') from public.ydna_owner_lineages where dna_type=p_type and owner_active and match_labels @> array[upper(btrim(p_label))] limit 1),'')
$$;
create function ydna_editor.record_rows(p_kind text) returns setof jsonb language plpgsql stable set search_path='' as $$
declare k text;t regclass;pk text;
begin
 foreach k in array array['modern','collected','study','ancient','related'] loop
  if p_kind not in ('all',k) then continue;end if;t:=ydna_editor.table_for(k);pk:=ydna_editor.key_for(k);
  return query execute format('select to_jsonb(t)||jsonb_build_object(''__kind'',%L,''__key'',%I::text,''__version'',ydna_editor.version(to_jsonb(t))) from %s t',k,pk,t);
 end loop;
end $$;
create function ydna_editor.filtered_rows(o jsonb) returns setof jsonb language plpgsql stable set search_path='' as $$
declare r jsonb;k text:=coalesce(o->>'kind','modern');q text:=btrim(coalesce(o->>'query',''));g text:=coalesce(o->>'governorate','');vis text:=coalesce(o->>'visibility','active');
 ids text[];source text:=coalesce(o->>'ids','');quality text:=coalesce(o->>'quality','');dna text:=coalesce(o->>'dna','y');hap text:=btrim(coalesce(o->>'haplogroup',''));duplicates text[]:='{}';new_until timestamptz;
begin
 if o is null or jsonb_typeof(o)<>'object' or k not in ('all','modern','collected','study','ancient','related') or length(q)>200 or length(hap)>100 or dna not in ('y','mt') or vis not in ('active','hidden','all')
 or source not in ('','ftdna','yfull','both','none') or quality not in ('','unassigned','missing_y','missing_mt','new','duplicate') then raise exception 'Ungültige Filter.';end if;
 if quality='duplicate' then
  select coalesce(array_agg(id),'{}') into duplicates from (select id from ydna_editor.record_rows('all') j cross join lateral unnest(ydna_editor.identifiers(j)) id where j->>'owner_active'='true' group by id having count(*)>1) d;
 end if;
 for r in select * from ydna_editor.record_rows(k) loop
  if vis<>'all' and (r->>'owner_active'='true')<>(vis='active') then continue;end if;
  if g<>'' and ((g='—' and btrim(coalesce(r->>'governorate','')) not in ('','—','-')) or (g<>'—' and r->>'governorate' is distinct from g)) then continue;end if;
  ids:=ydna_editor.identifiers(r);
  if (source='ftdna' and not exists(select 1 from unnest(ids) x where x like 'ftdna:%')) or (source='yfull' and not exists(select 1 from unnest(ids) x where x like 'yfull:%')) or (source='both' and cardinality(ids)<>2) or (source='none' and cardinality(ids)<>0) then continue;end if;
  if hap<>'' and ydna_editor.branch_key(dna,r->>case when dna='y' then 'y_dna' else 'mt_dna' end) is distinct from ydna_editor.branch_key(dna,hap) then continue;end if;
  if q<>'' and concat_ws(' ',r->>'name',r->>'sample_id',r->>'kit_number',r->>'yfull_id',r->>'ancestor_name',r->>'origin_raw',r->>'y_dna',r->>'mt_dna',ydna_editor.lineage_terms('y',r->>'y_dna'),ydna_editor.lineage_terms('mt',r->>'mt_dna')) not ilike '%'||q||'%' then continue;end if;
  if quality='unassigned' and btrim(coalesce(r->>'governorate','')) not in ('','—','-') then continue;end if;
  if quality='missing_y' and btrim(coalesce(r->>'y_dna','')) not in ('','—','-') then continue;end if;
  if quality='missing_mt' and btrim(coalesce(r->>'mt_dna','')) not in ('','—','-') then continue;end if;
  if quality='duplicate' and not ids&&duplicates then continue;end if;
  if quality='new' then
   if r->>'__kind'<>'modern' then continue;end if;
   select a.new_until into new_until from public.ydna_project_profile_activity a where a.sample_id=(r->>'__key')::bigint;
   if new_until is null or new_until<=now() then continue;end if;
  end if;
  return next r;
 end loop;
end $$;
create function ydna_editor.workbench(o jsonb) returns jsonb language plpgsql security definer set search_path='' as $$
declare actor uuid:=ydna_editor.assert_owner();s text:=coalesce(o->>'sort','y_dna');off integer:=coalesce((o->>'offset')::integer,0);lim integer:=coalesce((o->>'limit')::integer,60);descend boolean:=coalesce((o->>'descending')::boolean,false);n bigint;rows jsonb;
begin
 if s not in ('y_dna','mt_dna','name','kit_number','governorate') or off<0 or off>1000000 or lim not in (30,60,120,200) then raise exception 'Ungültige Sortierung oder Seitengröße.';end if;
 with records as materialized(select j,case s when 'name' then ydna_editor.sort_key(j->>'name',j->>'sample_id',j->>'kit_number',j->>'yfull_id') when 'kit_number' then ydna_editor.sort_key(j->>'kit_number',j->>'yfull_id',j->>'sample_id') else ydna_editor.sort_key(j->>s) end as sk from ydna_editor.filtered_rows(o) j),
 page as (select j from records order by case when not descend then sk end collate "C" asc nulls last,case when descend then sk end collate "C" desc nulls last,ydna_editor.sort_key(j->>'name',j->>'sample_id') collate "C" asc nulls last,j->>'__kind',j->>'__key' limit lim offset off)
 select (select count(*) from records),(select coalesce(jsonb_agg(j),'[]') from page) into n,rows;
 return jsonb_build_object('rows',rows,'total',n,'offset',off,'limit',lim);
end $$;
create function ydna_editor.groups(o jsonb) returns jsonb language plpgsql security definer set search_path='' as $$
declare actor uuid:=ydna_editor.assert_owner();dna text:=coalesce(o->>'dna','y');r jsonb;
begin
 select coalesce(jsonb_agg(v order by ydna_editor.sort_key(v->>'label') collate "C"),'[]') into r from (
 select jsonb_build_object('key',branch,'label',coalesce((select l.canonical_label from public.ydna_owner_lineages l where l.owner_active and l.dna_type=dna and l.canonical_key=branch),min(j->>case when dna='y' then 'y_dna' else 'mt_dna' end)),
 'count',count(*),'kinds',array_agg(distinct j->>'__kind')) v from (select j,ydna_editor.branch_key(dna,j->>case when dna='y' then 'y_dna' else 'mt_dna' end) branch from ydna_editor.filtered_rows(o-'haplogroup') j) a where branch is not null group by branch) b;
 return jsonb_build_object('groups',r,'dna',dna);
end $$;

create function ydna_editor.lineages() returns jsonb language plpgsql security definer set search_path='' as $$
declare actor uuid:=ydna_editor.assert_owner();r jsonb;
begin select coalesce(jsonb_agg(to_jsonb(l)||jsonb_build_object('__version',ydna_editor.version(to_jsonb(l))) order by l.dna_type,l.canonical_label),'[]') into r from public.ydna_owner_lineages l;return r;end $$;
create function ydna_editor.lineage_save(p_key text,p_type text,p_label text,p_aliases text[],p_url text,p_note text,p_version text,p_request uuid) returns jsonb language plpgsql security definer set search_path='' as $$
declare actor uuid:=ydna_editor.assert_owner();label text:=btrim(p_label);aliases text[];keys text[];prefix text;k text;old jsonb:='{}';data jsonb;r jsonb;prior ydna_editor.audit%rowtype;h text:=ydna_editor.version(jsonb_build_array('lineage',p_key,p_type,p_label,p_aliases,p_url,p_note,p_version));
begin
 perform pg_advisory_xact_lock(hashtextextended('egypt-ydna-sync',0));
 select * into prior from ydna_editor.audit where id=p_request;if found then if prior.actor<>actor or prior.request_hash<>h then raise exception 'Request already used';end if;return prior.after_state;end if;
 if p_type is null or p_type not in ('y','mt') or label is null or label !~ '^[A-Za-z0-9][A-Za-z0-9_.+*-]{0,79}$' or cardinality(p_aliases)>100 or length(coalesce(p_note,''))>4000 or length(coalesce(p_url,''))>2000 then raise exception 'Ungültige Linienangaben.';end if;
 if p_type='y' then label:=upper(label);end if;
 if coalesce(p_url,'')<>'' and (p_url !~ '^https://' or p_url ~ '^https://[^/?#]*@') then raise exception 'Bitte eine öffentliche HTTPS-Quelle ohne Zugangsdaten angeben.';end if;
 if exists(select 1 from unnest(p_aliases) v where btrim(v) !~ '^[A-Za-z0-9][A-Za-z0-9_.+*-]{0,79}$') then raise exception 'SNP-Namen bitte einzeln ohne Leerzeichen oder Sonderzeichen eingeben.';end if;
 select coalesce(array_agg(v order by upper(v)),'{}') into aliases from (select min(case when p_type='y' then upper(btrim(v)) else btrim(v) end) v from unnest(p_aliases) v where btrim(v)<>'' and upper(btrim(v))<>upper(label) group by upper(btrim(v))) a;
 prefix:=substring(upper(label) from '^([A-T]-)');
 if p_type='y' and prefix is not null and exists(select 1 from unnest(aliases) v where v ~ '^[A-T]-' and left(v,2)<>prefix) then raise exception 'SNP-Aliase müssen zur gleichen Y-DNA-Hauptgruppe gehören.';end if;
 select array_agg(distinct v) into keys from (select upper(label) v union all select upper(v) from unnest(aliases) v union all select prefix||upper(v) from unnest(aliases) v where prefix is not null and v !~ '^[A-T]-') a;
 k:=encode(sha256(convert_to(p_type||':'||upper(label),'UTF8')),'hex');
 if p_key is not null and p_key<>k then raise exception 'Die Hauptbezeichnung einer gespeicherten Linie bleibt erhalten. Ergänze gleichwertige Namen als Aliase.';end if;
 select to_jsonb(l) into old from public.ydna_owner_lineages l where record_key=k for update;
 if found and ydna_editor.version(old) is distinct from p_version then raise exception 'Die Linie wurde inzwischen geändert. Bitte neu laden.';end if;
 if not found then old:='{}';end if;
 if exists(select 1 from public.ydna_owner_lineages l where l.record_key<>k and l.owner_active and l.dna_type=p_type and l.match_labels&&keys) then raise exception 'Ein Name ist bereits einer anderen Linie zugeordnet. Bitte die vorhandene Zuordnung prüfen.';end if;
 insert into public.ydna_owner_lineages(record_key,dna_type,canonical_label,canonical_key,aliases,match_labels,source_url,note) values(k,p_type,label,upper(label),aliases,keys,coalesce(p_url,''),coalesce(p_note,''))
 on conflict(record_key) do update set aliases=excluded.aliases,match_labels=excluded.match_labels,source_url=excluded.source_url,note=excluded.note,owner_active=true,owner_modified_at=now() returning to_jsonb(ydna_owner_lineages) into data;
 r:=jsonb_build_object('kind','lineage','key',k,'version',ydna_editor.version(data),'data',data);
 insert into ydna_editor.audit(id,actor,action,kind,record_key,request_hash,before_state,after_state,reason) values(p_request,actor,case when old='{}' then 'create' else 'update' end,'lineage',k,h,old,r,'Owner-curated equivalent SNP names');return r;
end $$;
create function ydna_editor.undo_curated(p_id uuid,p_request uuid) returns jsonb language plpgsql security definer set search_path='' as $$
declare actor uuid:=ydna_editor.assert_owner();a ydna_editor.audit%rowtype;cur jsonb;d jsonb;r jsonb;h text:=ydna_editor.version(jsonb_build_array('undo-lineage',p_id));prior ydna_editor.audit%rowtype;
begin
 perform pg_advisory_xact_lock(hashtextextended('egypt-ydna-sync',0));select * into strict a from ydna_editor.audit where id=p_id for update;
 if a.kind<>'lineage' then return ydna_editor.undo_change(p_id,p_request);end if;
 select * into prior from ydna_editor.audit where id=p_request;if found then if prior.actor<>actor or prior.request_hash<>h then raise exception 'Request already used';end if;return prior.after_state;end if;
 select to_jsonb(l) into cur from public.ydna_owner_lineages l where record_key=a.record_key for update;
 if a.undone_at is not null or ydna_editor.version(cur) is distinct from a.after_state->>'version' then raise exception 'Neuere Änderung vorhanden. Bitte zuerst diese zurücknehmen.';end if;
 if a.action='create' then update public.ydna_owner_lineages set owner_active=false,owner_modified_at=now() where record_key=a.record_key returning to_jsonb(ydna_owner_lineages) into d;
 else
  if exists(select 1 from public.ydna_owner_lineages l where l.record_key<>a.record_key and l.owner_active and l.dna_type=a.before_state->>'dna_type' and l.match_labels&&array(select jsonb_array_elements_text(a.before_state->'match_labels'))) then raise exception 'Eine neuere Linie verwendet diese Namen. Bitte zuerst deren Änderung zurücknehmen.';end if;
  update public.ydna_owner_lineages set aliases=array(select jsonb_array_elements_text(a.before_state->'aliases')),match_labels=array(select jsonb_array_elements_text(a.before_state->'match_labels')),source_url=a.before_state->>'source_url',note=a.before_state->>'note',owner_active=(a.before_state->>'owner_active')::boolean,owner_modified_at=(a.before_state->>'owner_modified_at')::timestamptz where record_key=a.record_key returning to_jsonb(ydna_owner_lineages) into d;
 end if;
 update ydna_editor.audit set undone_at=now() where id=p_id;r:=jsonb_build_object('kind','lineage','key',a.record_key,'version',ydna_editor.version(d),'data',d);
 insert into ydna_editor.audit(id,actor,action,kind,record_key,request_hash,before_state,after_state,reason) values(p_request,actor,'undo','lineage',a.record_key,h,cur,r,'Restore prior SNP alias metadata');return r;
end $$;
create table ydna_editor.batch_requests(id uuid primary key,actor uuid not null,request_hash text not null,result jsonb not null,created_at timestamptz not null default now());
alter table ydna_editor.batch_requests enable row level security;
revoke all on ydna_editor.batch_requests from public,anon,authenticated,service_role;
create function ydna_editor.batch(p_items jsonb,p_action text,p_value text,p_reason text,p_batch uuid) returns jsonb language plpgsql security definer set search_path='' as $$
declare actor uuid:=ydna_editor.assert_owner();i jsonb;r jsonb;rows jsonb:='[]';n integer:=0;ok integer:=0;rid uuid;message text;original jsonb;patch jsonb;prior ydna_editor.batch_requests%rowtype;h text:=ydna_editor.version(jsonb_build_array(p_items,p_action,p_value,p_reason));result jsonb;
begin
 if p_items is null or p_action is null or p_reason is null or jsonb_typeof(p_items)<>'array' or jsonb_array_length(p_items) not between 1 and 200 or p_action not in ('governorate','hide','restore') or length(btrim(p_reason))<3 or p_batch is null then raise exception 'Bitte bis zu 200 Proben auswählen und einen Grund angeben.';end if;
 perform pg_advisory_xact_lock(hashtextextended('egypt-ydna-sync',0));
 select * into prior from ydna_editor.batch_requests where id=p_batch;if found then if prior.actor<>actor or prior.request_hash<>h then raise exception 'Importkennung bereits anders verwendet.';end if;return prior.result;end if;
 for i in select * from jsonb_array_elements(p_items) loop n:=n+1;rid:=md5(p_batch::text||':'||n)::uuid;
  begin
   if p_action='governorate' then
    patch:=jsonb_build_object('governorate',p_value);original:=ydna_editor.row_data(i->>'kind',i->>'key');
    if i->>'kind'='modern' and coalesce(original->>'kit_number','') ~ '^YF[0-9]+$' then
     if coalesce(original->>'yfull_id','') not in ('','—',original->>'kit_number') then raise exception 'Widersprüchliche YFull-Kennungen. Bitte zuerst die Probe einzeln prüfen.';end if;
     patch:=patch||jsonb_build_object('kit_number','','yfull_id',original->>'kit_number');
    end if;
    r:=ydna_editor.save_sample(i->>'kind',i->>'key',patch,i->>'version',rid);update ydna_editor.audit set reason=p_reason where id=rid;
   else r:=ydna_editor.visibility(i->>'kind',i->>'key',p_action='restore',i->>'version',p_reason,rid);end if;
   ok:=ok+1;rows:=rows||jsonb_build_array(jsonb_build_object('row',n,'status','saved','kind',i->>'kind','key',i->>'key'));
  exception when others then get stacked diagnostics message=message_text;rows:=rows||jsonb_build_array(jsonb_build_object('row',n,'status','failed','message',message));end;
 end loop;
 result:=jsonb_build_object('saved',ok,'failed',n-ok,'rows',rows);insert into ydna_editor.batch_requests(id,actor,request_hash,result) values(p_batch,actor,h,result);return result;
end $$;
-- All exposed operations authorize a verified owner and a live session.
revoke all on function ydna_editor.identifiers(jsonb),ydna_editor.branch_key(text,text),ydna_editor.lineage_terms(text,text),ydna_editor.record_rows(text),ydna_editor.filtered_rows(jsonb),ydna_editor.workbench(jsonb),ydna_editor.groups(jsonb),ydna_editor.lineages(),ydna_editor.lineage_save(text,text,text,text[],text,text,text,uuid),ydna_editor.undo_curated(uuid,uuid),ydna_editor.batch(jsonb,text,text,text,uuid) from public,anon,authenticated;
grant execute on function ydna_editor.workbench(jsonb),ydna_editor.groups(jsonb),ydna_editor.lineages(),ydna_editor.lineage_save(text,text,text,text[],text,text,text,uuid),ydna_editor.undo_curated(uuid,uuid),ydna_editor.batch(jsonb,text,text,text,uuid) to authenticated;
create function public.ydna_editor_workbench(p_options jsonb) returns jsonb language sql security invoker set search_path='' as $$select ydna_editor.workbench(p_options)$$;
create function public.ydna_editor_groups(p_options jsonb) returns jsonb language sql security invoker set search_path='' as $$select ydna_editor.groups(p_options)$$;
create function public.ydna_editor_lineages() returns jsonb language sql security invoker set search_path='' as $$select ydna_editor.lineages()$$;
create function public.ydna_editor_lineage_save(p_key text,p_type text,p_label text,p_aliases text[],p_url text,p_note text,p_version text,p_request uuid) returns jsonb language sql security invoker set search_path='' as $$select ydna_editor.lineage_save(p_key,p_type,p_label,p_aliases,p_url,p_note,p_version,p_request)$$;
create function public.ydna_editor_batch(p_items jsonb,p_action text,p_value text,p_reason text,p_batch uuid) returns jsonb language sql security invoker set search_path='' as $$select ydna_editor.batch(p_items,p_action,p_value,p_reason,p_batch)$$;
create or replace function public.ydna_editor_undo(p_id uuid,p_request uuid) returns jsonb language sql security invoker set search_path='' as $$select ydna_editor.undo_curated(p_id,p_request)$$;
revoke all on function public.ydna_editor_workbench(jsonb),public.ydna_editor_groups(jsonb),public.ydna_editor_lineages(),public.ydna_editor_lineage_save(text,text,text,text[],text,text,text,uuid),public.ydna_editor_batch(jsonb,text,text,text,uuid),public.ydna_editor_undo(uuid,uuid) from public,anon,authenticated;
grant execute on function public.ydna_editor_workbench(jsonb),public.ydna_editor_groups(jsonb),public.ydna_editor_lineages(),public.ydna_editor_lineage_save(text,text,text,text[],text,text,text,uuid),public.ydna_editor_batch(jsonb,text,text,text,uuid),public.ydna_editor_undo(uuid,uuid) to authenticated;

-- Preserve both typed provider IDs in either merge direction.
create or replace function ydna_editor.merge_samples(p_keep_kind text,p_keep_key text,p_other_kind text,p_other_key text,p_keep_version text,p_other_version text,p_reason text,p_confirm boolean,p_request uuid)
returns jsonb language plpgsql security definer set search_path='' as $$
declare actor uuid:=ydna_editor.assert_owner();a jsonb;b jsonb;patch jsonb:='{}';k text;v jsonb;after_a jsonb;after_b jsonb;r jsonb;
 h text:=ydna_editor.version(jsonb_build_array('merge',p_keep_kind,p_keep_key,p_other_kind,p_other_key,p_keep_version,p_other_version,p_reason));prior ydna_editor.audit%rowtype;before_meta jsonb:='{}';ft_ids text[];yf_ids text[];identity_row record;
begin
 perform pg_advisory_xact_lock(hashtextextended('egypt-ydna-sync',0));
 select * into prior from ydna_editor.audit where id=p_request;if found then if prior.actor<>actor or prior.request_hash<>h then raise exception 'Request already used';end if;return prior.after_state;end if;
 if not p_confirm or length(trim(p_reason))<5 or (p_keep_kind=p_other_kind and p_keep_key=p_other_key) then raise exception 'Confirm the same person and document the reason';end if;
 if p_keep_kind<>p_other_kind and not(p_keep_kind='modern' and p_other_kind='collected') then raise exception 'Cross-category links keep a modern sample and attach a collected sample. Choose that order';end if;
 a:=ydna_editor.row_data(p_keep_kind,p_keep_key,true);b:=ydna_editor.row_data(p_other_kind,p_other_key,true);
 if ydna_editor.version(a) is distinct from p_keep_version or ydna_editor.version(b) is distinct from p_other_version then raise exception 'A sample changed. Reload the merge preview';end if;
 if a->>'owner_active'<>'true' or b->>'owner_active'<>'true' or (p_keep_kind='modern' and a->>'sync_visibility'<>'public') or (p_other_kind='modern' and b->>'sync_visibility'<>'public') then raise exception 'Only active public samples can be merged';end if;
 select array_agg(distinct upper(btrim(x.token))) into ft_ids from unnest(array[a->>'kit_number',b->>'kit_number']) x(token) where upper(btrim(x.token)) ~ '^[A-Z]{0,3}[0-9]+$' and upper(btrim(x.token)) !~ '^YF[0-9]+$';
 select array_agg(distinct upper(btrim(x.token))) into yf_ids from unnest(array[a->>'kit_number',b->>'kit_number',a->>'yfull_id',b->>'yfull_id']) x(token) where upper(btrim(x.token)) ~ '^YF[0-9]+$';
 if cardinality(ft_ids)>1 or cardinality(yf_ids)>1 then raise exception 'Widersprüchliche Kennungen: Es darf nur eine FTDNA-Kitnummer und eine YFull-ID je Probe übernommen werden. Bitte Identität prüfen.';end if;
 for k,v in select * from jsonb_each(b) loop
 if k in ('name','kit_number','yfull_id','test_type','ethnic_group','origin_raw','governorate','y_dna','mt_dna','snp_path','full_snp_path','full_mtDNA_path','full_mtdna_path','y_link_1','y_link_2','mt_link_1','mt_link_2','ancestor_name','Description','study_reference','period','site','country','cultural_group')
 and coalesce(a->>k,'') in ('','—','-') and coalesce(v#>>'{}','') not in ('','—','-') then patch:=patch||jsonb_build_object(k,v);end if;
 end loop;
 if p_keep_kind='modern' then
 if cardinality(ft_ids)=1 then patch:=patch||jsonb_build_object('kit_number',ft_ids[1]);elsif coalesce(a->>'kit_number','') ~ '^YF[0-9]+$' then patch:=patch||jsonb_build_object('kit_number','');end if;
 if cardinality(yf_ids)=1 then patch:=patch||jsonb_build_object('yfull_id',yf_ids[1]);end if;
 patch:=patch||jsonb_build_object('sync_managed',false,'sync_updated_at',now());end if;
 after_a:=ydna_editor.put_row(p_keep_kind,p_keep_key,patch||jsonb_build_object('owner_modified_at',now()));
 if p_keep_kind='modern' and p_other_kind='modern' then
 -- Repair missing typed identity links from the two explicitly verified rows
 -- before recording the ownership snapshot used by undo.
 for identity_row in select * from (values
  ('ftdna',upper(btrim(a->>'kit_number')),p_keep_key::bigint),('ftdna',upper(btrim(b->>'kit_number')),p_other_key::bigint),
  ('yfull',upper(btrim(a->>'yfull_id')),p_keep_key::bigint),('yfull',upper(btrim(b->>'yfull_id')),p_other_key::bigint),
  ('yfull',upper(btrim(a->>'kit_number')),p_keep_key::bigint),('yfull',upper(btrim(b->>'kit_number')),p_other_key::bigint)
 ) v(namespace,external_id,sample_id) where (namespace='ftdna' and external_id ~ '^[A-Z]{0,3}[0-9]+$' and external_id !~ '^YF[0-9]+$') or (namespace='yfull' and external_id ~ '^YF[0-9]+$') loop
  if exists(select 1 from public.ydna_sync_optouts where identity_hash=encode(sha256(convert_to(identity_row.namespace||':'||identity_row.external_id,'UTF8')),'hex')) then raise exception 'Eine Kennung hat eine Opt-out-Sperre.';end if;
  if exists(select 1 from public.ydna_sync_identities i where i.namespace=identity_row.namespace and i.external_id=identity_row.external_id and i.sample_id not in (p_keep_key::bigint,p_other_key::bigint)) then raise exception 'Eine Kennung ist einer anderen Hauptprobe zugeordnet. Bitte diese zuerst auswählen.';end if;
  insert into public.ydna_sync_identities(namespace,external_id,sample_id,evidence_url) values(identity_row.namespace,identity_row.external_id,identity_row.sample_id,'https://github.com/egyptydna/Egypt-Y-DNA/blob/main/docs/OWNER-ADMIN.md') on conflict do nothing;
 end loop;
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
