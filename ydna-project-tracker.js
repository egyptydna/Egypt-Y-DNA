(function(root){
  'use strict';
  const escape=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const count=v=>Number.isSafeInteger(v)&&v>=0?v:0;
  function safeProjectURL(value){
    try{const u=new URL(value);return u.protocol==='https:'&&!u.username&&!u.password&&
      ['familytreedna.com','www.familytreedna.com'].includes(u.hostname)&&/^\/(public|groups)\/[^/]+/i.test(u.pathname)?u.href:null;}catch{return null;}
  }
  function date(value){const d=new Date(value);return value&&!isNaN(d)?d.toLocaleString(undefined,{timeZone:'UTC',year:'numeric',month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'})+' UTC':'Not yet saved';}
  function summaryHTML(status){
    const s=status.summary||{},p=s.projectSearch||{},d=s.projectDirectory||{};
    const stale=status.last_saved_at&&Date.now()-Date.parse(status.last_saved_at)>3*3600000;
    const state=status.state==='failed'?'Last tracking save failed; previous evidence retained.':stale?'The saved tracker is older than three hours. Scheduled checks may be delayed.':'Hourly server checks · bounded, resumable partial coverage';
    const metrics=[[d.trackedProjects,'Catalogued projects'],[d.projectsWithSavedEvidence,'With saved evidence'],[p.queued,'Pending search targets'],[p.checkedTargets,'Targets checked against saved evidence'],[p.exactKitMatches,'Kits confirmed in additional projects'],[p.anonymousLineageTargets,'Anonymous lineage searches']];
    const sourceRows=(s.sourcePartialRuns||[]).map(x=>`<tr><td>${escape(x.id)}</td><td>${escape(x.status)}</td><td>${count(x.records)}</td></tr>`).join('');
    return `<div class="project-tracker-top"><h2>Project tracking</h2><button type="button" class="ctrl-btn" data-project-refresh>Check saved status</button></div>
      <p class="${status.state==='failed'||stale?'project-error':''}">${escape(state)}</p>
      <p>Last attempt: ${escape(date(status.last_attempt_at))} · Last saved: ${escape(date(status.last_saved_at))}</p>
      <div class="project-tracker-metrics">${metrics.map(([n,label])=>`<div><strong>${count(n).toLocaleString()}</strong><span>${label}</span></div>`).join('')}</div>
      <p>${count(p.checkedProjectViews).toLocaleString()} saved project checks · ${count(p.permissionNeededProjectViews).toLocaleString()} checks awaiting provider permission · ${count(p.lineageCandidateProjectViews).toLocaleString()} lineage candidates without an identity link.</p>
      <p>${count(d.permissionNeededProjects).toLocaleString()} catalogued projects have no verified saved results here. Directory entries alone do not establish coverage or memberships.</p>
      <p>Project membership requires an exact public kit match. Anonymous branch increases remain anonymous. Unchecked projects, restricted sources and temporary failures are never a complete census.</p>
      <details><summary>Projects & membership evidence</summary><p>These are dated, saved public project records. A saved match does not mean the provider was checked live today.</p><input class="project-tracker-filter" aria-label="Filter tracked projects" placeholder="Filter projects" data-project-filter><div class="project-tracker-scroll" data-project-table>Loading project list…</div></details>
      <details><summary>Source checks in the latest import</summary><p>Importer: ${escape(s.sourceRun?.status||'No source run saved')} · ${escape(date(s.sourceRun?.finishedAt))}. Restricted sources were not fetched. Source dates remain attached to each profile.</p>
      <div class="project-tracker-scroll"><table><thead><tr><th>Source</th><th>Result</th><th>Records read</th></tr></thead><tbody>${sourceRows||'<tr><td colspan="3">No source report saved yet.</td></tr>'}</tbody></table></div>
      <p><a href="https://github.com/egyptydna/Egypt-Y-DNA/actions/workflows/ydna-sync.yml" target="_blank" rel="noopener">Automatic checks</a> · <a href="https://github.com/egyptydna/Egypt-Y-DNA/blob/main/docs/PROJECT-TRACKING.md" target="_blank" rel="noopener">Coverage & methodology</a></p></details>`;
  }
  const api={summaryHTML,safeProjectURL,count,escape};
  if(typeof module==='object'){module.exports=api;return;}
  root.YDNAProjectTracker=api;
  let saved=null,projects=[],memberships=[],inFlight=null,metadataPromise=null;
  let catalogAvailable=false,membershipsAvailable=false;
  let catalogQuery='',catalogPage=0,catalogRequest=0,catalogTimer;
  let renderedStale=false;
  const panel=()=>document.getElementById('project-tracker-panel');
  function projectTable(query=''){
    const target=panel()?.querySelector('[data-project-table]');if(!target)return;
    if(!catalogAvailable){target.textContent='Project list temporarily unavailable; the saved summary is retained.';return;}
    const totals=new Map();for(const m of memberships)totals.set(m.project_key,(totals.get(m.project_key)||0)+1);
    const shown=projects;
    target.innerHTML=`<table><thead><tr><th>Project</th><th>Saved exact memberships</th><th>Source evidence last seen</th><th>Coverage</th></tr></thead><tbody>${shown.map(p=>{
      const url=safeProjectURL(p.source_url);return `<tr><td>${url?`<a href="${escape(url)}" target="_blank" rel="noopener">${escape(p.name)}</a>`:escape(p.name)}</td><td>${membershipsAvailable?totals.get(p.project_key)||0:'Unavailable'}</td><td>${p.last_evidence_at?escape(date(p.last_evidence_at)):'No saved result evidence'}</td><td>${p.access_status==='saved_evidence'?'Saved public evidence':p.access_status==='permission_needed'?'Direct access requires permission':'Archived directory entry · not live checked'}</td></tr>`;
    }).join('')||'<tr><td colspan="4">No matching project.</td></tr>'}</tbody></table><p>Page ${catalogPage+1} · Up to 100 entries per page.</p><button class="ctrl-btn" data-project-prev ${catalogPage?'':'disabled'}>Previous</button> <button class="ctrl-btn" data-project-next ${projects.length===100?'':'disabled'}>Next</button>`;
    target.querySelector('[data-project-prev]').onclick=()=>loadCatalog(catalogQuery,catalogPage-1);
    target.querySelector('[data-project-next]').onclick=()=>loadCatalog(catalogQuery,catalogPage+1);
  }
  async function loadCatalog(query='',page=0){
    const request=++catalogRequest;
    try{
      let q=_sb.from('ydna_project_catalog').select('project_key,name,source_url,last_evidence_at,access_status').order('project_key');
      if(query)q=q.ilike('name','%'+query.replace(/[\\%_]/g,'\\$&')+'%');
      const result=await q.range(page*100,page*100+99);
      if(result.error)throw Error('catalog unavailable');if(request!==catalogRequest)return;
      projects=result.data;catalogAvailable=true;catalogQuery=query;catalogPage=page;projectTable();
    }catch{if(request===catalogRequest){const target=panel()?.querySelector('[data-project-table]');if(target)target.textContent='Project list temporarily unavailable. The saved summary and profiles are retained.';}}
  }
  function render(){
    const p=panel();if(!p||!saved)return;p.innerHTML=summaryHTML(saved);projectTable();p.querySelector('[data-project-refresh]').onclick=()=>load(true);const input=p.querySelector('[data-project-filter]');input.value=catalogQuery;input.oninput=e=>{const query=e.target.value;clearTimeout(catalogTimer);catalogTimer=setTimeout(()=>loadCatalog(query),300);};
    renderedStale=Boolean(saved.last_saved_at&&Date.now()-Date.parse(saved.last_saved_at)>3*3600000);
    const home=document.getElementById('project-tracker-dashboard');
    if(home){const d=saved.summary?.projectDirectory||{};home.innerHTML=`<strong>Automatic project tracking</strong><p>${count(d.trackedProjects)} catalogued projects · ${count(d.exactMemberships)} saved exact memberships · Last saved ${escape(date(saved.last_saved_at))}. Partial source coverage.</p><button class="ctrl-btn" type="button">Open project tracking & sources</button>`;home.querySelector('button').onclick=()=>{showSection('ytree');panel()?.scrollIntoView({block:'start',behavior:'smooth'});};}
  }
  async function load(manual=false){
    if(inFlight)return inFlight;
    inFlight=(async()=>{
      try{
        const r=await _sb.from('ydna_project_tracking_status').select('last_attempt_at,last_saved_at,state,summary').eq('id',true).single();
        if(r.error||!r.data)throw Error('status unavailable');
        const changed=saved?.last_saved_at&&saved.last_saved_at!==r.data.last_saved_at;
        const stale=Boolean(r.data.last_saved_at&&Date.now()-Date.parse(r.data.last_saved_at)>3*3600000);
        if(!saved||changed||manual||saved.last_attempt_at!==r.data.last_attempt_at||saved.state!==r.data.state||stale!==renderedStale){saved=r.data;render();if(changed){const p=document.createElement('p');p.textContent='A newer saved check is available. Reload the page to update profiles and evidence.';const b=document.createElement('button');b.className='ctrl-btn';b.textContent='Reload latest profiles';b.onclick=()=>location.reload();p.append(' ',b);panel()?.append(p);}}
      }catch{
        const p=panel();if(p){if(saved){render();const note=document.createElement('p');note.className='project-error';note.textContent='Status temporarily unavailable. The last displayed check is retained.';p.prepend(note);}else p.innerHTML='<p class="project-error">Project tracking status is temporarily unavailable. Existing archive profiles remain available.</p>';}
      }finally{inFlight=null;}
    })();return inFlight;
  }
  root.loadProjectTrackingMetadata=async function(){
    if(metadataPromise)return metadataPromise;
    metadataPromise=(async()=>{
      const paginate=async(table,columns)=>{const rows=[];for(let offset=0;offset<100000;offset+=1000){let q=_sb.from(table).select(columns).order(table==='ydna_project_catalog'?'project_key':'sample_id');if(table==='ydna_project_memberships')q=q.order('project_key');const r=await q.range(offset,offset+999);if(r.error)throw Error('Project metadata unavailable');rows.push(...r.data);if(r.data.length<1000)return rows;}throw Error('Project metadata limit');};
      const results=await Promise.allSettled([
        loadCatalog(),
        paginate('ydna_project_memberships','sample_id,project_key'),
        paginate('ydna_project_profile_activity','sample_id,new_until')]);
      if(results[1].status==='fulfilled'){memberships=results[1].value;membershipsAvailable=true;}
      if(results[2].status==='fulfilled'){
        const dates=new Map(results[2].value.map(a=>[a.sample_id,a.new_until]));
        for(const s of modernSamples){const times=(s.__linked_sample_ids||[s.id]).map(id=>dates.get(id)).filter(Boolean).sort();s.__new_until=times.at(-1)||null;}
      }
      render();await load();
    })();return metadataPromise;
  };
  document.addEventListener('DOMContentLoaded',()=>{
    const hero=document.querySelector('#section-home .dashboard-pyramid-hero');
    if(hero){const box=document.createElement('section');box.id='project-tracker-dashboard';box.className='project-tracker';box.setAttribute('aria-label','Automatic project tracking');box.textContent='Loading project tracking status…';hero.after(box);}
    load();setInterval(()=>{if(!document.hidden)load();},60000);
    document.addEventListener('visibilitychange',()=>{if(!document.hidden)load();});
  });
})(typeof window==='object'?window:globalThis);
