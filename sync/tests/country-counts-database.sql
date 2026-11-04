-- Synthetic facts only, always run inside a rolled-back transaction.
do $$
declare
 fact jsonb:='{"kind":"country_count","source_id":"synthetic-country-fact","namespace":"ftdna","node_label":"J-FGC1","country_code":"EG","reported_count":9,"count_scope":"inclusive","population":"ftdna_big_y","observed_at":"2026-11-04T00:00:00Z","source_url":"https://example.org/synthetic-count","accepted":true}'::jsonb;
 rid uuid; result jsonb; n bigint;
begin
 insert into public.ydna_sync_sources(id,url,adapter,publication_allowed) values('synthetic-country-fact','https://example.org','public_export',true);
 insert into public.ydna_sync_runs default values returning id into rid;
 result:=public.ydna_sync_ingest_country_count(fact,rid,true);
 if result->>'status'<>'would_insert' then raise exception 'Count dry run failed'; end if;
 select count(*) into n from public."Modern_published_samples";
 perform public.ydna_sync_ingest_country_count(fact,rid,false);
 if (select count(*) from public."Modern_published_samples")<>n then raise exception 'Anonymous facts created fake testers'; end if;
 result:=public.ydna_sync_ingest_country_count(fact,rid,false);
 if result->>'status'<>'unchanged' then raise exception 'Count idempotence failed'; end if;
 perform public.ydna_sync_ingest_country_count(fact||'{"observed_at":"2026-11-03T00:00:00Z","reported_count":8}',rid,false);
 if (select reported_count from public.ydna_sync_country_counts where source_id='synthetic-country-fact' and is_current)<>9 then raise exception 'Older snapshot replaced new count'; end if;
 perform public.ydna_sync_ingest_country_count(fact||'{"observed_at":"2026-11-05T00:00:00Z","reported_count":10}',rid,false);
 if (select count(*) from public.ydna_sync_country_counts where source_id='synthetic-country-fact' and is_current)<>1 then raise exception 'Multiple current snapshots'; end if;
 result:=public.ydna_sync_ingest_country_count(fact||'{"reported_count":20}',rid,false);
 if result->>'status'<>'review' then raise exception 'Contradictory count not reviewed'; end if;
 if has_function_privilege('anon','public.ydna_sync_ingest_country_count(jsonb,uuid,boolean)','execute') then raise exception 'Anonymous count writes exposed'; end if;
end $$;
