import unittest
from unittest.mock import Mock,patch
from sync.track_projects import track,seed_directory


class ProjectTrackerTests(unittest.TestCase):
    def test_dry_run_cannot_write(self):
        db = Mock()
        result = track(db=db)
        self.assertFalse(result['writes'])
        db.request.assert_not_called()

    @patch('sync.track_projects.seed_directory', return_value=False)
    def test_budget_and_skip_are_preserved(self, seed):
        db = Mock()
        db.request.return_value = {'status': 'recent_skip', 'lastSavedAt': 'saved'}
        self.assertEqual(track(True, db, budget=32)['status'], 'recent_skip')
        db.request.assert_called_once_with('rpc/ydna_project_tracker_refresh',
                                          {'p_budget': 32, 'p_force': False})
        with self.assertRaises(ValueError):
            track(True, db, budget=0)

    @patch('sync.track_projects.seed_directory', return_value=False)
    def test_failure_retains_previous_save_and_logs_no_response(self, seed):
        db = Mock()
        db.request.side_effect = [RuntimeError('secret payload must not escape'), None]
        with self.assertRaisesRegex(RuntimeError, 'previous data retained') as result:
            track(True, db)
        self.assertNotIn('secret payload', str(result.exception))
        self.assertEqual(db.request.call_args.args, ('rpc/ydna_project_tracker_failed', {}))

    @patch('sync.track_projects.seed_directory', return_value=True)
    def test_new_directory_is_reconciled_even_after_a_recent_check(self, seed):
        db=Mock();db.request.return_value={'status':'partial'}
        track(True,db)
        self.assertTrue(db.request.call_args.args[1]['p_force'])
        self.assertEqual(db.request.call_args.args[1]['p_budget'],32)

    def test_directory_is_metadata_only_bounded_and_not_reseeded_on_every_poll(self):
        db=Mock();db.request.return_value=[]
        seed_directory(db)
        calls=[c for c in db.request.call_args_list if c.args[0]=='rpc/ydna_project_catalog_seed']
        self.assertGreater(len(calls),1)
        for call in calls:
            self.assertLessEqual(len(call.args[1]['p_projects']),500)
            for row in call.args[1]['p_projects']:
                self.assertEqual(set(row),{'code','name','url'})
        self.assertTrue(calls[-1].args[1]['p_final'])
        version=calls[-1].args[1]['p_version']
        db.reset_mock();db.request.return_value=[{'seeded_directory_key':version}]
        seed_directory(db)
        self.assertEqual(db.request.call_count,1)
