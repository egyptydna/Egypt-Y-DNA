-- Disposable fixtures; never run against production.
begin;
update ydna_editor.account_policy set registration_closed=false;
insert into auth.users(id,email,email_confirmed_at) values('00000000-0000-4000-8000-000000000041','workbench-owner@example.invalid',now()),('00000000-0000-4000-8000-000000000042','workbench-outsider@example.invalid',now());
update ydna_editor.account_policy set registration_closed=true;
insert into ydna_editor.administrators(email,user_id) values('workbench-owner@example.invalid','00000000-0000-4000-8000-000000000041');
insert into auth.sessions(id,user_id) values('10000000-0000-4000-8000-000000000041','00000000-0000-4000-8000-000000000041'),('10000000-0000-4000-8000-000000000042','00000000-0000-4000-8000-000000000042');
-- Old source rows can contain a YFull ID in the old generic kit column.
insert into public."Modern_published_samples"(name,kit_number,y_dna) values('Workbench legacy','YF990006002','J-WORK');
insert into public."Modern_published_samples"(name,kit_number,y_dna) values('Workbench duplicate A','990006003','E-DUP'),('Workbench duplicate B','990006003','E-DUP');
insert into public."Modern_published_samples"(name,y_dna) select 'Paging fixture '||i,'E-M'||i from generate_series(65,1,-1) i;
select set_config('request.jwt.claims','{"sub":"00000000-0000-4000-8000-000000000041","session_id":"10000000-0000-4000-8000-000000000041"}',true);
set local role authenticated;
do $$
declare a jsonb;b jsonb;c jsonb;l jsonb;r jsonb;v text;keepkey text;mergeid uuid;aliasid uuid:=gen_random_uuid();updateid uuid:=gen_random_uuid();undoid uuid:=gen_random_uuid();batchid uuid:=gen_random_uuid();items jsonb;before_count integer;
begin
 r:=public.ydna_editor_workbench('{"kind":"modern","query":"Paging fixture","sort":"y_dna","limit":60}');assert r->>'total'='65';assert r#>>'{rows,0,y_dna}'='E-M1';assert r#>>'{rows,59,y_dna}'='E-M60';
 r:=public.ydna_editor_workbench('{"kind":"modern","query":"Paging fixture","sort":"y_dna","limit":60,"offset":60}');assert jsonb_array_length(r->'rows')=5;assert r#>>'{rows,0,y_dna}'='E-M61';
 r:=public.ydna_editor_workbench('{"kind":"modern","query":"Paging fixture","sort":"y_dna","descending":true}');assert r#>>'{rows,0,y_dna}'='E-M65';
 a:=public.ydna_editor_save('modern',null,'{"name":"Workbench FTDNA","kit_number":"990006001","y_dna":"E-WORK","mt_dna":"H1a"}',null,gen_random_uuid());
 b:=public.ydna_editor_save('modern',null,'{"name":"Workbench YFull","yfull_id":"YF990006001","y_dna":"E-ALIAS"}',null,gen_random_uuid());
 c:=public.ydna_editor_save('collected',null,'{"name":"Workbench collected","y_dna":"E-WORK"}',null,gen_random_uuid());
 l:=public.ydna_editor_lineage_save(null,'y','E-WORK',array['E-ALIAS','BARE123'],'https://example.invalid/lineage','Synthetic owner equivalence',null,aliasid);
 assert l#>>'{data,aliases,0}'='BARE123';
 r:=public.ydna_editor_lineage_save(null,'y','E-WORK',array['E-ALIAS','BARE123'],'https://example.invalid/lineage','Synthetic owner equivalence',null,aliasid);assert r->>'key'=l->>'key';
 r:=public.ydna_editor_workbench('{"kind":"all","query":"Workbench","haplogroup":"E-WORK","dna":"y"}');assert r->>'total'='3';
 -- Equal groups still represent three separate records until explicitly merged.
 r:=public.ydna_editor_groups('{"kind":"all","query":"Workbench","dna":"y"}');assert exists(select 1 from jsonb_array_elements(r->'groups') g where g->>'key'='E-WORK' and g->>'count'='3');
 r:=public.ydna_editor_workbench('{"kind":"all","query":"BARE123"}');assert r->>'total'='3';
 r:=public.ydna_editor_workbench('{"kind":"all","query":"Workbench","haplogroup":"E-BARE123"}');assert r->>'total'='3';
 r:=public.ydna_editor_workbench('{"kind":"modern","query":"Workbench","quality":"duplicate"}');assert r->>'total'='2';
 begin perform public.ydna_editor_lineage_save(null,'y','E-OTHER',array['E-ALIAS'],'','',null,gen_random_uuid());raise exception 'Ambiguous alias accepted';exception when others then if sqlerrm='Ambiguous alias accepted' then raise;end if;end;
 begin perform public.ydna_editor_lineage_save(null,'y','E-OTHER',array['J-OTHER'],'','',null,gen_random_uuid());raise exception 'Cross-group alias accepted';exception when others then if sqlerrm='Cross-group alias accepted' then raise;end if;end;
 r:=public.ydna_editor_lineage_save(l->>'key','y','E-WORK',array['E-ALIAS','BARE123','E-EXTRA'],'https://example.invalid/lineage','Synthetic updated equivalence',l->>'version',updateid);
 begin perform public.ydna_editor_lineage_save(l->>'key','y','E-WORK',array['E-STALE'],'','',l->>'version',gen_random_uuid());raise exception 'Stale alias update accepted';exception when others then if sqlerrm='Stale alias update accepted' then raise;end if;end;
 perform public.ydna_editor_undo(updateid,undoid);perform public.ydna_editor_undo(updateid,undoid);
 r:=public.ydna_editor_workbench('{"kind":"all","query":"E-EXTRA"}');assert r->>'total'='0';
 mergeid:=gen_random_uuid();r:=public.ydna_editor_merge('modern',a->>'key','modern',b->>'key',a->>'version',b->>'version','Synthetic same participant confirmation',true,mergeid);
 assert r#>>'{data,kit_number}'='990006001';assert r#>>'{data,yfull_id}'='YF990006001';keepkey:=r->>'key';
 r:=public.ydna_editor_workbench('{"kind":"modern","query":"Workbench","ids":"both"}');assert r->>'total'='1';assert r#>>'{rows,0,kit_number}'='990006001';assert r#>>'{rows,0,yfull_id}'='YF990006001';
 perform public.ydna_editor_undo(mergeid,gen_random_uuid());
 r:=public.ydna_editor_workbench('{"kind":"modern","query":"Workbench legacy"}');v:=r#>>'{rows,0,__version}';keepkey:=r#>>'{rows,0,__key}';
 a:=public.ydna_editor_save('modern',null,'{"name":"Workbench second FTDNA","kit_number":"990006002","y_dna":"J-WORK"}',null,gen_random_uuid());
 r:=public.ydna_editor_merge('modern',keepkey,'modern',a->>'key',v,a->>'version','Synthetic legacy cross-provider confirmation',true,gen_random_uuid());
 assert r#>>'{data,kit_number}'='990006002';assert r#>>'{data,yfull_id}'='YF990006002';
 -- Batch updates persist and replay safely. A stale row is reported, not overwritten.
 items:=jsonb_build_array(jsonb_build_object('kind','collected','key',c->>'key','version',c->>'version'),jsonb_build_object('kind','modern','key',a->>'key','version','stale-version'));
 r:=public.ydna_editor_batch(items,'governorate','New Valley','Synthetic reviewed regional assignment',batchid);assert r->>'saved'='1';assert r->>'failed'='1';
 r:=public.ydna_editor_batch(items,'governorate','New Valley','Synthetic reviewed regional assignment',batchid);assert r->>'saved'='1';
 r:=public.ydna_editor_workbench('{"kind":"collected","query":"Workbench","governorate":"New Valley"}');assert r->>'total'='1';assert r#>>'{rows,0,location_status}'='resolved';
 r:=public.ydna_editor_workbench('{"kind":"all","query":"Workbench","ids":"none"}');assert r->>'total'='1';
 perform public.ydna_editor_undo(aliasid,gen_random_uuid());r:=public.ydna_editor_workbench('{"kind":"all","query":"Workbench","haplogroup":"E-WORK"}');assert r->>'total'='2';
 assert not has_function_privilege('anon','public.ydna_editor_workbench(jsonb)','execute');
 assert not has_function_privilege('authenticated','ydna_editor.record_rows(text)','execute');
 assert not has_table_privilege('authenticated','public.ydna_owner_lineages','update');
end $$;
reset role;
do $$begin
 assert (select m.name='Workbench YFull' from public.ydna_sync_identities i join public."Modern_published_samples" m on m.id=i.sample_id where i.namespace='yfull' and i.external_id='YF990006001');
 assert (select count(*)=2 from public.ydna_sync_identities i join public."Modern_published_samples" m on m.id=i.sample_id where m.name='Workbench legacy' and i.external_id in ('990006002','YF990006002'));
end $$;
select set_config('request.jwt.claims','{"sub":"00000000-0000-4000-8000-000000000042","session_id":"10000000-0000-4000-8000-000000000042"}',true);
set local role authenticated;
do $$begin
 begin perform public.ydna_editor_workbench('{}');raise exception 'Outsider accessed records';exception when insufficient_privilege then null;end;
 begin perform public.ydna_editor_lineage_save(null,'y','E-X',array['E-Y'],'','',null,gen_random_uuid());raise exception 'Outsider changed aliases';exception when insufficient_privilege then null;end;
 begin perform public.ydna_editor_groups('{}');raise exception 'Outsider accessed groups';exception when insufficient_privilege then null;end;
end $$;
reset role;
rollback;
