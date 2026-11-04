-- Additive derived topology only; all existing tester/archive tables remain unchanged.
create table public.ydna_sync_tree_releases (
 source_id text not null references public.ydna_sync_sources(id),
 release_key text not null check(release_key ~ '^[0-9a-f]{64}$'),
 tree_sha text not null check(tree_sha ~ '^[0-9a-f]{64}$'),
 version text not null, commit_sha text not null check(commit_sha ~ '^[0-9a-f]{40}$'),
 published_at timestamptz not null, checked_at timestamptz not null default now(),
 source_url text not null check(source_url like 'https://github.com/%'),
 license_name text not null,license_url text not null,attribution text not null,
 node_count integer not null check(node_count>0),
 selected_node_count integer not null check(selected_node_count>0 and selected_node_count<=node_count),
 changes jsonb not null default '{}',metadata jsonb not null default '{}',
 is_current boolean not null default false,published boolean not null default false,
 primary key(source_id,release_key)
);
create unique index one_current_official_tree on public.ydna_sync_tree_releases(source_id) where is_current;
create table public.ydna_sync_official_tree_nodes (
 source_id text not null,release_key text not null,label text not null,parent_label text,
 aliases jsonb not null default '[]' check(jsonb_typeof(aliases)='array'),
 snp_groups jsonb not null default '[]' check(jsonb_typeof(snp_groups)='array'),
 age_estimates jsonb not null default '{}' check(jsonb_typeof(age_estimates)='object'),
 primary key(source_id,release_key,label),
 foreign key(source_id,release_key) references public.ydna_sync_tree_releases(source_id,release_key),
 foreign key(source_id,release_key,parent_label) references public.ydna_sync_official_tree_nodes(source_id,release_key,label) deferrable initially deferred,
 check(parent_label is null or parent_label<>label)
);
create index official_tree_parent on public.ydna_sync_official_tree_nodes(source_id,release_key,parent_label);
alter table public.ydna_sync_tree_releases enable row level security;
alter table public.ydna_sync_official_tree_nodes enable row level security;
revoke all on public.ydna_sync_tree_releases,public.ydna_sync_official_tree_nodes from public,anon,authenticated;
grant all on public.ydna_sync_tree_releases,public.ydna_sync_official_tree_nodes to service_role;
grant select on public.ydna_sync_tree_releases,public.ydna_sync_official_tree_nodes to anon,authenticated;
create policy published_official_release on public.ydna_sync_tree_releases for select to anon,authenticated using(published and is_current);
create policy published_official_nodes on public.ydna_sync_official_tree_nodes for select to anon,authenticated using(exists(
 select 1 from public.ydna_sync_tree_releases r where r.source_id=ydna_sync_official_tree_nodes.source_id
 and r.release_key=ydna_sync_official_tree_nodes.release_key and r.published and r.is_current));

create function public.ydna_sync_publish_tree(p_source text,p_release text) returns jsonb
language plpgsql security invoker set search_path=public,pg_temp as $$
declare v_release public.ydna_sync_tree_releases%rowtype; n bigint;
begin
 perform pg_advisory_xact_lock(hashtextextended('egypt-ydna-sync',0));
 if not exists(select 1 from public.ydna_sync_sources where id=p_source and publication_allowed) then raise exception 'Tree source not approved'; end if;
 select * into v_release from public.ydna_sync_tree_releases where source_id=p_source and release_key=p_release for update;
 if v_release.source_id is null then raise exception 'Tree release missing'; end if;
 select count(*) into n from public.ydna_sync_official_tree_nodes where source_id=p_source and release_key=p_release;
 if n<>v_release.selected_node_count then raise exception 'Tree release is incomplete'; end if;
 if (select count(*) from public.ydna_sync_official_tree_nodes where source_id=p_source and release_key=p_release and parent_label is null)<>1
 or not exists(select 1 from public.ydna_sync_official_tree_nodes where source_id=p_source and release_key=p_release and label='Y-Adam' and parent_label is null) then
  raise exception 'Published tree root missing or ambiguous'; end if;
 update public.ydna_sync_tree_releases set is_current=false where source_id=p_source and is_current and release_key<>p_release;
 update public.ydna_sync_tree_releases set published=true,is_current=true,checked_at=now() where source_id=p_source and release_key=p_release;
 return jsonb_build_object('status','published','selected_nodes',n,'version',v_release.version);
end $$;
revoke all on function public.ydna_sync_publish_tree(text,text) from public,anon,authenticated;
grant execute on function public.ydna_sync_publish_tree(text,text) to service_role;
