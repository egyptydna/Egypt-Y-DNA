import copy
import unittest
from unittest.mock import Mock
from sync.track_country import snapshot,primary_snapshot,backup_snapshot,track,PRIMARY,BACKUP

DATE='2026-11-04T00:00:00Z'
URL='https://example.org/published-counts'

class CountryTrackerTests(unittest.TestCase):
    def fixture(self):
        return {'name':'Egypt','slug':'egypt','n':9,'cumN':3,'terminal':[['J-TEST1',4],['E-M35',5]]},{'nodes':[[-1,'J-M1'],[0,'J-TEST1'],[-1,'E-M35']]}

    def test_anonymous_results_preserve_total_and_proven_paths(self):
        data,tree=self.fixture()
        value=primary_snapshot(data,tree,DATE,URL,{'backbone_url':URL})
        self.assertEqual(value['total_count'],9)
        self.assertEqual(next(n for n in value['nodes'] if n['label']=='J-TEST1')['path'],['J-M1','J-TEST1'])
        self.assertNotIn('kit_number',str(value));self.assertNotIn('Big Y',str(value))

    def test_missing_ancestry_is_not_fabricated(self):
        data,tree=self.fixture();data['terminal']=[['J-NEW',9]]
        value=primary_snapshot(data,tree,DATE,URL,{'backbone_url':URL})
        self.assertEqual(value['nodes'][0]['path'],[])

    def test_documented_backup_path_enriches_exact_branch_only(self):
        data,tree=self.fixture()
        backup={'nodes':[{'label':'J-TEST1','path':['J-M1','J-M2','J-TEST1'],'path_source_url':URL,'path_observed_at':DATE},
            {'label':'J-OTHER','path':['J-M1','J-OTHER'],'path_source_url':URL}]}
        value=primary_snapshot(data,tree,DATE,URL,{'backbone_url':URL},backup)
        self.assertEqual(next(n for n in value['nodes'] if n['label']=='J-TEST1')['path'],['J-M1','J-M2','J-TEST1'])
        self.assertEqual(len(value['nodes']),2)

    def test_polling_same_snapshot_is_idempotent(self):
        args=(PRIMARY,[{'label':'J-TEST1','count':9}],DATE,URL)
        self.assertEqual(snapshot(*args)['snapshot_key'],snapshot(*args)['snapshot_key'])
        self.assertNotEqual(snapshot(*args)['snapshot_key'],snapshot(PRIMARY,[{'label':'J-TEST1','count':10}],DATE,URL)['snapshot_key'])

    def test_rejects_incomplete_duplicate_and_noninteger_counts(self):
        for nodes,total in [([{'label':'J-TEST1','count':9}],10),([{'label':'J-TEST1','count':9},{'label':'j-test1','count':0}],9),
            ([{'label':'J-TEST1','count':True}],1),([{'label':'J-TEST1','count':-1}],-1)]:
            with self.assertRaises(ValueError):snapshot(PRIMARY,nodes,DATE,URL,total=total)

    def test_backup_only_direct_latest_published_ftdna_rows(self):
        row={'source_id':BACKUP,'namespace':'ftdna','country_code':'EG','count_scope':'direct','published':True,
             'node_label':'J-TEST1','reported_count':9,'observed_at':DATE}
        rows=[row,dict(row,count_scope='inclusive'),dict(row,published=False),dict(row,namespace='yfull')]
        self.assertEqual(backup_snapshot(rows,{'country_total':9,'country_terminal_rows':1})['total_count'],9)
        with self.assertRaises(ValueError):backup_snapshot(rows,{'country_total':10})
        self.assertIsNone(backup_snapshot(rows,{'snapshot_checked_at':'2026-11-05T00:00:00Z'}))

    def test_failure_keeps_selection_and_writes_no_profiles(self):
        db=Mock();db.request.side_effect=[[],{'snapshot_id':'retained','total_count':9}]
        report=track(True,db,Mock(side_effect=RuntimeError('Temporary source outage')))
        self.assertEqual(report['primary_status'],'unavailable');self.assertEqual(report['profiles_created'],0)
        self.assertEqual(report['selected']['snapshot_id'],'retained')
        self.assertEqual(db.request.call_args.args[0],'rpc/ydna_tracker_select')
        self.assertNotIn('Modern_published_samples',str(db.request.call_args_list))

    def test_dry_run_never_writes(self):
        data,tree=self.fixture();value=primary_snapshot(data,tree,DATE,URL,{'backbone_url':URL})
        report=track(False,fetcher=Mock(return_value=value))
        self.assertEqual(report['primary_total'],9);self.assertEqual(report['profiles_created'],0)

    def test_source_shape_or_index_change_stops_import(self):
        for change in ['country','index']:
            data,tree=self.fixture()
            if change=='country':data['name']='Other'
            else:tree['nodes'][1][0]=99
            with self.assertRaises(ValueError):primary_snapshot(data,tree,DATE,URL,{'backbone_url':URL})

    def test_no_personal_fields_are_carried_into_public_snapshot(self):
        value=snapshot(PRIMARY,[{'label':'J-TEST1','count':1,'kit_number':'DO NOT COPY','name':'private'}],DATE,URL)
        self.assertNotIn('kit_number',value['nodes'][0]);self.assertNotIn('name',value['nodes'][0])
