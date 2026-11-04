-- Run inside BEGIN/ROLLBACK after the migration. SYNTHETIC FIXTURES ONLY.
do $$
declare
 r jsonb := '{"namespace":"ftdna","external_id":"990099001","name":"SYNTHETIC FIXTURE ONLY","source_id":"fixture-a","source_url":"https://example.org/public-fixture","accepted":true,"test_type":"Big Y-700","test_status":"confirmed_big_y","haplogroup_status":"confirmed","y_dna":"J-TEST1","origin_raw":"Egypt","origin":{"country":"EG"},"str_markers":[{"position":0,"marker":"DYS425","source_label":"DYS425","value":"0"},{"position":1,"marker":"DYS464","source_label":"DYS464","value":"14-16-17-17"}]}'::jsonb;
 answer jsonb; sid bigint; n bigint; rid uuid;
begin
 insert into public.ydna_sync_sources(id,url,adapter,publication_allowed) values
 ('fixture-a','https://example.org/public-fixture','public_export',true),
 ('fixture-b','https://example.org/public-fixture-b','public_export',true),
 ('fixture-c','https://example.org/public-fixture-c','public_export',true);
 insert into public.ydna_sync_runs default values returning id into rid;
 answer := public.ydna_sync_ingest(r,rid,true);
 if answer->>'status'<>'would_insert' then raise exception 'Dry-run insertion failed: %',answer; end if;
 answer := public.ydna_sync_ingest(r,rid,false); sid:=(answer->>'sample_id')::bigint;
 if answer->>'status'<>'inserted' then raise exception 'New Big Y failed: %',answer; end if;
 answer := public.ydna_sync_ingest(r,rid,false);
 if answer->>'status'<>'unchanged' then raise exception 'Idempotence failed: %',answer; end if;
 perform public.ydna_sync_ingest(r||'{"source_id":"fixture-b"}',rid,false);
 perform public.ydna_sync_ingest(r||'{"source_id":"fixture-c"}',rid,false);
 select count(*) into n from public."Modern_published_samples" where kit_number='990099001';
 if n<>1 then raise exception 'Three-project deduplication failed'; end if;
 select count(*) into n from public.ydna_sync_str_values where allele='0' and observation_id in
 (select id from public.ydna_sync_observations where sample_id=sid);
 if n<>3 then raise exception 'Zero allele lost'; end if;
 -- Verified public cross-platform identity: one tester, no Big Y inference from YFull.
 answer:=public.ydna_sync_ingest(r||'{"namespace":"yfull","external_id":"YF990099001","source_id":"fixture-b","test_type":"YFull sequencing","test_status":"yfull_sequencing","identity_evidence_url":"https://example.org/public-identity-proof","verified_ids":[{"namespace":"ftdna","external_id":"990099001"}]}',rid,false);
 if (answer->>'sample_id')::bigint<>sid then raise exception 'Public ID linkage failed'; end if;
 -- Terminal move with an explicitly evidenced path; no intermediate nodes fabricated.
 r:=r||'{"y_dna":"J-TEST2","snp_path":["Y-Adam","J-TEST2"],"path_source_url":"https://example.org/tree-proof"}';
 perform public.ydna_sync_ingest(r,rid,false);
 if not exists(select 1 from public."Modern_published_samples" where id=sid and y_dna='J-TEST2' and full_snp_path='Y-Adam>J-TEST2') then
  raise exception 'Terminal move failed'; end if;
 -- Extra markers extend the profile, historical values survive a later source observation.
 r:=r||'{"str_markers":[{"position":0,"marker":"DYS393","source_label":"DYS393","value":"12"}]}';
 perform public.ydna_sync_ingest(r,rid,false);
 if not exists(select 1 from public.ydna_sync_str_values v join public.ydna_sync_observations o on o.id=v.observation_id where o.sample_id=sid and v.allele='14-16-17-17') then
  raise exception 'Historical STR lost'; end if;
 -- Manual correction takes priority even on a managed profile.
 update public."Modern_published_samples" set y_dna='J-MANUAL' where id=sid;
 perform public.ydna_sync_ingest(r||'{"y_dna":"J-TEST3"}',rid,false);
 if not exists(select 1 from public."Modern_published_samples" where id=sid and y_dna='J-MANUAL') then raise exception 'Manual override lost'; end if;
 if not exists(select 1 from public.ydna_sync_reviews where sample_id=sid and reason='field_conflict') then raise exception 'Conflict not queued'; end if;
 perform public.ydna_sync_withdraw('fixture-a','ftdna','990099001','https://example.org/withdrawal');
 perform public.ydna_sync_withdraw('fixture-b','ftdna','990099001','https://example.org/withdrawal');
 perform public.ydna_sync_withdraw('fixture-c','ftdna','990099001','https://example.org/withdrawal');
 if not exists(select 1 from public."Modern_published_samples" where id=sid and sync_visibility='public') then raise exception 'Another public source should keep profile visible'; end if;
 perform public.ydna_sync_withdraw('fixture-b','yfull','YF990099001','https://example.org/withdrawal');
 if not exists(select 1 from public."Modern_published_samples" where id=sid and sync_visibility='withdrawn') then raise exception 'Explicit withdrawal not hidden'; end if;
 perform public.ydna_sync_opt_out(sid);
 answer:=public.ydna_sync_ingest(r,rid,false);
 if answer->>'status'<>'opted_out' then raise exception 'Optout reimported'; end if;
 if exists(select 1 from public.ydna_sync_observations where sample_id=sid) then raise exception 'Optout payload retained'; end if;
 if has_function_privilege('anon','public.ydna_sync_ingest(jsonb,uuid,boolean)','execute') then raise exception 'Anon can import'; end if;
 if has_table_privilege('anon','public.ydna_sync_reviews','select') then raise exception 'Review data exposed'; end if;
end $$;
