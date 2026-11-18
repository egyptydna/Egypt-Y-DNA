-- Disposable synthetic fixtures only, always rolled back.
begin;
update ydna_editor.account_policy set registration_closed=false;
insert into auth.users(id,email,email_confirmed_at) values('00000000-0000-4000-8000-000000000051','group-owner@example.invalid',now());
update ydna_editor.account_policy set registration_closed=true;
insert into ydna_editor.administrators(email,user_id) values('group-owner@example.invalid','00000000-0000-4000-8000-000000000051');
insert into auth.sessions(id,user_id) values('10000000-0000-4000-8000-000000000051','00000000-0000-4000-8000-000000000051');
insert into public."Modern_published_samples"(name,y_dna,full_snp_path)
select 'Main-group fixture J1 '||i,'J-FIXTURE'||i,'Y-Adam>J-M267>J-FIXTURE'||i from generate_series(1,65) i;
insert into public."Modern_published_samples"(name,y_dna,full_snp_path) values
('Main-group fixture J2','J-M172','—'),
('Main-group fixture R1a','R-M198','—'),('Main-group fixture R1b','R-M269','—'),('Main-group fixture R2','R-M124','—'),
('Main-group fixture E','E-FIXTURE','—'),('Main-group fixture Q1','Q-M120','—'),('Main-group fixture Q2','Q-M378','—'),
('Main-group fixture unknown J','J-UNKNOWN','—'),('Main-group fixture conflict','J-M267','J-M172>J-M267'),
('Main-group fixture reference','J-REFERENCE','—'),('Main-group fixture equivalent reference','J-EQUIVALENT','—');
insert into public.ydna_sync_sources(id,url,adapter,publication_allowed) values('yfull-github','https://example.invalid/reference','yfull_github',true) on conflict do nothing;
insert into public.ydna_sync_tree_releases(source_id,release_key,tree_sha,version,commit_sha,published_at,source_url,license_name,license_url,attribution,node_count,selected_node_count,published,is_current,metadata)
values('yfull-github',repeat('f',64),repeat('f',64),'synthetic',repeat('f',40),now(),'https://github.com/example/reference','CC-BY-4.0','https://example.invalid/license','Synthetic only',3,3,true,true,'{"matches":{"J-EQUIVALENT":{"status":"equivalent_snp","label":"J-REFERENCE"}}}');
insert into public.ydna_sync_official_tree_nodes(source_id,release_key,label,parent_label) values
('yfull-github',repeat('f',64),'Y-Adam',null),('yfull-github',repeat('f',64),'J-M267','Y-Adam'),('yfull-github',repeat('f',64),'J-REFERENCE','J-M267');
do $$begin
 assert ydna_editor.y_main_group('{"y_dna":"J-REFERENCE"}')='J1';
 assert ydna_editor.y_main_group('{"y_dna":"J-EQUIVALENT"}')='J1';
 assert ydna_editor.y_main_group('{"y_dna":"J-UNLISTED","tree_path":["J-M267","J-UNLISTED"]}')='J1';
 assert ydna_editor.y_main_group('{"y_dna":"J-M267","full_snp_path":"J-M172>J-M267"}')='J';
 assert ydna_editor.y_main_group('{"y_dna":"J-UNKNOWN"}')='J';
 assert ydna_editor.y_main_group('{"y_dna":"R1a1a"}')='R1A';
 assert ydna_editor.y_main_group('{"y_dna":"R-M198","snp_path":"R-M124>R-M198"}')='R';
 assert ydna_editor.y_main_group('{"y_dna":"—","mt_dna":"J1"}') is null;
 assert not has_function_privilege('authenticated','ydna_editor.y_main_group(jsonb)','execute');
end $$;
select set_config('request.jwt.claims','{"sub":"00000000-0000-4000-8000-000000000051","session_id":"10000000-0000-4000-8000-000000000051"}',true);
set local role authenticated;
do $$declare r jsonb;g text;begin
 perform public.ydna_editor_save('collected',null,'{"name":"Main-group fixture collected","y_dna":"J-P58"}',null,gen_random_uuid());
 r:=public.ydna_editor_workbench('{"kind":"all","query":"Main-group fixture","main_group":"J1"}');
 assert r->>'total'='68';assert jsonb_array_length(r->'rows')=60;
 r:=public.ydna_editor_workbench('{"kind":"all","query":"Main-group fixture","main_group":"J1","offset":60}');assert jsonb_array_length(r->'rows')=8;
 foreach g in array array['J2','R1a','R1b','R2','E','Q1','Q2'] loop
  r:=public.ydna_editor_workbench(jsonb_build_object('kind','all','query','Main-group fixture','main_group',g));
  assert r->>'total'='1', 'Incorrect subgroup isolation: '||g;
 end loop;
 r:=public.ydna_editor_workbench('{"kind":"all","query":"Main-group fixture","main_group":"R1"}');assert r->>'total'='2';
 r:=public.ydna_editor_workbench('{"kind":"all","query":"Main-group fixture","main_group":"R"}');assert r->>'total'='3';
 r:=public.ydna_editor_groups('{"kind":"all","query":"Main-group fixture","main_group":"J2"}');assert jsonb_array_length(r->'groups')=1;assert r#>>'{groups,0,key}'='J-M172';
 begin perform public.ydna_editor_workbench('{"main_group":"invalid"}');raise exception 'Invalid main group accepted';exception when others then if sqlerrm='Invalid main group accepted' then raise;end if;end;
end $$;
reset role;
rollback;
