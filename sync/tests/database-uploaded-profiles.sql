begin;
set local role service_role;
do $$ declare p jsonb;r jsonb;n integer;begin
 select count(*) into n from public."Modern_published_samples";
 p:=jsonb_build_object('file',jsonb_build_object('file_hash',repeat('a',64),'file_name','synthetic.xlsx','row_count',1),
 'rows',jsonb_build_array(jsonb_build_object('record_key',repeat('b',64),'sheet_name','Synthetic','row_number',2,'name','SYNTHETIC SOURCE ONLY','ancestor_name','','country_code','EG','y_dna','J-TEST1','origin_raw','','location_status','unknown','location_evidence','{}'::jsonb,'snp_path','[]'::jsonb,'tree_path','[]'::jsonb,'path_kind','terminal_only','candidate_ids','[]'::jsonb)));
 r:=public.ydna_import_uploaded_profiles(p,true);
 if exists(select 1 from public.ydna_uploaded_files) then raise exception 'Dry-run wrote data';end if;
 r:=public.ydna_import_uploaded_profiles(p,false);
 if (r->>'inserted_source_records')::int<>1 then raise exception 'Source record missing';end if;
 r:=public.ydna_import_uploaded_profiles(p,false);
 if (r->>'inserted_source_records')::int<>0 or (r->>'retained_source_records')::int<>1 then raise exception 'Repeated upload duplicated records';end if;
 if (select count(*) from public."Modern_published_samples")<>n then raise exception 'Upload altered archive counts';end if;
 if exists(select 1 from public.ydna_uploaded_profiles where identity_state<>'unlinked') then raise exception 'Fabricated identity';end if;
 if exists(select 1 from public.ydna_uploaded_files where published) then raise exception 'New file published without approval';end if;
 -- Synthetic disposable fixture only: simulate explicit publication approval.
 update public.ydna_uploaded_files set published=true;
 begin
  perform public.ydna_import_uploaded_profiles(jsonb_set(p,'{rows,0,kit_number}','"invented"'),false);
  raise exception 'Excess fields allowed';
 exception when raise_exception then if sqlerrm='Excess fields allowed' then raise;end if;end;
end $$;
reset role;
set local role anon;
do $$ begin
 if (select count(*) from public.ydna_uploaded_profiles)<>1 then raise exception 'Public source row unavailable';end if;
 begin perform public.ydna_import_uploaded_profiles('{}',false);raise exception 'Anonymous import allowed';exception when insufficient_privilege then null;end;
end $$;
reset role;
update public.ydna_uploaded_files set published=false;
set local role anon;
do $$ begin if exists(select 1 from public.ydna_uploaded_profiles) then raise exception 'Hidden source leaked';end if;end $$;
reset role;
rollback;
