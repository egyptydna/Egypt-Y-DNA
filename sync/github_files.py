"""Read explicitly configured public GitHub files at an immutable commit.

Uses GitHub's published REST/raw interfaces, not FTDNA/YFull website scraping.
No access tokens are sent. Cached source files contain no runtime credentials.
"""
import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath
from .http import AGENT, NoRedirect, Unavailable


class GitHubFiles:
    def __init__(self, repo, branch='master', cache_dir='.sync-cache/github'):
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
            raise ValueError('Invalid public GitHub repository')
        self.repo, self.branch = repo, branch
        self.root=Path(cache_dir)/repo.replace('/','--')
        self.root.mkdir(parents=True,exist_ok=True)
        self.opener=urllib.request.build_opener(NoRedirect)
        self.head=None

    def request(self,url,limit=32_000_000):
        parsed=urllib.parse.urlsplit(url)
        if parsed.scheme!='https' or parsed.hostname not in ('api.github.com','raw.githubusercontent.com'):
            raise Unavailable('Only GitHub public file interfaces are permitted')
        for attempt in range(3):
            try:
                req=urllib.request.Request(url,headers={'User-Agent':AGENT,'Accept':'application/vnd.github+json'})
                with self.opener.open(req,timeout=45) as response:
                    data=response.read(limit+1)
                    if len(data)>limit: raise Unavailable('GitHub source exceeds size limit')
                    return data
            except urllib.error.HTTPError as error:
                if error.code not in (429,500,502,503,504) or attempt==2:
                    raise Unavailable(f'GitHub HTTP {error.code}; no redirect or authentication bypass') from None
                retry=error.headers.get('Retry-After','')
                time.sleep(min(60,int(retry) if retry.isdigit() else 2**(attempt+1)))
            except (TimeoutError,urllib.error.URLError):
                if attempt==2: raise Unavailable('GitHub source unavailable') from None
                time.sleep(2**(attempt+1))

    def resolve_head(self):
        data=json.loads(self.request(f'https://api.github.com/repos/{self.repo}/commits/'+urllib.parse.quote(self.branch,safe=''),2_000_000))
        sha=data.get('sha','')
        if not re.fullmatch('[0-9a-f]{40}',sha): raise Unavailable('Invalid GitHub commit response')
        self.head={'sha':sha,'committed_at':data['commit']['committer']['date']}
        return self.head

    def file(self,path):
        if not self.head: self.resolve_head()
        if path.startswith('/') or '..' in PurePosixPath(path).parts: raise ValueError('Invalid GitHub source path')
        sha=self.head['sha']
        target=self.root/sha/path
        if target.exists(): return target.read_bytes()
        data=self.request(f'https://raw.githubusercontent.com/{self.repo}/{sha}/'+urllib.parse.quote(path,safe='/'))
        target.parent.mkdir(parents=True,exist_ok=True)
        temp=target.with_suffix(target.suffix+'.tmp')
        temp.write_bytes(data);temp.replace(target)
        return data

    def file_published_at(self,path):
        """Date of the last commit touching this file, not its download or sample upload date."""
        if not self.head: self.resolve_head()
        target=self.root/self.head['sha']/'.file-dates.json'
        dates=json.loads(target.read_text()) if target.exists() else {}
        if path not in dates:
            query=urllib.parse.urlencode({'path':path,'sha':self.head['sha'],'per_page':1})
            rows=json.loads(self.request(f'https://api.github.com/repos/{self.repo}/commits?{query}',2_000_000))
            if not rows: raise Unavailable('No source publication commit found')
            dates[path]=rows[0]['commit']['committer']['date']
            target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(dates))
        return dates[path]

    def permalink(self,path):
        return f'https://github.com/{self.repo}/blob/{self.head["sha"]}/'+urllib.parse.quote(path,safe='/')


def sha256(data):
    return hashlib.sha256(data).hexdigest()
