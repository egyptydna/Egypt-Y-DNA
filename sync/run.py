"""python -m sync.run [--apply] [--sources sync/data/sources.json]. Dry run is default."""
import argparse
import collections
import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from .adapters import ADAPTERS
from .http import PublicHTTP, Unavailable
from .normalize import Gazetteer, prepare

PROJECT_URL = 'https://lsfmpmfoqdtkgndtaxen.supabase.co'


class Database:
    def __init__(self):
        self.key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
        if os.environ.get('SUPABASE_URL', PROJECT_URL).rstrip('/') != PROJECT_URL:
            raise ValueError('Refusing a different Supabase project')
        if not self.key: raise ValueError('SUPABASE_SERVICE_ROLE_KEY is required for --apply')

    def request(self, resource, payload=None, method='POST'):
        req = urllib.request.Request(PROJECT_URL+'/rest/v1/'+resource,
            data=json.dumps(payload).encode() if payload is not None else None, method=method,
            headers={'apikey': self.key, 'Authorization': 'Bearer '+self.key,
                     'Content-Type': 'application/json', 'Prefer': 'return=representation,resolution=merge-duplicates'})
        # RPC retries are safe: ingestion is idempotent. Never expose response bodies or credentials in logs.
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=45) as response:
                    content = response.read()
                    return json.loads(content) if content else None
            except urllib.error.HTTPError as e:
                if e.code not in (429, 500, 502, 503, 504) or attempt == 2:
                    raise RuntimeError(f'Supabase operation failed: HTTP {e.code}') from None
            except (TimeoutError, urllib.error.URLError):
                if attempt == 2: raise RuntimeError('Supabase network unavailable') from None
            import time
            time.sleep(2**attempt)


def synchronize(sources, apply=False, http=None, db=None):
    http = http or PublicHTTP()
    db = db or (Database() if apply else None)
    gaz = Gazetteer()
    report = {'mode': 'apply' if apply else 'dry_run', 'started_at': datetime.now(timezone.utc).isoformat(),
              'sources': [], 'counts': {}, 'discovered_projects': [], 'records': 0}
    counts = collections.Counter()
    seen = set()
    run = None
    if apply:
        run = db.request('ydna_sync_runs', {'status': 'running'})[0]['id']
    try:
        if apply:
            # Geographic data are non-personal; keep the governorate directory in sync.
            db.request('ydna_sync_places?on_conflict=id', [dict(id=g['id'],name=g['name'],aliases=g['aliases'],
                governorate_iso=g['iso'],district=g.get('district'),source_url=g['source_url'],
                metadata={'feature':g.get('feature')}) for g in gaz.governorates])
        for source in sources:
            entry = {'id': source['id'], 'url': source.get('url'), 'status': 'disabled', 'records': 0}
            report['sources'].append(entry)
            if not source.get('enabled'): continue
            if apply:
                db.request('ydna_sync_sources?on_conflict=id', {k: source.get(k) for k in
                    ('id', 'url', 'adapter', 'publication_allowed', 'permission_url')})
            try:
                if source.get('adapter') not in ADAPTERS: raise Unavailable('Unsupported adapter')
                records, projects = ADAPTERS[source['adapter']](source, http)
                report['discovered_projects'].extend(projects)
                entry.update(status='ok', records=len(records))
                for raw in records:
                    if raw.get('visibility') == 'withdrawn':
                        if not raw.get('withdrawal_evidence_url'):
                            raise ValueError('Explicit public withdrawal evidence required')
                        if apply:
                            result = db.request('rpc/ydna_sync_withdraw', {'p_source':source['id'],
                                'p_namespace':raw['namespace'],'p_external_id':raw['external_id'],
                                'p_evidence_url':raw['withdrawal_evidence_url']})
                            counts[result['status']] += 1
                        else: counts['withdrawal_candidates'] += 1
                        continue
                    record = prepare(raw, gaz)
                    identity = (record['namespace'], record['external_id'])
                    if identity in seen: counts['duplicates_in_run'] += 1
                    seen.add(identity)
                    if apply:
                        result = db.request('rpc/ydna_sync_ingest', {'p_record': record, 'p_run': run, 'p_dry_run': False})
                        counts[result['status']] += 1
                        if result.get('duplicate'): counts['existing_observations'] += 1
                        counts['conflicts'] += result.get('conflicts', 0)
                    else:
                        counts['accepted_candidates' if record['accepted'] else 'review_candidates'] += 1
                        for reason in record['review_reasons']: counts[reason] += 1
                    report['records'] += 1
                if apply:
                    db.request('ydna_sync_sources?id=eq.'+urllib.parse.quote(source['id']),
                        {'last_success_at': datetime.now(timezone.utc).isoformat(), 'last_status': 'ok'}, 'PATCH')
            except (Unavailable, ValueError, KeyError) as error:
                # Never remove known data on fetch, format, robots, or permission failures.
                entry.update(status='unavailable', reason=str(error)[:180])
                counts['unavailable_sources'] += 1
                if apply:
                    db.request('ydna_sync_sources?id=eq.'+urllib.parse.quote(source['id']), {'last_status': entry['reason']}, 'PATCH')
        report['counts'] = dict(counts)
        report['unique_candidates'] = len(seen)
        report['discovered_projects'] = sorted(set(report['discovered_projects']))
        report['status'] = 'partial' if counts['unavailable_sources'] else 'completed'
        if apply:
            db.request('ydna_sync_runs?id=eq.'+run, {'finished_at': datetime.now(timezone.utc).isoformat(),
                'status': report['status'], 'report': report}, 'PATCH')
            http.commit_cache()
        return report
    except Exception:
        if apply:
            db.request('ydna_sync_runs?id=eq.'+run, {'finished_at': datetime.now(timezone.utc).isoformat(), 'status': 'failed'}, 'PATCH')
        raise


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--sources', default='sync/data/sources.json')
    args = parser.parse_args()
    report = synchronize(json.loads(Path(args.sources).read_text()), args.apply)
    Path('reports').mkdir(exist_ok=True)
    Path('reports/latest.json').write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n')
    summary = 'Y-DNA synchronization: '+report['status']+'\n\n'+json.dumps(report['counts'], indent=2)+'\n'
    Path('reports/latest.md').write_text(summary)
    if os.getenv('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as f: f.write(summary)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == '__main__': main()
