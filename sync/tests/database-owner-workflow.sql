-- Disposable database only. Synthetic authentication and sample fixtures.
begin;
update ydna_editor.account_policy set registration_closed=false;
insert into auth.users(id,email,encrypted_password,email_confirmed_at) values
 ('00000000-0000-4000-8000-000000000011','bulk-owner@example.invalid','synthetic-hash-original',now()),
 ('00000000-0000-4000-8000-000000000012','bulk-outsider@example.invalid',null,now());
insert into ydna_editor.administrators(email,user_id) values('bulk-owner@example.invalid','00000000-0000-4000-8000-000000000011');
insert into auth.sessions(id,user_id) values('10000000-0000-4000-8000-000000000011','00000000-0000-4000-8000-000000000011'),('10000000-0000-4000-8000-000000000012','00000000-0000-4000-8000-000000000012');
update ydna_editor.account_policy set registration_closed=true;
do $$begin
 begin insert into auth.users(id,email) values(gen_random_uuid(),'blocked@example.invalid');raise exception 'Registration was open';exception when insufficient_privilege then null;end;
 begin update auth.users set encrypted_password='unapproved-synthetic-hash' where email='bulk-owner@example.invalid';raise exception 'Password changed without approval';exception when insufficient_privilege then null;end;
 begin update auth.users set email='replacement@example.invalid' where email='bulk-owner@example.invalid';raise exception 'Owner email changed without approval';exception when insufficient_privilege then null;end;
 update auth.users set last_sign_in_at=now() where email='bulk-owner@example.invalid';
 insert into ydna_editor.credential_change_windows(user_id,expires_at,reason) values('00000000-0000-4000-8000-000000000011',now()+interval '5 minutes','Synthetic maintenance authorization');
 update auth.users set encrypted_password='approved-synthetic-hash' where email='bulk-owner@example.invalid';
 assert not exists(select 1 from ydna_editor.credential_change_windows);
 begin update auth.users set encrypted_password='second-synthetic-hash' where email='bulk-owner@example.invalid';raise exception 'Maintenance permission reused';exception when insufficient_privilege then null;end;
end $$;
select set_config('request.jwt.claims','{"sub":"00000000-0000-4000-8000-000000000011","session_id":"10000000-0000-4000-8000-000000000011"}',true);
set local role authenticated;
do $$
declare a jsonb;rows jsonb;preview jsonb;r jsonb;batch uuid:=gen_random_uuid();key text;
begin
 a:=public.ydna_editor_save('modern',null,'{"name":"Synthetic bulk baseline","kit_number":"990002001","governorate":"Cairo"}',null,gen_random_uuid());key:=a->>'key';
 r:=public.ydna_editor_lookup_identity('990002001','');assert r->>'exists'='true';assert r#>>'{matches,0,key}'=key;
 assert public.ydna_editor_lookup_identity('990002001','',key)->>'exists'='false';
 rows:='[{"kit_number":"990002001","name":"Do not replace baseline"},{"kit_number":"990002002","name":"Synthetic bulk second","y_dna":"J-BULKTEST","governorate":"Cairo"},{"kit_number":"990002002","name":"Duplicate in file"},{"kit_number":"990002003","governorate":"Unknown island"},{"yfull_id":"YF990002004","name":"Synthetic bulk YFull"}]';
 preview:=public.ydna_editor_import_preview('modern',rows);
 assert preview#>>'{rows,0,status}'='exists';assert preview#>>'{rows,1,status}'='ready';assert preview#>>'{rows,2,status}'='duplicate';assert preview#>>'{rows,3,status}'='invalid';assert preview#>>'{rows,4,status}'='ready';
 r:=public.ydna_editor_import('modern',rows,batch);assert r->>'added'='2';assert r->>'skipped'='2';assert r->>'failed'='1';
 r:=public.ydna_editor_import('modern',rows,batch);assert r->>'added'='2';
 r:=public.ydna_editor_list('modern','Synthetic bulk','','active',0);assert r->>'total'='3';
 r:=public.ydna_editor_list('modern','990002001','','active',0);assert r#>>'{rows,0,name}'='Synthetic bulk baseline';
 r:=public.ydna_editor_import('collected','[{"name":"Synthetic bulk collected","y_dna":"E-BULKTEST"}]',gen_random_uuid());assert r->>'added'='1';
 begin perform public.ydna_editor_import_preview('modern','[]');raise exception 'Empty import accepted';exception when others then if sqlerrm='Empty import accepted' then raise;end if;end;
 assert not has_table_privilege('authenticated','ydna_editor.credential_change_windows','insert');
 assert not has_table_privilege('authenticated','ydna_editor.account_policy','update');
end $$;
reset role;
select set_config('request.jwt.claims','{"sub":"00000000-0000-4000-8000-000000000012","session_id":"10000000-0000-4000-8000-000000000012"}',true);
set local role authenticated;
do $$begin
 begin perform public.ydna_editor_lookup_identity('990002001','');raise exception 'Outsider identity lookup';exception when insufficient_privilege then null;end;
 begin perform public.ydna_editor_import_preview('modern','[{"kit_number":"990002009"}]');raise exception 'Outsider import preview';exception when insufficient_privilege then null;end;
 begin perform public.ydna_editor_import('modern','[{"kit_number":"990002009"}]',gen_random_uuid());raise exception 'Outsider imported';exception when insufficient_privilege then null;end;
 assert not has_function_privilege('anon','public.ydna_editor_import(text,jsonb,uuid)','execute');
end $$;
reset role;
rollback;
