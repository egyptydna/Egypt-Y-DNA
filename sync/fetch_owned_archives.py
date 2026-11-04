"""Read the owner's saved snapshots. Never request FTDNA/YFull or start a crawl.

Get a fresh Observatory service credential with Sites.get_site. Pass the token
through hidden stdin, never a command argument, file or GitHub secret.
"""
import argparse
import getpass
import gzip
import http.client
import io
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from .http import NoRedirect
from .owned_archives import OBSERVATORY

LIMIT=32_000_000


def decode_snapshot(raw):
    if raw[:2]==b'\x1f\x8b':raw=gzip.GzipFile(fileobj=io.BytesIO(raw)).read(LIMIT+1)
    if len(raw)>LIMIT:raise ValueError('Owner archive exceeds size limit')
    data=json.loads(raw)
    if not isinstance(data,dict):raise ValueError('Expected owner archive object')
    return data


def read_snapshot(url,token=None):
    if url != OBSERVATORY+'api/data':
        raise ValueError('Only the explicitly owned Observatory read endpoint is permitted')
    if token and not url.startswith(OBSERVATORY):raise ValueError('Site credential cannot leave its Site')
    headers={'User-Agent':'Egypt-Y-DNA owner archive transfer'}
    if token:headers['OAI-Sites-Authorization']='Bearer '+token
    opener=urllib.request.build_opener(NoRedirect)
    request=urllib.request.Request(url,headers=headers,method='GET')
    for attempt in range(3):
        try:
            with opener.open(request,timeout=45) as response:return decode_snapshot(response.read(LIMIT+1))
        except urllib.error.HTTPError as error:
            if error.code not in (429,500,502,503,504) or attempt==2:raise
        except (TimeoutError,urllib.error.URLError,http.client.HTTPException,ConnectionError):
            if attempt==2:raise
        time.sleep(2**attempt)


def fetch_owned(config,outdir):
    if config.get('owner_authorized') is not True:raise ValueError('Explicit owner transfer authorization is required')
    token=config.get('observatory_token')
    if not isinstance(token,str) or not token:raise ValueError('Fresh Sites owner service access is required')
    out=Path(outdir).resolve();repo=Path(__file__).resolve().parents[1]
    if out==repo or repo in out.parents:raise ValueError('Keep real archive snapshots outside the public repository')
    out.mkdir(parents=True,exist_ok=True);report={};files={}
    try:
        data=read_snapshot(OBSERVATORY+'api/data',token)
        if not isinstance(data.get('records'),list):raise ValueError('Owner Observatory format changed')
        path=out/'observatory.json';path.write_text(json.dumps(data,ensure_ascii=False));files['observatory']=str(path)
        report['observatory']={'status':'ok','checked_at':data.get('checkedAt'),'upstream_sync':data.get('sync'),
            'coverage':data.get('coverage'),'records':len(data['records'])}
    except (ValueError,TimeoutError,urllib.error.URLError,http.client.HTTPException,ConnectionError):
        report['observatory']={'status':'unavailable'}
    (out/'source-status.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    if not files:raise ValueError('No owned archive snapshot could be read; existing database data must be retained')
    return {'files':files,'sources':report}


def main():
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--outdir',required=True);args=parser.parse_args()
    config=json.loads(getpass.getpass('Fresh owner access JSON (hidden): ') if sys.stdin.isatty() else sys.stdin.read())
    result=fetch_owned(config,args.outdir);print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
