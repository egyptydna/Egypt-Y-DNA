let platformNamesMemo=null;
const phyloNodeLookup=new Map();
function loadPhyloEvidence(details) {
  if(!details.open||details.dataset.loaded)return;
  const node=phyloNodeLookup.get(decodePathArg(details.dataset.nodePath));
  if(!node)return;
  details.querySelector('.phylo-evidence-body').innerHTML=renderOfficialNodeInfo(node)+renderSyncCountryEvidence(node);
  details.dataset.loaded='true';
}
function treePlatformNames(node) {
  if(currentTreeType==='mt')return {primary:node.display,secondary:''};
  if(!platformNamesMemo||platformNamesMemo.facts!==syncCountryCounts||platformNamesMemo.release!==syncOfficialRelease){
    const ftdnaLabels=new Set(syncCountryCounts.filter(f=>f.namespace==='ftdna').map(f=>String(f.node_label).toUpperCase()));
    const byReference=new Map();
    for(const label of ftdnaLabels){
      const reference=YDNASync.officialPath({y_dna:label},syncOfficialRelease,syncOfficialNodes);
      if(!reference)continue;
      if(!byReference.has(reference.label))byReference.set(reference.label,new Set());
      byReference.get(reference.label).add(label);
    }
    platformNamesMemo={facts:syncCountryCounts,release:syncOfficialRelease,ftdnaLabels,byReference};
  }
  const label=node.display,reference=YDNASync.officialPath({y_dna:label},syncOfficialRelease,syncOfficialNodes);
  const ft=reference?[...(platformNamesMemo.byReference.get(reference.label)||[])]:[];
  // Several FTDNA branches may resolve to one older YFull branch. That does
  // not establish interchangeable names or justify collapsing the branches.
  const primary=platformNamesMemo.ftdnaLabels.has(label.toUpperCase())?label:ft.length===1?ft[0]:label;
  const secondary=[];
  if(reference&&reference.label!==primary)secondary.push(`YFull: ${reference.label} (v${reference.version})`);
  if(ft.length>1)secondary.push(`FTDNA reference matches: ${ft.join(', ')} · distinct source branches retained`);
  return {primary,secondary:secondary.join(' · ')};
}
function compactTreeOptions() {
  return {
    type:currentTreeType,collapsed:collapsedNodes,names:treePlatformNames,
    identity:s=>YDNASync.publicId(s)==='—'?'':YDNASync.publicId(s),
    name:s=>YDNASync.displayName(s),
    location:s=>[s.governorate||s.site,s.__sourceType==='related'?s.country:null].filter(isRealValue).join(' · ')||'Origin unknown',
    test:s=>currentTreeType==='mt'?(s.mt_dna||''):s.__sourceType==='modern'?[s.test_type,YDNASync.labels[YDNASync.status(s)]].filter(isRealValue).filter((v,i,a)=>a.indexOf(v)===i).join(' · '):s.y_dna,
    issue:s=>currentTreeType==='mt'?'':YDNASync.pathIssue(s),
    sort:sortNodeChildren,aliases:renderNodeAliases,counts:syncNodeCountHTML,
    age:n=>{if(currentTreeType==='mt')return '';const info=officialInfoForNode(n);return info?.age_estimates?.tmrca?.estimate!=null?`TMRCA ${info.age_estimates.tmrca.estimate} ybp`:'';},
    hasEvidence:n=>{
      phyloNodeLookup.set(n.pathKey,n);
      return currentTreeType!=='mt'&&(officialInfoForNode(n)||syncCountryFacts(n).length);
    },
    evidence:n=>renderOfficialNodeInfo(n)+renderSyncCountryEvidence(n)
  };
}
