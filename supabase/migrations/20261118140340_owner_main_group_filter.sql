-- Read-only lineage classification for owner filters; no sample values change.
create function ydna_editor.y_main_group(sample jsonb) returns text
language plpgsql stable set search_path='' as $$
declare terminal text:=upper(btrim(sample->>'y_dna'));root text;tokens text[]:='{}';labels text[];value jsonb;field text;
 release record;matched jsonb;reference_tokens text[];a boolean;b boolean;c boolean;r1 boolean;
begin
 if terminal is null or terminal !~ '^[A-T]($|[-0-9])' then return null;end if;
 root:=left(terminal,1);
 if root not in ('J','Q','R') then return root;end if;
 labels:=array[terminal];
 select labels||coalesce(array_agg(distinct v),'{}') into labels
 from public.ydna_owner_lineages l cross join lateral unnest(l.match_labels) v
 where l.dna_type='y' and l.owner_active and l.match_labels @> array[terminal];
 tokens:=labels;
 foreach field in array array['full_snp_path','snp_path','tree_path'] loop
  value:=sample->field;
  if jsonb_typeof(value)='array' then
   select tokens||coalesce(array_agg(upper(btrim(v))),'{}') into tokens from jsonb_array_elements_text(value) v;
  elsif jsonb_typeof(value)='string' then
   tokens:=tokens||regexp_split_to_array(upper(value#>>'{}'),'\s*[>/,;]\s*');
  end if;
 end loop;
 -- Published terminal reference paths are branch metadata, not extra people.
 if cardinality(tokens)=cardinality(labels) then
  select tokens||coalesce(array_agg(distinct upper(btrim(v))),'{}') into tokens
  from public.ydna_sync_country_counts f cross join lateral jsonb_array_elements_text(f.snp_path) v
  where f.published and f.is_current and f.count_scope='direct' and f.node_label=any(labels) and f.path_source_url like 'https://%';
 end if;
 select * into release from public.ydna_sync_tree_releases where source_id='yfull-github' and published and is_current limit 1;
 if found then
  matched:=release.metadata->'matches'->terminal;
  if matched->>'status' in ('exact','equivalent_snp') then labels:=labels||array[matched->>'label'];end if;
  with recursive ancestry as (
   select n.label,n.parent_label,array[n.label] visited,0 depth from public.ydna_sync_official_tree_nodes n
   where n.source_id=release.source_id and n.release_key=release.release_key and n.label=any(labels)
   union all
   select n.label,n.parent_label,a.visited||n.label,a.depth+1 from ancestry a join public.ydna_sync_official_tree_nodes n
   on n.source_id=release.source_id and n.release_key=release.release_key and n.label=a.parent_label
   where a.depth<255 and not n.label=any(a.visited)
  ) select array_agg(distinct upper(label)) into reference_tokens from ancestry;
  tokens:=tokens||coalesce(reference_tokens,'{}');
 end if;
 if root='J' then
  select bool_or(v like 'J1%' or regexp_replace(v,'^J-','') in ('M267','P58')),
         bool_or(v like 'J2%' or regexp_replace(v,'^J-','') in ('M172','M410','L26','M319')) into a,b from unnest(tokens) v;
  return case when a and b then root when a then 'J1' when b then 'J2' else root end;
 elsif root='Q' then
  select bool_or(v like 'Q1%' or regexp_replace(v,'^Q-','') in ('L472','MEH2','M346','L54','M120','M25')),
         bool_or(v like 'Q2%' or regexp_replace(v,'^Q-','') in ('L275','M378')) into a,b from unnest(tokens) v;
  return case when a and b then root when a then 'Q1' when b then 'Q2' else root end;
 else
  select bool_or(v like 'R1A%' or regexp_replace(v,'^R-','') in ('M420','M459','M198','M417')),
         bool_or(v like 'R1B%' or regexp_replace(v,'^R-','') in ('M343','M269','M73')),
         bool_or(v like 'R2%' or regexp_replace(v,'^R-','') in ('M479','M124')),bool_or(v='R1') into a,b,c,r1 from unnest(tokens) v;
  return case when (a and b) or (c and (a or b or r1)) then root when a then 'R1A' when b then 'R1B' when c then 'R2' when r1 then 'R1' else root end;
 end if;
end $$;
revoke all on function ydna_editor.y_main_group(jsonb) from public,anon,authenticated;

create or replace function ydna_editor.filtered_rows(o jsonb) returns setof jsonb language plpgsql stable set search_path='' as $$
declare r jsonb;k text:=coalesce(o->>'kind','modern');q text:=btrim(coalesce(o->>'query',''));g text:=coalesce(o->>'governorate','');vis text:=coalesce(o->>'visibility','active');
 ids text[];source text:=coalesce(o->>'ids','');quality text:=coalesce(o->>'quality','');dna text:=coalesce(o->>'dna','y');hap text:=btrim(coalesce(o->>'haplogroup',''));duplicates text[]:='{}';new_until timestamptz;main_group text:=upper(btrim(coalesce(o->>'main_group','')));family text;
begin
 if o is null or jsonb_typeof(o)<>'object' or k not in ('all','modern','collected','study','ancient','related') or length(q)>200 or length(hap)>100 or dna not in ('y','mt') or vis not in ('active','hidden','all')
 or source not in ('','ftdna','yfull','both','none') or quality not in ('','unassigned','missing_y','missing_mt','new','duplicate') then raise exception 'Ungültige Filter.';end if;
 if main_group not in ('','A','B','C','D','E','F','G','H','I','J','J1','J2','K','L','M','N','O','P','Q','Q1','Q2','R','R1','R1A','R1B','R2','S','T') then raise exception 'Ungültige Y-DNA-Hauptgruppe.';end if;
 if quality='duplicate' then
  select coalesce(array_agg(id),'{}') into duplicates from (select id from ydna_editor.record_rows('all') j cross join lateral unnest(ydna_editor.identifiers(j)) id where j->>'owner_active'='true' group by id having count(*)>1) d;
 end if;
 for r in select * from ydna_editor.record_rows(k) loop
  if vis<>'all' and (r->>'owner_active'='true')<>(vis='active') then continue;end if;
  if g<>'' and ((g='—' and btrim(coalesce(r->>'governorate','')) not in ('','—','-')) or (g<>'—' and r->>'governorate' is distinct from g)) then continue;end if;
  if main_group<>'' then
   family:=ydna_editor.y_main_group(r);
   if family is null or not (family=main_group or (main_group in ('J','Q','R') and left(family,1)=main_group) or (main_group='R1' and family in ('R1A','R1B'))) then continue;end if;
  end if;
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
