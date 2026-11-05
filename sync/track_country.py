"""Own, server-side tracker for published anonymous Egyptian FTDNA branch counts.

No provider website crawling and no tester identities are created. The primary
input is a projection of public aggregate facts from GitHub. The already-owned
Observatory mirror supplies a second, independently timestamped snapshot.
"""
import argparse
import hashlib
import json
import re
from datetime import datetime,timezone
from pathlib import Path
from .github_files import GitHubFiles,sha256
from .run import Database

PRIMARY='ftdna-aggregate-github'
BACKUP='owner-observatory-export'
REPO='ftdnastat/ftdnastat.github.io'
LABEL=re.compile(r'[A-T][A-Za-z0-9*.+_\-]*')
PUBLICATION='https://github.com/egyptydna/Egypt-Y-DNA/blob/main/docs/COUNTRY-TRACKER.md'


def timestamp(value):
    parsed=datetime.fromisoformat(str(value).replace('Z','+00:00'))
    if parsed.tzinfo is None:raise ValueError('Source date requires a timezone')
    return parsed


def snapshot(source_id,nodes,observed_at,source_url,details=None,total=None):
    timestamp(observed_at)
    clean=[];seen=set()
    for item in nodes:
        label=str(item['label']).strip();count=item['count'];path=item.get('path') or []
        if not LABEL.fullmatch(label) or label.upper() in seen:raise ValueError('Invalid or duplicate source branch')
        if not isinstance(count,int) or isinstance(count,bool) or count<0:raise ValueError('Invalid branch count')
        if not isinstance(path,list) or any(not isinstance(p,str) or not re.fullmatch(r'[A-Za-z0-9*.+_\-]+',p) for p in path):raise ValueError('Invalid reference path')
        if path and (path[-1].upper()!=label.upper() or len(path)!=len(set(path)) or not str(item.get('path_source_url','')).startswith('https://')):raise ValueError('Unverified reference path')
        seen.add(label.upper())
        clean.append(dict(label=label,count=count,path=path,path_source_url=item.get('path_source_url'),
            path_kind=item.get('path_kind','terminal_only'),path_observed_at=item.get('path_observed_at')))
    clean.sort(key=lambda n:n['label'].upper())
    actual=sum(n['count'] for n in clean)
    if total is not None and (not isinstance(total,int) or isinstance(total,bool) or actual!=total):raise ValueError('Incomplete country total')
    if not str(source_url).startswith('https://'):raise ValueError('Public snapshot evidence required')
    # Check time never enters the identity: an unchanged poll creates no new samples.
    fingerprint=sha256(json.dumps([source_id,observed_at,[(n['label'],n['count'],n['path']) for n in clean]],sort_keys=True).encode())
    return dict(source_id=source_id,snapshot_key=fingerprint,provider='ftdna',country_code='EG',
        observed_at=observed_at,total_count=actual,nodes=clean,source_url=source_url,details=details or {})


def backup_snapshot(rows,metadata=None):
    metadata=metadata or {}
    direct=[r for r in rows if r.get('source_id')==BACKUP and r.get('namespace')=='ftdna'
        and r.get('country_code')=='EG' and r.get('count_scope')=='direct' and r.get('published',True)]
    if not direct:return None
    date=metadata.get('snapshot_checked_at') or max((r['observed_at'] for r in direct),key=timestamp)
    direct=[r for r in direct if timestamp(r['observed_at'])==timestamp(date)]
    if not direct:return None
    if metadata.get('country_terminal_rows') is not None and len(direct)!=metadata['country_terminal_rows']:raise ValueError('Incomplete backup import')
    nodes=[dict(label=r['node_label'],count=r['reported_count'],path=r.get('snp_path') or [],
        path_source_url=r.get('path_source_url'),path_kind='archived_public_tree',path_observed_at=r['observed_at']) for r in direct]
    return snapshot(BACKUP,nodes,date,metadata.get('archive_url','https://egypt-ydna-observatory.kimoeln.chatgpt.site/'),
        dict(collector='Owned Observatory mirror',scope='Public FTDNA Y-DNA country branch counts',
            reported_other_total=metadata.get('reported_other_total'),backup_total_note=metadata.get('country_coverage_note')),
        total=metadata.get('country_total'))


def primary_snapshot(data,backbone,observed_at,source_url,details,backup=None):
    if data.get('name')!='Egypt' or data.get('slug')!='egypt' or not isinstance(data.get('terminal'),list):raise ValueError('Not an Egyptian country dataset')
    if not isinstance(backbone.get('nodes'),list) or data.get('cumN')!=len(backbone['nodes']):raise ValueError('Backbone index changed')
    paths={}
    for index,row in enumerate(backbone['nodes']):
        if not isinstance(row,list) or len(row)<2 or not isinstance(row[0],int) or not -1<=row[0]<index or not LABEL.fullmatch(str(row[1])):raise ValueError('Invalid source backbone')
        paths[row[1]]=(paths[backbone['nodes'][row[0]][1]] if row[0]>=0 else [])+[row[1]]
    archived={n['label'].upper():n for n in (backup or {}).get('nodes',[]) if n.get('path')}
    nodes=[]
    for row in data['terminal']:
        if not isinstance(row,list) or len(row)!=2:raise ValueError('Invalid terminal count')
        label,count=row;ref=archived.get(str(label).upper())
        if ref:
            path=ref['path'];path_url=ref['path_source_url'];kind='archived_public_tree';path_date=ref.get('path_observed_at')
        else:
            path=paths.get(label,[]);path_url=details.get('backbone_url') if path else None
            kind='published_backbone' if path else 'terminal_only';path_date=observed_at if path else None
        nodes.append(dict(label=label,count=count,path=path,path_source_url=path_url,path_kind=kind,path_observed_at=path_date))
    # The backbone URL documents ancestry; it is not copied into public details wholesale.
    details={k:v for k,v in details.items() if k!='backbone_url'}
    if backup:
        details.update({k:backup.get('details',{}).get(k) for k in ('reported_other_total','backup_total_note')})
    return snapshot(PRIMARY,nodes,observed_at,source_url,details,total=data.get('n'))


def fetch_primary(backup=None,files=None):
    files=files or GitHubFiles(REPO)
    head=files.resolve_head()
    license_bytes=files.file('LICENSE')
    if not license_bytes.startswith(b'MIT License\n') or b'Copyright (c) 2026 Arsen Abdusalamov' not in license_bytes:
        raise ValueError('Repository license changed; review required')
    # This collector reads only non-identifying factual totals. It never treats
    # the software license as permission for individual DNA profiles or crawling.
    data=json.loads(files.file('data/egypt.y.json'))
    tree=json.loads(files.file('data/compare-tree.y.json'))
    version=json.loads(files.file('version.json'))
    date=files.file_published_at('data/egypt.y.json')
    return primary_snapshot(data,tree,date,files.permalink('data/egypt.y.json'),dict(
        collector='Egypt Y-DNA public aggregate tracker',version=version.get('version'),data_date=version.get('yPublished'),
        commit_sha=head['sha'],backbone_url=files.permalink('data/compare-tree.y.json'),
        license_name='MIT (repository code/documentation)',license_url=files.permalink('LICENSE'),
        attribution='FTDNA public country counts; processing by ftdnastat / Arsen Abdusalamov',
        reuse_basis='Owner-authorized use of published anonymous aggregate facts; no individual profiles or provider website access.',
        path_note='Dated, published reference ancestry; missing intermediate SNPs are never inferred.'),backup)


def rows(db,resource):
    result=[]
    for offset in range(0,100000,1000):
        page=db.request(resource+'&offset='+str(offset)+'&limit=1000',method='GET')
        result.extend(page)
        if len(page)<1000:return result
    raise ValueError('Source exceeds country tracker size limit')


def read_backup(db):
    sources=db.request('ydna_sync_sources?id=eq.'+BACKUP+'&select=metadata,publication_allowed',method='GET')
    if not sources or not sources[0]['publication_allowed']:return None
    data=rows(db,'ydna_sync_country_counts?source_id=eq.'+BACKUP+'&namespace=eq.ftdna&country_code=eq.EG&count_scope=eq.direct&published=eq.true&is_current=eq.true&order=id')
    return backup_snapshot(data,sources[0]['metadata'])


def track(apply=False,db=None,fetcher=fetch_primary):
    if apply and db is None:db=Database()
    report={'checked_at':datetime.now(timezone.utc).isoformat(),'mode':'apply' if apply else 'dry_run','profiles_created':0}
    backup=None
    if db:
        try:
            backup=read_backup(db)
            if backup:
                report['backup_total']=backup['total_count']
                if apply:report['backup']=db.request('rpc/ydna_tracker_publish',{'p_snapshot':backup,'p_dry_run':False})
        except (ValueError,RuntimeError) as error:report['backup_status']='unavailable';report['backup_error_type']=type(error).__name__
    try:
        primary=fetcher(backup)
        report.update(primary_status='ok',primary_total=primary['total_count'],primary_data_at=primary['observed_at'])
        if apply:
            db.request('ydna_sync_sources?on_conflict=id',dict(id=PRIMARY,url='https://github.com/'+REPO,
                adapter='public_aggregate_tracker',publication_allowed=True,permission_url=PUBLICATION,
                metadata={'aggregate_facts_only':True,'scope':'Egyptian country branch counts; no individual data',
                    'attribution':primary['details'].get('attribution'),'reuse_basis':primary['details'].get('reuse_basis')}))
            result=db.request('rpc/ydna_tracker_publish',{'p_snapshot':primary,'p_dry_run':False})
            report['primary']=result
            if result.get('status')=='review':report['primary_status']='unavailable'
    except Exception as error:
        # No payload, credentials, or remote response bodies go into public logs.
        report.update(primary_status='unavailable',primary_error_type=type(error).__name__)
    if apply:
        message='Primary public file checked. The newest verified complete snapshot is displayed.' if report['primary_status']=='ok' else 'Primary source unavailable or invalid. Retaining the newest verified snapshot or Observatory backup.'
        report['selected']=db.request('rpc/ydna_tracker_select',{'p_primary_status':report['primary_status'],'p_message':message})
    return report


def main():
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    report=track(args.apply)
    out=Path('reports');out.mkdir(exist_ok=True)
    (out/'country-tracker.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
