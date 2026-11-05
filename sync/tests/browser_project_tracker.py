import json,urllib.request,urllib.error,mimetypes,time
from pathlib import Path
from urllib.parse import urlsplit,parse_qs,unquote
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[2]
errors=[];catalog_requests=[];status_failed=False
now='2026-11-05T09:00:00Z'
status={'last_attempt_at':now,'last_saved_at':now,'state':'partial','summary':{
 'projectDirectory':{'trackedProjects':9740,'projectsWithSavedEvidence':2,'permissionNeededProjects':9738,'exactMemberships':3},
 'projectSearch':{'targets':3,'queued':1,'checkedTargets':2,'exactKitMatches':1,'anonymousLineageTargets':1,'checkedProjectViews':2,'lineageCandidateProjectViews':1},
 'sourceRun':{'status':'partial','finishedAt':now},'sourcePartialRuns':[{'id':'public-fixture','status':'ok','records':2},{'id':'restricted-fixture','status':'restricted','records':0}]}}
samples=[{'id':1,'name':'Synthetic profile','kit_number':'990001','test_type':'Big Y-700','y_dna':'J-TEST1','full_snp_path':'Y-Adam>J-M267>J-TEST1','governorate':'Sūhāj','sync_visibility':'public'},
 {'id':2,'name':'Synthetic baseline','kit_number':'990002','test_type':'Y-DNA37','y_dna':'E-TEST2','full_snp_path':'Y-Adam>E-M35>E-TEST2','governorate':'—','sync_visibility':'public'}]
cache={}
def route_handler(route):
 global status_failed
 url=route.request.url;u=urlsplit(url)
 if '.supabase.co' in u.netloc:
  table=unquote(u.path.rsplit('/',1)[-1]);q=parse_qs(u.query)
  data=[]
  if table=='Modern_published_samples':data=samples
  elif table=='ydna_project_tracking_status':
   if status_failed:route.fulfill(status=503,content_type='application/json',body='{"message":"fixture unavailable"}');return
   data=status
  elif table=='ydna_project_catalog':
   limit=int(q.get('limit',['100'])[0]);offset=int(q.get('offset',['0'])[0]);catalog_requests.append((limit,offset))
   assert limit<=100
   if 'name' in q:data=[{'project_key':'fixture-a','name':'Fixture A','source_url':'https://www.familytreedna.com/public/Fixture-A','access_status':'saved_evidence','last_evidence_at':now}]
   else:data=[{'project_key':f'fixture-{i:03}','name':f'Project {i:03}','source_url':f'https://www.familytreedna.com/public/Fixture-{i}','access_status':'unverified','last_evidence_at':None} for i in range(offset,offset+100)]
  elif table=='ydna_project_memberships':data=[{'sample_id':1,'project_key':'fixture-a'},{'sample_id':1,'project_key':'fixture-b'}]
  elif table=='ydna_project_profile_activity':data=[{'sample_id':1,'new_until':'2099-01-01T00:00:00Z'},{'sample_id':2,'new_until':None}]
  elif table=='ydna_sync_observations':data=[{'sample_id':1,'namespace':'ftdna','is_current':True,'published':True,'project':'Fixture A','test_type':'Big Y-700'}]
  elif table=='ydna_sync_runs':data=[{'started_at':now}]
  elif table=='ydna_tracker_status':data=None
  route.fulfill(status=200,content_type='application/json',body=json.dumps(data));return
 if u.netloc=='egyptydna.github.io':
  path=root/(u.path.split('/Egypt-Y-DNA/',1)[-1] or 'index.html')
  if path.is_file():route.fulfill(path=str(path));return
  route.fulfill(status=404,body='');return
 if '.vercel.app' in u.netloc:errors.append('Unexpected Vercel request');route.abort();return
 if u.netloc in ('fonts.googleapis.com','fonts.gstatic.com'):route.abort();return
 try:
  if url not in cache:
   with urllib.request.urlopen(url,timeout=30) as r:cache[url]=(r.read(),r.headers.get('Content-Type','application/javascript'))
  body,kind=cache[url];route.fulfill(status=200,content_type=kind,body=body)
 except Exception:route.abort()

with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':1440,'height':1000})
 page.route('**/*',route_handler);page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('https://egyptydna.github.io/Egypt-Y-DNA/',wait_until='networkidle',timeout=120000)
 page.wait_for_function('modernSamples.length===2 && modernSamples[0].__new_until',timeout=30000)
 assert '9740 catalogued projects' in page.locator('#project-tracker-dashboard').inner_text()
 page.locator('#project-tracker-dashboard button').click()
 page.wait_for_selector('#project-tracker-panel:visible')
 assert 'Kits confirmed in additional projects' in page.locator('#project-tracker-panel').inner_text()
 page.locator('#project-tracker-panel details').first.locator('summary').click()
 page.locator('[data-project-next]').click();page.wait_for_function("document.querySelector('[data-project-table]').textContent.includes('Page 2')")
 page.locator('[data-project-filter]').fill('Fixture A');page.wait_for_function("document.querySelector('[data-project-table]').textContent.includes('Fixture A')")
 assert page.locator('[data-project-table] tbody tr').count()==1
 page.evaluate("setCountryTreeMode('profiles')")
 page.select_option('#treeTestStatus','new')
 assert page.locator('#tree-inner .project-new-badge').count()==1
 assert page.locator('.tree-sample-card').count()==1
 status_failed=True
 page.locator('[data-project-refresh]').click()
 page.wait_for_function("document.querySelector('#project-tracker-panel').textContent.includes('Status temporarily unavailable')")
 assert '9,740' in page.locator('#project-tracker-panel').inner_text()
 for width,height in [(1440,1000),(390,844)]:
  page.set_viewport_size({'width':width,'height':height})
  page.locator('#project-tracker-panel').scroll_into_view_if_needed()
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
  out=root/'reports';out.mkdir(exist_ok=True);page.screenshot(path=str(out/f'project-tracker-{width}.png'))
 assert not errors,errors
 print(json.dumps({'syntheticBrowser':'passed','desktopAndMobile':True,'pagedCatalogRequests':catalog_requests,'newBadge':1,'statusFailureRetainsSummary':True,'pageErrors':len(errors)}))
 browser.close()
