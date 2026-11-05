-- Attach owner-authorized public observations to an exact existing identity.
-- This function never updates a tester's curated archive fields.
create function public.ydna_sync_attach_archive_evidence(p_record jsonb,p_dry_run boolean default true)
returns jsonb language plpgsql security invoker set search_path=public,pg_temp as $$
declare
 ns text:=p_record->>'namespace'; eid text:=upper(p_record->>'external_id'); src text:=p_record->>'source_id';
 ids bigint[]; sid bigint; oid bigint; v_checksum text:=md5(p_record::text); marker jsonb; markers integer:=0;
 s public."Modern_published_samples"%rowtype; old_ob public.ydna_sync_observations%rowtype;
begin
 perform pg_advisory_xact_lock(hashtextextended('egypt-ydna-sync',0));
 if ns is null or ns not in ('ftdna','yfull') or eid is null or eid !~ '^[A-Z]{0,3}[0-9]+$' or (ns='yfull' and eid !~ '^YF[0-9]+$') then raise exception 'Invalid external identity'; end if;
 if exists(select 1 from public.ydna_sync_optouts where identity_hash=encode(sha256(convert_to(ns||':'||eid,'UTF8')),'hex')) then
  return jsonb_build_object('status','opted_out','evidence_attached',false); end if;
 if not coalesce((p_record->>'accepted')::boolean,false) or p_record->'origin'->>'country' is distinct from 'EG'
  or p_record->>'sample_kind' is distinct from 'modern' or p_record->>'origin_kind' is distinct from 'paternal'
  or not coalesce((p_record->>'publication_allowed')::boolean,false) then raise exception 'Accepted modern Egyptian paternal evidence required'; end if;
 if not exists(select 1 from public.ydna_sync_sources where id=src and publication_allowed and adapter='owned_archive_transfer'
  and metadata->>'archive_url'=p_record->>'archive_source_url') then raise exception 'Owner-authorized archive source required'; end if;
 select array_agg(distinct id) into ids from public."Modern_published_samples" m
 where m.sync_visibility='public' and ((ns='ftdna' and upper(trim(m.kit_number))=eid)
  or (ns='yfull' and (upper(trim(m.yfull_id))=eid or upper(trim(m.kit_number))=eid))
  or exists(select 1 from public.ydna_sync_identities i where i.namespace=ns and i.external_id=eid and i.sample_id=m.id));
 if coalesce(cardinality(ids),0)<>1 then return jsonb_build_object('status','review','reason','exact_existing_identity_required','evidence_attached',false); end if;
 sid:=ids[1];select * into strict s from public."Modern_published_samples" where id=sid for update;
 if exists(select 1 from public.ydna_sync_identities where namespace=ns and external_id=eid and sample_id<>sid) then
  return jsonb_build_object('status','review','reason','identity_collision','evidence_attached',false); end if;
 select * into old_ob from public.ydna_sync_observations where source_id=src and namespace=ns and external_id=eid and is_current order by id desc limit 1;
 if old_ob.id is not null and not old_ob.published then return jsonb_build_object('status','suppressed','evidence_attached',false); end if;
 if old_ob.id is not null and old_ob.checksum=v_checksum then return jsonb_build_object('status','retained_existing','evidence_attached',false,'sample_id',sid); end if;
 if p_dry_run then return jsonb_build_object('status','would_attach_evidence','sample_id',sid,'marker_count',jsonb_array_length(coalesce(p_record->'str_markers','[]'))); end if;
 insert into public.ydna_sync_identities(namespace,external_id,sample_id,evidence_url)
  values(ns,eid,sid,p_record->>'source_url') on conflict do nothing;
 update public.ydna_sync_observations set is_current=false where source_id=src and namespace=ns and external_id=eid and is_current;
 -- Reuse a previously recorded identical version if a source returns to it.
 insert into public.ydna_sync_observations(source_id,namespace,external_id,checksum,sample_id,payload,published,is_current)
 values(src,ns,eid,v_checksum,sid,p_record,true,true)
 on conflict(source_id,namespace,external_id,checksum) do update
  set sample_id=excluded.sample_id,last_seen_at=now(),is_current=true
 returning id into oid;
 for marker in select * from jsonb_array_elements(coalesce(p_record->'str_markers','[]')) loop
  insert into public.ydna_sync_str_values(observation_id,position,marker,source_label,allele)
   values(oid,(marker->>'position')::integer,marker->>'marker',marker->>'source_label',marker->>'value') on conflict do nothing;
  markers:=markers+1;
 end loop;
 if coalesce(s.y_dna,'') not in ('','—','-') and coalesce(p_record->>'y_dna','') not in ('','—','-') and s.y_dna<>p_record->>'y_dna' then
  perform public.ydna_sync_review(sid,src,'source_terminal_difference',jsonb_build_object('existing',s.y_dna,'proposed',p_record->>'y_dna','observation_id',oid,'resolution_policy','Curated tester retained; source claim attached separately'));
 end if;
 return jsonb_build_object('status','retained_existing','evidence_attached',true,'sample_id',sid,'observation_id',oid,'marker_count',markers);
end $$;
revoke all on function public.ydna_sync_attach_archive_evidence(jsonb,boolean) from public,anon,authenticated;
grant execute on function public.ydna_sync_attach_archive_evidence(jsonb,boolean) to service_role;
