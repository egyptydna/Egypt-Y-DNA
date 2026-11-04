-- Synthetic topology only, always rolled back.
do $$
declare n bigint; result jsonb; a text:=repeat('a',64); b text:=repeat('b',64);
begin
 select count(*) into n from public."Modern_published_samples";
 insert into public.ydna_sync_sources(id,url,adapter,publication_allowed) values('synthetic-official-tree','https://example.org','yfull_github',true);
 insert into public.ydna_sync_tree_releases(source_id,release_key,tree_sha,version,commit_sha,published_at,source_url,license_name,license_url,attribution,node_count,selected_node_count)
 values('synthetic-official-tree',a,a,'1.0.0',repeat('a',40),now(),'https://github.com/example/tree','CC-BY-4.0','https://example.org/license','SYNTHETIC ONLY',4,2);
 insert into public.ydna_sync_official_tree_nodes(source_id,release_key,label,parent_label) values('synthetic-official-tree',a,'Y-Adam',null);
 begin
  perform public.ydna_sync_publish_tree('synthetic-official-tree',a);
  raise exception 'Incomplete release was published';
 exception when others then
  if sqlerrm<>'Tree release is incomplete' then raise; end if;
 end;
 insert into public.ydna_sync_official_tree_nodes(source_id,release_key,label,parent_label) values('synthetic-official-tree',a,'J-TEST1','Y-Adam');
 result:=public.ydna_sync_publish_tree('synthetic-official-tree',a);
 if result->>'status'<>'published' then raise exception 'Tree publication failed'; end if;
 insert into public.ydna_sync_tree_releases(source_id,release_key,tree_sha,version,commit_sha,published_at,source_url,license_name,license_url,attribution,node_count,selected_node_count)
 values('synthetic-official-tree',b,b,'1.1.0',repeat('b',40),now(),'https://github.com/example/tree','CC-BY-4.0','https://example.org/license','SYNTHETIC ONLY',5,1);
 insert into public.ydna_sync_official_tree_nodes(source_id,release_key,label,parent_label) values('synthetic-official-tree',b,'Y-Adam',null);
 perform public.ydna_sync_publish_tree('synthetic-official-tree',b);
 if (select count(*) from public.ydna_sync_tree_releases where source_id='synthetic-official-tree' and is_current)<>1 then raise exception 'Current release switch is not atomic'; end if;
 if (select count(*) from public."Modern_published_samples")<>n then raise exception 'Topology import invented testers'; end if;
 if has_function_privilege('anon','public.ydna_sync_publish_tree(text,text)','execute') then raise exception 'Anonymous tree writes exposed'; end if;
end $$;
