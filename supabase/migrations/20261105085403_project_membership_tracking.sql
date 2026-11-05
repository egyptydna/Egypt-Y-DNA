-- Additive project tracking. Existing archive/profile/STR records are preserved.
create table public.ydna_project_catalog (
 project_key text primary key, name text not null, source_url text not null,
 discovered_at timestamptz not null default now(),
 last_evidence_at timestamptz, access_status text not null default 'unverified'
);
create table public.ydna_project_memberships (
 sample_id bigint not null references public."Modern_published_samples"(id),
 project_key text not null references public.ydna_project_catalog(project_key),
 observation_id bigint not null references public.ydna_sync_observations(id),
 evidence_url text not null, first_seen_at timestamptz not null default now(),
 last_seen_at timestamptz not null, is_baseline boolean not null,
 primary key(sample_id,project_key)
);
create index on public.ydna_project_memberships(project_key);
create index on public.ydna_project_memberships(observation_id);
create table public.ydna_project_profile_activity (
 sample_id bigint primary key references public."Modern_published_samples"(id),
 first_detected_at timestamptz not null default now(), new_until timestamptz
);
-- Initial deployment is a baseline, not thousands of newly discovered people.
insert into public.ydna_project_profile_activity(sample_id)
 select id from public."Modern_published_samples";
create table public.ydna_project_targets (
 target_key text primary key, kind text not null check(kind in ('kit','lineage')),
 sample_id bigint references public."Modern_published_samples"(id), lineage text,
 snapshot_id uuid references public.ydna_tracker_snapshots(id),
 origin_project text, created_at timestamptz not null default now(),
 checked_at timestamptz, status text not null default 'pending',
 check(kind<>'lineage' or sample_id is null)
);
create index on public.ydna_project_targets(sample_id);
create index on public.ydna_project_targets(snapshot_id);
create index on public.ydna_project_targets(checked_at nulls first);
create table public.ydna_project_target_checks (
 target_key text not null references public.ydna_project_targets(target_key),
 project_key text not null references public.ydna_project_catalog(project_key),
 status text not null check(status in ('exact_kit_match','lineage_candidate','no_saved_match','permission_needed')),
 checked_at timestamptz not null default now(),
 evidence_scope text not null default 'saved_public_evidence',
 primary key(target_key,project_key)
);
create index on public.ydna_project_target_checks(project_key);
create table public.ydna_project_tracking_status (
 id boolean primary key default true check(id),
 initialized_at timestamptz not null default now(),
 seeded_directory_key text,
 last_attempt_at timestamptz, last_saved_at timestamptz,
 state text not null default 'pending', summary jsonb not null default '{}'
);
insert into public.ydna_project_tracking_status(id) values(true);
do $$ declare t text; begin
 foreach t in array array['ydna_project_catalog','ydna_project_memberships',
 'ydna_project_profile_activity','ydna_project_targets','ydna_project_target_checks',
 'ydna_project_tracking_status'] loop
  execute format('alter table public.%I enable row level security',t);
  execute format('revoke all on public.%I from public,anon,authenticated',t);
  execute format('grant all on public.%I to service_role',t);
 end loop;
end $$;
grant select on public.ydna_project_catalog,public.ydna_project_memberships,
 public.ydna_project_profile_activity,public.ydna_project_tracking_status to anon,authenticated;
create policy project_catalog_read on public.ydna_project_catalog for select to anon,authenticated using(true);
create policy project_status_read on public.ydna_project_tracking_status for select to anon,authenticated using(true);
create policy project_membership_read on public.ydna_project_memberships for select to anon,authenticated using(
 exists(select 1 from public."Modern_published_samples" s where s.id=sample_id and s.sync_visibility='public')
 and exists(select 1 from public.ydna_sync_observations o where o.id=observation_id and o.published));
create policy project_activity_read on public.ydna_project_profile_activity for select to anon,authenticated using(
 exists(select 1 from public."Modern_published_samples" s where s.id=sample_id and s.sync_visibility='public'));

create function public.ydna_project_tracker_refresh(p_budget integer default 128,p_force boolean default false)
returns jsonb language plpgsql security invoker set search_path=public,pg_temp as $$
declare
 v_now timestamptz:=now(); st public.ydna_project_tracking_status%rowtype;
 t public.ydna_project_targets%rowtype; v_processed integer:=0;
 v_project_search jsonb; v_directory jsonb; v_sources jsonb; v_run jsonb;
 v_summary jsonb; v_previous_snapshot uuid; v_latest_snapshot uuid;
 v_evidence_changed_at timestamptz;
begin
 if p_budget<1 or p_budget>512 then raise exception 'Invalid search budget'; end if;
 if not pg_try_advisory_xact_lock(hashtextextended('egypt-project-tracking',0)) then
  return jsonb_build_object('status','already_running'); end if;
 select * into st from public.ydna_project_tracking_status where id for update;
 if not p_force and st.last_saved_at>v_now-interval '50 minutes' and st.state<>'failed' then
  return jsonb_build_object('status','recent_skip','lastAttemptAt',st.last_attempt_at,
   'lastSavedAt',st.last_saved_at,'summary',st.summary); end if;
 update public.ydna_project_tracking_status set last_attempt_at=v_now where id;

 -- Catalog only documented project labels/URLs. A listed project is not a checked report.
 insert into public.ydna_project_catalog(project_key,name,source_url,last_evidence_at,access_status)
 select lower(btrim(o.payload->>'project')),min(btrim(o.payload->>'project')),
  min(o.payload->>'source_url'),max(o.last_seen_at),'saved_evidence'
 from public.ydna_sync_observations o
 join public.ydna_sync_sources src on src.id=o.source_id and src.publication_allowed
 join public."Modern_published_samples" s on s.id=o.sample_id and s.sync_visibility='public'
 where o.published and o.is_current and o.namespace='ftdna'
  and length(btrim(o.payload->>'project')) between 1 and 160
  and o.payload->>'source_url' ~ '^https://(www\.)?familytreedna\.com/public/[^/?#]+'
 group by lower(btrim(o.payload->>'project'))
 on conflict(project_key) do update set last_evidence_at=excluded.last_evidence_at,
  source_url=excluded.source_url,access_status='saved_evidence';
 insert into public.ydna_project_catalog(project_key,name,source_url,access_status)
 select lower((regexp_match(url,'/public/([^/?#]+)'))[1]),
  (regexp_match(url,'/public/([^/?#]+)'))[1],min(url),'permission_needed'
 from public.ydna_sync_sources
 where adapter='ftdna_project' and url ~ '^https://(www\.)?familytreedna\.com/public/[^/?#]+'
 group by (regexp_match(url,'/public/([^/?#]+)'))[1]
 on conflict do nothing;
 -- The optional owner-maintained directory remains private. Publish its project metadata only.
 if to_regclass('public.ftdna_archive_project_candidates') is not null then
  execute $q$insert into public.ydna_project_catalog(project_key,name,source_url,access_status)
   select distinct on(lower((regexp_match(project_url,'/public/([^/?#]+)'))[1]))
    lower((regexp_match(project_url,'/public/([^/?#]+)'))[1]),
    coalesce(nullif(label,''),(regexp_match(project_url,'/public/([^/?#]+)'))[1]),
    project_url,'permission_needed'
   from public.ftdna_archive_project_candidates
   where project_url ~ '^https://(www\.)?familytreedna\.com/public/[^/?#]+'
   on conflict do nothing$q$;
 end if;

 -- Exact typed identity only: neither names nor shared branch labels join people.
 insert into public.ydna_project_memberships(sample_id,project_key,observation_id,evidence_url,
  first_seen_at,last_seen_at,is_baseline)
 select distinct on(o.sample_id,lower(btrim(o.payload->>'project')))
  o.sample_id,lower(btrim(o.payload->>'project')),o.id,o.payload->>'source_url',
  o.first_seen_at,o.last_seen_at,st.last_saved_at is null
 from public.ydna_sync_observations o
 join public.ydna_sync_sources src on src.id=o.source_id and src.publication_allowed
 join public."Modern_published_samples" s on s.id=o.sample_id and s.sync_visibility='public'
 join public.ydna_sync_identities i on i.sample_id=o.sample_id and i.namespace='ftdna'
  and i.external_id=upper(btrim(o.external_id))
 join public.ydna_project_catalog p on p.project_key=lower(btrim(o.payload->>'project'))
 where o.published and o.is_current and o.namespace='ftdna'
  and upper(btrim(o.external_id)) ~ '^[A-Z]{0,3}[0-9]+$'
  and upper(btrim(o.external_id)) !~ '^YF[0-9]+$'
  and o.payload->>'source_url' ~ '^https://(www\.)?familytreedna\.com/public/[^/?#]+'
 order by o.sample_id,lower(btrim(o.payload->>'project')),o.last_seen_at desc,o.id desc
 on conflict(sample_id,project_key) do update set observation_id=excluded.observation_id,
  evidence_url=excluded.evidence_url,last_seen_at=excluded.last_seen_at;
 insert into public.ydna_project_profile_activity(sample_id,new_until)
 select s.id,v_now+interval '30 days' from public."Modern_published_samples" s
 where s.sync_visibility='public' on conflict do nothing;
 insert into public.ydna_project_targets(target_key,kind,sample_id,origin_project)
 select 'kit:'||m.sample_id,'kit',m.sample_id,
  (array_agg(m.project_key order by m.first_seen_at,m.project_key))[1]
 from public.ydna_project_memberships m group by m.sample_id on conflict do nothing;

 -- Anonymous increases start lineage checks and NEVER acquire a sample identity.
 select snapshot_id into v_latest_snapshot from public.ydna_tracker_status where provider='ftdna';
 v_previous_snapshot:=nullif(st.summary->>'lastCountrySnapshotId','')::uuid;
 if v_latest_snapshot is not null and v_latest_snapshot is distinct from v_previous_snapshot then
  insert into public.ydna_project_targets(target_key,kind,lineage,snapshot_id)
  select 'lineage:'||c.snapshot_id||':'||md5(c.branch_label),'lineage',c.branch_label,c.snapshot_id
  from public.ydna_tracker_changes c
  where c.snapshot_id=v_latest_snapshot and c.kind='branch_change'
   and c.after_count>c.before_count and c.branch_label is not null
  on conflict do nothing;
 end if;

 select max(greatest(discovered_at,coalesce(last_evidence_at,discovered_at)))
 into v_evidence_changed_at from public.ydna_project_catalog;
 for t in select targets.* from public.ydna_project_targets targets
  where targets.checked_at is null or targets.checked_at<v_now-interval '24 hours'
   or targets.checked_at<v_evidence_changed_at
  order by targets.checked_at nulls first,targets.created_at,targets.target_key limit p_budget loop
  insert into public.ydna_project_target_checks(target_key,project_key,status,checked_at)
  select t.target_key,p.project_key,
   case when t.kind='kit' and exists(select 1 from public.ydna_project_memberships m
    where m.sample_id=t.sample_id and m.project_key=p.project_key) then 'exact_kit_match'
   when t.kind='lineage' and exists(select 1 from public.ydna_sync_observations o
    join public."Modern_published_samples" s on s.id=o.sample_id and s.sync_visibility='public'
    where o.is_current and o.published and lower(btrim(o.payload->>'project'))=p.project_key
     and upper(o.payload->>'y_dna')=upper(t.lineage)) then 'lineage_candidate'
   when p.access_status='permission_needed' then 'permission_needed' else 'no_saved_match' end,v_now
  from public.ydna_project_catalog p where p.access_status='saved_evidence'
   and t.origin_project is distinct from p.project_key
  on conflict(target_key,project_key) do update set status=excluded.status,checked_at=excluded.checked_at;
  update public.ydna_project_targets set checked_at=v_now,status=case
   when kind='lineage' then 'lineage_only'
   when exists(select 1 from public.ydna_project_target_checks c
    where c.target_key=t.target_key and c.status='exact_kit_match') then 'exact_match'
   else 'checked_saved_evidence' end where target_key=t.target_key;
  v_processed:=v_processed+1;
 end loop;

 select jsonb_build_object('targets',count(*),
  'queued',count(*) filter(where checked_at is null or checked_at<v_now-interval '24 hours'
   or checked_at<v_evidence_changed_at),
  'checkedTargets',count(*) filter(where checked_at is not null),
  'anonymousLineageTargets',count(*) filter(where kind='lineage'),
  'exactKitMatches',count(*) filter(where kind='kit' and status='exact_match'),
  'checkedProjectViews',(select count(*) from public.ydna_project_target_checks where status<>'permission_needed'),
  'permissionNeededProjectViews',(select count(*) from public.ydna_project_target_checks where status='permission_needed'),
  'lineageCandidateProjectViews',(select count(*) from public.ydna_project_target_checks where status='lineage_candidate'),
  'failedProjectViews',0,'partialProjectViews',0,
  'evidenceScope','saved_public_evidence','identityLinkForAnonymous',false)
 into v_project_search from public.ydna_project_targets;
 select jsonb_build_object('trackedProjects',count(*),
  'projectsWithSavedEvidence',count(*) filter(where access_status='saved_evidence'),
  'permissionNeededProjects',count(*) filter(where access_status<>'saved_evidence'),
  'neverLiveCheckedProjects',count(*),'fullCensus',false,
  'exactMemberships',(select count(*) from public.ydna_project_memberships m
   join public."Modern_published_samples" s on s.id=m.sample_id and s.sync_visibility='public'),
  'newProfiles30Days',(select count(*) from public.ydna_project_profile_activity a
   join public."Modern_published_samples" s on s.id=a.sample_id and s.sync_visibility='public' where a.new_until>v_now))
 into v_directory from public.ydna_project_catalog;
 select jsonb_build_object('startedAt',started_at,'finishedAt',finished_at,'status',status)
 into v_run from public.ydna_sync_runs order by started_at desc limit 1;
 select coalesce(jsonb_agg(jsonb_build_object('id',x->>'id','status',x->>'status',
  'records',coalesce((x->>'records')::integer,0),'reason',x->>'reason')),'[]') into v_sources
 from public.ydna_sync_runs r cross join lateral jsonb_array_elements(r.report->'sources') x
 where r.id=(select id from public.ydna_sync_runs order by started_at desc limit 1);
 v_summary:=jsonb_build_object('projectSearch',v_project_search,'projectDirectory',v_directory,
  'sourceRun',v_run,'sourcePartialRuns',v_sources,'processedTargets',v_processed,
  'lastCountrySnapshotId',v_latest_snapshot,'fullCensus',false,
  'scope','Saved published Y-DNA project evidence. Direct provider access is not granted by this tracker.');
 update public.ydna_project_tracking_status set last_saved_at=v_now,state='partial',summary=v_summary where id;
 return jsonb_build_object('status','partial','lastAttemptAt',v_now,'lastSavedAt',v_now,'summary',v_summary);
end $$;

create function public.ydna_project_tracker_failed()
returns void language sql security invoker set search_path=public,pg_temp as $$
 update public.ydna_project_tracking_status set last_attempt_at=now(),state='failed' where id;
$$;
create function public.ydna_project_catalog_seed(p_projects jsonb,p_version text,p_final boolean default false)
returns jsonb language plpgsql security invoker set search_path=public,pg_temp as $$
declare n integer;
begin
 if jsonb_typeof(p_projects)<>'array' or jsonb_array_length(p_projects)>500
  or p_version !~ '^[0-9a-f]{64}$' then raise exception 'Invalid project directory batch'; end if;
 if exists(select 1 from jsonb_array_elements(p_projects) x where
  length(btrim(x->>'code')) not between 1 and 160 or length(x->>'name')>500
  or x->>'url' !~ '^https://(www\.)?familytreedna\.com/(public|groups)/[^/?#]+'
  or x->>'code' is null or x->>'url' is null or x->>'name' is null) then
  raise exception 'Invalid project directory entry'; end if;
 insert into public.ydna_project_catalog(project_key,name,source_url,access_status)
 select distinct on(lower(btrim(x->>'code'))) lower(btrim(x->>'code')),x->>'name',x->>'url','unverified'
 from jsonb_array_elements(p_projects) x on conflict do nothing;
 get diagnostics n=row_count;
 if p_final then update public.ydna_project_tracking_status set seeded_directory_key=p_version where id; end if;
 return jsonb_build_object('insertedProjects',n,'batchSize',jsonb_array_length(p_projects));
end $$;
revoke all on function public.ydna_project_tracker_refresh(integer,boolean),
 public.ydna_project_tracker_failed(),public.ydna_project_catalog_seed(jsonb,text,boolean) from public,anon,authenticated;
grant execute on function public.ydna_project_tracker_refresh(integer,boolean),
 public.ydna_project_tracker_failed(),public.ydna_project_catalog_seed(jsonb,text,boolean) to service_role;
