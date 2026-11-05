"""Production smoke check: metadata and HEAD counts only; no profile downloads."""
import os,json
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright

SITE='https://egyptydna.github.io/Egypt-Y-DNA/'
METADATA={'ydna_project_tracking_status','ydna_project_catalog','ydna_sync_tree_releases','ydna_sync_official_tree_nodes'}
def public_routes(route):
 u=urlsplit(route.request.url)
 if '.supabase.co' in u.netloc:
  if route.request.method=='HEAD' or u.path.endswith('/rpc/ydna_editor_context') or u.path.rsplit('/',1)[-1] in METADATA:
   route.continue_();return
  body='null' if u.path.endswith('ydna_tracker_status') else '[]'
  route.fulfill(status=200,content_type='application/json',body=body);return
 if u.netloc in ('egyptydna.github.io','cdn.jsdelivr.net'):
  route.continue_();return
 route.abort()

with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE','/usr/bin/chromium') or None,headless=True,args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':1440,'height':1000})
 page.route('**/*',public_routes)
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 for attempt in range(18):
  page.goto(SITE+'?verify='+os.environ.get('GITHUB_SHA','live'),wait_until='networkidle',timeout=120000)
  if page.locator('script[src*="ydna-owner-tools.js"]').count():break
  page.wait_for_timeout(10000)
 else:raise AssertionError('Updated production HTML did not become available')
 page.wait_for_function("typeof YDNAOwnerTools==='object' && typeof YDNALineageLinks==='object' && typeof ownerCanManage==='function'")
 page.wait_for_selector('#nav-admin',state='attached')
 assert not page.locator('#nav-admin').is_visible()
 assert page.locator('#owner-register').count()==0
 page.evaluate("showSection('admin')")
 assert page.locator('#owner-login').is_visible()
 assert not page.locator('#owner-workspace').is_visible()
 access=page.evaluate("async()=>{const r=await _sb.rpc('ydna_editor_context');return {status:r.status,denied:Boolean(r.error)}}")
 assert access['denied'] and access['status'] in (401,403),access
 count=page.evaluate("async()=>{const r=await _sb.from('ydna_uploaded_profiles').select('record_key',{count:'exact',head:true}).eq('published',true);return {status:r.status,count:r.count,error:Boolean(r.error)}}")
 assert count['status']==200 and not count['error'],count
 links=page.evaluate("YDNALineageLinks.links({y_dna:'E-M35'}).map(x=>({provider:x.provider,secure:x.url.startsWith('https://')}))")
 assert {r['provider'] for r in links}=={'yfull','ftdna'} and all(r['secure'] for r in links)
 for width in (1440,390):
  page.set_viewport_size({'width':width,'height':900})
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
 assert not errors,errors
 print(json.dumps({'production':'passed','privateNavigation':True,'registrationUIAbsent':True,'anonymousEditorDenied':access,'collectedProfileCount':count,'lineageProviders':len(links),'individualProfilesDownloaded':False,'pageErrors':errors}))
 browser.close()
