-- Synthetic records only. All fixture writes are rolled back.
begin;
do $$
declare a bigint; b bigint; c bigint; d bigint; r jsonb; n integer;
begin
 insert into public."Modern_published_samples"(kit_number,y_dna,full_snp_path,governorate)
 values('99001122','J-TEST2','Y-Adam>J>J1>J-TEST1>J-TEST2','Cairo') returning id into a;
 insert into public."Modern_published_samples"(kit_number,y_dna,full_snp_path,governorate)
 values('99001122','J-TEST1','Y-Adam>J>J1>J-TEST1','Port Said') returning id into b;
 r:=public.ydna_sync_merge_duplicate(a,b,'https://example.org/synthetic-kit');
 assert r->>'status'='merged';
 assert (select sync_origin_conflict from public."Modern_published_samples" where id=a);
 assert (select sync_visibility='merged' and sync_merged_into=a from public."Modern_published_samples" where id=b);
 assert (select governorate='Cairo' and y_dna='J-TEST2' from public."Modern_published_samples" where id=a);
 assert (select governorate='Port Said' and y_dna='J-TEST1' from public."Modern_published_samples" where id=b);
 assert (select sample_id=a from public.ydna_sync_identities where namespace='ftdna' and external_id='99001122');
 assert (public.ydna_sync_merge_duplicate(a,b,'https://example.org/synthetic-kit')->>'status'='unchanged');
 assert exists(select 1 from public.ydna_sync_reviews where sample_id=a and reason='merged_origin_conflict');
 insert into public."Modern_published_samples"(yfull_id,y_dna,mt_dna,test_type)
 values('YF99001122','C-TEST1','U3b3d2a','YSEQ') returning id into c;
 insert into public."Modern_published_samples"(yfull_id,y_dna,test_type)
 values('YF99001122','C-TEST1','YFull sequencing') returning id into d;
 insert into public.ydna_sync_sources(id,url,adapter,publication_allowed)
 values('synthetic-merge','https://example.org/synthetic','approved_json',true);
 insert into public.ydna_sync_observations(source_id,namespace,external_id,checksum,sample_id,payload)
 values('synthetic-merge','yfull','YF99001122','synthetic',d,'{"source_url":"https://example.org/synthetic"}');
 perform public.ydna_sync_merge_duplicate(c,d,'https://example.org/synthetic-yf');
 assert (select mt_dna='U3b3d2a' and test_type='YSEQ' from public."Modern_published_samples" where id=c);
 assert (select sample_id=c from public.ydna_sync_observations where source_id='synthetic-merge');
 assert (select count(*)=2 from public.ydna_sync_identity_merges where canonical_id in (a,c));
 assert not has_function_privilege('anon','public.ydna_sync_merge_duplicate(bigint,bigint,text)','execute');
 assert not has_table_privilege('anon','public.ydna_sync_identity_merges','select');
 -- A request using an archived ID must purge identifying claims for both rows.
 perform public.ydna_sync_opt_out(d);
 assert (select count(*)=2 from public."Modern_published_samples" where id in (c,d) and sync_visibility='opted_out' and yfull_id is null);
 assert not exists(select 1 from public.ydna_sync_observations where sample_id in (c,d));
 assert (select original_canonical='{}'::jsonb and original_retired='{}'::jsonb from public.ydna_sync_identity_merges where retired_id=d);
 assert exists(select 1 from public.ydna_sync_optouts where identity_hash=encode(sha256(convert_to('yfull:YF99001122','UTF8')),'hex'));
 -- A shared kit with two contradictory explicit YFull IDs is not a safe merge.
 insert into public."Modern_published_samples"(kit_number,yfull_id) values('99003344','YF99003344') returning id into a;
 insert into public."Modern_published_samples"(kit_number,yfull_id) values('99003344','YF99003345') returning id into b;
 begin
  perform public.ydna_sync_merge_duplicate(a,b,'https://example.org/conflict');
  raise exception 'Conflicting IDs were incorrectly merged';
 exception when raise_exception then
  if sqlerrm<>'Conflicting verified external IDs' then raise; end if;
 end;
 assert (select sync_visibility='public' from public."Modern_published_samples" where id=b);
 -- A name or a shared haplogroup does not establish a shared identity.
 insert into public."Modern_published_samples"(name,y_dna) values('Synthetic identical name','J-TEST1') returning id into a;
 insert into public."Modern_published_samples"(name,y_dna) values('Synthetic identical name','J-TEST1') returning id into b;
 begin
  perform public.ydna_sync_merge_duplicate(a,b,'https://example.org/no-id');
  raise exception 'Name-only merge incorrectly accepted';
 exception when raise_exception then
  if sqlerrm<>'No exact shared kit or YFull ID' then raise; end if;
 end;
end $$;
rollback;
