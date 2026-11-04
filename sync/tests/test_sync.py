"""Synthetic fixtures only. No fixture identity is a claimed real-world tester."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
from sync.adapters import parse_ftdna, collect_ftdna, collect_export, country_form, public_projects
from sync.http import robots_rules, Unavailable, SourceRestricted
from sync.normalize import Gazetteer, prepare, marker_name, str_value
from sync.run import synchronize


def fixture(**changes):
    record = dict(namespace='ftdna',external_id='990099001',name='SYNTHETIC TEST ONLY',
        country='Egypt',origin_raw='Dakahlia, Egypt',origin_kind='paternal',sample_kind='modern',
        y_dna='J-TEST1',test_type='Big Y-700',source_url='https://example.org/public-test-fixture',
        source_id='fixture',publication_allowed=True,permission_url='https://example.org/fixture-permission',str_markers=[])
    return dict(record,**changes)


class NormalizeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.gaz = Gazetteer()

    def test_confirmed_big_y(self):
        r=prepare(fixture(),self.gaz)
        self.assertTrue(r['accepted']);self.assertEqual(r['test_status'],'confirmed_big_y')

    def test_yfull_is_not_big_y(self):
        r=prepare(fixture(namespace='yfull',external_id='YF990099001',test_type='Big Y-700'),self.gaz)
        self.assertEqual(r['test_type'],'YFull sequencing');self.assertEqual(r['test_status'],'yfull_sequencing')

    def test_yfull_new_flag_does_not_replace_id_or_sample_kind(self):
        r=prepare(fixture(namespace='yfull',external_id='YF990099001',is_new=True,tree_version='synthetic-fixture'),self.gaz)
        self.assertTrue(r['accepted']);self.assertTrue(r['is_new'])
        self.assertEqual(r['external_id'],'YF990099001')
        self.assertEqual(r['test_status'],'yfull_sequencing')
        ancient=prepare(fixture(namespace='yfull',external_id='YF990099001',is_new=True,sample_kind='ancient'),self.gaz)
        self.assertFalse(ancient['accepted'])

    def test_study_and_ancient_excluded(self):
        for kind in ['ancient','study','unknown']:
            self.assertFalse(prepare(fixture(sample_kind=kind),self.gaz)['accepted'])

    def test_str_prediction(self):
        r=prepare(fixture(test_type='Y-DNA37',haplogroup_status='predicted'),self.gaz)
        self.assertEqual(r['test_status'],'str_only')

    def test_no_name_based_egypt_inference(self):
        r=prepare(fixture(name='محمد',country='',origin_raw='',y_dna='J-M267'),self.gaz)
        self.assertFalse(r['accepted'])

    def test_country_only(self):
        r=prepare(fixture(origin_raw='Egypt'),self.gaz)
        self.assertTrue(r['accepted']);self.assertIsNone(r['origin']['governorate_iso'])

    def test_residence_not_paternal(self):
        self.assertFalse(prepare(fixture(origin_kind='residence'),self.gaz)['accepted'])

    def test_village_arabic_and_transliteration(self):
        for origin in ['ميت غمر, مصر','Mit Ghamr, Egypt','المنصورة, Egypt','Mansoura, Egypt']:
            r=self.gaz.resolve(origin,'Egypt');self.assertEqual(r['governorate_iso'],'EG-DK',origin)

    def test_ambiguous_village(self):
        gaz=Gazetteer([dict(id='a',name='Test Village',iso='EG-DK'),dict(id='b',name='Test Village',iso='EG-GH')])
        r=gaz.resolve('Test Village','Egypt');self.assertEqual(r['status'],'ambiguous');self.assertIsNone(r['governorate_iso'])
        self.assertEqual(gaz.resolve('Test Village, Dakahlia','Egypt')['governorate_iso'],'EG-DK')

    def test_governorates(self):
        self.assertEqual(len(self.gaz.governorates),27)
        for name,iso in [('Sharkeya','EG-SHR'),('بورسعيد','EG-PTS'),('New Valley','EG-WAD'),('الوادي الجديد','EG-WAD')]:
            self.assertEqual(self.gaz.resolve(name,'Egypt')['governorate_iso'],iso)

    def test_str_exact(self):
        self.assertEqual(str_value('14-16-17-17'),'14-16-17-17')
        self.assertEqual(str_value('0'),'0');self.assertIsNone(str_value(''))
        self.assertNotEqual(marker_name('DYS389i'),marker_name('DYS389ii'))
        self.assertEqual(marker_name('Y GATA H4'),'Y-GATA-H4')
        with self.assertRaises(ValueError):str_value('estimated 12')

    def test_unverified_path_not_invented(self):
        r=prepare(fixture(snp_path=['Y-Adam','J-TEST1']),self.gaz)
        self.assertFalse(r['accepted']);self.assertEqual(r['snp_path'],[])

    def test_permission_gate(self):
        self.assertFalse(prepare(fixture(publication_allowed=False),self.gaz)['accepted'])


class AdapterTests(unittest.TestCase):
    HTML='''<table><tr><th>Kit Number</th><th>Country</th><th>Haplogroup</th><th>Test</th><th>DYS389i</th><th>DYS389ii</th><th>DYS464</th><th>DYS425</th></tr><tr><td>990099001</td><td>Egypt</td><td style="color:green">J-TEST1</td><td>Big Y-700</td><td>13</td><td>29</td><td>14-16-17-17</td><td>0</td></tr><tr><td>MIN</td><td>Egypt</td><td>J</td><td></td><td>1</td><td>1</td><td>1</td><td>1</td></tr></table>'''

    def test_public_table(self):
        rows=parse_ftdna(self.HTML,{'id':'fixture','url':'https://example.org','publication_allowed':True})
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['str_markers'][2]['value'],'14-16-17-17')
        self.assertEqual(rows[0]['str_markers'][3]['value'],'0')
        self.assertEqual(rows[0]['haplogroup_status'],'confirmed')

    def test_private_visibility(self):
        with self.assertRaises(Unavailable): parse_ftdna('Results pages are visible to group members only.',{})

    def test_discovery(self):
        self.assertEqual(public_projects('<a href="/public/J-M267?iframe=ycolorized">J1</a><a href="https://evil.test/public/G">bad</a>'),['J-M267'])

    def test_robots_no_impersonation(self):
        robots='User-agent: Googlebot\nAllow: /\nUser-agent: *\nDisallow: /\nCrawl-delay: 10\n'
        self.assertEqual(robots_rules(robots,'/tree/J/'),(False,10))
        self.assertFalse(robots_rules('User-agent: *\nDisallow: /*kit=*','/public/J?kit=123')[0])

    def test_no_ftdna_request_without_provider_permission(self):
        http=Mock()
        with self.assertRaises(SourceRestricted):
            collect_ftdna({'url':'https://www.familytreedna.com/public/J-M267'},http)
        http.get.assert_not_called()

    def test_authorized_ftdna_source_uses_public_table(self):
        http=Mock()
        http.get.return_value=self.HTML.encode()
        records,_=collect_ftdna({'id':'fixture','url':'https://example.org',
            'automated_access_allowed':True,'access_permission_url':'https://example.org/permission'},http)
        self.assertEqual(len(records),1)

    def test_access_flag_alone_does_not_override_terms(self):
        http=Mock()
        with self.assertRaises(SourceRestricted):
            collect_ftdna({'url':'https://www.familytreedna.com/public/J-M267','automated_access_allowed':True},http)
        http.get.assert_not_called()


class RunTests(unittest.TestCase):
    def test_restricted_source_is_reported_without_result_request(self):
        http=Mock()
        report=synchronize([dict(id='restricted',url='https://www.familytreedna.com/public/J-M267',
            adapter='ftdna_project',enabled=True)],http=http)
        self.assertEqual(report['sources'][0]['status'],'restricted')
        self.assertEqual(report['counts']['restricted_sources'],1)
        self.assertEqual(report['sources_checked_successfully'],0)
        http.get.assert_not_called()

    def test_three_projects_and_no_change_repeat(self):
        sources=[dict(id=str(i),adapter='fixture',enabled=True) for i in range(3)]
        with patch('sync.run.ADAPTERS',{'fixture':lambda s,h:([fixture(source_id=s['id'])],[]) }):
            a=synchronize(sources);b=synchronize(sources)
        self.assertEqual(a['unique_candidates'],1);self.assertEqual(a['counts']['duplicates_in_run'],2)
        self.assertEqual(a['counts'],b['counts'])

    def test_temporarily_unreachable(self):
        def failed(s,h):raise Unavailable('Temporary HTTP 503')
        with patch('sync.run.ADAPTERS',{'fixture':failed}):
            report=synchronize([dict(id='f',adapter='fixture',enabled=True)])
        self.assertEqual(report['status'],'partial');self.assertEqual(report['records'],0)


if __name__=='__main__':unittest.main()
