"""Polite public HTTP only. Never retry authentication/robots refusals."""
import fnmatch
import http.cookiejar
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

AGENT = 'EgyptYDNA-PublicSync/1.0 (+https://github.com/egyptydna/Egypt-Y-DNA)'


class Unavailable(Exception): pass


class SourceRestricted(Unavailable):
    """A provider's explicit access restriction; no result request may be made."""


def robots_rules(text, path):
    groups, agents, rules, delay = [], [], [], 5
    in_rules = False
    for line in text.splitlines() + ['User-agent: end-of-file']:
        line = line.split('#', 1)[0].strip()
        if ':' not in line: continue
        key, value = [s.strip() for s in line.split(':', 1)]
        key = key.lower()
        if key == 'user-agent':
            if in_rules:
                groups.append((agents, rules, delay))
                agents, rules, delay, in_rules = [], [], 5, False
            agents.append(value.lower())
        else:
            in_rules = True
            if key in ('allow', 'disallow') and value: rules.append((key == 'allow', value))
            if key == 'crawl-delay':
                try: delay = max(5, float(value))
                except ValueError: pass
    specific = [g for g in groups if any(a != '*' and a in AGENT.lower() for a in g[0])]
    selected = specific or [g for g in groups if '*' in g[0]]
    matches = []
    for _, rule_list, _ in selected:
        for allow, pattern in rule_list:
            expression = re.escape(pattern).replace(r'\*', '.*')
            expression = expression[:-2]+'$' if expression.endswith(r'\$') else expression
            if re.match(expression, path): matches.append((len(pattern.replace('*', '')), allow))
    return (max(matches)[1] if matches else True), max([g[2] for g in selected] or [5])


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl): return None


class PublicHTTP:
    def __init__(self, cache_dir='.sync-cache'):
        self.path = Path(cache_dir)/'http.json'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.cache = json.loads(self.path.read_text()) if self.path.exists() else {}
        self.robots, self.last = {}, {}
        # Anonymous session cookies only, to support ordinary public ASP.NET forms.
        self.opener = urllib.request.build_opener(NoRedirect, urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def _request(self, url, headers=None, data=None):
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != 'https' or parsed.username or parsed.password:
            raise Unavailable('Only public HTTPS URLs permitted')
        # Only explicit hosts. Redirects are not followed, including redirects to login pages.
        if parsed.hostname not in ('www.familytreedna.com', 'discover.familytreedna.com', 'www.yfull.com'):
            raise Unavailable('Host not allowlisted')
        for attempt in range(3):
            elapsed = time.monotonic() - self.last.get(parsed.netloc, 0)
            time.sleep(max(0, self.robots.get(parsed.netloc, ('', 5))[1]-elapsed))
            self.last[parsed.netloc] = time.monotonic()
            try:
                req = urllib.request.Request(url, data=data, headers={'User-Agent': AGENT, **(headers or {})})
                with self.opener.open(req, timeout=30) as response:
                    body = response.read(12_000_001)
                    if len(body) > 12_000_000: raise Unavailable('Response exceeds size limit')
                    return body, dict(response.headers)
            except urllib.error.HTTPError as error:
                if error.code == 304: return None, {}
                if error.code not in (429, 500, 502, 503, 504):
                    raise Unavailable(f'HTTP {error.code}; no authentication or redirect bypass') from error
                if attempt == 2: raise Unavailable(f'Temporary HTTP {error.code}') from error
                retry = error.headers.get('Retry-After', '')
                time.sleep(min(60, max(5, int(retry) if retry.isdigit() else 5 * 2**attempt)))
            except (TimeoutError, urllib.error.URLError) as error:
                if attempt == 2: raise Unavailable('Network unavailable') from error
                time.sleep(5 * 2**attempt)

    def get(self, url, incremental=True, data=None):
        parsed = urllib.parse.urlsplit(url)
        origin = f'{parsed.scheme}://{parsed.netloc}'
        if parsed.netloc not in self.robots:
            body, _ = self._request(origin+'/robots.txt')
            self.robots[parsed.netloc] = (body.decode('utf-8', 'replace'), 5)
        allowed, delay = robots_rules(self.robots[parsed.netloc][0], parsed.path + ('?'+parsed.query if parsed.query else ''))
        self.robots[parsed.netloc] = (self.robots[parsed.netloc][0], delay)
        if not allowed: raise Unavailable('robots.txt disallows this agent')
        old = self.cache.get(url, {}) if incremental and not data else {}
        headers = {}
        if old.get('etag'): headers['If-None-Match'] = old['etag']
        if old.get('last_modified'): headers['If-Modified-Since'] = old['last_modified']
        if data: headers['Content-Type'] = 'application/x-www-form-urlencoded'
        body, response_headers = self._request(url, headers, data)
        if body is not None and incremental and not data:
            # Committed only after a successful run, not after fetch or dry-run.
            self.cache[url] = {'etag': response_headers.get('ETag'), 'last_modified': response_headers.get('Last-Modified')}
        return body

    def commit_cache(self):
        self.path.write_text(json.dumps(self.cache))
