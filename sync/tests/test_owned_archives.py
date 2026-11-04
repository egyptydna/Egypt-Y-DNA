import copy,json,tempfile,unittest
from pathlib import Path
from sync.owned_archives import parse_observatory,parse_tracker,sql_plan,literal,inclusive_country_counts
from sync.normalize import Gazetteer,prepare
from sync.fetch_owned_archives import decode_snapshot,read_snapshot,fetch_owned
from unittest.mock import patch
import gzip,urllib.error


def observed():
    return {'checkedAt':'2026-11-04T15:25:30Z','records':[
        {'id':'yfull:YF990099001','provider':'yfull','kind':'sample','ancient':False,'sampleId':'YF990099001',
         'country':'Egypt','region':'Al Iskandarīyah','haplogroup':'J-TEST1','path':['J','J-TEST1'],
         'sourceUrl':'https://www.yfull.com/tree/J-TEST1/','firstSeen':'2026-11-04T09:32:00Z'},
        {'id':'ftdna:J-TEST1','provider':'ftdna','dna':'y','kind':'aggregate','country':'Egypt','haplogroup':'J-TEST1',
         'count':9,'sourceUrl':'https://www.familytreedna.com/public/y-dna-haplotree/J;name=J-TEST1',
         'path':['J','J-TEST1'],'observedAt':'2026-11-04T15:25:30Z','note':'Directly on this branch, excluding downstream branches.'}
    ],'coverage':[{'provider':'ftdna','aggregateCount':9}]}


def tracked():
    return {'updated':'2026-10-20T00:00:00Z','samples':[{'provider':'FamilyTreeDNA project','type':'Y-DNA',
        'period':'Modern','firstSeenAt':'2026-10-01T00:00:00Z','projectRecords':[
            {'id':'990099001','project':'Fixture','source':'https://www.familytreedna.com/public/Fixture?iframe=ydna-results-overview',
             'publicFields':[{'label':'Country','value':'Egypt'},{'label':'Haplogroup','value':'J-TEST1'},
                {'label':'Test','value':'Big Y-700'},{'label':'DYS425','value':'0'},
                {'label':'DYS464','value':'14-16-17-17'},{'label':'Name','value':'NOT COPIED'}]}
        ]}]}


class OwnedArchiveTests(unittest.TestCase):
    def test_actual_yfull_evidence_keeps_sequencing_type_and_region(self):
        rows,counts,sources,stats=parse_observatory(observed())
        row=prepare(rows[0],Gazetteer())
        self.assertTrue(row['accepted']);self.assertEqual(row['test_status'],'yfull_sequencing')
        self.assertEqual(row['origin']['governorate_iso'],'EG-ALX')
        self.assertEqual(row['snp_path'],['Y-Adam','J','J-TEST1'])
        self.assertNotIn('kit_number',row)

    def test_aggregate_count_never_creates_a_tester_or_implies_big_y(self):
        rows,counts,_,_=parse_observatory(observed())
        self.assertEqual(len(rows),1);self.assertEqual(len(counts),1)
        self.assertEqual(counts[0]['population'],'unknown');self.assertEqual(counts[0]['count_scope'],'direct')
        self.assertNotIn('external_id',counts[0])

    def test_inclusive_country_totals_follow_verified_paths_and_stay_separate(self):
        _,direct,_,_=parse_observatory(observed())
        direct.append(dict(direct[0],node_label='J-TEST2',reported_count=2,snp_path=['J','J-TEST1','J-TEST2']))
        derived={r['node_label']:r for r in inclusive_country_counts(direct)}
        self.assertEqual(derived['J-TEST1']['reported_count'],11)
        self.assertEqual(derived['J-TEST1']['count_scope'],'inclusive')
        self.assertEqual(direct[0]['reported_count'],9)
        self.assertTrue(derived['J']['derived_from_direct_counts'])

    def test_mt_scientific_and_ancient_records_are_separate(self):
        data=observed();row=data['records'][0]
        for extra in [dict(row,id='mt',dna='mt'),dict(row,id='ancient',ancient=True),
                      dict(row,id='study',sampleId='ERR990099001')]:data['records'].append(extra)
        rows,_,_,stats=parse_observatory(data)
        self.assertEqual(len(rows),1);self.assertEqual(sum(stats.values()),3)

    def test_count_scope_and_total_must_be_explicit(self):
        data=observed();data['coverage'][0]['aggregateCount']=10
        with self.assertRaises(ValueError):parse_observatory(data)
        data=observed();data['records'][1]['note']='Scope unknown';data['coverage']=[]
        self.assertEqual(len(parse_observatory(data)[1]),0)

    def test_names_or_merged_locations_do_not_prove_egyptian_origin(self):
        data=tracked();data['samples'][0]['location']='Egypt'
        data['samples'][0]['projectRecords'][0]['publicFields'][0]['value']='Saudi Arabia'
        self.assertEqual(len(parse_tracker(data)[0]),0)

    def test_public_test_column_and_exact_str_values(self):
        row=parse_tracker(tracked())[0][0]
        self.assertEqual(row['test_type'],'Big Y-700')
        self.assertEqual([m['value'] for m in row['str_markers']],['0','14-16-17-17'])
        self.assertEqual([m['position'] for m in row['str_markers']],[3,4])
        self.assertNotIn('name',row)

    def test_big_y_word_in_subgroup_is_not_test_evidence(self):
        data=tracked();r=data['samples'][0]['projectRecords'][0]
        r['subgroup']='Big Y-700 cluster';r['publicFields'][2]['value']='Y-DNA37'
        row=prepare(parse_tracker(data)[0][0],Gazetteer())
        self.assertEqual(row['test_status'],'str_only')

    def test_same_kit_in_three_projects_keeps_three_sources_one_identity(self):
        data=tracked();original=data['samples'][0]['projectRecords'][0]
        for name in ['Second','Third']:
            data['samples'][0]['projectRecords'].append(dict(copy.deepcopy(original),project=name))
        rows,_,sources,_=parse_tracker(data)
        self.assertEqual(len(sources),3);self.assertEqual(len({r['external_id'] for r in rows}),1)

    def test_cross_platform_link_requires_an_explicit_published_field(self):
        data=tracked();data['samples'][0]['projectRecords'][0]['publicFields'].append({'label':'YFull ID','value':'YF990099001'})
        row=parse_tracker(data)[0][0]
        self.assertEqual(row['verified_ids'][0]['external_id'],'YF990099001')
        self.assertEqual(row['identity_evidence_url'],row['source_url'])

    def test_source_host_validation_and_duplicate_archive_ids(self):
        data=observed();data['records'][0]['sourceUrl']='https://example.org/tree/J-TEST1/'
        with self.assertRaises(ValueError):parse_observatory(data)
        data=observed();data['records'].append(data['records'][0])
        with self.assertRaises(ValueError):parse_observatory(data)

    def test_parameter_data_is_quoted_and_plan_has_no_network_or_schema_writes(self):
        self.assertEqual(literal("x'; drop table users; --"),"'x''; drop table users; --'")
        rows,counts,sources,stats=parse_observatory(observed())
        with tempfile.TemporaryDirectory() as directory:
            plan=sql_plan(rows,counts,sources,stats,directory)
            sql='\n'.join(Path(f).read_text() for f in plan['files'])
            self.assertIn('ydna_sync_ingest_country_count',sql);self.assertIn('ydna_sync_ingest',sql)
            self.assertNotIn('delete from',sql.lower());self.assertNotIn('create table',sql.lower())
            self.assertEqual(plan['summary']['unique_profile_ids'],1)

    def test_owned_fetcher_refuses_upstream_urls_and_cross_site_credentials(self):
        for url in ['https://www.yfull.com/tree/','https://www.familytreedna.com/public/Egypt']:
            with self.assertRaises(ValueError):read_snapshot(url)
        with self.assertRaises(ValueError):read_snapshot('https://egypt-dna-tracker.vercel.app/api/data','fixture-secret')

    def test_compressed_owner_data_and_array_format_guard(self):
        self.assertEqual(decode_snapshot(gzip.compress(b'{"samples":[]}')),{'samples':[]})
        with self.assertRaises(ValueError):decode_snapshot(b'[]')

    def test_owned_fetch_fallback_reports_actual_saved_date(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch('sync.fetch_owned_archives.read_snapshot',side_effect=[observed(),urllib.error.HTTPError('https://example.org',503,'unavailable',None,None),tracked()]):
                result=fetch_owned({'owner_authorized':True,'observatory_token':'fixture-secret'},directory)
        self.assertEqual(result['sources']['tracker']['status'],'saved_fallback')
        self.assertEqual(result['sources']['tracker']['snapshot_at'],'2026-10-20T00:00:00Z')
