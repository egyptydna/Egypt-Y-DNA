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
samples=[{'id':1,'name':'Synthetic profile','kit_number':'990001','test_type':'Big Y-700','y_dna':'E-TEST1','full_snp_path':'Y-Adam>E-M35>E-M78>E-V13>E-CTS1>E-TEST1','mt_dna':'U3b3d2a','full_mtDNA_path':'mt-Eve>L>L3>N>R>U>U3>U3b>U3b3d2a','governorate':'Sūhāj','sync_visibility':'public'},
 {'id':2,'name':'Synthetic baseline','kit_number':'—','yfull_id':'YF990002','test_type':'YFull sequencing','y_dna':'J-TEST2','full_snp_path':'Y-Adam>J-M267>J-TEST2','mt_dna':'H1c','full_mtDNA_path':'mt-Eve>L>L3>N>R>H>H1>H1c','governorate':'—','sync_visibility':'public'}]
cache={}
def route_handler(route):
 global status_failed
 url=route.request.url;u=urlsplit(url)
 if '.supabase.co' in u.netloc:
  table=unquote(u.path.rsplit('/',1)[-1]);q=parse_qs(u.query)
  data=[]
  if table=='Modern_published_samples':data=samples
  elif table=='Modern_study_samples':data=[{'id':93,'name':'Synthetic study','sample_id':'STUDY93','y_dna':'E-STUDY','full_snp_path':'Y-Adam>E-M35>E-M78>E-V13>E-STUDY','mt_dna':'U3','full_mtDNA_path':'mt-Eve>L>L3>N>R>U>U3','study_reference':'Synthetic permitted publication'}]
  elif table=='ydna_uploaded_profiles':data=[{'record_key':'a'*64,'name':'Synthetic upload','y_dna':'E-TEST1','governorate':'Fixture governorate','country_code':'EG','tree_path':['E-M35','E-M78','E-V13','E-CTS1','E-TEST1'],'snp_path':['E-V13','E-CTS1','E-TEST1'],'sheet_name':'Synthetic fixture','row_number':2}]
  elif table=='Ancient_published_samples':data=[{'id':91,'name':'Synthetic ancient','sample_id':'ANCIENT91','y_dna':'E-CTS1','full_snp_path':'Y-Adam>E-M35>E-M78>E-V13>E-CTS1','mt_dna':'U3','full_mtDNA_path':'mt-Eve>L>L3>N>R>U>U3','site':'Fixture site','period':'Published date range','study_reference':'Fixture publication','Description':'Published archaeological context'}]
  elif table=='ancient_related_samples':data=[{'id':92,'name':'Synthetic related','sample_id':'RELATED92','y_dna':'E-ANCIENT','full_snp_path':'Y-Adam>E-M35>E-M78>E-V13>E-CTS1>E-ANCIENT','country':'Austria','mt_dna':'H2','full_mtdna_path':'mt-Eve>L>L3>N>R>H>H2','period':'Fixture period','study_reference':'Fixture publication'}]
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
  elif table=='ydna_sync_observations':
   data=[{'id':1,'sample_id':1,'namespace':'ftdna','external_id':'990001','is_current':True,'published':True,'last_seen_at':now,'project':'Fixture A','test_type':'Big Y-700','country':'Egypt','payload':{'source_id':'fixture','source_url':'https://example.org/fixture-a','project':'Fixture A','test_type':'Big Y-700','y_dna':'E-TEST1','snp_path':['E-V13','E-CTS1','E-TEST1'],'str_markers':[{'marker':'DYS425','source_label':'DYS425','position':0,'value':'0'},{'marker':'DYS464','source_label':'DYS464','position':1,'value':'14-16-17-17'}]}},
    {'id':2,'sample_id':2,'namespace':'yfull','external_id':'YF990002','is_current':True,'published':True,'last_seen_at':now,'project':'','test_type':'YFull sequencing','payload':{'source_url':'https://example.org/fixture-yfull','str_markers':[],'y_dna':'J-TEST2'}}]
   data[0]['branch_age']={'kind':'lineage_estimate','dna_type':'y','unit':'ybp','node_label':'J-COUNT2','formed':{'estimate':6500},'tmrca':{'estimate':4200},'observed_at':now,'source_url':'https://discover.familytreedna.com/y-dna/J-COUNT2/time-tree'}
   data[0]['payload']['branch_age']=data[0]['branch_age']
   if 'sample_id' in q:
    selected=1 if '1' in q['sample_id'][0] else 2;data=[r for r in data if r['sample_id']==selected]
  elif table=='ydna_sync_tree_releases':data=[{'source_id':'yfull-github','release_key':'synthetic-release','version':'fixture','published_at':now,'checked_at':now,'source_url':'https://github.com/YFullTeam/YTree','license_url':'https://github.com/YFullTeam/YTree/blob/master/LICENSE.md','attribution':'Synthetic reference fixture','node_count':8,'selected_node_count':8,'metadata':{'matches':{}}}]
  elif table=='ydna_sync_official_tree_nodes':
   parents={'Y-Adam':None,'E-V13':'Y-Adam','E-CTS1':'E-V13','E-TEST1':'E-CTS1','E-ANCIENT':'E-CTS1','E-STUDY':'E-V13','J-M267':'Y-Adam','J-TEST2':'J-M267'}
   data=[{'label':label,'parent_label':parent,'aliases':[],'snp_groups':[],'age_estimates':{'unit':'ybp','formed':{'estimate':7000,'low':6500,'high':7500},'tmrca':{'estimate':5000,'low':4500,'high':5500}}} for label,parent in parents.items()]
  elif table=='ydna_sync_runs':data=[{'started_at':now}]
  elif table=='ydna_tracker_status':data={'provider':'ftdna','snapshot_id':'synthetic','checked_at':now,'primary_status':'ok'}
  elif table=='ydna_tracker_snapshots':
   record={'id':'synthetic','source_id':'fixture','observed_at':now,'total_count':5,'nodes':[{'label':'E-TEST1','count':3,'path':['E-M35','E-M78','E-V13','E-CTS1','E-TEST1'],'path_source_url':'https://example.org/path'},{'label':'J-COUNT2','count':2,'path':['J-M267','J-COUNT2'],'path_source_url':'https://example.org/path'}],'source_url':'https://example.org/counts','details':{}}
   data=record if 'id' in q else [record]
  elif table=='ydna_tracker_changes':data=[]
  route.fulfill(status=200,content_type='application/json',body=json.dumps(data));return
 if u.netloc=='egyptydna.github.io':
  path=root/(u.path.split('/Egypt-Y-DNA/',1)[-1] or 'index.html')
  if path.is_file():route.fulfill(path=str(path));return
  route.fulfill(status=404,body='');return
 if '.vercel.app' in u.netloc:errors.append('Unexpected Vercel request');route.abort();return
 if u.netloc!='cdn.jsdelivr.net':route.abort();return
 try:
  if url not in cache:
   with urllib.request.urlopen(url,timeout=30) as r:cache[url]=(r.read(),r.headers.get('Content-Type','application/javascript'))
  body,kind=cache[url];route.fulfill(status=200,content_type=kind,body=body)
 except Exception:route.abort()

with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':1440,'height':1000})
 page.add_init_script("Object.defineProperty(navigator,'clipboard',{value:{writeText:async(value)=>{window.fixtureClipboard=value}}})")
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
 # Y-DNA chart -> profile popup -> original STRs and CSV.
 page.evaluate("document.getElementById('treeTestStatus').value='';setCountryTreeMode('profiles');openTreeBreakdownModal('modern',breakdownGroupForSample(modernSamples[0],'y'),'y')")
 page.locator('#kits-container [data-profile-uid]').first.click()
 page.wait_for_selector('#sample-detail-modal.active')
 page.wait_for_selector('#sync-str-body tr')
 assert page.locator('#sample-modal-path').inner_text()=='E-V13 > CTS1 > TEST1'
 assert 'Y-Adam' not in page.locator('#kits-container').inner_text()
 assert page.locator('#sync-str-body tr').count()==2
 assert '0' in page.locator('#sync-str-body').inner_text()
 assert page.locator('#sync-str-search').count()==0
 page.get_by_role('button',name='Copy STRs',exact=True).click()
 page.wait_for_function("window.fixtureClipboard")
 assert page.evaluate("window.fixtureClipboard")=="DYS425\t0\nDYS464\t14-16-17-17"
 assert 'copied' in page.locator('#sync-str-copy-status').inner_text()
 with page.expect_download() as download:
  page.get_by_role('button',name='Download STRs & evidence (CSV)').click()
 assert download.value.suggested_filename=='public-profile-STR-evidence.csv'
 page.evaluate('closeSampleModal(null);closeModal(null)')
 print('Y-DNA chart popup, terminal path, STR table and CSV passed',flush=True)
 # Maternal chart opens its own path even though current tree type is still Y.
 page.evaluate("openMtHomeModal(mtHaplo(modernSamples[0].mt_dna,modernSamples[0].full_mtDNA_path))")
 page.locator('#kits-container .profile-open-details').first.click()
 page.wait_for_selector('#sample-detail-modal.active')
 assert page.locator('#sample-modal-path').inner_text()=='U3 > U3b > U3b3d2a'
 assert page.locator('#sample-modal-path-label').text_content()=='Terminal mtDNA path'
 page.evaluate('closeSampleModal(null);closeModal(null)')
 print('mtDNA chart popup uses the maternal terminal path',flush=True)
 # Provider filters and popup action for a synthetic newly received YFull record.
 page.evaluate("modernSamples[1].__new_until='2099-01-01T00:00:00Z';renderTrackedResults()")
 page.locator('#nav-new').click();page.select_option('#tracked-provider','yfull')
 assert page.locator('#tracked-results-list article').count()==1
 page.locator('#tracked-results-list button').click()
 page.wait_for_selector('#sample-detail-modal.active')
 page.wait_for_function("document.getElementById('sample-sync-details').textContent.includes('No STR values have been published')")
 assert page.get_by_role('button',name='Download STRs & evidence (CSV)').is_disabled()
 page.evaluate('closeSampleModal(null)')
 page.select_option('#tracked-provider','ftdna')
 assert page.locator('#tracked-results-list article').count()==1
 page.set_viewport_size({'width':390,'height':844})
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
 page.locator('#nav-ytree').click();page.evaluate("setCountryTreeMode('profiles')")
 assert page.locator('#tree-inner .phylo-reference-bar').count()==1
 assert page.locator('#tree-inner .phylo-node-name').count()>2
 color=page.locator('#tree-inner .phylo-node .phylo-node-name').first.evaluate('(e)=>getComputedStyle(e).backgroundColor')
 assert color=='rgb(37, 139, 21)',color
 for tree in ['y','mt']:
  page.evaluate("showSection('"+('ytree' if tree=='y' else 'mtree')+"');"+("setCountryTreeMode('profiles')" if tree=='y' else ''))
  assert page.locator('#tree-inner .phylo-root').get_attribute('data-tree')==tree
  if tree=='y':
   assert page.locator('#tree-inner .phylo-age').count()>0
   assert 'formed 7000 ybp, TMRCA 5000 ybp' in page.locator('#tree-inner').inner_text()
  else:assert page.locator('#tree-inner .phylo-age').count()==0
  alignment=page.locator('#tree-inner .phylo-root').evaluate("e=>{const n=e.querySelector(':scope > .phylo-node-row > .phylo-node-name'),u=e.querySelector(':scope > ul');return Math.abs(n.getBoundingClientRect().left-u.getBoundingClientRect().left)}")
  assert alignment<=1,alignment
  assert page.locator('#tree-inner .phylo-sample').count()==(6 if tree=='y' else 5)
  assert page.locator('#tree-inner .phylo-sample-country').filter(has_text='🇪🇬').count()==(5 if tree=='y' else 4)
  assert page.locator('#tree-inner .phylo-sample[data-kind=related] .phylo-sample-country').inner_text()=='🇦🇹 AT'
  for kind in ['study','ancient','related']:
   row=page.locator(f'#tree-inner .phylo-sample[data-kind={kind}] > .tree-sample-card').first
   assert row.evaluate('(e)=>getComputedStyle(e).borderLeftWidth')=='0px'
   assert row.locator('.phylo-cohort-symbol').count()==1
   assert row.is_visible()
  page.locator('#tree-inner .tree-sample-card').first.click()
  assert page.evaluate('sampleModalTreeType')==tree
  page.evaluate('closeSampleModal(null)')
  for width,height in [(1440,1000),(390,844)]:
   page.set_viewport_size({'width':width,'height':height});page.locator('#tree-wrap').scroll_into_view_if_needed()
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
   out=root/'reports';out.mkdir(exist_ok=True);page.screenshot(path=str(out/f'profile-tree-{tree}-{width}.png'))
 # Anonymous counts still total five; known profile rows carry no dot identity.
 page.evaluate("showSection('ytree');setCountryTreeMode('ftdna')")
 assert page.locator('.country-result-dot').count()==5
 assert 'formed 6500 ybp, TMRCA 4200 ybp' in page.locator('#tree-inner').inner_text()
 ft_info=page.locator('#tree-inner .phylo-node-row').filter(has=page.locator('.phylo-node-name',has_text='J-COUNT2')).locator('summary').first
 ft_info.click();assert 'FTDNA' in page.locator('#tree-inner .phylo-evidence[open]').inner_text()
 group=page.locator('.country-known-profiles details').first
 assert group.evaluate('(e)=>e.open')
 group.locator('summary').click()
 page.wait_for_function("!document.querySelector('.country-known-profiles details').open")
 page.evaluate('renderTree()')
 assert not page.locator('.country-known-profiles details').first.evaluate('(e)=>e.open')
 page.locator('#btn-show-all-profiles').click()
 assert page.locator('.country-known-profiles details').first.evaluate('(e)=>e.open')
 assert page.locator('#tree-inner .tree-sample-card:visible').count()==6
 assert 'overlap unverified'  in page.locator('.country-known-profiles').first.inner_text()
 assert page.locator('.country-known-profiles .tree-sample-card').count()==6
 assert page.locator('#tree-inner .phylo-provider').filter(has_text='YFull').count()==1
 assert page.locator('#tree-inner .phylo-sample-test').first.evaluate('(e)=>getComputedStyle(e).backgroundColor')=='rgba(0, 0, 0, 0)'
 assert page.locator('#tree-pills [data-family=J1]').count()==1
 page.locator('#tree-pills [data-family=J1]').click()
 assert page.locator('#tree-inner .tree-sample-card').count()==1
 assert 'YF990002' in page.locator('#tree-inner').inner_text()
 assert page.locator('.country-result-dot').count()==2
 page.evaluate('treeReset()')
 assert page.locator('.country-result-dot').count()==5
 assert page.locator('#tree-inner .tree-sample-card').count()==6
 page.locator('#treeSearch').fill('TEST2');page.locator('#treeSearch').press('Enter')
 assert 'YF990002' in page.locator('#tree-inner').inner_text()
 page.evaluate('treeReset()')
 page.set_viewport_size({'width':1440,'height':700})
 page.evaluate("window.scrollTo(0,document.getElementById('tree-workbench').getBoundingClientRect().top+scrollY+120)")
 page.wait_for_function("Math.abs(document.getElementById('tree-workbench').getBoundingClientRect().top-document.querySelector('nav[aria-label=\"Primary navigation\"]').getBoundingClientRect().bottom)<2")
 assert page.locator('#tree-dock-search').is_visible()
 page.locator('#tree-dock-search').fill('TEST2');page.locator('.tree-dock-search button').click()
 assert 'YF990002' in page.locator('#tree-inner').inner_text()
 page.locator('#tree-workbench [data-tree-mode=full]').click()
 assert page.locator('#tree-workbench [data-tree-mode=full]').get_attribute('aria-pressed')=='true'
 page.evaluate("treeReset();setCountryTreeMode('profiles');treeSetHaplo('J1')")
 assert page.locator('#tree-pills').inner_text().find('E (')>=0
 page.evaluate("treeSetHaplo(null);showSection('archive')")
 page.select_option('#archiveSort','name')
 assert 'Synthetic baseline' in page.locator('#archive-body tr').first.text_content()
 page.locator('#archive-body .profile-name-link').first.click();page.wait_for_selector('#sample-detail-modal.active')
 page.evaluate("closeSampleModal(null);showSection('ancient')")
 page.locator('#ancient-body .profile-name-link').first.click();page.wait_for_selector('#sample-detail-modal.active')
 assert 'Published date range' in page.locator('#sample-modal-historical').inner_text()
 assert 'Fixture publication' in page.locator('#sample-modal-historical').inner_text()
 assert 'Published archaeological context' in page.locator('#sample-modal-description').inner_text()
 page.evaluate('closeSampleModal(null)')
 page.locator('#related-ancient-body .profile-name-link').first.click();page.wait_for_selector('#sample-detail-modal.active')
 assert 'Austria' in page.locator('#sample-modal-historical').inner_text()
 page.evaluate("closeSampleModal(null);showSection('ytree')")
 print('Combined tree includes uncounted YFull and intermediate ancient profiles; clade/SNP filters, archive sorting and both ancient popups passed',flush=True)
 page.evaluate("setCountryTreeMode('profiles')")
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
 print(json.dumps({'syntheticBrowser':'passed','desktopAndMobile':True,'pagedCatalogRequests':catalog_requests,'profileDetailsAndSTRs':True,'cohortFlagsAndSymbols':True,'stickySNPControls':True,'datedBranchAges':True,'manualGroupHiding':True,'separateDNATrees':True,'maternalPopupContext':True,'providerFilters':True,'anonymousSeparation':True,'statusFailureRetainsSummary':True,'pageErrors':len(errors)}))
 browser.close()
