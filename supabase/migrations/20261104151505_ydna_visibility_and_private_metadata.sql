-- Explicitly documented deny policies for private metadata; service_role bypasses RLS.
create policy private_identities on public.ydna_sync_identities for all to anon,authenticated using(false) with check(false);
create policy private_optouts on public.ydna_sync_optouts for all to anon,authenticated using(false) with check(false);
create policy private_places on public.ydna_sync_places for all to anon,authenticated using(false) with check(false);
create policy private_reviews on public.ydna_sync_reviews for all to anon,authenticated using(false) with check(false);
create policy private_sources on public.ydna_sync_sources for all to anon,authenticated using(false) with check(false);

create or replace function public.ydna_sync_opt_out(p_sample bigint) returns void
language plpgsql security invoker set search_path=public,pg_temp as $$
declare ids jsonb;
begin
 perform pg_advisory_xact_lock(hashtextextended('egypt-ydna-sync',0));
 select coalesce(jsonb_agg(x),'[]') into ids from (
  select namespace,external_id from public.ydna_sync_identities where sample_id=p_sample
  union select 'ftdna',upper(trim(kit_number)) from public."Modern_published_samples" where id=p_sample and kit_number ~ '^[A-Za-z]{0,3}[0-9]+$'
  union select 'yfull',upper(trim(yfull_id)) from public."Modern_published_samples" where id=p_sample and yfull_id ~ '^YF[0-9]+$'
 ) x;
 insert into public.ydna_sync_optouts(identity_hash)
 select encode(sha256(convert_to((i->>'namespace')||':'||(i->>'external_id'),'UTF8')),'hex') from jsonb_array_elements(ids) i on conflict do nothing;
 update public."Modern_published_samples" set sync_visibility='opted_out',name=null,kit_number=null,yfull_id=null,
 origin_raw=null,y_link_1=null,y_link_2=null,sync_published='{}' where id=p_sample;
 delete from public.ydna_sync_reviews where sample_id=p_sample or exists(select 1 from jsonb_array_elements(ids) i
  where details->>'namespace'=i->>'namespace' and upper(details->>'external_id')=i->>'external_id');
 delete from public.ydna_sync_observations where sample_id=p_sample;
 delete from public.ydna_sync_identities where sample_id=p_sample;
end $$;

-- Only an explicit public withdrawal proof is actionable. Missing rows or failed fetches are not proof.
create function public.ydna_sync_withdraw(p_source text,p_namespace text,p_external_id text,p_evidence_url text)
returns jsonb language plpgsql security invoker set search_path=public,pg_temp as $$
declare sid bigint;
begin
 perform pg_advisory_xact_lock(hashtextextended('egypt-ydna-sync',0));
 if p_evidence_url not like 'https://%' or not exists(select 1 from public.ydna_sync_sources where id=p_source and publication_allowed) then
  raise exception 'Public withdrawal evidence and authorized source required'; end if;
 select sample_id into sid from public.ydna_sync_identities where namespace=p_namespace and external_id=upper(p_external_id);
 if sid is null then return jsonb_build_object('status','unknown_identity'); end if;
 update public.ydna_sync_observations set published=false where source_id=p_source and sample_id=sid and namespace=p_namespace and external_id=upper(p_external_id);
 if not exists(select 1 from public.ydna_sync_observations where sample_id=sid and published) then
  update public."Modern_published_samples" set sync_visibility='withdrawn' where id=sid and sync_managed;
 end if;
 perform public.ydna_sync_review(sid,p_source,'public_visibility_withdrawn',jsonb_build_object('evidence_url',p_evidence_url));
 return jsonb_build_object('status','withdrawn','sample_id',sid);
end $$;
revoke all on function public.ydna_sync_withdraw(text,text,text,text) from public,anon,authenticated;
grant execute on function public.ydna_sync_withdraw(text,text,text,text) to service_role;

-- The existing duplicate is deliberately preserved and queued, never silently deleted.
select public.ydna_sync_review(null,'legacy','duplicate_existing_identity',jsonb_build_object('namespace','ftdna','external_id',kit_number,'sample_ids',jsonb_agg(id order by id)))
 from public."Modern_published_samples" where kit_number is not null and kit_number<>'—' group by kit_number having count(*)>1;
