let syncTextQuery = '';
let syncLatestStart = Infinity;
const syncComparisons = new Map();
const syncTreeAliases = new Map();
let syncCountryCounts = [];

async function loadSyncMetadata() {
  // Independent enrichment queries run together. A slow or unavailable
  // reference service must not block loading the public sample archive.
  const sampleById=new Map();
  for(const sample of modernSamples)for(const id of sample.__linked_sample_ids||[sample.id])
    sampleById.set(id,sample);
  const runTask=(async()=>{
    const run=await _sb.from('ydna_sync_runs').select('started_at')
      .in('status',['completed','partial']).order('started_at',{ascending:false}).limit(1);
    if(run.data?.[0])syncLatestStart=Date.parse(run.data[0].started_at);
  })();
  const observationTask=(async()=>{
    for(let offset=0;;offset+=1000){
      const evidence=await _sb.from('ydna_sync_observations')
        .select('sample_id,namespace,is_current,published,project:payload->>project,test_type:payload->>test_type,country:payload->>country').eq('is_current',true).eq('published',true).order('id')
        .range(offset,offset+999);
      if(evidence.error)break;
      for(const item of evidence.data){
        const sample=sampleById.get(item.sample_id);
        if(sample)YDNASync.addObservation(sample,item);
      }
      if(evidence.data.length<1000)break;
    }
  })();
  const aliasesTask=(async()=>{
    for(let offset=0;;offset+=1000){
      const nodes=await _sb.from('ydna_sync_tree_nodes')
        .select('label,aliases').order('source_id').order('label').range(offset,offset+999);
      if(nodes.error)break;
      for(const node of nodes.data){
        const key=node.label.toUpperCase();
        syncTreeAliases.set(key,[...new Set([...(syncTreeAliases.get(key)||[]),
          ...(Array.isArray(node.aliases)?node.aliases:[])
            .filter(a=>typeof a==='string')])]);
      }
      if(nodes.data.length<1000)break;
    }
  })();
  const countsTask=(async()=>{
    const facts=[];
    for(let offset=0;;offset+=1000){
      const page=await _sb.from('ydna_sync_country_counts').select('*')
        .eq('is_current',true).order('id').range(offset,offset+999);
      if(page.error)break;
      facts.push(...page.data);
      if(page.data.length<1000)break;
    }
    syncCountryCounts=facts;
  })();
  await Promise.allSettled([runTask,observationTask,aliasesTask,countsTask,loadOfficialTree()]);
}

function resetSyncTreeFocus() {
  if(currentTreeType==='y')countryTreeMode='profiles';
  treeFocusPath=null; treeSearchTargetPath=null; treeSearchResultPath='';
  renderTree();
}

function syncNodeCountHTML(node) {
  if(currentTreeType==='mt') return '';
  const c=YDNASync.nodeCounts(node);
  const counts=[c.direct?`${c.direct} direct`:null,c.modern!==node.count?`${c.modern} modern`:null,c.bigY?`${c.bigY} Big Y`:null].filter(Boolean);
  return `<span class="tree-count" title="${c.direct} modern directly at this node; ${c.modern} modern and ${c.bigY} confirmed Big Y including subbranches">${counts.join(' · ')}</span>`;
}

function visibleSyncCountryCounts() {
  if(currentTreeType==='mt' || !treeShowModern || document.getElementById('treeGovernorate').value) return [];
  const kind=document.getElementById('treeTestStatus').value;
  return syncCountryCounts.filter(fact=>{
    if(kind==='modern' && fact.population==='unknown') return false;
    if(['new','str_only','snp_tested'].includes(kind)) return false;
    if(kind==='confirmed_big_y' && fact.population!=='ftdna_big_y') return false;
    if(kind==='yfull' && fact.namespace!=='yfull') return false;
    if(syncTextQuery && ![fact.node_label,...(fact.snp_path||[])].join(' ').toLowerCase().includes(syncTextQuery.toLowerCase())) return false;
    if(treeHaploFilter && treeGroupForSample({y_dna:fact.node_label,snp_path:(fact.snp_path||[]).join('>')})!==treeHaploFilter) return false;
    return true;
  });
}

let syncTerminalPathsMemo=null;
let syncCountryFactsMemo=null;
function resetSyncMetadataIndexes() {
  syncTerminalPathsMemo=null;
  syncCountryFactsMemo=null;
}
function resetSyncCountryFactsIndex() {
  syncCountryFactsMemo=null;
}
function syncKnownTerminalPaths() {
  if(syncTerminalPathsMemo)return syncTerminalPathsMemo;
  syncTerminalPathsMemo=YDNASync.knownTerminalPaths(allTreeSamples().concat(syncCountryCounts
    .filter(f=>Array.isArray(f.snp_path) && f.snp_path.length &&
      String(f.path_source_url||'').startsWith('https://'))
    .map(f=>({y_dna:f.node_label,full_snp_path:f.snp_path.join('>')}))));
  return syncTerminalPathsMemo;
}

function syncCountryFacts(node) {
  if(!syncCountryFactsMemo){
    syncCountryFactsMemo=new Map();
    for(const fact of visibleSyncCountryCounts()){
      const placement=syncTreeTopology==='yfull'
        ? YDNASync.officialPath({y_dna:fact.node_label},syncOfficialRelease,syncOfficialNodes)
        : null;
      const key=String(placement?.label||fact.node_label||'').toUpperCase();
      if(!syncCountryFactsMemo.has(key))syncCountryFactsMemo.set(key,[]);
      syncCountryFactsMemo.get(key).push(fact);
    }
  }
  return syncCountryFactsMemo.get(node.display.toUpperCase())||[];
}

function ensureSyncCountryCountNodes(root,knownPaths) {
  for(const fact of visibleSyncCountryCounts()) {
    const placement=syncTreeTopology==='yfull'?YDNASync.officialPath({y_dna:fact.node_label},syncOfficialRelease,syncOfficialNodes):null;
    const published=Array.isArray(fact.snp_path)&&fact.snp_path.length?fact.snp_path.join('>'):'';
    const path=placement?.path||parsePath(published || knownPaths.get(fact.node_label) || '',fact.node_label);
    let node=root;
    const ancestors=[{display:'Y-Adam'}];
    for(const raw of path.slice(1)) {
      const display=placement?canonicalHeadName(raw):normalizeDisplay(raw,ancestors);
      if(!node.childMap.has(display)) {
        const child={raw,display,pathKey:node.pathKey+'>'+display,children:[],childMap:new Map(),samples:[],parent:node,count:0,
          family:inferFamilyFromDisplay(display,node.family),aliases:[]};
        node.childMap.set(display,child);node.children.push(child);
      }
      node=node.childMap.get(display);ancestors.push({display});
    }
    if(placement && placement.label!==fact.node_label) addAliasToNode(node,fact.node_label);
  }
}

function renderSyncCountryEvidence(node) {
  if(currentTreeType==='mt') return '';
  const facts=syncCountryFacts(node);
  if(!facts.length) return '';
  const known=syncKnownTerminalPaths();
  const samples=allTreeSamples();
  const rows=facts.map(fact=>{
    const result=YDNASync.reconcileCountryCount(fact,samples,known);
    const remaining=result.conflict?'Counts differ — review required':result.comparable?
      `${result.known} matching public ID(s) · ${result.unresolved} arithmetically unidentified`:
      'Counted population unspecified — kept separate from profiles';
    const scope=fact.count_scope==='inclusive'?'including descendants':'directly at this branch';
    return `<div style="margin:.4rem 0;padding:.5rem .75rem;border-left:3px solid #8b6a1c;font-size:11px;max-width:520px">
      <strong>${esc(fact.namespace.toUpperCase())} · Egypt: ${result.reported} reported</strong> · ${esc(scope)}<br>
      ${esc(remaining)}<br>${syncSourceLink(fact.source_url,'Count source')} · As of ${esc(fact.observed_at)}
      <div style="color:#64748b">Cohort comparison; no specific anonymous record is assigned to a person. Not added to identified tester statistics.</div>
    </div>`;
  }).join('');
  return `<div class="tree-country-evidence">${rows}</div>`;
}

function syncSourceLink(url, label) {
  try { if(new URL(url).protocol!=='https:') return ''; } catch { return ''; }
  return `<a class="underline" href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(label)}</a>`;
}

async function loadSyncDetails(sample) {
  const panel=document.getElementById('sample-sync-details');
  panel.innerHTML='';
  panel.__strProfile=null;
  if(sample.__sourceType!=='modern') return;
  const sourcePaths=sample.__source_snp_paths||[];
  const compareSourcePaths=sourcePaths.length>1
    ? `<details class="mt-2"><summary>Compare documented source tree paths (${sourcePaths.length})</summary>
      <p>Different releases and providers may report different intermediate branches. Original paths are preserved, not silently replaced.</p>
      ${sourcePaths.map(row=>`<p><b>${esc(row.source)} · record ${esc(row.sample_id)}</b></p>
        <p class="sample-detail-code">${esc(String(row.path).split('>').join(' > '))}</p>`).join('')}</details>`
    : '';
  panel.innerHTML=`<div class="sample-detail-label">Test evidence</div><p>${esc(YDNASync.identitySummary(sample))}</p><p>${esc(YDNASync.labels[YDNASync.status(sample)] || sample.test_status)} · ${esc(YDNASync.preferredTest(sample))}</p>${YDNASync.preferredTest(sample)!==sample.test_type?`<p>Preserved archive test: ${esc(sample.test_type)}</p>`:''}<p>${esc(sample.origin_raw || '')}</p>${sample.sync_origin_conflict?'<p class="phylo-warning">Conflicting source governorates: pending review. Included in the Egyptian total, excluded from governorate statistics. Original records remain archived.</p>':''}<p>Updated: ${esc(sample.sync_updated_at || sample.created_at || '—')}</p>${compareSourcePaths}<div id="sync-evidence-loading">Loading public source evidence…</div>`;
  try {
    const observations=[];
    for(let offset=0; ; offset+=1000) {
      const result=await _sb.from('ydna_sync_observations').select('*').in('sample_id',sample.__linked_sample_ids||[sample.id]).order('id',{ascending:false}).range(offset,offset+999);
      if(result.error) throw result.error;
      observations.push(...result.data);
      if(result.data.length<1000) break;
    }
    if(currentSampleModal?.__uid!==sample.__uid) return;
    const loading=document.getElementById('sync-evidence-loading');
    if(!observations.length) { loading.textContent='No synchronized STR evidence available for this profile.'; return; }
    const markers=YDNAProfiles.strRows(observations);
    panel.__strProfile={sample,markers};
    const sources=observations.map(o=>`<li>${syncSourceLink(o.payload.source_url,o.payload.project||o.source_id)} · ${esc(o.namespace)}: ${esc(o.external_id)} · ${esc(o.payload.y_dna || '—')} ${esc(o.payload.y_dna_alias || '')} · ${esc(o.payload.test_type || 'Unspecified')} · Imported: ${esc(o.last_seen_at)}${o.is_current?'':' (previous observation)'}${o.payload.snp_path?.length?`<p>${esc(o.payload.snp_path.join(' > '))}</p>`:''}</li>`).join('');
    loading.outerHTML=`<div><div class="sample-detail-label">Public source claims (differences retained for review)</div><ul class="space-y-2 text-sm">${sources}</ul></div>
      <div><div class="sample-detail-label">Published STRs</div>
      <p class="text-xs">${new Set(markers.filter(m=>m.current).map(m=>m.marker)).size} current STR markers with source evidence. Original marker order and alleles are retained; unknown values are shown as —. Earlier observations remain labelled.</p>
      ${markers.length?'':'<p>No STR values have been published for this profile in the available sources. No alleles are inferred from its branch.</p>'}
      <div style="overflow:auto;max-height:360px"><table class="w-full text-left text-sm"><thead><tr><th>Marker</th><th>Source label</th><th>Alleles</th><th>Evidence</th></tr></thead><tbody id="sync-str-body"></tbody></table></div>
      <button class="ctrl-btn" type="button" onclick="copyProfileSTRs()" ${YDNAProfiles.strText(markers)?'':'disabled'}>Copy STRs</button> <button class="ctrl-btn" type="button" onclick="exportProfileSTRs()" ${markers.length?'':'disabled'}>Download STRs & evidence (CSV)</button><p class="text-xs">Copy uses the largest current source panel in its original order. All source panels, earlier values and differences remain in the table and CSV.</p><p id="sync-str-copy-status" role="status"></p><div id="sync-str-comparison" style="overflow:auto"></div></div>`;
    filterSyncSTR('');
  } catch(error) {
    if(currentSampleModal?.__uid===sample.__uid) {
      const loading=document.getElementById('sync-evidence-loading');
      if(loading) loading.textContent='Public source details are temporarily unavailable.';
    }
  }
}

function filterSyncSTR(query) {
  const panel=document.getElementById('sample-sync-details');
  const target=document.getElementById('sync-str-body');
  if(!target || !panel.__strProfile) return;
  target.innerHTML=panel.__strProfile.markers.filter(m=>[m.marker,m.source_label,m.value].join(' ').toLowerCase().includes(query.toLowerCase()))
    .map(m=>`<tr><td>${esc(m.marker)}</td><td>${esc(m.source_label)}</td><td>${esc(m.value ?? '—')}</td><td>${syncSourceLink(m.source,m.current?'Current source':'Earlier source')} · ${esc(m.date)}</td></tr>`).join('');
}

function addSyncComparison() {
  const profile=document.getElementById('sample-sync-details').__strProfile;
  if(!profile) return;
  syncComparisons.set(profile.sample.id,profile);
  const profiles=[...syncComparisons.values()];
  const markers=[...new Set(profiles.flatMap(p=>p.markers.map(m=>m.marker)))];
  document.getElementById('sync-str-comparison').innerHTML=`<p>${profiles.length} tester(s). Open another tester and add it to compare. All source values are retained.</p>
    <button class="ctrl-btn" onclick="syncComparisons.clear();document.getElementById('sync-str-comparison').innerHTML=''">Clear comparison</button>
    <table class="w-full text-sm text-left"><thead><tr><th>Marker</th>${profiles.map(p=>`<th>${esc(p.sample.kit_number || p.sample.yfull_id || p.sample.id)}</th>`).join('')}</tr></thead><tbody>${markers.map(marker=>`<tr><td>${esc(marker)}</td>${profiles.map(p=>`<td>${esc([...new Set(p.markers.filter(m=>m.marker===marker && m.value!=null).map(m=>m.value))].join(' / ')||'—')}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
}
