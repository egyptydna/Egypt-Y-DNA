"""Non-identifying source totals. These are never converted into fake tester rows."""
from datetime import datetime
import re


def prepare_country_count(raw):
    record=dict(raw)
    reasons=[]
    if record.get('namespace') not in ('ftdna','yfull'): reasons.append('unknown_count_namespace')
    label=str(record.get('node_label') or '').strip().upper()
    record['node_label']=label
    if not re.fullmatch(r'[A-T][A-Z0-9*.+_\-]*',label): reasons.append('invalid_count_node')
    if record.get('country_code')!='EG': reasons.append('count_not_egypt')
    count=record.get('reported_count')
    if not isinstance(count,int) or isinstance(count,bool) or count<0 or count>2147483647: reasons.append('invalid_reported_count')
    if record.get('count_scope') not in ('direct','inclusive'): reasons.append('unknown_count_scope')
    population=record.get('population','unknown')
    record['population']=population
    valid_populations={'ftdna':('ftdna_big_y','unknown'),'yfull':('yfull_modern','unknown')}
    if population not in valid_populations.get(record.get('namespace'),()): reasons.append('invalid_count_population')
    try:
        date=datetime.fromisoformat(str(record.get('observed_at') or '').replace('Z','+00:00'))
        if date.tzinfo is None: raise ValueError('Timezone required')
    except ValueError: reasons.append('missing_count_observation_date')
    if not str(record.get('source_url') or '').startswith('https://'): reasons.append('missing_count_evidence')
    if not record.get('publication_allowed') or not str(record.get('permission_url') or '').startswith('https://'):
        reasons.append('count_publication_permission_unverified')
    path=record.get('snp_path',[])
    if not isinstance(path,list) or any(not isinstance(p,str) or not re.fullmatch(r'[A-Za-z0-9*.+_\-]+',p) for p in path):
        reasons.append('invalid_count_path');record['snp_path']=[]
    elif path and (path[-1].upper()!=label or not str(record.get('path_source_url') or '').startswith('https://')):
        reasons.append('unverified_count_path');record['snp_path']=[]
    record['kind']='country_count'
    record['review_reasons']=reasons
    record['accepted']=not reasons
    return record
