let platformNamesMemo=null;
const phyloNodeLookup=new Map();
function treeCountryCountBadge(node) {
  if(currentTreeType==='mt')return '';
  const facts=syncCountryFacts(node).filter(f=>f.namespace==='ftdna');
  if(!facts.length)return '';
  const inclusive=facts.filter(f=>f.count_scope==='inclusive'),shown=inclusive.length?inclusive:facts.filter(f=>f.count_scope==='direct');
  const values=new Set(shown.map(f=>f.reported_count));
  if(values.size!==1)return '<span class="phylo-country-count">FTDNA: differing source counts</span>';
  const count=[...values][0],scope=inclusive.length?'including subbranches':'directly at this branch';
  const dates=[...new Set(shown.map(f=>String(f.observed_at||'').slice(0,10)))].join(', ');
  return `<span class="phylo-country-count" title="${esc(`FTDNA Egyptian country entries ${scope}; source snapshot ${dates}. May overlap with identified profiles; these counts do not supply kit identities.`)}">FTDNA: ${esc(count)} ${inclusive.length?'incl.':'direct'}</span>`;
}
function loadPhyloEvidence(details) {
  if(!details.open||details.dataset.loaded)return;
  const node=phyloNodeLookup.get(decodePathArg(details.dataset.nodePath));
  if(!node)return;
  details.querySelector('.phylo-evidence-body').innerHTML=renderOfficialNodeInfo(node)+renderSyncCountryEvidence(node);
  details.dataset.loaded='true';
}
function treePlatformNames(node) {
  if(currentTreeType==='mt')return {primary:node.display,secondary:''};
  const samples=typeof modernSamples==='undefined'?[]:modernSamples;
  if(!platformNamesMemo||platformNamesMemo.facts!==syncCountryCounts||platformNamesMemo.release!==syncOfficialRelease||platformNamesMemo.samples!==samples){
    const ftdnaLabels=new Set(syncCountryCounts.filter(f=>f.namespace==='ftdna').map(f=>String(f.node_label).toUpperCase().replace(/\*+$/,'')));
    for(const sample of samples){
      const branch=YDNASync.officialPath(sample,syncOfficialRelease,syncOfficialNodes);
      if(!branch)continue;
      for(const link of [sample.y_link_1,sample.y_link_2]){
        try{
          const url=new URL(link),label=url.pathname.match(/^\/y-dna\/([^/]+)(?:\/|$)/i)?.[1]?.toUpperCase();
          if(url.protocol!=='https:'||url.hostname!=='discover.familytreedna.com'||!label)continue;
          const ft=YDNASync.officialPath({y_dna:label},syncOfficialRelease,syncOfficialNodes);
          if(ft?.label===branch.label)ftdnaLabels.add(label.replace(/\*+$/,''));
        }catch{}
      }
    }
    const byReference=new Map();
    for(const label of ftdnaLabels){
      const reference=YDNASync.officialPath({y_dna:label},syncOfficialRelease,syncOfficialNodes);
      if(!reference)continue;
      if(!byReference.has(reference.label))byReference.set(reference.label,new Set());
      byReference.get(reference.label).add(label);
    }
    platformNamesMemo={facts:syncCountryCounts,release:syncOfficialRelease,samples,ftdnaLabels,byReference};
  }
  const label=node.display,reference=YDNASync.officialPath({y_dna:label},syncOfficialRelease,syncOfficialNodes);
  const ft=reference?[...(platformNamesMemo.byReference.get(reference.label)||[])]:[];
  // Several FTDNA branches may resolve to one older YFull branch. That does
  // not establish interchangeable names or justify collapsing the branches.
  const basal=label.endsWith('*')?'*':'';
  const primary=platformNamesMemo.ftdnaLabels.has(label.toUpperCase().replace(/\*+$/,''))?label:ft.length===1?ft[0]+basal:label;
  const secondary=[];
  if(reference&&reference.label+basal!==primary)secondary.push(`YFull: ${reference.label}${basal} (v${reference.version})`);
  const ambiguous=ft.length>1&&!platformNamesMemo.ftdnaLabels.has(label.toUpperCase().replace(/\*+$/,''));
  if(ambiguous)secondary.push(`FTDNA: ${ft.join(' / ')}`);
  return {primary,secondary:secondary.join(' · '),note:ambiguous?'An older reference groups these labels; their distinct source branches are retained.':''};
}
function compactTreeOptions() {
  return {
    type:currentTreeType,collapsed:collapsedNodes,names:treePlatformNames,isNew:YDNASync.isNew,
    providers:s=>s.__sourceType==='modern'?YDNAProfiles.providers(s):[],sortSamples:sortTreeProfiles,
    identity:s=>YDNASync.publicId(s)==='—'?'':YDNASync.publicId(s),
    countryLabel:s=>{const country=currentTreeType==='mt'?s.mt_country:s.__public_country||s.country;return /^(Egypt|EG|مصر)$/i.test(country||'')?'🇪🇬 EGY':'';},
    name:s=>YDNASync.displayName(s),
    location:s=>[s.governorate||s.site,s.__sourceType==='related'?s.country:null].filter(isRealValue).join(' · ')||'Origin unknown',
    test:s=>currentTreeType==='mt'?(s.mt_dna||''):s.__sourceType==='modern'?[YDNASync.preferredTest(s),YDNASync.labels[YDNASync.status(s)]].filter(isRealValue).filter((v,i,a)=>a.indexOf(v)===i).join(' · '):s.y_dna,
    issue:s=>currentTreeType==='mt'?'':YDNASync.pathIssue(s,undefined,syncOfficialRelease,syncOfficialNodes),
    sort:sortNodeChildren,aliases:renderNodeAliases,counts:syncNodeCountHTML,country:treeCountryCountBadge,
    age:n=>{if(currentTreeType==='mt')return '';const info=officialInfoForNode(n),age=info?.age_estimates;if(!age)return '';return [age.formed?.estimate!=null?`formed ${age.formed.estimate} ybp`:null,age.tmrca?.estimate!=null?`TMRCA ${age.tmrca.estimate} ybp`:null].filter(Boolean).join(', ');},
    hasEvidence:n=>{
      phyloNodeLookup.set(n.pathKey,n);
      return currentTreeType!=='mt'&&(officialInfoForNode(n)||syncCountryFacts(n).length);
    },
    evidence:n=>renderOfficialNodeInfo(n)+renderSyncCountryEvidence(n)
  };
}
