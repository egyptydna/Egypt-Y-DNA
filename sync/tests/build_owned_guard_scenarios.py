"""Generate synthetic SQL for the disposable CI database only; never run against Supabase."""
import copy,json
from pathlib import Path
from sync.normalize import Gazetteer,prepare
from sync.owned_archives import parse_observatory,parse_tracker,sql_plan,json_literal
from .test_owned_archives import observed,tracked

out=Path('/tmp/owned-archive-guard-ci');out.mkdir(exist_ok=True)
statements=[];gaz=Gazetteer()


def plan_case(name,record,source,guarded=False):
    plan=sql_plan([record],[],[source],{'synthetic_ci_case':name},out/name,guarded_updates=guarded)
    statements.extend(Path(f).read_text() for f in plan['files'])


def seed(record):
    statements.append('select public.ydna_sync_ingest('+json_literal(prepare(record,gaz))+',null,false);')


def expect(predicate,message):
    statements.append("do $assert_owned$ begin if not ("+predicate+") then raise exception '"+message+"'; end if; end $assert_owned$;")


record,_,sources,_=parse_observatory(observed());base=record[0];source=sources[0]
statements.append('''insert into public."Modern_published_samples"(yfull_id,y_dna,test_type,test_status)
values('YF990099001','J-MANUAL1','Big Y-700','confirmed_big_y');''')
plan_case('insert-only-preserves-manual',base,source)
expect("(select y_dna='J-MANUAL1' and test_type='Big Y-700' from public.\"Modern_published_samples\" where yfull_id='YF990099001')",'Manual profile changed')

auto=dict(copy.deepcopy(base),external_id='YF990099002',y_dna='J-OLD2',snp_path=['Y-Adam','J','J-OLD2'],source_url='https://www.yfull.com/tree/J-OLD2/')
seed(auto)
changed=dict(copy.deepcopy(auto),y_dna='J-NEW2',snp_path=['Y-Adam','J','J-NEW2'],source_url='https://www.yfull.com/tree/J-NEW2/')
newsource=copy.deepcopy(source);newsource['metadata']['snapshot_checked_at']='2026-11-04T16:25:30Z'
plan_case('clean-primary-source-update',changed,newsource,True)
expect("(select y_dna='J-NEW2' and full_snp_path='Y-Adam>J>J-NEW2' from public.\"Modern_published_samples\" where yfull_id='YF990099002')",'Clean source update did not move the tester')

statements.append("update public.\"Modern_published_samples\" set y_dna='J-MANUAL2' where yfull_id='YF990099002';")
changed_again=dict(copy.deepcopy(changed),y_dna='J-OTHER2',snp_path=['Y-Adam','J','J-OTHER2'])
plan_case('manual-edit-freezes-profile',changed_again,newsource,True)
expect("(select y_dna='J-MANUAL2' and full_snp_path='Y-Adam>J>J-NEW2' from public.\"Modern_published_samples\" where yfull_id='YF990099002')",'Manual edit was overwritten or its path was partially changed')

ftdna,_,ft_sources,_=parse_tracker(tracked());ft=ftdna[0];ft['external_id']='990099003'
plan_case('seed-confirmed-big-y',ft,ft_sources[0])
weaker=dict(copy.deepcopy(ft),test_type='Y-DNA37',haplogroup_status='predicted')
plan_case('do-not-downgrade-big-y',weaker,ft_sources[0],True)
expect("(select test_type='Big Y-700' and test_status='confirmed_big_y' from public.\"Modern_published_samples\" where kit_number='990099003')",'Big-Y evidence was downgraded')

pending=dict(copy.deepcopy(auto),external_id='YF990099004')
seed(pending)
statements.append("select public.ydna_sync_review(id,'owner-observatory-export','field_conflict','{\"field\":\"y_dna\"}') from public.\"Modern_published_samples\" where yfull_id='YF990099004';")
pending_changed=dict(copy.deepcopy(pending),y_dna='J-NEW4',snp_path=['Y-Adam','J','J-NEW4'])
plan_case('open-review-freezes-profile',pending_changed,newsource,True)
expect("(select y_dna='J-OLD2' from public.\"Modern_published_samples\" where yfull_id='YF990099004')",'Open review did not freeze profile updates')

stale=dict(copy.deepcopy(auto),external_id='YF990099005')
oldsource=copy.deepcopy(source);oldsource['metadata']['snapshot_checked_at']='2026-11-04T14:25:30Z'
plan_case('older-fallback-is-ignored',stale,oldsource,True)
expect("not exists(select 1 from public.\"Modern_published_samples\" where yfull_id='YF990099005')",'Older fallback was treated as a current snapshot')

Path('/tmp/owned-archive-guard-scenarios.sql').write_text('\n'.join(statements))
print('Generated synthetic guard scenarios for the disposable CI database.')
