"""Maintain resumable project searches from the site's verified saved evidence.

The database keeps private search targets and publishes counters only. No names,
kit numbers, genetic calls, or service credentials are logged by this runner.
"""
import argparse
import json
import gzip
import hashlib
from pathlib import Path
from .run import Database


def seed_directory(db):
    path = Path(__file__).parent/'data/project-directory.json.gz'
    raw = path.read_bytes()
    version = hashlib.sha256(raw).hexdigest()
    saved = db.request('ydna_project_tracking_status?id=eq.true&select=seeded_directory_key', method='GET')
    if saved and saved[0].get('seeded_directory_key') == version:
        return False
    data = json.loads(gzip.decompress(raw))
    projects = data['projects']
    for offset in range(0, len(projects), 500):
        db.request('rpc/ydna_project_catalog_seed',
                   {'p_projects': projects[offset:offset+500], 'p_version': version,
                    'p_final': offset+500 >= len(projects)})
    return True


def track(apply=False, db=None, budget=128, force=False):
    if not 1 <= budget <= 512:
        raise ValueError('Budget must be between 1 and 512 targets')
    if not apply:
        return {'mode': 'dry_run', 'writes': False, 'budget': budget,
                'scope': 'Saved public project evidence; no direct provider access'}
    db = db or Database()
    try:
        directory_seeded = seed_directory(db)
        return db.request('rpc/ydna_project_tracker_refresh',
                          {'p_budget': budget, 'p_force': bool(force or directory_seeded)})
    except Exception:
        # Keep the last good summary and its saved timestamp when a run fails.
        try:
            db.request('rpc/ydna_project_tracker_failed', {})
        except Exception:
            pass
        raise RuntimeError('Project tracking could not be saved; previous data retained') from None


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--budget', type=int, default=128)
    args = parser.parse_args()
    report = track(args.apply, budget=args.budget)
    out = Path('reports'); out.mkdir(exist_ok=True)
    (out/'project-tracker.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
