-- Disposable database only. All fixture changes are rolled back.
begin;
do $$
declare sid bigint; other_id bigint; run_id uuid; r jsonb; n integer; snap uuid;
begin
 insert into public.ydna_sync_sources(id,url,adapter,publication_allowed,permission_url)
 values('project-fixture','https://example.org/public','public_export',true,'https://example.org/approval');
 insert into public.ydna_sync_runs(status,report) values('partial','{"sources":[{"id":"fixture","status":"restricted","records":0}]}') returning id into run_id;
 insert into public."Modern_published_samples"(kit_number,y_dna,sync_managed) values('990001','J-FIXTURE',true) returning id into sid;
 insert into public.ydna_sync_identities values('ftdna','990001',sid,'https://example.org/identity');
 insert into public.ydna_sync_observations(source_id,namespace,external_id,checksum,sample_id,payload,published)
 values('project-fixture','ftdna','990001','a',sid,'{"project":"Fixture-A","source_url":"https://www.familytreedna.com/public/Fixture-A","y_dna":"J-FIXTURE"}',true),
 ('project-fixture','ftdna','990001','b',sid,'{"project":"Fixture-B","source_url":"https://www.familytreedna.com/public/Fixture-B","y_dna":"J-FIXTURE"}',true);
 insert into public."Modern_published_samples"(kit_number,y_dna) values('YF990001','J-FIXTURE') returning id into other_id;
 insert into public.ydna_sync_identities values('ftdna','YF990001',other_id,'https://example.org/invalid-typed-id');
 insert into public.ydna_sync_observations(source_id,namespace,external_id,checksum,sample_id,payload,published)
 values('project-fixture','ftdna','YF990001','bad',other_id,'{"project":"Fixture-A","source_url":"https://www.familytreedna.com/public/Fixture-A","y_dna":"J-FIXTURE"}',true);
 r:=public.ydna_project_tracker_refresh(1,true);
 if (select count(*) from public.ydna_project_memberships where sample_id=sid)<>2 then raise exception 'Exact kit membership missing'; end if;
 if exists(select 1 from public.ydna_project_memberships where sample_id=other_id) then raise exception 'YFull ID treated as FTDNA kit'; end if;
 if (select summary->'projectSearch'->>'exactKitMatches' from public.ydna_project_tracking_status where id)<>'1' then raise exception 'Additional exact project not counted'; end if;
 if (select new_until from public.ydna_project_profile_activity where sample_id=sid) is null then raise exception 'New accepted profile did not get a 30-day marker'; end if;
 r:=public.ydna_project_tracker_refresh(128,false);
 if r->>'status'<>'recent_skip' then raise exception 'Recent check duplicated'; end if;
 select count(*) into n from public.ydna_project_memberships;
 perform public.ydna_project_tracker_refresh(128,true);
 if (select count(*) from public.ydna_project_memberships)<>n then raise exception 'Replay added duplicate membership'; end if;
 insert into public.ydna_tracker_snapshots(source_id,snapshot_key,provider,country_code,observed_at,total_count,nodes,source_url,details)
 values('project-fixture',repeat('a',64),'ftdna','EG',now(),2,'[{"label":"J-FIXTURE","count":2}]','https://example.org/counts','{}') returning id into snap;
 insert into public.ydna_tracker_changes(snapshot_id,change_key,branch_label,kind,before_count,after_count)
 values(snap,'fixture-change','J-FIXTURE','branch_change',1,2);
 insert into public.ydna_tracker_status(provider,snapshot_id,checked_at,primary_status,message)
 values('ftdna',snap,now(),'ok','fixture') on conflict(provider) do update set snapshot_id=excluded.snapshot_id;
 r:=public.ydna_project_tracker_refresh(1,true);
 if not exists(select 1 from public.ydna_project_targets where kind='lineage' and sample_id is null) then raise exception 'Missing anonymous lineage target'; end if;
 if not exists(select 1 from public.ydna_project_target_checks c join public.ydna_project_targets t using(target_key) where t.kind='lineage' and c.status='lineage_candidate') then raise exception 'Lineage candidates missing'; end if;
 if exists(select 1 from public.ydna_project_target_checks c join public.ydna_project_targets t using(target_key) where t.kind='lineage' and c.status='exact_kit_match') then raise exception 'Anonymous candidate identified as a person'; end if;
 if r->'summary'->>'fullCensus'<>'false' then raise exception 'Partial evidence claimed complete'; end if;
 if has_function_privilege('anon','public.ydna_project_tracker_refresh(integer,boolean)','execute') then raise exception 'Anonymous tracker write'; end if;
 if has_table_privilege('anon','public.ydna_project_targets','select') then raise exception 'Private search targets exposed'; end if;
 perform public.ydna_project_tracker_failed();
 if (select last_saved_at is null or state<>'failed' from public.ydna_project_tracking_status where id) then raise exception 'Failed run removed last save'; end if;
 update public."Modern_published_samples" set sync_visibility='private' where id=sid;
end $$;
set local role anon;
do $$ begin
 if exists(select 1 from public.ydna_project_memberships) then raise exception 'Hidden profile membership leaked'; end if;
end $$;
reset role;
rollback;
