let countryTreeMode='ftdna';
let countryTracker=null,countryTrackerStatus=null,countryTrackerHistory=[];
let countryTrackerLoading=null,countryTrackerError='',countryTrackerRoot=null;
let countryTreeFamily=null;

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
    <p>Checked hourly on the server. Source publication can lag behind FTDNA. ${status.primary_status!=='ok'?'Primary feed unavailable; the last verified snapshot is retained.':''}</p>
    <details><summary>Tracker history & sources</summary><p>${countryLink(s.source_url,'Selected source snapshot')} · ${countryLink('https://egypt-ydna-observatory.kimoeln.chatgpt.site/archive?new=1','Observatory backup')} · ${countryLink('https://github.com/egyptydna/Egypt-Y-DNA/actions/workflows/ydna-tracker.yml','Server checks')}</p>
    <p>${esc(s.details.attribution||'FTDNA public country counts · owned Observatory archive')}. Counts represent published results; they do not establish individual identities or Big Y test types. The 622-result baseline is not presented as 622 newly discovered people.</p>
    ${s.details.backup_total_note?`<p>${esc(s.details.backup_total_note)}</p>`:''}
    <ol class="country-history">${snapshots}</ol></details>`;
  document.querySelector('#treeDataset option[value="ftdna"]').textContent=`FTDNA results · ${s.total_count}`;
}

function updateCountryTreeControls(){
  const country=isCountryTree()||isUploadedTree(),select=document.getElementById('treeDataset');
  if(currentTreeType==='y')loadUploadedProfiles();
  document.getElementById('tree-dataset-control').hidden=currentTreeType!=='y';select.value=countryTreeMode;
  for(const id of ['btn-source-all','btn-modern','btn-study','btn-ancient','btn-related'])document.getElementById(id).hidden=country;
  document.getElementById('ydna-sync-filters').classList.toggle('hidden',country||currentTreeType==='mt');
  document.querySelector('#section-tree .related-reference-note').hidden=country;
  document.querySelector('#section-tree .tree-legend-chip').parentElement.hidden=country;
  renderCountryTrackerPanel();
}

function renderCountryTree(){
  document.getElementById('official-tree-panel').innerHTML='';
  document.getElementById('tree-summary-grid').innerHTML='';document.getElementById('tree-stats').innerHTML='';
  const inner=document.getElementById('tree-inner'),pills=document.getElementById('tree-pills');
  if(!countryTracker){pills.innerHTML='';inner.innerHTML=`<p>${esc(countryTrackerError||'Loading verified country results…')}</p>`;return;}
  const selected=countryTreeFamily?countryTracker.nodes.filter(n=>n.label.startsWith(countryTreeFamily+'-')):null;
  const root=selected?YDNACountryTree.build({...countryTracker,nodes:selected,total_count:selected.reduce((s,n)=>s+n.count,0)}):countryTrackerRoot;
  lastTreeRawRoot=root;
  const focused=YDNACountryTree.find(root,treeFocusPath)||root;
  const profiles=YDNACountryTree.profilesByBranch(modernSamples),sampleOptions=compactTreeOptions();
  const uploads=YDNACountryTree.profilesByBranch(uploadedProfiles);
  const display=YDNACountryTree.compact(focused,treeMode==='full',new Set([...profiles.keys(),...uploads.keys()]));
  document.getElementById('btn-tree-back').classList.toggle('hidden',focused===root);
  const families=[...new Set(countryTracker.nodes.map(n=>n.label[0]))].sort();
  sampleOptions.location=s=>[s.origin_raw,s.governorate].filter(isRealValue).filter((v,i,a)=>a.indexOf(v)===i).join(' · ')||'Paternal origin unknown';
  pills.innerHTML=`<button class="haplo-pill" onclick="countryTreeFamily=null;clearTreeFocus()">All · ${countryTracker.total_count}</button>`+families.map(f=>`<button class="haplo-pill" data-family="${f}" onclick="focusCountryFamily(this.dataset.family)">${f} · ${countryTracker.nodes.filter(n=>n.label[0]===f).reduce((sum,n)=>sum+n.count,0)}</button>`).join('');
  const options={...compactTreeOptions(),collapsed:collapsedNodes,names:n=>{
    const reference=YDNASync.officialPath({y_dna:n.display},syncOfficialRelease,syncOfficialNodes);
    return {primary:n.display,secondary:reference&&reference.label!==n.display?`YFull: ${reference.label} (v${reference.version} reference)`:''};
  },countLabel:n=>`${n.count} results`,counts:n=>n.directCount?`<span class="tree-count">${n.directCount} direct</span>`:'',
  aliases:()=>'',country:()=>'',age:()=>'',hasEvidence:()=>false,evidence:()=>'',
  hasGroup:n=>profiles.has(n.display.toUpperCase())||uploads.has(n.display.toUpperCase()),
  group:n=>{
    const known=profiles.get(n.display.toUpperCase())||[];
    const fromFile=uploads.get(n.display.toUpperCase())||[];
    return (n.directCount?`<li class="country-result-group"><button class="country-result-button" data-branch="${esc(n.display)}" onclick="openCountryResult(this.dataset.branch)"><span class="country-result-dots" aria-hidden="true">${'<i class="country-result-dot"></i>'.repeat(n.directCount)}</span><span>Egypt · ${n.directCount} reported ${n.directCount===1?'result':'results'}</span><span class="phylo-detail-hint">Count details ›</span></button></li>`:'')+
      (known.length?`<li class="country-known-profiles"><details><summary>${known.length} public archive ${known.length===1?'profile':'profiles'} at this branch · overlap unverified</summary><ul>${known.map(s=>DNATreeView.sample(s,sampleOptions)).join('')}</ul></details></li>`:'')+
      (fromFile.length?`<li class="country-known-profiles uploaded-branch-profiles"><details><summary>${fromFile.length} uploaded source ${fromFile.length===1?'record':'records'} · identity unlinked</summary><ul>${fromFile.map(uploadedProfileRow).join('')}</ul></details></li>`:'');
  }};
  inner.innerHTML=DNATreeView.node(display,options,true);
  if(!treeFocusPath&&!treeSearchResultPath){document.getElementById('tree-result-path').classList.remove('active');document.getElementById('tree-result-path').innerHTML='';}
  updateTreeFloatingToggle();
}

function focusCountryFamily(family){
  const nodes=YDNACountryTree.flatten(countryTrackerRoot).filter(n=>n.display.startsWith(family+'-'));
  if(!nodes.length)return;
  // A family can have several disconnected terminal-only branches. Show its
  // count groups without attaching them to an invented common SNP.
  countryTreeFamily=family;treeFocusPath=null;renderCountryTree();
  // The next All / search action restores the complete census.
}

function searchCountryTree(query){
  if(isUploadedTree())return searchUploadedTree(query);
  if(!isCountryTree())return false;
  if(!countryTracker)return true;
  countryTreeFamily=null;
  countryTrackerRoot=YDNACountryTree.build(countryTracker);
  const nodes=YDNACountryTree.flatten(countryTrackerRoot),q=query.trim().toUpperCase();
  const found=nodes.find(n=>n.display.toUpperCase()===q)||nodes.find(n=>n.display.toUpperCase().replace(/^[A-T]-/,'')===q);
  if(found){treeSearchResultPath='';treeFocusPath=found.pathKey;collapsedNodes.clear();renderClickableTreePath(treeFocusPath);renderTree();updateShareUrl({section:'ytree'});requestAnimationFrame(()=>scrollTreeIntoView());return true;}
  if(q&&allTreeSamples().some(s=>YDNASync.matches(s,'','',query,Infinity))){countryTreeMode='profiles';return false;}
  if(q&&uploadedProfiles.some(s=>uploadedMatches(s,query))){countryTreeMode='uploaded';return searchUploadedTree(query);}
  treeFocusPath=null;treeSearchResultPath=q?`No published FTDNA branch found for ${query}`:'';
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
    ${profiles.length?`<h4>Public archive profiles at this branch</h4><p>Shown for reference. Their overlap with the source count is not established; they are not added to or subtracted from the total.</p><ul>${profiles.map(s=>`<li><button class="ctrl-btn" data-uid="${esc(s.__uid)}" onclick="document.getElementById('country-result-dialog').close();openSampleModalByUid(this.dataset.uid)">${esc(YDNASync.publicId(s)==='—'?YDNASync.displayName(s):YDNASync.publicId(s))}</button></li>`).join('')}</ul>`:''}`;
  dialog.showModal();
}
