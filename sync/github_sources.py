import json
import re
from pathlib import Path
from .github_files import GitHubFiles, sha256
from .http import SourceRestricted
from .topology import YFullTree


def collect_yfull_github(source,http=None):
    if not source.get('publication_allowed'):
        raise SourceRestricted('Official YFull GitHub source is not enabled for publication')
    if source.get('repo','YFullTeam/YTree').lower()!='yfullteam/ytree':
        raise SourceRestricted('Official YFull adapter requires the YFullTeam/YTree repository')
    files=GitHubFiles(source.get('repo','YFullTeam/YTree'),source.get('branch','master'))
    head=files.resolve_head()
    license_bytes=files.file('LICENSE.md')
    if sha256(license_bytes)!=source.get('expected_license_sha256') or not license_bytes.startswith(b'Creative Commons Attribution 4.0 International Public License'):
        raise SourceRestricted('YFull repository license changed; publication requires review')
    version=files.file('current_version.txt').decode().strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+',version): raise ValueError('Invalid published YFull version')
    raw=files.file('current_tree.json');tree=YFullTree(json.loads(raw))
    previous=None;state_path=files.root/'last-applied.json'
    if state_path.exists():
        state=json.loads(state_path.read_text());old=files.root/state['commit_sha']/'current_tree.json'
        if old.exists(): previous=YFullTree(json.loads(old.read_bytes()))
    published=files.file_published_at('current_tree.json')
    return [{'kind':'licensed_tree','tree':tree,'tree_sha':sha256(raw),'version':version,'commit_sha':head['sha'],
        'published_at':published,'source_id':source['id'],'source_url':files.permalink('current_tree.json'),
        'license_name':'CC-BY-4.0','license_url':files.permalink('LICENSE.md'),
        'attribution':'YFull / YFullTeam, YTree — CC BY 4.0',
        'changes':tree.diff(previous),'cache_state_path':state_path,
        'cache_state':{'commit_sha':head['sha'],'tree_sha':sha256(raw),'version':version}}],[]


def parse_ftdnastat_egypt(data,backbone,source,observed_at,source_url):
    if data.get('slug')!='egypt' or data.get('name')!='Egypt': raise ValueError('Not the Egypt statistics file')
    terminal=data.get('terminal');nodes=backbone.get('nodes');cum=data.get('cum')
    if not isinstance(terminal,list) or not isinstance(nodes,list) or not isinstance(cum,list): raise ValueError('Unsupported ftdnastat schema')
    if data.get('cumN')!=len(nodes): raise ValueError('Cumulative index does not match its published backbone')
    total=data.get('n')
    if not isinstance(total,int) or isinstance(total,bool) or total<0: raise ValueError('Invalid ftdnastat country total')
    labels=[]
    for i,row in enumerate(nodes):
        if not isinstance(row,list) or len(row)<2 or not isinstance(row[0],int) or row[0]<-1 or row[0]>=i:
            raise ValueError('Invalid ftdnastat ancestor index')
        labels.append(row[1])
    if len(set(labels))!=len(labels): raise ValueError('Duplicate ftdnastat backbone label')
    records=[];seen=set()
    def add(label,count,scope):
        if not isinstance(label,str) or not re.fullmatch(r'[A-T][A-Za-z0-9*.+_\-]*',label): raise ValueError('Invalid ftdnastat node')
        if not isinstance(count,int) or isinstance(count,bool) or count<0: raise ValueError('Invalid ftdnastat count')
        if (label,scope) in seen: raise ValueError('Duplicate ftdnastat count')
        seen.add((label,scope))
        records.append({'kind':'country_count','source_id':source['id'],'namespace':'ftdna','node_label':label,
            'reported_count':count,'country_code':'EG','count_scope':scope,'population':'unknown',
            'observed_at':observed_at,'source_url':source_url,'publication_allowed':source.get('publication_allowed',False),
            'permission_url':source.get('data_permission_url') or ''})
    for row in terminal:
        if not isinstance(row,list) or len(row)!=2: raise ValueError('Invalid ftdnastat terminal row')
        add(row[0],row[1],'direct')
    if sum(r['reported_count'] for r in records)!=total: raise ValueError('Terminal counts do not add up to the country total')
    for row in cum:
        if not isinstance(row,list) or len(row)!=2 or not isinstance(row[0],int) or not 0<=row[0]<len(nodes):
            raise ValueError('Invalid ftdnastat cumulative index')
        add(labels[row[0]],row[1],'inclusive')
    return records,{'country_total':total,'terminal_rows':len(terminal),'cumulative_rows':len(cum),'backbone_nodes':len(nodes)}


def collect_ftdnastat(source,http=None):
    # MIT is the software license. It is never substituted for permission to reuse the data.
    if not source.get('publication_allowed') or not str(source.get('data_permission_url') or '').startswith('https://'):
        raise SourceRestricted('ftdnastat data reuse not approved; software MIT license is insufficient')
    files=GitHubFiles(source.get('repo','ftdnastat/ftdnastat.github.io'),source.get('branch','master'))
    files.resolve_head()
    data=json.loads(files.file('data/egypt.y.json'));backbone=json.loads(files.file('data/compare-tree.y.json'))
    records,_=parse_ftdnastat_egypt(data,backbone,source,files.file_published_at('data/egypt.y.json'),files.permalink('data/egypt.y.json'))
    return records,[]
