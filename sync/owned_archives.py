"""Transfer existing observations from the owner's two archives; never crawl providers.

No runtime credentials or real tester datasets belong in Git. SQL output is private
staging for the existing Supabase ingestion functions and must not be committed.
"""
import argparse
import hashlib
import json
import re
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from .country_counts import prepare_country_count
from .normalize import Gazetteer,external_id,marker_name,normalized,prepare,str_value

OBSERVATORY='https://egypt-ydna-observatory.kimoeln.chatgpt.site/'
TRACKER='https://egypt-dna-tracker.vercel.app/'
PROJECT='lsfmpmfoqdtkgndtaxen'


def public_url(url,hosts):
    parsed=urlsplit(str(url or ''))
    if parsed.scheme!='https' or parsed.hostname not in hosts or parsed.username or parsed.password:
        raise ValueError('Observation does not cite an expected public source')
    return url


def source_config(source_id,archive_url,snapshot):
    if not isinstance(snapshot,str) or datetime.fromisoformat(snapshot.replace('Z','+00:00')).tzinfo is None:
        raise ValueError('A dated owner archive snapshot is required')
    return dict(id=source_id,url=archive_url,adapter='owned_archive_transfer',publication_allowed=True,
        permission_url=archive_url,metadata={'authorization_basis':'Owner-authorized transfer of existing archive observations; no permission for direct provider crawling is asserted.',
        'snapshot_checked_at':snapshot,'archive_url':archive_url})


def parse_observatory(data):
    source=source_config('owner-observatory-export',OBSERVATORY,data.get('checkedAt'))
    records=[];counts=[];stats=Counter();seen=set()
    for item in data['records']:
        if item.get('dna','y')!='y':stats['excluded_mtdna']+=1;continue
        if normalized(item.get('country')) not in ('egypt','eg','egy','مصر'):
            stats['unproven_egyptian_origin']+=1;continue
        provider=item.get('provider');key=(provider,item.get('id'))
        if key in seen:raise ValueError('Duplicate archive observation identity')
        seen.add(key)
        if provider=='yfull' and item.get('kind')=='sample':
            if item.get('ancient') is not False:stats['excluded_ancient_or_unspecified']+=1;continue
            sample=item.get('sampleId','')
            if not re.fullmatch(r'YF\d+',sample):stats['excluded_scientific_or_noncustomer_id']+=1;continue
            url=public_url(item.get('sourceUrl'),{'www.yfull.com','yfull.com'})
            path=item.get('path') or []
            if not isinstance(path,list):raise ValueError('Invalid archived SNP path')
            records.append(dict(source_id=source['id'],namespace='yfull',external_id=sample,
                country='Egypt',origin_raw=item.get('region') or item['country'],origin_kind='paternal',sample_kind='modern',
                y_dna=item['haplogroup'],test_type='YFull sequencing',source_url=url,
                publication_allowed=True,permission_url=OBSERVATORY,
                snp_path=(['Y-Adam']+path if path and path[0]!='Y-Adam' else path),path_source_url=url,
                archive_source_url=OBSERVATORY,archive_record_id=item['id'],archive_first_seen_at=item.get('firstSeen'),
                archive_snp_blocks=item.get('aliases',[])))
        elif provider=='ftdna' and item.get('kind')=='aggregate':
            if 'excluding downstream' not in item.get('note','').lower():
                stats['unproven_count_scope']+=1;continue
            url=public_url(item.get('sourceUrl'),{'www.familytreedna.com','familytreedna.com','discover.familytreedna.com'})
            path=item.get('path') or []
            counts.append(dict(kind='country_count',source_id=source['id'],namespace='ftdna',
                node_label=item['haplogroup'],country_code='EG',reported_count=item['count'],
                count_scope='direct',population='unknown',observed_at=item['observedAt'],source_url=url,
                publication_allowed=True,permission_url=OBSERVATORY,snp_path=path,path_source_url=url))
        else:stats['unsupported_record']+=1
    coverage=next((c for c in data.get('coverage',[]) if c.get('provider')=='ftdna'),None)
    if coverage and coverage.get('aggregateCount')!=sum(c['reported_count'] for c in counts):
        raise ValueError('Archived FTDNA direct counts disagree with its coverage total')
    return records,counts,[source],dict(stats)


def inclusive_country_counts(direct_counts):
    """Compute sums only along complete archived paths; never invent testers or ancestry."""
    totals={};paths={};evidence={};ambiguous=set()
    for fact in direct_counts:
        path=fact.get('snp_path') or []
        if not path or path[-1]!=fact['node_label'] or len(path)!=len(set(path)):
            raise ValueError('Cannot derive inclusive counts from an incomplete or cyclic source path')
        for i,label in enumerate(path):
            prefix=path[:i+1]
            if label in paths and paths[label]!=prefix:ambiguous.add(label)
            paths[label]=prefix;totals[label]=totals.get(label,0)+fact['reported_count'];evidence.setdefault(label,fact)
    result=[]
    for label,total in sorted(totals.items()):
        if label in ambiguous:continue
        fact=evidence[label]
        result.append(dict(fact,source_id='owner-observatory-derived-counts',node_label=label,
            reported_count=total,count_scope='inclusive',snp_path=paths[label],derived_from_direct_counts=True))
    return result


def parse_tracker(data):
    records=[];sources={};stats=Counter()
    for sample in data['samples']:
        if sample.get('provider')!='FamilyTreeDNA project' or sample.get('type')!='Y-DNA' or sample.get('period')!='Modern':
            stats['excluded_other_sample_kind']+=1;continue
        found=False
        for row in sample.get('projectRecords',[]):
            fields=row.get('publicFields',[])
            values={f['label']:f.get('value') for f in fields}
            # Require the actual published project country cell, not a merged/inferred location.
            if normalized(values.get('Country')) not in ('egypt','eg','مصر'):continue
            kit=external_id('ftdna',row['id'])
            url=public_url(row.get('source'),{'www.familytreedna.com','familytreedna.com'})
            if not urlsplit(url).path.startswith('/public/'):raise ValueError('Not a public project source')
            project=str(row.get('project') or '')
            if not project:raise ValueError('Missing archive project identity')
            sid='owner-tracker-project-'+hashlib.sha256(project.encode()).hexdigest()[:16]
            sources[sid]=source_config(sid,TRACKER,data.get('updated'))
            markers=[]
            for position,field in enumerate(fields):
                label=field['label'];canonical=marker_name(label)
                if canonical:markers.append(dict(marker=canonical,source_label=label,position=position,value=str_value(field.get('value'))))
                elif re.match(r'^(?:DYS|DYF|Y[- ]?GATA|YCA|CDY)',label,re.I):
                    markers.append(dict(marker=label,source_label=label,position=position,value=field.get('value')))
            haplo=str(values.get('Haplogroup') or '').strip()
            if not haplo or haplo in ('—','-'):stats['missing_published_haplogroup']+=1;continue
            test=str(values.get('Test') or row.get('test') or '')
            record=dict(source_id=sid,namespace='ftdna',external_id=kit,country='Egypt',origin_raw=str(values['Country']),
                origin_kind='paternal',sample_kind='modern',project=project,y_dna=haplo,test_type=test,
                haplogroup_status='predicted' if re.fullmatch(r'Y-DNA(?:12|25|37|67|111)',test) else 'unknown',
                source_url=url,publication_allowed=True,permission_url=TRACKER,str_markers=markers,
                archive_source_url=TRACKER,archive_first_seen_at=sample.get('firstSeenAt'))
            linked=values.get('YFull ID') or values.get('YFull')
            if isinstance(linked,str) and re.fullmatch(r'YF\d+',linked.strip(),re.I):
                record.update(verified_ids=[{'namespace':'yfull','external_id':linked.strip().upper()}],identity_evidence_url=url)
            records.append(record);found=True
        if not found:stats['no_published_egypt_project_row']+=1
    # An explicitly published Big-Y test takes precedence when establishing a new primary source.
    records.sort(key=lambda r:(r['external_id'],-({'Big Y-700':2,'Big Y-500':1}.get(r['test_type'],0)),
        -sum(m['value'] is not None for m in r['str_markers']),r['source_id']))
    return records,[],list(sources.values()),dict(stats)


def literal(value):
    return "'"+str(value).replace("'","''")+"'"


def json_literal(value):
    return literal(json.dumps(value,ensure_ascii=False,separators=(',',':')))+'::jsonb'


def sql_plan(records,counts,sources,summary,outdir,run_id=None,guarded_updates=False,batch_size=20,evidence_only=False):
    if evidence_only and guarded_updates:raise ValueError('Evidence-only mode cannot update curated profiles')
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True)
    run_id=str(uuid.UUID(run_id)) if run_id else str(uuid.uuid4())
    gaz=Gazetteer();records=[prepare(r,gaz) for r in records];counts=[prepare_country_count(c) for c in counts]
    summary=dict(summary,update_policy='evidence_only_existing_profiles' if evidence_only else 'guarded_automatic_profiles' if guarded_updates else 'new_profiles_only',profile_observations=len(records),unique_profile_ids=len({(r['namespace'],r['external_id']) for r in records}),
        accepted_observations=sum(r['accepted'] for r in records),review_observations=sum(not r['accepted'] for r in records),count_facts=len(counts))
    header='begin; set local standard_conforming_strings=on; set local role service_role;\n'
    start=header+'insert into public.ydna_sync_runs(id,status,report) values('+literal(run_id)+",'running',"+json_literal({'mode':'owner_archive_transfer','plan':summary})+');\n'
    for source in sources:
        start+=('insert into public.ydna_sync_sources(id,url,adapter,publication_allowed,permission_url,metadata) values('+','.join([
            literal(source['id']),literal(source['url']),literal(source['adapter']),'true',literal(source['permission_url']),json_literal(source['metadata'])])+
            ") on conflict(id) do update set metadata=excluded.metadata where coalesce((ydna_sync_sources.metadata->>'snapshot_checked_at')::timestamptz,'-infinity'::timestamptz)<=(excluded.metadata->>'snapshot_checked_at')::timestamptz;\n")
    start+='commit;\n';(out/'00-start.sql').write_text(start)
    source_dates={s['id']:s['metadata']['snapshot_checked_at'] for s in sources}
    operations=[('ydna_sync_ingest',r) for r in records]+[('ydna_sync_ingest_country_count',c) for c in counts]
    files=['00-start.sql']
    for offset in range(0,len(operations),batch_size):
        rows=[dict(function=fn,record=r,snapshot_at=source_dates[r['source_id']]) for fn,r in operations[offset:offset+batch_size]]
        script=header+'''do $owned_archive_batch$
declare op jsonb; result jsonb; checked jsonb; existing public."Modern_published_samples"%rowtype;
run_key uuid:='''+literal(run_id)+'''::uuid; totals jsonb; label text; may_update boolean;
begin
 select report->'counts' into totals from public.ydna_sync_runs where id=run_key for update;
 totals:=coalesce(totals,'{}'::jsonb);
 for op in select * from jsonb_array_elements('''+json_literal(rows)+''') loop
  if exists(select 1 from public.ydna_sync_sources where id=op->'record'->>'source_id'
   and (metadata->>'snapshot_checked_at')::timestamptz>(op->>'snapshot_at')::timestamptz) then
   result:=jsonb_build_object('status','older_snapshot_ignored');
   label:=case when op->>'function'='ydna_sync_ingest' then 'profiles_older_snapshot_ignored' else 'counts_older_snapshot_ignored' end;
  elsif op->>'function'='ydna_sync_ingest' then
   checked:=public.ydna_sync_ingest(op->'record',run_key,true);
   may_update:=false;
   if checked->>'status'='would_reconcile' then
    select * into existing from public."Modern_published_samples" where id=(checked->>'sample_id')::bigint;
    may_update:='''+('true' if guarded_updates else 'false')+''' and existing.sync_managed
     and existing.sync_primary_source=op->'record'->>'source_id'
     and not exists(select 1 from public.ydna_sync_reviews where sample_id=existing.id and status='pending')
     and not exists(select 1 from jsonb_each(existing.sync_published) e where to_jsonb(existing)->e.key is distinct from e.value)
     and not exists(select 1 from jsonb_each(jsonb_build_object(
      'test_type',op->'record'->>'test_type','test_status',op->'record'->>'test_status',
      'y_dna',op->'record'->>'y_dna','y_dna_alias',op->'record'->>'y_dna_alias',
      'origin_raw',op->'record'->>'origin_raw','governorate',op->'record'->'origin'->>'governorate',
      'governorate_iso',op->'record'->'origin'->>'governorate_iso','y_link_1',op->'record'->>'source_url',
      'full_snp_path',case when jsonb_array_length(coalesce(op->'record'->'snp_path','[]'))>0 then
       (select string_agg(v,'>' order by n) from jsonb_array_elements_text(op->'record'->'snp_path') with ordinality p(v,n)) end)) e
      where e.value<>'null'::jsonb and e.value#>>'{}' not in ('','—','-')
      and coalesce(to_jsonb(existing)->>e.key,'') not in ('','—','-')
      and to_jsonb(existing)->e.key is distinct from e.value
      and existing.sync_published->e.key is distinct from to_jsonb(existing)->e.key)
     and not (existing.test_type in ('Big Y-500','Big Y-700') and existing.test_type is distinct from op->'record'->>'test_type');
   end if;
   if '''+('false' if evidence_only else "checked->>'status'='would_insert' or may_update")+''' then
    result:=public.ydna_sync_ingest(op->'record',run_key,false);
   elsif checked->>'status'='would_reconcile' then
    result:=public.ydna_sync_attach_archive_evidence(op->'record',false);
    if coalesce((result->>'evidence_attached')::boolean,false) then
     totals:=totals||jsonb_build_object('evidence_attached',coalesce((totals->>'evidence_attached')::int,0)+1,
      'str_values_attached',coalesce((totals->>'str_values_attached')::int,0)+(result->>'marker_count')::int);
    end if;
   else
    result:=checked;
    if checked->>'status'='review' then perform public.ydna_sync_review(null,op->'record'->>'source_id','archive_candidate_requires_review',op->'record'); end if;
   end if;
   label:='profiles_'||(result->>'status');
  else
   result:=public.ydna_sync_ingest_country_count(op->'record',run_key,false); label:='counts_'||(result->>'status');
  end if;
  totals:=totals||jsonb_build_object(label,coalesce((totals->>label)::int,0)+1);
  if coalesce((result->>'conflicts')::int,0)>0 then totals:=totals||jsonb_build_object('field_conflicts',coalesce((totals->>'field_conflicts')::int,0)+(result->>'conflicts')::int); end if;
 end loop;
 update public.ydna_sync_runs set report=jsonb_set(report,'{counts}',totals) where id=run_key;
end $owned_archive_batch$;
commit;
'''
        name=f'{offset//batch_size+1:03d}-records.sql';(out/name).write_text(script);files.append(name)
    finish=header+"update public.ydna_sync_runs set status='completed',finished_at=now() where id="+literal(run_id)+";\n"
    for source in sources:
        finish+="update public.ydna_sync_sources set last_success_at=now(),last_status='owner_archive_transfer_completed' where id="+literal(source['id'])+';\n'
    finish+='commit;\n';(out/'999-finish.sql').write_text(finish);files.append('999-finish.sql')
    plan=dict(project_id=PROJECT,run_id=run_id,files=[str(out/f) for f in files],summary=summary)
    (out/'plan.json').write_text(json.dumps(plan,indent=2));return plan


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--observatory');parser.add_argument('--tracker');parser.add_argument('--outdir',required=True)
    parser.add_argument('--owner-authorized',action='store_true',required=True)
    parser.add_argument('--guarded-updates',action='store_true',help='Only untouched automatically managed profiles from their primary source, without pending reviews')
    parser.add_argument('--evidence-only',action='store_true',help='Only attach source evidence to existing profiles; never create or update tester rows')
    args=parser.parse_args();records=[];counts=[];sources=[];summary={}
    for kind,path in [('observatory',args.observatory),('tracker',args.tracker)]:
        if path:
            try:
                parsed=(parse_observatory if kind=='observatory' else parse_tracker)(json.loads(Path(path).read_text()))
                records+=parsed[0];counts+=parsed[1];sources+=parsed[2];summary[kind]=parsed[3]
                if kind=='observatory' and parsed[1]:
                    derived=inclusive_country_counts(parsed[1]);counts+=derived
                    source=source_config('owner-observatory-derived-counts',OBSERVATORY,parsed[2][0]['metadata']['snapshot_checked_at'])
                    source['metadata']['derivation']='Sum of archived direct Egypt counts along the published source paths; separate from individual profiles.'
                    sources.append(source);summary[kind]['derived_inclusive_facts']=len(derived)
            except (ValueError,KeyError,TypeError) as error:
                summary[kind]={'status':'unavailable','error_type':type(error).__name__}
    if not records and not counts:raise ValueError('No supported archive observations')
    print(json.dumps(sql_plan(records,counts,sources,summary,args.outdir,guarded_updates=args.guarded_updates,evidence_only=args.evidence_only),indent=2))


if __name__=='__main__':main()
