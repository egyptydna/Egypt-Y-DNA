create policy private_identity_merges on public.ydna_sync_identity_merges
 for all to anon,authenticated using(false) with check(false);
create index identity_merge_canonical on public.ydna_sync_identity_merges(canonical_id);
create index modern_merged_into on public."Modern_published_samples"(sync_merged_into) where sync_merged_into is not null;

-- Opting out through either the retired or canonical ID covers the complete
-- verified identity. Private historical backup erasure remains a maintainer task.
alter function public.ydna_sync_opt_out(bigint) rename to ydna_sync_opt_out_single;
create function public.ydna_sync_opt_out(p_sample bigint) returns void
language plpgsql security invoker set search_path=public,pg_temp as $$
declare linked_ids bigint[]; sid bigint;
begin
 perform pg_advisory_xact_lock(hashtextextended('egypt-ydna-sync',0));
 with recursive linked(id) as (
  values(p_sample)
  union
  select e.b from linked l join (
   select canonical_id a,retired_id b from public.ydna_sync_identity_merges
   union all select retired_id,canonical_id from public.ydna_sync_identity_merges
  ) e on e.a=l.id
 ) select array_agg(id) into linked_ids from linked;
 foreach sid in array linked_ids loop
  perform public.ydna_sync_opt_out_single(sid);
 end loop;
 update public.ydna_sync_identity_merges set original_canonical='{}',original_retired='{}',
  evidence_url='https://egyptydna.github.io/Egypt-Y-DNA/'
  where canonical_id=any(linked_ids) or retired_id=any(linked_ids);
end $$;
revoke all on function public.ydna_sync_opt_out(bigint) from public,anon,authenticated;
grant execute on function public.ydna_sync_opt_out(bigint) to service_role;
