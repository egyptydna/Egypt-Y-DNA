import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from sync.topology import YFullTree,reference_labels
from sync.tree_store import plan_release,sync_tree
from sync.github_sources import parse_ftdnastat_egypt,collect_ftdnastat,collect_yfull_github
from sync.github_files import GitHubFiles
from sync.adapters import parse_consent_csv,collect_github_export
from sync.http import SourceRestricted
from sync.run import synchronize


def branch(label,children=None,snps=''):
    return dict(id=label,formed=1000,tmrca=500,snps=snps,tmrcalowage=400,tmrcahighage=600,children=children or [])


def tree_fixture():
    return branch('',[branch('J-M1',[branch('J-TEST1',snps='TEST1/ALIAS1, EQUIV2')]),branch('E-M35')])


class TopologyTests(unittest.TestCase):
    def test_exact_equivalent_blocks_and_aliases(self):
        tree=YFullTree(tree_fixture())
        self.assertEqual(tree.match('J-TEST1')['status'],'exact')
        self.assertEqual(tree.match('J-ALIAS1')['label'],'J-TEST1')
        self.assertEqual(tree.match('J-EQUIV2')['status'],'equivalent_snp')
        self.assertEqual(tree.path('J-TEST1'),['Y-Adam','J-M1','J-TEST1'])
        self.assertEqual(tree.nodes['J-TEST1']['snp_groups'],[['TEST1','ALIAS1'],['EQUIV2']])

    def test_ambiguous_marker_not_assigned(self):
        raw=tree_fixture();raw['children'][0]['children'].append(branch('J-TEST2',snps='ALIAS1'))
        self.assertEqual(YFullTree(raw).match('J-ALIAS1')['status'],'ambiguous')

    def test_no_individuals_in_tree(self):
        raw=tree_fixture();raw['children'].append(branch('YF990099001'))
        with self.assertRaises(ValueError):YFullTree(raw)
        self.assertEqual(reference_labels([{'y_dna':'J-TEST1','y_dna_alias':'YF990099001'}]),['J-TEST1'])

    def test_missing_ages_and_units_not_guessed(self):
        raw=tree_fixture();raw['formed']='-';tree=YFullTree(raw)
        self.assertIsNone(tree.nodes['Y-Adam']['age_estimates']['formed']['estimate'])
        self.assertEqual(tree.nodes['J-TEST1']['age_estimates']['unit'],'ybp')

    def test_source_duplicate_and_invalid_interval_fail(self):
        raw=tree_fixture();raw['children'].append(branch('E-M35'))
        with self.assertRaises(ValueError):YFullTree(raw)
        raw=tree_fixture();raw['tmrcalowage']=700
        with self.assertRaises(ValueError):YFullTree(raw)

    def test_incremental_structural_changes(self):
        old=YFullTree(tree_fixture());raw=tree_fixture()
        moved=raw['children'][0]['children'].pop();raw['children'].append(branch('J-NEW',[moved]))
        moved['tmrca']=501;moved['snps']+=', EXTRA3'
        diff=YFullTree(raw).diff(old)
        self.assertEqual(diff['new_nodes'],1);self.assertEqual(diff['moved_nodes'],1)
        self.assertEqual(diff['changed_snp_blocks'],1);self.assertEqual(diff['changed_age_estimates'],1)

    def test_selected_paths_include_ancestors(self):
        nodes,matches=YFullTree(tree_fixture()).select(['J-ALIAS1','R-NOTFOUND'])
        self.assertEqual([n['label'] for n in nodes],['Y-Adam','J-M1','J-TEST1'])
        self.assertEqual(matches['R-NOTFOUND']['status'],'unmatched')


class StatisticsTests(unittest.TestCase):
    def fixture(self):
        return {'slug':'egypt','name':'Egypt','n':9,'terminal':[['J-TEST1',4],['E-M35',5]],'cumN':3,'cum':[[0,4],[1,4],[2,5]]},{'nodes':[[-1,'J-M1','J'],[0,'J-TEST1','test'],[-1,'E-M35','E']]}

    def test_scope_and_backbone_indices(self):
        data,backbone=self.fixture()
        rows,summary=parse_ftdnastat_egypt(data,backbone,{'id':'fixture'},'2026-11-04T00:00:00Z','https://example.org')
        self.assertEqual(summary['country_total'],9);self.assertEqual(len(rows),5)
        self.assertEqual(rows[2]['node_label'],'J-M1');self.assertEqual(rows[0]['count_scope'],'direct')
        self.assertEqual(rows[2]['count_scope'],'inclusive');self.assertEqual(rows[0]['population'],'unknown')
        self.assertNotIn('external_id',rows[0])

    def test_mismatched_total_and_index_fail(self):
        data,backbone=self.fixture();data['n']=10
        with self.assertRaises(ValueError):parse_ftdnastat_egypt(data,backbone,{'id':'fixture'},'','')
        data,backbone=self.fixture();data['cumN']=999
        with self.assertRaises(ValueError):parse_ftdnastat_egypt(data,backbone,{'id':'fixture'},'','')

    def test_mit_software_license_does_not_enable_data_import(self):
        with patch('sync.github_sources.GitHubFiles') as client:
            with self.assertRaises(SourceRestricted):collect_ftdnastat({'publication_allowed':False})
            client.assert_not_called()


class ConsentFeedTests(unittest.TestCase):
    CSV='namespace,external_id,country,origin_kind,sample_kind,publication_consent,source_url,y_dna,test_type,DYS425,DYS464\nftdna,990099001,Egypt,paternal,modern,true,https://example.org/public,J-TEST1,Big Y-700,0,14-16-17-17\n'

    def test_approved_csv_preserves_null_and_multicopy(self):
        row=parse_consent_csv(self.CSV,{'id':'fixture','publication_allowed':True,'permission_url':'https://example.org/permission'},'https://example.org')[0]
        self.assertTrue(row['publication_allowed']);self.assertEqual(row['str_markers'][0]['value'],'0')
        self.assertEqual(row['str_markers'][1]['value'],'14-16-17-17')

    def test_csv_requires_explicit_row_consent(self):
        row=parse_consent_csv(self.CSV.replace(',true,',',false,'),{'id':'fixture','publication_allowed':True},'https://example.org')[0]
        self.assertFalse(row['publication_allowed'])

    def test_unapproved_feed_not_fetched(self):
        with patch('sync.adapters.GitHubFiles') as client:
            with self.assertRaises(SourceRestricted):collect_github_export({'publication_allowed':False})
            client.assert_not_called()

    def test_public_consent_feed_reaches_the_existing_ingestion_pipeline(self):
        source={'id':'fixture','adapter':'github_public_export','enabled':True,'publication_allowed':True,
            'permission_url':'https://example.org/permission','repo':'owner/public-feed','path':'testers.csv','format':'csv'}
        files=Mock();files.file.return_value=self.CSV.encode();files.permalink.return_value='https://github.com/owner/public-feed'
        with patch('sync.adapters.GitHubFiles',return_value=files):
            report=synchronize([source],http=Mock())
        self.assertEqual(report['counts']['accepted_candidates'],1)
        self.assertEqual(report['records'],1)
        self.assertEqual(report['sources'][0]['status'],'ok')


class GitHubAccessTests(unittest.TestCase):
    def test_immutable_file_cache_and_traversal_rejection(self):
        with tempfile.TemporaryDirectory() as root:
            files=GitHubFiles('YFullTeam/YTree',cache_dir=root)
            files.head={'sha':'a'*40}
            files.request=Mock(return_value=b'licensed tree')
            self.assertEqual(files.file('current_tree.json'),b'licensed tree')
            self.assertEqual(files.file('current_tree.json'),b'licensed tree')
            files.request.assert_called_once()
            self.assertIn('/'+'a'*40+'/',files.request.call_args.args[0])
            for path in ['../outside','/absolute','data/../../outside']:
                with self.assertRaises(ValueError):files.file(path)

    def test_changed_license_stops_before_tree_download(self):
        files=Mock();files.file.return_value=b'changed license'
        with patch('sync.github_sources.GitHubFiles',return_value=files):
            with self.assertRaises(SourceRestricted):
                collect_yfull_github({'publication_allowed':True,'expected_license_sha256':'0'*64})
        files.file.assert_called_once_with('LICENSE.md')

    def test_unofficial_repository_cannot_claim_yfull_attribution(self):
        with patch('sync.github_sources.GitHubFiles') as client:
            with self.assertRaises(SourceRestricted):
                collect_yfull_github({'publication_allowed':True,'repo':'someone/fork'})
            client.assert_not_called()


class PublicationTests(unittest.TestCase):
    def job(self,root):
        return dict(tree=YFullTree(tree_fixture()),source_id='fixture',tree_sha='a'*64,version='1.0.0',
            commit_sha='b'*40,published_at='2026-11-04T00:00:00Z',source_url='https://github.com/owner/repo',
            license_name='CC-BY-4.0',license_url='https://example.org/license',attribution='Fixture',
            changes={'baseline':True,'new_nodes':4},cache_state_path=Path(root)/'last-applied.json',cache_state={})

    def test_second_run_updates_check_date_without_republishing_nodes(self):
        with tempfile.TemporaryDirectory() as root:
            job=self.job(root);release,_=plan_release(job,['J-TEST1'])
            db=Mock();db.request.return_value=[{'release_key':release['release_key'],'tree_sha':job['tree_sha']}]
            result=sync_tree(job,db,True,['J-TEST1'])
            self.assertEqual(result['status'],'unchanged');self.assertEqual(result['changes']['new_nodes'],0)
            self.assertEqual(db.request.call_count,2)
            self.assertEqual(db.request.call_args.args[-1],'PATCH')

    def test_new_archive_labels_do_not_count_as_new_source_branches(self):
        with tempfile.TemporaryDirectory() as root:
            job=self.job(root);db=Mock()
            db.request.side_effect=[[{'release_key':'c'*64,'tree_sha':job['tree_sha']}],[],[],{'status':'published'}]
            result=sync_tree(job,db,True,['J-TEST1'])
            self.assertEqual(result['changes']['new_nodes'],0)
            self.assertEqual(result['profiles_created'],0)

    def test_missing_cache_does_not_report_all_existing_branches_as_new(self):
        with tempfile.TemporaryDirectory() as root:
            job=self.job(root);db=Mock()
            db.request.side_effect=[[{'release_key':'c'*64,'tree_sha':'d'*64}],[],[],{'status':'published'}]
            result=sync_tree(job,db,True,['J-TEST1'])
            self.assertTrue(result['changes']['comparison_unavailable'])
            self.assertNotIn('new_nodes',result['changes'])

    def test_failed_stage_does_not_publish_or_advance_cache(self):
        with tempfile.TemporaryDirectory() as root:
            job=self.job(root);db=Mock();db.request.side_effect=[[],[],RuntimeError('temporary error')]
            with self.assertRaises(RuntimeError):sync_tree(job,db,True,['J-TEST1'])
            self.assertFalse(job['cache_state_path'].exists())
            self.assertFalse(any(c.args[0].startswith('rpc/') for c in db.request.call_args_list))
