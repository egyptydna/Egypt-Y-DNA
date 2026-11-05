"""Protected editor UI using exclusively synthetic fixtures; no real auth mail."""
from pathlib import Path
# Reuse only the synthetic public-data router, never the other test's actions.
base=Path(__file__).with_name('browser_profile_details.py').read_text().split('with sync_playwright() as p:')[0]
exec(compile(base,str(Path(__file__).with_name('browser_profile_details.py')),'exec'))
import copy,uuid
signed=False;calls=[];journal=[];versions=10
modern=copy.deepcopy(samples)
for r in modern:r['owner_active']=True
collected=[{'record_key':'a'*64,'name':'Synthetic collected participant','y_dna':'E-TEST1','governorate':None,'owner_active':True,'tree_path':[],'snp_path':[],'ancestor_name':'Synthetic ancestor','origin_raw':'','sheet_name':'Synthetic','row_number':2}]
def rows_for(kind):return modern if kind=='modern' else collected if kind=='collected' else []
def wrap(row,kind):return dict(row,__kind=kind,__key=str(row.get('record_key',row.get('id'))),__version='v'+str(row.get('_version',1)))
def reply(route,data,status=200):route.fulfill(status=status,content_type='application/json',body=json.dumps(data))
def owner_router(route):
 global signed,versions
 u=urlsplit(route.request.url);table=unquote(u.path.rsplit('/',1)[-1])
 if u.netloc=='fixture.invalid':signed=u.path=='/login';reply(route,{});return
 if '.supabase.co' in u.netloc and '/rpc/ydna_editor_' in u.path:
  if not signed:reply(route,{'message':'Administrator sign-in required'},403);return
  body=route.request.post_data_json or {};calls.append((table,body))
  if table=='ydna_editor_context':reply(route,{'administrator':True});return
  if table=='ydna_editor_history':reply(route,journal[::-1]);return
  kind=body.get('p_kind',body.get('p_keep_kind','modern'));rows=rows_for(kind)
  if table=='ydna_editor_list':
   query=body.get('p_query','').lower();gov=body.get('p_governorate','');visibility=body.get('p_visibility','active')
   selected=[r for r in rows if (not query or query in json.dumps(r).lower()) and (not gov or (r.get('governorate') or '—')==gov) and (visibility=='all' or r.get('owner_active',True)==(visibility=='active'))]
   offset=body.get('p_offset',0);reply(route,{'rows':[wrap(r,kind) for r in selected[offset:offset+60]],'total':len(selected)});return
  row=next((r for r in rows if str(r.get('record_key',r.get('id')))==body.get('p_key',body.get('p_keep_key'))),None)
  action='update'
  if table=='ydna_editor_save':
   if row is None:row={'id':max(r['id'] for r in modern)+1,'owner_active':True};modern.append(row);action='create'
   row.update(body['p_patch'])
  elif table=='ydna_editor_visibility':row['owner_active']=body['p_active'];action='restore' if body['p_active'] else 'remove'
  elif table=='ydna_editor_merge':
   assert body['p_confirm'] is True and len(body['p_reason'])>=5
   other=next(r for r in rows_for(body['p_other_kind']) if str(r.get('record_key',r.get('id')))==body['p_other_key']);other['owner_active']=False;action='merge'
  elif table=='ydna_editor_undo':reply(route,{});return
  versions+=1;row['_version']=versions
  journal.append({'id':body['p_request'],'action':action,'kind':kind,'record_key':str(row.get('id',row.get('record_key'))),'reason':body.get('p_reason',''),'created_at':now,'undone_at':None})
  reply(route,{'kind':kind,'key':str(row.get('id',row.get('record_key'))),'version':'v'+str(versions),'data':row});return
 if '.supabase.co' in u.netloc and table in ('Modern_published_samples','ydna_uploaded_profiles'):
  reply(route,[r for r in (modern if table=='Modern_published_samples' else collected) if r.get('owner_active',True)]);return
 route_handler(route)

with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 page=b.new_page(viewport={'width':1440,'height':1000});page.route('**/*',owner_router);page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('https://egyptydna.github.io/Egypt-Y-DNA/',wait_until='networkidle',timeout=120000)
 page.wait_for_function('modernSamples.length===2 && collectedSamples.length===1')
 assert page.locator('#stats-grid .region-card').count()==28
 assert page.locator('link[rel=icon]').get_attribute('href').endswith('.svg')
 assert page.locator('meta[property="og:image"]').get_attribute('content').endswith('/assets/giza-hero.jpg')
 page.evaluate("""window.syntheticSigned=false;_sb.auth.getUser=async()=>({data:{user:window.syntheticSigned?{id:'fixture-owner'}:null}});_sb.auth.signInWithPassword=async()=>{await fetch('https://fixture.invalid/login');window.syntheticSigned=true;return {data:{user:{id:'fixture-owner'}},error:null}};_sb.auth.signOut=async()=>{await fetch('https://fixture.invalid/logout');window.syntheticSigned=false;return {error:null}};_sb.auth.signUp=async()=>({data:{user:null},error:null});""")
 page.locator('#nav-admin').click();assert page.locator('#owner-login').is_visible();assert not page.locator('#owner-workspace').is_visible()
 page.locator('#owner-email').fill('owner@example.invalid');page.locator('#owner-password').fill('synthetic-password-only');page.locator('#owner-auth-form button[type=submit]').click()
 page.wait_for_selector('#owner-workspace:visible');page.wait_for_selector('#owner-rows [data-edit]')
 page.locator('#owner-new').click();page.locator('#owner-editor-dialog [name=name]').fill('New synthetic participant');page.locator('#owner-editor-dialog [name=kit_number]').fill('990000909');page.locator('#owner-editor-dialog [name=y_dna]').fill('E-OWNERFIXTURE');page.locator('#owner-editor-dialog [name=governorate]').select_option('Port Said');page.locator('#owner-editor-dialog [type=checkbox]').check();page.locator('#owner-save-form [type=submit]').click()
 page.wait_for_function("document.querySelector('#owner-rows').textContent.includes('New synthetic participant')")
 row=page.locator('#owner-rows tr').filter(has_text='New synthetic participant');row.locator('[data-edit]').click();page.locator('#owner-editor-dialog [name=governorate]').select_option('New Valley');page.locator('#owner-editor-dialog [type=checkbox]').check();page.locator('#owner-save-form [type=submit]').click();page.wait_for_function("document.querySelector('#owner-rows').textContent.includes('New Valley')")
 row=page.locator('#owner-rows tr').filter(has_text='New synthetic participant');row.locator('[data-visibility]').click();page.locator('#owner-editor-dialog [name=reason]').fill('Synthetic removal');page.locator('#owner-editor-dialog [type=submit]').click();page.wait_for_function("!document.querySelector('#owner-rows').textContent.includes('New synthetic participant')")
 page.locator('#owner-visibility').select_option('hidden');page.wait_for_selector('#owner-rows [data-visibility]');page.locator('#owner-rows [data-visibility]').first.click();page.locator('#owner-editor-dialog [name=reason]').fill('Synthetic restoration');page.locator('#owner-editor-dialog [type=submit]').click();page.wait_for_function("document.querySelector('#owner-admin-status').textContent.includes('wiederhergestellt')")
 page.locator('#owner-visibility').select_option('active');page.wait_for_selector('#owner-rows [data-select]');page.locator('#owner-rows [data-select]').first.check();page.locator('#owner-kind').select_option('collected');page.wait_for_function("document.querySelector('#owner-rows').textContent.includes('Synthetic collected participant')");page.locator('#owner-rows [data-select]').first.check();page.locator('#owner-merge').click();assert page.locator('.owner-merge-preview article').count()==2;page.locator('#owner-editor-dialog [name=reason]').fill('Owner confirmed same synthetic participant');page.locator('#owner-editor-dialog [name=confirmed]').check();page.locator('#owner-editor-dialog [type=submit]').click();page.wait_for_function("document.querySelector('#owner-admin-status').textContent.includes('zusammengeführt')")
 page.locator('#owner-history').click();page.wait_for_selector('.owner-history article');assert page.locator('.owner-history article').count()>=5;page.locator('#owner-editor-dialog .owner-dialog-close').click()
 page.locator('#owner-kind').select_option('modern');page.wait_for_selector('#owner-rows [data-edit]')
 for width in (1440,390):
  page.set_viewport_size({'width':width,'height':900});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');page.screenshot(path=str(root/'reports'/f'owner-admin-{width}.png'))
 page.locator('#owner-signout').click();page.wait_for_selector('#owner-login:visible');assert not page.locator('#owner-workspace').is_visible()
 assert not errors,errors
 print(json.dumps({'ownerUI':'passed','loginAndSignout':True,'createEditRemoveRestoreMergeHistory':True,'all27GovernoratesAndUnassigned':True,'desktopAndMobile':True,'protectedRPCCalls':len(calls),'pageErrors':errors}))
 b.close()
