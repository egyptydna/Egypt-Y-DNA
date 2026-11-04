let syncOfficialRelease=null;
let syncOfficialNodes=new Map();
let syncTreeTopology='yfull';

async function loadOfficialTree() {
  try {
    const result=await _sb.from('ydna_sync_tree_releases').select('*').eq('source_id','yfull-github').eq('is_current',true).limit(1);
    if(result.error || !result.data?.length) return;
    const release=result.data[0],nodes=new Map();
    for(let offset=0; ; offset+=1000) {
      const page=await _sb.from('ydna_sync_official_tree_nodes').select('label,parent_label,aliases,snp_groups,age_estimates')
        .eq('source_id',release.source_id).eq('release_key',release.release_key).order('label').range(offset,offset+999);
      if(page.error) return;
      for(const node of page.data) nodes.set(node.label,node);
      if(page.data.length<1000) break;
    }
    if(nodes.size!==release.selected_node_count || !nodes.has('Y-Adam')) return;
    syncOfficialRelease=release;syncOfficialNodes=nodes;
  } catch { console.warn('Official YFull tree metadata temporarily unavailable'); }
}

function setOfficialTopology(value) {
  syncTreeTopology=value==='yfull'?'yfull':'published';
  treeFocusPath=null;treeSearchTargetPath=null;treeSearchResultPath='';collapsedNodes.clear();renderTree();
}

function renderOfficialTreePanel() {
  const panel=document.getElementById('official-tree-panel');
  if(!panel) return;
  panel.classList.toggle('hidden',currentTreeType==='mt');
  if(!syncOfficialRelease) { panel.textContent='Official YFull topology: no published GitHub snapshot loaded.';return; }
  const r=syncOfficialRelease;
  panel.innerHTML=`<label for="official-topology-mode">Tree paths</label>
    <select id="official-topology-mode" class="ctrl-btn" onchange="setOfficialTopology(this.value)">
      <option value="published" ${syncTreeTopology==='published'?'selected':''}>Existing published paths</option>
      <option value="yfull" ${syncTreeTopology==='yfull'?'selected':''}>Official YFull paths · v${esc(r.version)}</option>
    </select>
    <p>Unmatched or conflicting labels keep their existing published paths. Branch ages describe the lineage, not the individual tester.<br>
    YFull GitHub v${esc(r.version)} · source published ${esc(r.published_at.slice(0,10))} · checked ${esc(r.checked_at.slice(0,10))}<br>
    ${esc(r.node_count-1)} source branches indexed; ${esc(r.selected_node_count)} path nodes for this archive. This is the GitHub snapshot, not a claim about the current live YTree version.</p>
    <p>${esc(r.attribution)} · ${syncSourceLink(r.license_url,'License')} · ${syncSourceLink(r.source_url,'Original JSON')} · Relevant paths and metadata extracted.</p>`;
}

function officialInfoForNode(node) {
  if(!syncOfficialRelease) return null;
  if(syncOfficialNodes.has(node.display)) return syncOfficialNodes.get(node.display);
  const match=syncOfficialRelease.metadata?.matches?.[node.display.toUpperCase()];
  return match && ['exact','equivalent_snp'].includes(match.status)?syncOfficialNodes.get(match.label):null;
}

function publishedAgeText(age) {
  if(age?.estimate==null) return 'unknown';
  const interval=age.low!=null && age.high!=null?` (published interval ${age.low}–${age.high})`:'';
  return `${age.estimate} ybp${interval}`;
}

function renderOfficialNodeInfo(node) {
  if(currentTreeType==='mt') return '';
  const info=officialInfoForNode(node);
  if(!info) return '';
  const alias=info.label!==node.display?` · YFull branch ${info.label}`:'';
  return `<div class="tree-official-evidence" style="margin:.25rem 0;font-size:10px;color:#64748b">YFull v${esc(syncOfficialRelease.version)}${esc(alias)} · Branch TMRCA: ${esc(publishedAgeText(info.age_estimates?.tmrca))}</div>`;
}

function renderOfficialSampleInfo(sample) {
  const target=document.getElementById('sample-official-tree');
  if(!target) return;
  target.innerHTML='';
  if(!syncOfficialRelease || currentTreeType==='mt' || !isRealValue(sample.y_dna)) return;
  const placement=YDNASync.officialPath(sample,syncOfficialRelease,syncOfficialNodes);
  if(!placement) {
    target.textContent=`Official YFull GitHub v${syncOfficialRelease.version}: no unambiguous placement for the published labels. Original source path retained.`;
    return;
  }
  const node=syncOfficialNodes.get(placement.label);
  target.innerHTML=`<div class="sample-detail-label">Official YFull Y-DNA reference · v${esc(placement.version)}</div>
    <p>Published record: ${esc(sample.y_dna)} · YFull branch: ${esc(placement.label)}</p>
    <div class="sample-detail-code">${esc(placement.path.join(' > '))}</div>
    <p>Branch formed: ${esc(publishedAgeText(node.age_estimates?.formed))}<br>Branch TMRCA: ${esc(publishedAgeText(node.age_estimates?.tmrca))}</p>
    <details><summary>Published defining SNP blocks</summary><p class="sample-detail-code">${esc((node.snp_groups||[]).map(g=>g.join(' / ')).join(', '))}</p></details>
    <p>${esc(syncOfficialRelease.attribution)} · ${syncSourceLink(syncOfficialRelease.license_url,'License')} · ${syncSourceLink(syncOfficialRelease.source_url,'Source JSON')}</p>`;
}
