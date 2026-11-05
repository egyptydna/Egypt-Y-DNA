-- Disposable CI transaction; fixtures are anonymous counts, never real profiles.
begin;
insert into public.ydna_sync_sources(id,url,adapter,publication_allowed)
 values('ftdna-aggregate-github','https://example.org/anonymous-fixture','public_aggregate_tracker',true),
 ('owner-observatory-export','https://example.org/backup-fixture','owned_archive_transfer',true)
 on conflict(id) do update set publication_allowed=true;
set local role service_role;
do $$ declare p jsonb; r jsonb; first_id uuid; n integer; before_profiles integer; begin
 select count(*) into before_profiles from public."Modern_published_samples";
 p:=jsonb_build_object('source_id','ftdna-aggregate-github','snapshot_key',repeat('a',64),'provider','ftdna','country_code','EG',
  'observed_at',now()-interval '4 hours','total_count',622,'source_url','https://example.org/counts',
  'nodes',jsonb_build_array(jsonb_build_object('label','J-TEST1','count',622,'path','[]'::jsonb)));
 r:=public.ydna_tracker_publish(p,true);
 if r->>'status'<>'would_publish' or exists(select 1 from public.ydna_tracker_snapshots) then raise exception 'Dry run wrote data'; end if;
 r:=public.ydna_tracker_publish(p,false);first_id:=(r->>'snapshot_id')::uuid;
 if r->>'status'<>'published' or (r->>'new_results')::int<>0 then raise exception 'Baseline is not new results'; end if;
 r:=public.ydna_tracker_publish(p,false);
 if r->>'status'<>'unchanged' or (select count(*) from public.ydna_tracker_snapshots)<>1 then raise exception 'Duplicate poll'; end if;
 -- Same total, terminal reassignment: branch changes are not new testers.
 p:=p||jsonb_build_object('snapshot_key',repeat('b',64),'observed_at',now()-interval '3 hours',
  'nodes',jsonb_build_array(jsonb_build_object('label','J-TEST2','count',622,'path','[]'::jsonb)));
 r:=public.ydna_tracker_publish(p,false);
 if (r->>'new_results')::int<>0 or exists(select 1 from public.ydna_tracker_changes where kind='total_increase') then raise exception 'Branch refinement was called new people'; end if;
 -- A real country-total increase has its own event.
 p:=p||jsonb_build_object('snapshot_key',repeat('c',64),'observed_at',now()-interval '2 hours','total_count',623,
  'nodes',jsonb_build_array(jsonb_build_object('label','J-TEST2','count',623,'path','[]'::jsonb)));
 r:=public.ydna_tracker_publish(p,false);
 if (r->>'new_results')::int<>1 then raise exception 'New result not detected'; end if;
 -- Invalid totals and personal fields fail atomically.
 begin
  perform public.ydna_tracker_publish(p||jsonb_build_object('snapshot_key',repeat('d',64),'total_count',624),false);
  raise exception 'Accepted incomplete total';
 exception when raise_exception then if sqlerrm='Accepted incomplete total' then raise; end if; end;
 begin
  perform public.ydna_tracker_publish(p||jsonb_build_object('snapshot_key',repeat('d',64),'nodes',jsonb_build_array(jsonb_build_object('label','J-TEST2','count',623,'path','[]'::jsonb,'name','not allowed'))),false);
  raise exception 'Accepted personal field';
 exception when raise_exception then if sqlerrm='Accepted personal field' then raise; end if; end;
 -- A corrupt / empty primary must not replace the complete snapshot.
 r:=public.ydna_tracker_publish(p||jsonb_build_object('snapshot_key',repeat('e',64),'observed_at',now(),'total_count',0,'nodes','[]'::jsonb),false);
 if r->>'status'<>'review' then raise exception 'Unexpected country loss accepted'; end if;
 r:=public.ydna_tracker_select('unavailable','Source temporarily unreachable');
 if (r->>'total_count')::int<>623 then raise exception 'Outage lost existing results'; end if;
 -- A newer complete Observatory backup can take over on primary failure.
 p:=p||jsonb_build_object('source_id','owner-observatory-export','snapshot_key',repeat('f',64),'observed_at',now()-interval '1 hour');
 perform public.ydna_tracker_publish(p,false);
 r:=public.ydna_tracker_select('unavailable','Use saved backup');
 if r->>'source_id'<>'owner-observatory-export' then raise exception 'Fallback not selected'; end if;
 -- Equivalent counts permit the independently checked primary to be displayed.
 r:=public.ydna_tracker_select('ok','Primary agrees with backup');
 if r->>'source_id'<>'ftdna-aggregate-github' then raise exception 'Primary not selected'; end if;
 if (select count(*) from public."Modern_published_samples")<>before_profiles then raise exception 'Tracker altered individual archive'; end if;
 -- Unpublished snapshots and their events are hidden from public readers.
 update public.ydna_tracker_snapshots set published=false where id=first_id;
end $$;
reset role;
set local role anon;
do $$ begin
 if (select count(*) from public.ydna_tracker_snapshots)<>3 then raise exception 'Public snapshot RLS failed'; end if;
 if exists(select 1 from public.ydna_tracker_changes where kind='baseline' and after_count=622) then raise exception 'Hidden snapshot event leaked'; end if;
 begin
  perform public.ydna_tracker_select('ok','unauthorized');
  raise exception 'Anonymous writer allowed';
 exception when insufficient_privilege then null; end;
end $$;
reset role;
rollback;
