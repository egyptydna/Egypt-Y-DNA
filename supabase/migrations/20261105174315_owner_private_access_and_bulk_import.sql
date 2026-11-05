-- No participant identities, administrator emails or credentials are embedded.
create table ydna_editor.account_policy(singleton boolean primary key default true check(singleton),registration_closed boolean not null default true);
insert into ydna_editor.account_policy default values;
create table ydna_editor.credential_change_windows(user_id uuid primary key,expires_at timestamptz not null,reason text not null check(length(trim(reason))>=10));
alter table ydna_editor.account_policy enable row level security;
alter table ydna_editor.credential_change_windows enable row level security;
revoke all on ydna_editor.account_policy,ydna_editor.credential_change_windows from public,anon,authenticated,service_role;
-- Bind the already verified owner account once. Future email changes cannot
-- transfer this authorization to a new account.
update ydna_editor.administrators a set user_id=u.id from auth.users u
 where a.enabled and a.user_id is null and lower(u.email)=a.email and u.email_confirmed_at is not null and u.deleted_at is null;
create function ydna_editor.guard_accounts() returns trigger language plpgsql security definer set search_path='' as $$
begin
 if tg_op='INSERT' then
  if coalesce((select registration_closed from ydna_editor.account_policy where singleton),true) then
   raise exception 'Registration is closed. This website has a private owner account only.' using errcode='42501';
  end if;
 elsif exists(select 1 from ydna_editor.administrators a where a.user_id=old.id) and
  (new.encrypted_password is distinct from old.encrypted_password or new.email is distinct from old.email) then
  -- No public RPC can open a window. A trusted database administrator must
  -- explicitly approve a short, single-use maintenance window first.
  delete from ydna_editor.credential_change_windows where user_id=old.id and expires_at>clock_timestamp();
  if not found then raise exception 'Owner credentials are locked. An explicit maintenance authorization is required.' using errcode='42501';end if;
 end if;
 return new;
end $$;
revoke all on function ydna_editor.guard_accounts() from public,anon,authenticated,service_role;
create trigger ydna_owner_account_guard before insert or update of email,encrypted_password on auth.users for each row execute function ydna_editor.guard_accounts();

create function ydna_editor.lookup_identity(p_kit text default '',p_yfull text default '',p_exclude text default null) returns jsonb
language plpgsql security definer set search_path='' as $$
declare actor uuid:=ydna_editor.assert_owner();kit text:=upper(trim(coalesce(p_kit,'')));yf text:=upper(trim(coalesce(p_yfull,'')));matches jsonb;
begin
 if kit in ('—','-') then kit:='';end if;if yf in ('—','-') then yf:='';end if;
 if (kit<>'' and (kit !~ '^[A-Z]{0,3}[0-9]+$' or kit ~ '^YF[0-9]+$')) or (yf<>'' and yf !~ '^YF[0-9]+$') then raise exception 'Bitte Kitnummer und YFull-ID in die passenden Felder eintragen.';end if;
 select coalesce(jsonb_agg(r),'[]'::jsonb) into matches from (
  select s.id::text as key,'modern' as kind,s.name,s.kit_number,s.yfull_id,s.y_dna,s.governorate,s.owner_active,s.sync_visibility
  from public."Modern_published_samples" s where s.id::text is distinct from p_exclude and
  ((kit<>'' and upper(trim(s.kit_number))=kit) or (yf<>'' and (upper(trim(s.yfull_id))=yf or upper(trim(s.kit_number))=yf)) or
   exists(select 1 from public.ydna_sync_identities i where i.sample_id=s.id and ((kit<>'' and i.namespace='ftdna' and i.external_id=kit) or (yf<>'' and i.namespace='yfull' and i.external_id=yf))))
  order by s.owner_active desc,s.id limit 5
 ) r;
 return jsonb_build_object('exists',jsonb_array_length(matches)>0,'matches',matches);
end $$;

create function ydna_editor.preview_import(p_kind text,p_rows jsonb) returns jsonb language plpgsql security definer set search_path='' as $$
declare actor uuid:=ydna_editor.assert_owner();item jsonb;patch jsonb;found_identity jsonb;result jsonb:='[]';seen text[]:=array[]::text[];ids text[];token text;duplicate boolean;n integer:=0;error_text text;
begin
 if p_kind is null or p_rows is null or p_kind not in ('modern','collected') or jsonb_typeof(p_rows)<>'array' or jsonb_array_length(p_rows)>200 or jsonb_array_length(p_rows)=0 or octet_length(p_rows::text)>1000000 then raise exception 'Bitte 1 bis 200 Proben pro Import verwenden.';end if;
 for item in select * from jsonb_array_elements(p_rows) loop
  n:=n+1;
  begin
   patch:=ydna_editor.check_patch(p_kind,item);
   if p_kind='modern' then
    if coalesce(nullif(trim(patch->>'name'),''),nullif(trim(patch->>'kit_number'),''),nullif(trim(patch->>'yfull_id'),'')) is null then raise exception 'Name oder Kitnummer fehlt.';end if;
    found_identity:=ydna_editor.lookup_identity(patch->>'kit_number',patch->>'yfull_id');
    if (found_identity->>'exists')::boolean then result:=result||jsonb_build_array(jsonb_build_object('row',n,'status','exists','message','Diese Probe ist bereits vorhanden.','matches',found_identity->'matches'));continue;end if;
    perform ydna_editor.check_ids(patch,null);
   elsif coalesce(trim(patch->>'name'),'')='' or coalesce(patch->>'y_dna','') !~ '^[A-T]-[A-Z0-9*.+_-]+$' then raise exception 'Name und terminale Y-DNA-Linie sind erforderlich.';
   end if;
   ids:=array[]::text[];duplicate:=false;
   if p_kind='modern' then
    if coalesce(patch->>'kit_number','') not in ('','—','-') then ids:=array_append(ids,'ftdna:'||(patch->>'kit_number'));end if;
    if coalesce(patch->>'yfull_id','') not in ('','—','-') then ids:=array_append(ids,'yfull:'||(patch->>'yfull_id'));end if;
    foreach token in array ids loop if token=any(seen) then duplicate:=true;end if;end loop;
   end if;
   if duplicate then result:=result||jsonb_build_array(jsonb_build_object('row',n,'status','duplicate','message','Kitnummer / YFull-ID ist in dieser Datei bereits enthalten.'));
   else seen:=seen||ids;result:=result||jsonb_build_array(jsonb_build_object('row',n,'status','ready','message','Neue Probe – bereit zum Hinzufügen.'));end if;
  exception when others then get stacked diagnostics error_text=message_text;result:=result||jsonb_build_array(jsonb_build_object('row',n,'status','invalid','message',error_text));
  end;
 end loop;
 return jsonb_build_object('rows',result);
end $$;

create function ydna_editor.import_samples(p_kind text,p_rows jsonb,p_batch uuid) returns jsonb language plpgsql security definer set search_path='' as $$
declare actor uuid:=ydna_editor.assert_owner();item jsonb;preview jsonb;row_result jsonb;results jsonb:='[]';r jsonb;request_id uuid;prior ydna_editor.audit%rowtype;n integer:=0;added integer:=0;skipped integer:=0;failed integer:=0;error_text text;
begin
 if p_batch is null then raise exception 'Importkennung fehlt.';end if;
 perform pg_advisory_xact_lock(hashtextextended('egypt-ydna-sync',0));
 preview:=ydna_editor.preview_import(p_kind,p_rows);
 for item in select * from jsonb_array_elements(p_rows) loop
  n:=n+1;request_id:=md5(p_batch::text||':'||n)::uuid;
  begin
   select * into prior from ydna_editor.audit where id=request_id;
   if found then
    r:=ydna_editor.save_sample(p_kind,null,item,null,request_id);added:=added+1;
    results:=results||jsonb_build_array(jsonb_build_object('row',n,'status','added','key',r->>'key','message','Bereits durch diesen Import gespeichert.'));continue;
   end if;
   row_result:=preview->'rows'->(n-1);
   if row_result->>'status'<>'ready' then
    if row_result->>'status'='invalid' then failed:=failed+1;else skipped:=skipped+1;end if;
    results:=results||jsonb_build_array(row_result);continue;
   end if;
   r:=ydna_editor.save_sample(p_kind,null,item,null,request_id);added:=added+1;
   results:=results||jsonb_build_array(jsonb_build_object('row',n,'status','added','key',r->>'key','message','Probe hinzugefügt.'));
  exception when others then get stacked diagnostics error_text=message_text;failed:=failed+1;
   results:=results||jsonb_build_array(jsonb_build_object('row',n,'status','invalid','message',error_text));
  end;
 end loop;
 return jsonb_build_object('added',added,'skipped',skipped,'failed',failed,'rows',results);
end $$;
revoke all on function ydna_editor.lookup_identity(text,text,text),ydna_editor.preview_import(text,jsonb),ydna_editor.import_samples(text,jsonb,uuid) from public,anon,authenticated;
grant execute on function ydna_editor.lookup_identity(text,text,text),ydna_editor.preview_import(text,jsonb),ydna_editor.import_samples(text,jsonb,uuid) to authenticated;
create function public.ydna_editor_lookup_identity(p_kit text default '',p_yfull text default '',p_exclude text default null) returns jsonb language sql security invoker set search_path='' as $$select ydna_editor.lookup_identity(p_kit,p_yfull,p_exclude)$$;
create function public.ydna_editor_import_preview(p_kind text,p_rows jsonb) returns jsonb language sql security invoker set search_path='' as $$select ydna_editor.preview_import(p_kind,p_rows)$$;
create function public.ydna_editor_import(p_kind text,p_rows jsonb,p_batch uuid) returns jsonb language sql security invoker set search_path='' as $$select ydna_editor.import_samples(p_kind,p_rows,p_batch)$$;
revoke all on function public.ydna_editor_lookup_identity(text,text,text),public.ydna_editor_import_preview(text,jsonb),public.ydna_editor_import(text,jsonb,uuid) from public,anon,authenticated;
grant execute on function public.ydna_editor_lookup_identity(text,text,text),public.ydna_editor_import_preview(text,jsonb),public.ydna_editor_import(text,jsonb,uuid) to authenticated;
