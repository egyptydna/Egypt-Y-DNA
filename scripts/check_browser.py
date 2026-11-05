"""Read-only live-data browser check plus an explicitly synthetic in-browser STR fixture. Requires playwright and /usr/bin/chromium."""
import json,urllib.request,urllib.error
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
errors=[];api=[]
def route_handler(route):
 url=route.request.url
 if '.vercel.app/' in url:errors.append('Unexpected Vercel dependency');route.abort();return
 if 'ydna_sync_observations' in url and '-990099001' in url:
  route.fulfill(status=200,content_type='application/json',body=json.dumps([{'id':1,'source_id':'fixture','namespace':'ftdna','external_id':'990099001','is_current':True,'last_seen_at':'2026-11-04T00:00:00Z','payload':{'source_url':'https://example.org/synthetic-fixture','test_type':'Big Y-700','y_dna':'J-TEST1','str_markers':[{'marker':'DYS425','source_label':'DYS425','position':0,'value':'0'},{'marker':'DYS464','source_label':'DYS464','position':1,'value':'14-16-17-17'}]}}]));return
 if url.startswith('https://egyptydna.github.io/Egypt-Y-DNA/'):
  name=url.split('/Egypt-Y-DNA/',1)[1].split('?',1)[0] or 'index.html'
  path=root/name
  if path.is_file():
   route.fulfill(path=str(path));return
  route.fulfill(status=404,body='');return
 if any(x in url for x in ['fonts.googleapis','fonts.gstatic','google-analytics','favicon']):route.abort();return
 try:
  headers={k:v for k,v in route.request.headers.items() if k.lower() not in ['host','content-length','accept-encoding']}
  req=urllib.request.Request(url,headers=headers,method=route.request.method,data=route.request.post_data_buffer)
  with urllib.request.urlopen(req,timeout=40) as r:
   data=r.read();rh=dict(r.headers);rh.pop('Content-Encoding',None);rh.pop('content-encoding',None);rh.pop('Content-Length',None);rh.pop('content-length',None)
   if '.supabase.co' in url:api.append((url.split('/rest/v1/')[-1].split('?')[0],r.status))
   route.fulfill(status=r.status,headers=rh,body=data)
 except urllib.error.HTTPError as e:
  api.append((url.split('/rest/v1/')[-1].split('?')[0],e.code));route.fulfill(status=e.code,body=e.read())
 except Exception as e:errors.append(type(e).__name__+': '+url.split('?')[0]);route.abort()
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':1440,'height':1000})
 page.on('pageerror',lambda error:errors.append(str(error)))
 page.route('**/*',route_handler)
 page.goto('https://egyptydna.github.io/Egypt-Y-DNA/',wait_until='networkidle',timeout=120000)
 page.wait_for_function('modernSamples.length > 300',timeout=60000)
 print('Data',page.evaluate('({modern:modernSamples.length,studies:studySamples.length,ancient:ancientSamples.length,related:relatedAncientSamples.length})'))
 assert page.evaluate("modernSamples.filter(s=>s.yfull_id==='YF129136').length===1 && modernSamples.find(s=>s.yfull_id==='YF129136').mt_dna==='U3b3d2a'")
 assert page.evaluate("modernSamples.find(s=>s.kit_number==='MI33015').governorate==='—'")
 assert page.evaluate("!getRegionTotals('Ash Sharqīyah').pool.some(s=>s.kit_number==='MI33015')")
 page.evaluate("showSection('ytree');currentTreeType='y';treeShowModern=true;treeShowStudy=false;treeShowAncient=false;treeShowRelated=false;renderTree()")
 print('Tree cards',page.locator('.tree-sample-card').count())
 page.wait_for_function('syncOfficialRelease?.version && syncOfficialNodes.size > 0')
 print('Unresolved source path issues',page.evaluate("modernSamples.filter(s=>YDNASync.pathIssue(s,undefined,syncOfficialRelease,syncOfficialNodes)).map(s=>({record:s.id,terminal:s.y_dna,issue:YDNASync.pathIssue(s,undefined,syncOfficialRelease,syncOfficialNodes)}))"))
 assert 'CC BY 4.0' in page.locator('#official-tree-panel').inner_text()
 before=page.evaluate('buildRawTree(treeFilteredSamples()).count')
 page.select_option('#official-topology-mode','published')
 assert page.evaluate('buildRawTree(treeFilteredSamples()).count')==before
 page.select_option('#official-topology-mode','yfull')
 assert page.evaluate('buildRawTree(treeFilteredSamples()).count')==before
 page.evaluate("openSampleModal(modernSamples.find(s=>YDNASync.officialPath(s,syncOfficialRelease,syncOfficialNodes)))")
 assert 'official yfull y-dna reference' in page.locator('#sample-official-tree').inner_text().lower()
 assert 'Branch TMRCA' in page.locator('#sample-official-tree').inner_text()
 assert page.evaluate("['exact','equivalent_snp'].includes(syncOfficialRelease.metadata.matches['J-FGC1'].status)")
 page.evaluate('closeSampleModal(null)')
 print('Official licensed topology, attribution, ages and fallback mode: same tester count',before)
 # Exercise the compact tree through real controls, with the new Egyptian J2a sample.
 page.select_option('#official-topology-mode','auto')
 page.wait_for_timeout(200)
 page.evaluate("window.scrollTo({top:document.getElementById('tree-wrap').getBoundingClientRect().top+scrollY-88,behavior:'instant'})")
 overview=root.parent/'artifacts';overview.mkdir(exist_ok=True)
 page.screenshot(path=str(overview/'ydna-tree-overview.png'))
 page.evaluate("document.getElementById('treeSearch').value='YF149485';runTreeSearch()")
 assert page.locator('.phylo-sample-id').get_by_text('YF149485',exact=True).count()==1
 assert page.evaluate("YDNASync.yFamily(modernSamples.find(s=>s.yfull_id==='YF149485'),syncOfficialRelease,syncOfficialNodes,syncLineagePathCache)==='J2'")
 assert page.locator('.phylo-root').get_attribute('data-tree')=='y'
 assert page.locator('.phylo-root > .phylo-node-row .phylo-node-name').inner_text()=='J-M319'
 page.locator('.phylo-sample-row').filter(has=page.get_by_text('YF149485',exact=True)).click()
 assert page.locator('#sample-detail-modal').is_visible()
 page.evaluate('closeSampleModal(null)')
 artifacts=root.parent/'artifacts';artifacts.mkdir(exist_ok=True)
 page.wait_for_timeout(250)
 page.evaluate("window.scrollTo({top:document.getElementById('tree-wrap').getBoundingClientRect().top+scrollY-88,behavior:'instant'})")
 page.screenshot(path=str(artifacts/'ydna-tree-desktop.png'))
 page.set_viewport_size({'width':390,'height':844})
 page.evaluate("window.scrollTo({top:document.getElementById('tree-wrap').getBoundingClientRect().top+scrollY-88,behavior:'instant'})")
 page.screenshot(path=str(artifacts/'ydna-tree-mobile.png'))
 overflow=page.evaluate('({width:document.documentElement.scrollWidth,viewport:innerWidth,elements:[...document.querySelectorAll("body *")].filter(e=>getComputedStyle(e).position!=="fixed"&&e.getBoundingClientRect().right>innerWidth+1&&e.getBoundingClientRect().width>0).slice(0,5).map(e=>({tag:e.tagName,id:e.id,width:e.getBoundingClientRect().width}))})')
 assert overflow['width']<=overflow['viewport']+1,overflow
 page.set_viewport_size({'width':1440,'height':1000})
 page.evaluate("treeReset();syncTextQuery='';renderTree()")
 page.select_option('#treeTestStatus','confirmed_big_y',force=True)
 page.evaluate('resetSyncTreeFocus()')
 print('Big Y filtered',page.evaluate('treeFilteredSamples().length'))
 assert page.evaluate("treeFilteredSamples().every(s=>YDNASync.status(s)==='confirmed_big_y')")
 page.select_option('#treeTestStatus','',force=True)
 page.evaluate("resetSyncTreeFocus();openSampleModal(modernSamples.find(s=>s.test_type==='Big Y-700'))")
 page.wait_for_timeout(800)
 print('Details',page.locator('#sample-sync-details').inner_text()[:140])
 page.evaluate("closeSampleModal(null);currentTreeType='mt';renderTree()")
 print('mtDNA cards',page.locator('.tree-sample-card').count())
 assert page.locator('.phylo-root').get_attribute('data-tree')=='mt'
 assert page.evaluate("parseMtPath('—','H2a2b').join('>')==='mt-Eve>H2a2b'")
 page.evaluate("window.scrollTo({top:document.getElementById('tree-wrap').getBoundingClientRect().top+scrollY-88,behavior:'instant'})")
 page.screenshot(path=str(artifacts/'mtdna-tree-desktop.png'))
 # Synthetic browser-only tester verifies the UI when production has no imported STR profiles.
 page.evaluate("currentTreeType='y';modernSamples.push({id:-990099001,__uid:'synthetic-ui-test',__sourceType:'modern',name:'SYNTHETIC UI TEST ONLY',kit_number:'990099001',governorate:'Port Said',y_dna:'J-TEST1',test_type:'Big Y-700',test_status:'confirmed_big_y'});renderTree();openSampleModal(modernSamples.at(-1))")
 page.wait_for_function("document.getElementById('sync-str-body')?.textContent.includes('14-16-17-17')")
 assert '0' in page.locator('#sync-str-body').inner_text()
 page.evaluate("filterSyncSTR('DYS464')")
 assert page.locator('#sync-str-body tr').count()==1
 page.evaluate("addSyncComparison()")
 assert '14-16-17-17' in page.locator('#sync-str-comparison').inner_text()
 assert page.evaluate("getRegionTotals('Port Said').pool.some(s=>s.id===-990099001)")
 assert page.evaluate("buildRawTree(treeFilteredSamples()).count>0")
 page.evaluate("modernSamples=modernSamples.filter(s=>s.id!==-990099001)")
 print('Synthetic STR search, comparison, terminal-only tree and regional statistics: passed')
 page.evaluate("modernSamples.push({id:-990099002,__uid:'synthetic-count-test',__sourceType:'modern',name:'SYNTHETIC COUNT TEST ONLY',kit_number:'990099002',governorate:'Port Said',y_dna:'J-TEST1',test_type:'Big Y-700',test_status:'confirmed_big_y'});syncCountryCounts=[{id:-1,namespace:'ftdna',node_label:'J-TEST1',country_code:'EG',reported_count:9,count_scope:'inclusive',population:'ftdna_big_y',observed_at:'2026-11-04T00:00:00Z',source_url:'https://example.org/synthetic-count',snp_path:[]}];renderTree()")
 page.locator('.phylo-evidence[data-node-label="J-TEST1"]').evaluate('(d)=>d.open=true')
 page.wait_for_selector('.tree-country-evidence')
 text=page.locator('.tree-country-evidence').inner_text()
 print('Synthetic country-count evidence:',text)
 assert '9 reported' in text and '1 matching public ID(s)' in text and '8 arithmetically unidentified' in text
 assert page.evaluate("modernSamples.filter(s=>s.id===-990099002).length") == 1
 page.evaluate("modernSamples=modernSamples.filter(s=>s.id!==-990099002);syncCountryCounts=[];renderTree()")
 print('Nine source counts + one identified kit: no fake tester rows, arithmetic remainder eight')
 print('Errors',errors)
 print('API',api)
 assert not errors
 browser.close()
