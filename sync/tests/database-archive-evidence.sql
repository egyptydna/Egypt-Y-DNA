-- Synthetic evidence only. Existing curated fields must remain byte-for-byte intact.
begin;
do $$
declare sid bigint; before_row jsonb; r jsonb; result jsonb; oid bigint; n integer;
begin
 insert into public."Modern_published_samples"(kit_number,name,y_dna,test_type,governorate,mt_dna)
 values('990088001','SYNTHETIC CURATED PROFILE','J-TEST1','Big Y-700','Cairo','U3') returning id into sid;
 select to_jsonb(s) into before_row from public."Modern_published_samples" s where id=sid;
 insert into public.ydna_sync_sources(id,url,adapter,publication_allowed,metadata)
 values('synthetic-archive-evidence','https://example.org/archive','owned_archive_transfer',true,'{"archive_url":"https://example.org/archive"}');
 r:='{"namespace":"ftdna","external_id":"990088001","source_id":"synthetic-archive-evidence","source_url":"https://example.org/public-project","archive_source_url":"https://example.org/archive","accepted":true,"publication_allowed":true,"origin":{"country":"EG"},"origin_kind":"paternal","sample_kind":"modern","y_dna":"J-TEST2","test_type":"Y-DNA37","str_markers":[{"position":0,"marker":"DYS425","source_label":"DYS425","value":"0"},{"position":1,"marker":"DYS464","source_label":"DYS464","value":"14-16-17-17"},{"position":2,"marker":"DYS393","source_label":"DYS393","value":null}]}'::jsonb;
 result:=public.ydna_sync_attach_archive_evidence(r,true);
 assert result->>'status'='would_attach_evidence';
 assert not exists(select 1 from public.ydna_sync_identities where sample_id=sid);
 result:=public.ydna_sync_attach_archive_evidence(r,false);oid:=(result->>'observation_id')::bigint;
 assert (result->>'evidence_attached')::boolean;
 assert (select to_jsonb(s)=before_row from public."Modern_published_samples" s where id=sid);
 assert (select count(*)=3 from public.ydna_sync_str_values where observation_id=oid);
 assert exists(select 1 from public.ydna_sync_str_values where observation_id=oid and allele='0');
 assert exists(select 1 from public.ydna_sync_str_values where observation_id=oid and allele='14-16-17-17');
 assert exists(select 1 from public.ydna_sync_str_values where observation_id=oid and allele is null);
 assert exists(select 1 from public.ydna_sync_reviews where sample_id=sid and reason='source_terminal_difference');
 result:=public.ydna_sync_attach_archive_evidence(r,false);
 assert not (result->>'evidence_attached')::boolean;
 assert (select count(*)=1 from public.ydna_sync_observations where sample_id=sid);
 -- Additional published alleles create source history without changing the curated tester.
 r:=jsonb_set(r,'{str_markers,0,value}','"1"');
 result:=public.ydna_sync_attach_archive_evidence(r,false);
 assert (result->>'evidence_attached')::boolean;
 assert (select count(*)=2 from public.ydna_sync_observations where sample_id=sid);
 assert (select count(*)=1 from public.ydna_sync_observations where sample_id=sid and is_current);
 assert exists(select 1 from public.ydna_sync_str_values v join public.ydna_sync_observations o on o.id=v.observation_id where o.sample_id=sid and v.allele='0');
 assert (select to_jsonb(s)=before_row from public."Modern_published_samples" s where id=sid);
 -- Explicitly withdrawn evidence cannot be made public by a stale archive replay.
 update public.ydna_sync_observations set published=false where sample_id=sid and is_current;
 assert (public.ydna_sync_attach_archive_evidence(r,false)->>'status'='suppressed');
 begin
  perform public.ydna_sync_attach_archive_evidence(r-'origin',false);
  raise exception 'Missing origin accepted';
 exception when raise_exception then if sqlerrm<>'Accepted modern Egyptian paternal evidence required' then raise;end if;end;
 perform public.ydna_sync_opt_out(sid);
 assert (public.ydna_sync_attach_archive_evidence(r,false)->>'status'='opted_out');
 assert not has_function_privilege('anon','public.ydna_sync_attach_archive_evidence(jsonb,boolean)','execute');
end $$;
rollback;
