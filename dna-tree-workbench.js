/* Fixed tree controls and source-validated lineage ages. No source fetching here. */
(function(root){
  'use strict';
  function ageMetric(value){
    if(!value||value.estimate==null)return null;
    const n=value.estimate,low=value.low,high=value.high;
    if(typeof n!=='number'||!Number.isFinite(n)||n<0)return null;
    if(low!=null&&(typeof low!=='number'||!Number.isFinite(low)||low<0||low>n))return null;
    if(high!=null&&(typeof high!=='number'||!Number.isFinite(high)||high<n))return null;
    return {estimate:n,low:low??null,high:high??null};
  }
  function ftdnaAge(observation){
    const age=observation.branch_age;
    if(observation.namespace!=='ftdna'||observation.published!==true||observation.is_current!==true||age?.kind!=='lineage_estimate'||age.dna_type!=='y'||age.unit!=='ybp')return null;
    if(!/^[A-T]-[A-Z0-9*.+_-]+$/i.test(age.node_label||'')||!Number.isFinite(Date.parse(age.observed_at)))return null;
    try{
      const u=new URL(age.source_url);
      if(u.protocol!=='https:'||u.hostname!=='discover.familytreedna.com'||u.username||u.password||decodeURIComponent(u.pathname.split('/')[2]||'').toUpperCase()!==age.node_label.toUpperCase()||u.pathname.split('/')[1]!=='y-dna')return null;
    }catch{return null;}
    const formed=ageMetric(age.formed),tmrca=ageMetric(age.tmrca);
    if(!formed&&!tmrca||formed&&tmrca&&formed.estimate<tmrca.estimate)return null;
    return {provider:'FTDNA',sourceLabel:age.node_label,sourceURL:age.source_url,date:age.observed_at,formed,tmrca};
  }
  const chooseAges=(yfull,ftdna)=>yfull&&(ageMetric(yfull.formed)||ageMetric(yfull.tmrca))?yfull:ftdna||null;
  const ageText=record=>record?[record.formed?`formed ${record.formed.estimate} ybp`:null,record.tmrca?`TMRCA ${record.tmrca.estimate} ybp`:null].filter(Boolean).join(', '):'';
  const api={ageMetric,ftdnaAge,chooseAges,ageText};
  if(typeof module==='object'){module.exports=api;return;}
  root.DNATreeWorkbench=api;
  const savedFTDNA=new Map();
  root.ingestPublishedBranchAge=function(observation){
    const age=ftdnaAge(observation);if(!age)return;
    const key=age.sourceLabel.toUpperCase(),items=savedFTDNA.get(key)||[];
    if(!items.some(v=>JSON.stringify(v)===JSON.stringify(age)))items.push(age);
    savedFTDNA.set(key,items);
  };
  root.publishedBranchAge=function(node){
    if(currentTreeType==='mt')return null;
    const info=officialInfoForNode(node),release=syncOfficialRelease;
    const yfull=info&&release?{provider:'YFull',version:release.version,sourceLabel:info.label,sourceURL:release.source_url,date:release.published_at,formed:ageMetric(info.age_estimates?.formed),tmrca:ageMetric(info.age_estimates?.tmrca)}:null;
    const items=[...(savedFTDNA.get(String(node.display).toUpperCase())||[])].sort((a,b)=>Date.parse(b.date)-Date.parse(a.date));
    // Equally dated conflicting claims remain unresolved, never averaged.
    const latest=items[0],conflict=latest&&items.some(v=>Date.parse(v.date)===Date.parse(latest.date)&&JSON.stringify([v.formed,v.tmrca])!==JSON.stringify([latest.formed,latest.tmrca]));
    return chooseAges(yfull,conflict?null:latest);
  };
  root.treeBranchAgeText=node=>ageText(root.publishedBranchAge(node));
  root.treeBranchAgeTitle=function(node){
    const age=root.publishedBranchAge(node);if(!age)return '';
    return `${age.provider}${age.version?' v'+age.version:''} · reference ${age.sourceLabel} · source ${String(age.date).slice(0,10)} · lineage estimates in years before present. Open info for published intervals.`;
  };
  root.renderBranchAgeInfo=function(node){
    const age=root.publishedBranchAge(node);if(!age)return '';
    const value=m=>!m?'not published':`${m.estimate} ybp${m.low!=null&&m.high!=null?` (published interval ${m.low}–${m.high})`:''}`;
    return `<div class="tree-official-evidence"><p>${esc(age.provider)}${age.version?' v'+esc(age.version):''} · reference branch ${esc(age.sourceLabel)} · source date ${esc(String(age.date).slice(0,10))}</p><p>Formed: ${esc(value(age.formed))} · TMRCA: ${esc(value(age.tmrca))}</p><p>Published lineage estimates, not the age of a tested person. ${syncSourceLink(age.sourceURL,'Age source')}</p></div>`;
  };
  root.runDockTreeSearch=function(){
    document.getElementById('treeSearch').value=document.getElementById('tree-dock-search').value;runTreeSearch();
  };
  root.syncTreeWorkbench=function(){
    const dock=document.getElementById('tree-workbench');if(!dock)return;
    document.getElementById('tree-dock-title').textContent=currentTreeType==='mt'?'mtDNA Tree':'Y-DNA Tree';
    const search=document.getElementById('tree-dock-search');
    search.placeholder=currentTreeType==='mt'?'Find mtDNA lineage or sample…':'Find SNP or sample…';
    if(document.activeElement!==search)search.value=document.getElementById('treeSearch').value;
    dock.querySelectorAll('[data-tree-mode]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.treeMode===treeMode)));
    document.getElementById('tree-dock-topology-label').hidden=currentTreeType==='mt'||isUploadedTree();
    const select=document.getElementById('tree-dock-topology');select.value=syncTreeTopology;
    select.querySelector('[value="yfull"]').disabled=!syncOfficialRelease;
    select.querySelector('[value="yfull"]').textContent=syncOfficialRelease?'YFull v'+syncOfficialRelease.version:'YFull reference unavailable';
  };
  document.addEventListener('DOMContentLoaded',()=>{
    const nav=document.querySelector('nav[aria-label="Primary navigation"]');
    const resize=()=>document.documentElement.style.setProperty('--tree-nav-height',(nav?.getBoundingClientRect().height||80)+'px');
    if(typeof ResizeObserver==='function'&&nav)new ResizeObserver(resize).observe(nav);
    resize();root.syncTreeWorkbench();
    document.getElementById('treeSearch').addEventListener('input',()=>{document.getElementById('tree-dock-search').value=document.getElementById('treeSearch').value;});
  });
})(typeof window==='object'?window:globalThis);
