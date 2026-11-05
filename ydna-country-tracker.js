let countryTreeMode='ftdna';
let countryTracker=null,countryTrackerStatus=null,countryTrackerHistory=[];
let countryTrackerLoading=null,countryTrackerError='',countryTrackerRoot=null;
let countryTreeFamily=null;
let showAnonymousCountryResults=false;
function toggleAnonymousCountryResults(value){showAnonymousCountryResults=Boolean(value);renderTree();}

const countryDate=value=>value?new Date(value).toLocaleString('en-GB',{timeZone:'UTC',dateStyle:'medium',timeStyle:'short'})+' UTC':'Not available';
const countryLink=(url,label)=>{try{const u=new URL(url);return u.protocol==='https:'?`<a href="${esc(u.href)}" target="_blank" rel="noopener noreferrer">${esc(label)}</a>`:'';}catch{return '';}};
function isCountryTree(){return currentTreeType==='y'&&countryTreeMode==='ftdna';}

async function loadCountryTracker(){
  if(countryTrackerLoading)return countryTrackerLoading;
  countryTrackerLoading=(async()=>{
    try{
      const status=await _sb.from('ydna_tracker_status').select('*').eq('provider','ftdna').maybeSingle();
      if(status.error||!status.data?.snapshot_id)throw Error('No verified tracker snapshot available');
      const [snapshot,history]=await Promise.all([
        _sb.from('ydna_tracker_snapshots').select('*').eq('id',status.data.snapshot_id).single(),
        _sb.from('ydna_tracker_snapshots').select('id,source_id,observed_at,total_count').order('observed_at',{ascending:false}).limit(8)
      ]);
      if(snapshot.error)throw Error('Snapshot unavailable');
      const root=YDNACountryTree.build(snapshot.data);
      countryTracker=snapshot.data;countryTrackerRoot=root;countryTrackerStatus=status.data;
      const ids=(history.data||[]).map(s=>s.id);
      const changes=ids.length?await _sb.from('ydna_tracker_changes').select('*').in('snapshot_id',ids).order('change_key').limit(150):{data:[]};
      countryTrackerHistory=(history.data||[]).map(s=>({...s,changes:(changes.data||[]).filter(c=>c.snapshot_id===s.id)}));
      countryTrackerError='';
    }catch(error){countryTrackerError='Tracker temporarily unavailable. Existing tester profiles remain available.';}
    if(document.getElementById('section-tree')?.classList.contains('active'))renderTree();
  })();
  return countryTrackerLoading;
}

function setCountryTreeMode(mode){
  countryTreeMode=['profiles','uploaded'].includes(mode)?mode:'ftdna';uploadedQuery='';
  countryTreeFamily=null;
  treeFocusPath=null;treeSearchTargetPath=null;treeSearchResultPath='';syncTextQuery='';treeHaploFilter=null;
  collapsedNodes.clear();resetRawTreeCache();
  document.getElementById('treeSearch').value='';
  document.getElementById('tree-result-path').classList.remove('active');
  if(countryTreeMode==='ftdna'){
    document.getElementById('treeTestStatus').value='';document.getElementById('treeGovernorate').value='';
  }
  renderTree();updateShareUrl({section:currentTreeType==='mt'?'mtree':'ytree'});
}

function renderCountryTrackerPanel(){
  if(isUploadedTree()){renderUploadedPanel();return;}
  const panel=document.getElementById('country-tracker-panel');
  panel.hidden=currentTreeType!=='y';if(panel.hidden)return;
  if(!countryTracker){panel.innerHTML=`<p>${esc(countryTrackerError||'Loading the Egyptian FTDNA result tracker…')}</p><button class="ctrl-btn" onclick="setCountryTreeMode('profiles')">Open tester profiles</button>`;loadCountryTracker();return;}
  const s=countryTracker,status=countryTrackerStatus,backup=s.source_id==='owner-observatory-export';
  const snapshots=countryTrackerHistory.map(h=>`<li><time>${esc(countryDate(h.observed_at))}</time> · ${h.total_count} results · ${h.source_id==='owner-observatory-export'?'Observatory backup':'Primary feed'}<ul>${h.changes.slice(0,15).map(c=>`<li>${esc(YDNACountryTree.changeLabel(c))}</li>`).join('')}${h.changes.length>15?'<li>Additional branch changes recorded in the tracker.</li>':''}</ul></li>`).join('');
  panel.innerHTML=`<div class="country-tracker-heading"><strong>Egypt · ${s.total_count} reported FTDNA results</strong><span>${backup?'Observatory backup':'Own tracker · public aggregate feed'}</span></div>
    <div class="country-tracker-dates">Source updated: ${esc(countryDate(s.observed_at))} · Last check: ${esc(countryDate(status.checked_at))}</div>
    <label class="country-anonymous-toggle"><input type="checkbox" ${showAnonymousCountryResults?'checked':''} onchange="toggleAnonymousCountryResults(this.checked)"> Show anonymous source-count rows</label><p>These are country totals published by FTDNA, without a kit-by-kit identity mapping. They can overlap with the samples below and are not additional identified people. The rows are hidden by default.</p>
    <p>Checked hourly on the server. Source publication can lag behind FTDNA. ${status.primary_status!=='ok'?'Primary feed unavailable; the last verified snapshot is retained.':''}</p>
    <details><summary>Tracker history & sources</summary><p>${countryLink(s.source_url,'Selected source snapshot')} · ${countryLink('https://egypt-ydna-observatory.kimoeln.chatgpt.site/archive?new=1','Observatory backup')} · ${countryLink('https://github.com/egyptydna/Egypt-Y-DNA/actions/workflows/ydna-tracker.yml','Server checks')}</p>
    <p>${esc(s.details.attribution||'FTDNA public country counts · owned Observatory archive')}. Counts represent published results; they do not establish individual identities or Big Y test types. The 622-result baseline is not presented as 622 newly discovered people.</p>
    ${s.details.backup_total_note?`<p>${esc(s.details.backup_total_note)}</p>`:''}
    <ol class="country-history">${snapshots}</ol></details>`;
  document.querySelector('#treeDataset option[value="ftdna"]').textContent=`Combined · FTDNA counts / YFull / archive`;
}

function updateCountryTreeControls(){
  const country=isUploadedTree(),select=document.getElementById('treeDataset');
  if(currentTreeType==='y')loadUploadedProfiles();
  document.getElementById('tree-dataset-control').hidden=currentTreeType!=='y';select.value=countryTreeMode;
  for(const id of ['btn-source-all','btn-modern','btn-study','btn-ancient','btn-related'])document.getElementById(id).hidden=country;
  document.getElementById('ydna-sync-filters').classList.toggle('hidden',country||currentTreeType==='mt');
  document.querySelector('#section-tree .related-reference-note').hidden=country;
  document.querySelector('#section-tree .tree-legend-chip').parentElement.hidden=country;
  renderCountryTrackerPanel();
}

function countryFamily(fact){
  return treeMajorGroup({y_dna:fact.label,full_snp_path:(fact.path||[]).join('>')});
}
function combinedCountryTree(family=countryTreeFamily){
  const facts=family?countryTracker.nodes.filter(n=>countryFamily(n)===family):countryTracker.nodes;
  const base=YDNACountryTree.build({...countryTracker,nodes:facts,total_count:facts.reduce((n,f)=>n+f.count,0)});
  const known=syncKnownTerminalPaths();
  const profiles=treeFilteredSamples(true).filter(s=>!family||treeMajorGroup(s)===family);
  const entries=profiles.map(sample=>{
    const placement=YDNASync.safePlacement(sample,syncOfficialRelease,syncOfficialNodes,syncTreeTopology,known);
    const chain=[];
    const path=parsePath(placement.path.join('>'),sample.y_dna).map(raw=>{
      const display=placement.version?canonicalHeadName(raw):normalizeDisplay(raw,chain);chain.push({display});return display;
    });
    return {sample,path};
  });
  return YDNACountryTree.overlay(base,entries);
}
function renderCountryTree(){
  if(!countryTracker&&countryTrackerError){countryTreeMode='profiles';renderTree();return;}
  if(countryTreeFamily===null&&treeHaploFilter)countryTreeFamily=treeHaploFilter;
  document.getElementById('official-tree-panel').innerHTML='';
  document.getElementById('tree-summary-grid').innerHTML='';document.getElementById('tree-stats').innerHTML='';
  const inner=document.getElementById('tree-inner'),pills=document.getElementById('tree-pills');
  if(!countryTracker){pills.innerHTML='';inner.innerHTML=`<p>${esc(countryTrackerError||'Loading verified country results…')}</p>`;return;}
  const root=combinedCountryTree();lastTreeRawRoot=root;
  const focused=YDNACountryTree.find(root,treeFocusPath)||root;
  const uploads=new Map();
  const sampleOptions=compactTreeOptions();
  const display=YDNACountryTree.compact(focused,treeMode==='full',new Set(uploads.keys()));
  document.getElementById('btn-tree-back').classList.toggle('hidden',focused===root);
  const families=[...new Set([...countryTracker.nodes.map(countryFamily),...treeFilteredSamples(true).map(treeMajorGroup)])].sort(YDNAProfiles.groupCompare);
  pills.innerHTML=`<button type="button" class="haplo-pill ${!countryTreeFamily?'on':''}" onclick="focusCountryFamily(null)">All groups</button>`+families.map(f=>`<button type="button" class="haplo-pill ${countryTreeFamily===f?'on':''}" data-family="${esc(f)}" onclick="focusCountryFamily(this.dataset.family)">${esc(YDNAProfiles.groupLabel(f))}</button>`).join('');
  const options={...sampleOptions,collapsed:collapsedNodes,names:n=>{
    const reference=YDNASync.officialPath({y_dna:n.display},syncOfficialRelease,syncOfficialNodes);
    return {primary:n.display,secondary:reference&&reference.label!==n.display?`YFull: ${reference.label} (v${reference.version} reference)`:''};
  },countLabel:n=>[n.count?`${n.count} reported FTDNA results`:null,n.profileCount?`${n.profileCount} samples`:null].filter(Boolean).join(' · '),
  counts:()=>'',aliases:()=>'',country:()=>'',age:treeBranchAgeText,ageTitle:treeBranchAgeTitle,
  hasEvidence:n=>{phyloNodeLookup.set(n.pathKey,n);return !!publishedBranchAge(n);},evidence:renderOfficialNodeInfo,
  sampleGroup:n=>n.samples.length?`<li class="country-known-profiles"><details ${treeProfileGroupOpen(n.pathKey+'|archive')?'open':''} data-profile-group="${esc(treeProfileGroupKey(n.pathKey+'|archive'))}" ontoggle="rememberTreeProfileGroup(this)"><summary>${n.samples.length} ${n.samples.length===1?'profile':'profiles'} · overlap unverified</summary><ul>${sortTreeProfiles(n.samples).map(s=>DNATreeView.sample(s,sampleOptions)).join('')}</ul></details></li>`:'',
  hasGroup:n=>uploads.has(n.display.toUpperCase()),
  group:n=>{
    const fromFile=uploads.get(n.display.toUpperCase())||[];
    return (showAnonymousCountryResults&&n.directCount?`<li class="country-result-group"><button class="country-result-button" data-branch="${esc(n.display)}" onclick="openCountryResult(this.dataset.branch)"><span class="country-result-dots" aria-hidden="true">${'<i class="country-result-dot"></i>'.repeat(n.directCount)}</span><span>🇪🇬 FTDNA country count · ${n.directCount}</span><span class="phylo-detail-hint">Count details ›</span></button></li>`:'')+
      (fromFile.length?`<li class="country-known-profiles uploaded-branch-profiles"><details ${treeProfileGroupOpen(n.pathKey+'|uploaded')?'open':''} data-profile-group="${esc(treeProfileGroupKey(n.pathKey+'|uploaded'))}" ontoggle="rememberTreeProfileGroup(this)"><summary>${fromFile.length} collected ${fromFile.length===1?'record':'records'}</summary><ul>${fromFile.map(uploadedProfileRow).join('')}</ul></details></li>`:'');
  }};
  inner.innerHTML=`<p class="combined-tree-note">${root.count} reported FTDNA results · ${root.profileCount} samples in this selection. Includes saved YFull, owner-collected, study and ancient samples. These totals can overlap and are never added together.</p>`+DNATreeView.node(display,options,true);
  if(!treeFocusPath&&!treeSearchResultPath){document.getElementById('tree-result-path').classList.remove('active');document.getElementById('tree-result-path').innerHTML='';}
  updateTreeSourceButtons();updateTreeFloatingToggle();
}
function focusCountryFamily(family){
  countryTreeFamily=family;treeHaploFilter=family;treeHaploFilterByType.y=family;
  treeFocusPath=null;treeSearchResultPath='';renderTree();updateShareUrl({section:'ytree'});
}
function searchCountryTree(query){
  if(isUploadedTree())return searchUploadedTree(query);
  if(!isCountryTree())return false;
  if(!countryTracker)return true;
  countryTreeFamily=null;treeHaploFilter=null;
  syncTextQuery='';treeSearchResultPath='';
  const root=combinedCountryTree(null),q=query.trim().toUpperCase();
  const exact=q?searchTreeExact(root,q):null;
  if(exact){treeFocusPath=exact.node.pathKey;collapsedNodes.clear();renderClickableTreePath(treeFocusPath);renderTree();updateShareUrl({section:'ytree'});requestAnimationFrame(()=>scrollTreeIntoView());return true;}
  if(q&&allTreeSamples().some(s=>matchSearchRow(s,query))){syncTextQuery=query;treeFocusPath=null;renderTree();return true;}
  if(q&&uploadedProfiles.some(s=>uploadedMatches(s,query))){countryTreeMode='uploaded';return searchUploadedTree(query);}
  treeFocusPath=null;treeSearchResultPath=q?`No saved SNP or profile found for ${query}`:'';
  renderTree();const bar=document.getElementById('tree-result-path');bar.textContent=treeSearchResultPath;bar.classList.toggle('active',!!q);return true;
}

function openCountryResult(label){
  const fact=countryTracker.nodes.find(n=>n.label===label);if(!fact)return;
  const profiles=YDNACountryTree.profilesByBranch(modernSamples).get(label.toUpperCase())||[];
  let dialog=document.getElementById('country-result-dialog');
  if(!dialog){dialog=document.createElement('dialog');dialog.id='country-result-dialog';document.body.append(dialog);}
  dialog.innerHTML=`<form method="dialog"><button class="ctrl-btn country-close">Close ×</button></form><h3>${esc(label)} · Egypt</h3>
    <p><strong>${fact.count} source-reported ${fact.count===1?'result':'results'} directly at this branch</strong></p>
    <p>The source publishes this count without a person-by-person mapping. The dots represent counted results; they have no invented kit numbers, names or test types.</p>
    <p>Published SNP path: ${esc(fact.path?.join(' → ')||'Terminal branch only; ancestry not published in this feed.')}</p>
    <p>Snapshot: ${esc(countryDate(countryTracker.observed_at))}</p>
    <p>${countryLink(countryTracker.source_url,'Count source')} · ${countryLink(fact.path_source_url,'Published path source')}</p>
    ${profiles.length?`<h4>Public samples at this branch</h4><p>Shown for reference. Their overlap with the source count is not established; they are not added to or subtracted from the total.</p><ul>${profiles.map(s=>`<li><button class="ctrl-btn" data-uid="${esc(s.__uid)}" onclick="document.getElementById('country-result-dialog').close();openSampleModalByUid(this.dataset.uid)">${esc(YDNASync.publicId(s)==='—'?YDNASync.displayName(s):YDNASync.publicId(s))}</button></li>`).join('')}</ul>`:''}`;
  dialog.showModal();
}
