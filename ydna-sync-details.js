let syncTextQuery = '';
let syncLatestStart = Infinity;
const syncComparisons = new Map();

async function loadSyncMetadata() {
  // Optional enrichment must never break the existing archive if a migration is unavailable.
  try {
    const run = await _sb.from('ydna_sync_runs').select('started_at').in('status', ['completed','partial']).order('started_at',{ascending:false}).limit(1);
    if (run.data?.[0]) syncLatestStart = Date.parse(run.data[0].started_at);
    for (let offset=0; ; offset+=1000) {
      const evidence = await _sb.from('ydna_sync_observations').select('sample_id,project:payload->>project').eq('is_current',true).range(offset,offset+999);
      if (evidence.error) break;
      for (const item of evidence.data) {
        const sample=modernSamples.find(s=>s.id===item.sample_id);
        if(sample && item.project) sample.__projects=[...new Set([...(sample.__projects||[]),item.project])];
      }
      if(evidence.data.length<1000) break;
    }
  } catch (error) { console.warn('Optional synchronization metadata unavailable'); }
}

function resetSyncTreeFocus() {
  treeFocusPath=null; treeSearchTargetPath=null; treeSearchResultPath='';
  renderTree();
}

function syncNodeCountHTML(node) {
  if(currentTreeType==='mt') return '';
  const c=YDNASync.nodeCounts(node);
  return `<span class="tree-count" title="Modern testers directly at this node / modern testers including subbranches / confirmed Big Y including subbranches">${c.direct} direct · ${c.modern} modern · ${c.bigY} Big Y</span>`;
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
  panel.innerHTML=`<div class="sample-detail-label">Test evidence</div><p>${esc(YDNASync.labels[YDNASync.status(sample)] || sample.test_status)} · ${esc(sample.test_type)} · ${esc(sample.yfull_id || '')}</p><p>${esc(sample.origin_raw || '')}</p><p>Updated: ${esc(sample.sync_updated_at || sample.created_at || '—')}</p><div id="sync-evidence-loading">Loading public source evidence…</div>`;
  try {
    const observations=[];
    for(let offset=0; ; offset+=1000) {
      const result=await _sb.from('ydna_sync_observations').select('*').eq('sample_id',sample.id).order('id',{ascending:false}).range(offset,offset+999);
      if(result.error) throw result.error;
      observations.push(...result.data);
      if(result.data.length<1000) break;
    }
    if(currentSampleModal?.__uid!==sample.__uid) return;
    const loading=document.getElementById('sync-evidence-loading');
    if(!observations.length) { loading.textContent='No synchronized STR evidence available for this profile.'; return; }
    const markers=observations.flatMap(o=>(o.payload.str_markers||[]).map(m=>({...m,source:o.payload.source_url,date:o.last_seen_at,current:o.is_current})));
    panel.__strProfile={sample,markers};
    const sources=observations.map(o=>`<li>${syncSourceLink(o.payload.source_url,o.payload.project||o.source_id)} · ${esc(o.namespace)}: ${esc(o.external_id)} · ${esc(o.payload.y_dna || '—')} ${esc(o.payload.y_dna_alias || '')} · ${esc(o.payload.test_type || 'Unspecified')} · ${esc(o.last_seen_at)}${o.is_current?'':' (previous observation)'}${o.payload.snp_path?.length?`<p>${esc(o.payload.snp_path.join(' > '))}</p>`:''}</li>`).join('');
    loading.outerHTML=`<div><div class="sample-detail-label">Public source claims (differences retained for review)</div><ul class="space-y-2 text-sm">${sources}</ul></div>
      <div><label for="sync-str-search" class="sample-detail-label">Search STR markers or alleles</label><input id="sync-str-search" class="tree-search" type="search" oninput="filterSyncSTR(this.value)">
      <p class="text-xs">Original marker order and alleles; unknown values are shown as —. Earlier observations remain labelled.</p>
      <div style="overflow:auto;max-height:360px"><table class="w-full text-left text-sm"><thead><tr><th>Marker</th><th>Source label</th><th>Alleles</th><th>Evidence</th></tr></thead><tbody id="sync-str-body"></tbody></table></div>
      <button class="ctrl-btn" onclick="addSyncComparison()">Add to STR comparison</button><div id="sync-str-comparison" style="overflow:auto"></div></div>`;
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
