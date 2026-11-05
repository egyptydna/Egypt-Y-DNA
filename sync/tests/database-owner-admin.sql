-- Synthetic records only; no production identities, emails or genetic data.
begin;
insert into auth.users(id,email,email_confirmed_at) values
 ('00000000-0000-4000-8000-000000000001','owner@example.invalid',now()),
 ('00000000-0000-4000-8000-000000000002','outsider@example.invalid',now()),
 ('00000000-0000-4000-8000-000000000003','unverified@example.invalid',null);
insert into auth.sessions(id,user_id) values
 ('10000000-0000-4000-8000-000000000001','00000000-0000-4000-8000-000000000001'),
 ('10000000-0000-4000-8000-000000000002','00000000-0000-4000-8000-000000000002'),
 ('10000000-0000-4000-8000-000000000003','00000000-0000-4000-8000-000000000003');
insert into ydna_editor.administrators(email) values('owner@example.invalid'),('unverified@example.invalid');
select set_config('request.jwt.claims','{"sub":"00000000-0000-4000-8000-000000000001","session_id":"10000000-0000-4000-8000-000000000001"}',true);
set local role authenticated;
do $$
declare a jsonb;b jsonb;c jsonb;r jsonb;oldversion text;aid uuid:=gen_random_uuid();bid uuid:=gen_random_uuid();sid text;
begin
 assert public.ydna_editor_context()->>'administrator'='true';
 a:=public.ydna_editor_save('modern',null,'{"name":"Synthetic owner sample","kit_number":"990000101","y_dna":"E-OWNERFIXTURE","governorate":"Cairo"}',null,aid);
 assert a->>'kind'='modern';assert a#>>'{data,governorate}'='Cairo';sid:=a->>'key';
 r:=public.ydna_editor_save('modern',null,'{"name":"Synthetic owner sample","kit_number":"990000101","y_dna":"E-OWNERFIXTURE","governorate":"Cairo"}',null,aid);assert r->>'key'=sid;
 begin perform public.ydna_editor_save('modern',null,'{"name":"Conflict","kit_number":"990000101"}',null,gen_random_uuid());raise exception 'Duplicate ID accepted';exception when others then if sqlerrm='Duplicate ID accepted' then raise;end if;end;
 oldversion:=a->>'version';
 a:=public.ydna_editor_save('modern',sid,'{"governorate":"Port Said"}',oldversion,gen_random_uuid());assert a#>>'{data,governorate}'='Port Said';
 begin perform public.ydna_editor_save('modern',sid,'{"governorate":"Cairo"}',oldversion,gen_random_uuid());raise exception 'Stale edit accepted';exception when others then if sqlerrm='Stale edit accepted' then raise;end if;end;
 begin perform public.ydna_editor_save('modern',sid,'{"sync_visibility":"public"}',a->>'version',gen_random_uuid());raise exception 'Internal field accepted';exception when others then if sqlerrm='Internal field accepted' then raise;end if;end;
 b:=public.ydna_editor_save('collected',null,'{"name":"Synthetic collected participant","y_dna":"E-OWNERFIXTURE","governorate":"—"}',null,bid);
 assert b#>>'{data,location_status}'='unknown';assert b#>'{data,governorate}'='null'::jsonb;
 b:=public.ydna_editor_save('collected',b->>'key','{"governorate":"New Valley"}',b->>'version',gen_random_uuid());assert b#>>'{data,location_status}'='resolved';
 c:=public.ydna_editor_visibility('modern',sid,false,a->>'version','Synthetic removal',gen_random_uuid());assert c#>>'{data,owner_active}'='false';
 r:=public.ydna_editor_list('modern','Synthetic owner sample','','active',0);assert jsonb_array_length(r->'rows')=0;
 a:=public.ydna_editor_visibility('modern',sid,true,c->>'version','Synthetic restoration',gen_random_uuid());
 c:=public.ydna_editor_merge('modern',sid,'collected',b->>'key',a->>'version',b->>'version','Owner verified the same synthetic participant',true,gen_random_uuid());
 assert c->>'kind'='modern';
 r:=public.ydna_editor_list('collected','Synthetic collected participant','','active',0);assert jsonb_array_length(r->'rows')=0;
 r:=public.ydna_editor_history();assert jsonb_array_length(r)>3;
 perform public.ydna_editor_undo((r->0->>'id')::uuid,gen_random_uuid());
 r:=public.ydna_editor_list('collected','Synthetic collected participant','','active',0);assert jsonb_array_length(r->'rows')=1;
end $$;
reset role;
select set_config('request.jwt.claims','{"sub":"00000000-0000-4000-8000-000000000002","session_id":"10000000-0000-4000-8000-000000000002"}',true);
set local role authenticated;
do $$begin
 begin perform public.ydna_editor_context();raise exception 'Outsider got admin';exception when insufficient_privilege then null;end;
 assert not has_table_privilege('authenticated','ydna_editor.audit','select');
 assert not has_function_privilege('authenticated','ydna_editor.put_row(text,text,jsonb)','execute');
end $$;
reset role;
select set_config('request.jwt.claims','{"sub":"00000000-0000-4000-8000-000000000003","session_id":"10000000-0000-4000-8000-000000000003"}',true);
set local role authenticated;
do $$begin begin perform public.ydna_editor_context();raise exception 'Unverified email got admin';exception when insufficient_privilege then null;end;end $$;
reset role;
delete from auth.sessions where user_id='00000000-0000-4000-8000-000000000001';
select set_config('request.jwt.claims','{"sub":"00000000-0000-4000-8000-000000000001","session_id":"10000000-0000-4000-8000-000000000001"}',true);
set local role authenticated;
do $$begin begin perform public.ydna_editor_context();raise exception 'Revoked session got admin';exception when insufficient_privilege then null;end;end $$;
reset role;
set local role anon;
do $$begin
 assert not has_function_privilege('anon','public.ydna_editor_save(text,text,jsonb,text,uuid)','execute');
 assert not has_table_privilege('anon',(select c.oid from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='ydna_editor' and c.relname='administrators'),'select');
end $$;
reset role;
rollback;
