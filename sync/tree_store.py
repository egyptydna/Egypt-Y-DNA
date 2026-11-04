"""Stage a licensed relevant subtree, then publish it in one DB transaction."""
import json
from datetime import datetime,timezone
from .topology import reference_labels,release_key


def read_references(db):
    refs=[]
    for table in ['Modern_published_samples','Modern_study_samples','Ancient_published_samples','ancient_related_samples']:
        for offset in range(0,1_000_000,1000):
            resource=table+'?select=y_dna,y_dna_alias&order=id&offset='+str(offset)+'&limit=1000'
            if table=='Modern_published_samples': resource+='&sync_visibility=eq.public'
            rows=db.request(resource,method='GET')
            refs.extend(rows)
            if len(rows)<1000: break
    for offset in range(0,1_000_000,1000):
        rows=db.request('ydna_sync_country_counts?select=node_label&published=eq.true&is_current=eq.true&order=id&offset='+str(offset)+'&limit=1000',method='GET')
        refs.extend(rows)
        if len(rows)<1000: break
    return reference_labels(refs)


def plan_release(job,queries):
    tree=job['tree'];nodes,matches=tree.select(queries)
    key=release_key(job['tree_sha'],queries)
    release={k:job[k] for k in ['source_id','tree_sha','version','commit_sha','published_at','source_url','license_name','license_url','attribution']}
    release.update(release_key=key,node_count=len(tree.nodes),selected_node_count=len(nodes),
        changes=job['changes'],metadata={'matches':matches,'processing':'Relevant published paths extracted; original SNP groups and ybp ages preserved.',
        'contains_individual_testers':False})
    staged=[dict(n,source_id=job['source_id'],release_key=key) for n in nodes]
    return release,staged


def sync_tree(job,db=None,apply=False,queries=None):
    queries=read_references(db) if queries is None and db else (queries or [])
    release,nodes=plan_release(job,queries)
    summary={'version':job['version'],'source_commit':job['commit_sha'],'source_published_at':job['published_at'],
        'source_nodes':release['node_count'],'selected_nodes':len(nodes),
        'matched_queries':sum(m['status'] in ('exact','equivalent_snp') for m in release['metadata']['matches'].values()),
        'ambiguous_queries':sum(m['status']=='ambiguous' for m in release['metadata']['matches'].values()),
        'unmatched_queries':sum(m['status']=='unmatched' for m in release['metadata']['matches'].values()),
        'changes':job['changes'],'profiles_created':0,'status':'dry_run'}
    if not apply: return summary
    existing=db.request('ydna_sync_tree_releases?source_id=eq.'+job['source_id']+'&is_current=eq.true&select=release_key,tree_sha',method='GET')
    if existing and existing[0]['release_key']==release['release_key']:
        db.request('ydna_sync_tree_releases?source_id=eq.'+job['source_id']+'&release_key=eq.'+release['release_key'],
            {'checked_at':datetime.now(timezone.utc).isoformat()},'PATCH')
        summary['status']='unchanged'
        summary['changes']={'baseline':False,'new_nodes':0,'removed_nodes':0,'moved_nodes':0,'changed_snp_blocks':0,'changed_age_estimates':0}
    else:
        if existing and existing[0]['tree_sha']==release['tree_sha']:
            # Only the archive's requested labels changed, not the source topology.
            summary['changes']={'baseline':False,'new_nodes':0,'removed_nodes':0,'moved_nodes':0,'changed_snp_blocks':0,'changed_age_estimates':0}
        elif existing and job['changes'].get('baseline'):
            # An evicted Actions cache is not evidence that every branch is new.
            summary['changes']={'baseline':False,'comparison_unavailable':True,'reason':'Previous full source snapshot not in cache'}
        release['changes']=summary['changes']
        db.request('ydna_sync_tree_releases?on_conflict=source_id,release_key',release)
        for offset in range(0,len(nodes),200):
            db.request('ydna_sync_official_tree_nodes?on_conflict=source_id,release_key,label',nodes[offset:offset+200])
        result=db.request('rpc/ydna_sync_publish_tree',{'p_source':job['source_id'],'p_release':release['release_key']})
        summary['status']=result['status']
    job['cache_state_path'].write_text(json.dumps(job['cache_state']))
    return summary
