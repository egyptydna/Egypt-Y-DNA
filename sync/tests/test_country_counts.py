import unittest
from unittest.mock import patch, Mock
from sync.country_counts import prepare_country_count
from sync.run import synchronize


def count_fixture(**changes):
    return dict(dict(kind='country_count',namespace='ftdna',node_label='J-FGC1',country_code='EG',
        reported_count=9,count_scope='inclusive',population='ftdna_big_y',observed_at='2026-11-04T00:00:00Z',
        source_url='https://example.org/synthetic-count',source_id='synthetic-count',publication_allowed=True,
        permission_url='https://example.org/synthetic-permission'),**changes)


class CountryCountTests(unittest.TestCase):
    def test_count_is_not_a_tester(self):
        r=prepare_country_count(count_fixture());self.assertTrue(r['accepted']);self.assertNotIn('external_id',r)

    def test_unknown_scope_does_not_allow_arithmetic_guess(self):
        self.assertFalse(prepare_country_count(count_fixture(count_scope='unknown'))['accepted'])

    def test_no_timestamp_invention(self):
        for date in ['', '2026-11-04', '2026-11-04T00:00:00']:
            self.assertFalse(prepare_country_count(count_fixture(observed_at=date))['accepted'])

    def test_count_requires_nonnegative_integer(self):
        for count in [-1,1.5,True,'9']:
            self.assertFalse(prepare_country_count(count_fixture(reported_count=count))['accepted'])
        self.assertTrue(prepare_country_count(count_fixture(reported_count=0))['accepted'])

    def test_yfull_population_is_separate(self):
        self.assertTrue(prepare_country_count(count_fixture(namespace='yfull',population='yfull_modern'))['accepted'])
        self.assertFalse(prepare_country_count(count_fixture(namespace='yfull'))['accepted'])

    def test_path_must_have_a_public_evidence_link(self):
        self.assertFalse(prepare_country_count(count_fixture(snp_path=['Y-Adam','J-FGC1']))['accepted'])

    def test_restricted_counts_remain_private(self):
        self.assertFalse(prepare_country_count(count_fixture(publication_allowed=False))['accepted'])

    def test_scheduled_ingestion_keeps_counts_out_of_tester_import(self):
        class DatabaseFixture:
            def __init__(self): self.resources=[]
            def request(self,resource,payload=None,method='POST'):
                self.resources.append(resource)
                if resource=='ydna_sync_runs': return [{'id':'synthetic-run-only'}]
                if resource=='rpc/ydna_sync_ingest_country_count': return {'status':'inserted'}
                if resource=='rpc/ydna_sync_ingest': raise AssertionError('A country count became a tester')
                return []
        db=DatabaseFixture()
        with patch('sync.run.ADAPTERS',{'fixture':lambda s,h:([count_fixture()],[])}):
            report=synchronize([{'id':'synthetic-count','adapter':'fixture','enabled':True}],apply=True,http=Mock(),db=db)
        self.assertEqual(report['counts']['country_counts_inserted'],1)
        self.assertEqual(report['unique_candidates'],0)
        self.assertNotIn('rpc/ydna_sync_ingest',db.resources)
