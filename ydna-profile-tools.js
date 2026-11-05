/* Source-backed profile presentation. Never resolve an anonymous count to a person. */
(function(root){
  'use strict';
  const real=v=>v!=null&&!['','—','-'].includes(String(v).trim());
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const clean=v=>String(v).trim().toUpperCase().replace(/^[A-T]-/,'').replace(/\*$/,'');
  const Y_ANCHORS=['V13','V22','V65','M81','M123','V38','M78','M35','FGC1723','P58','M267','M172','M198','M417','M269','M343','M242','M70','M184','M201','M89'];
  const MT_ANCHORS=['H1','H2','H3','U3','U5','U6','J1','J2','T1','T2','K1','K2','M1','L0','L1','L2','L3','L4','L5','L6','H','HV','U','J','T','K','V','W','X','M','N','R'];
  function terminalPath(sample,type='y'){
    const mt=type==='mt',terminal=String((mt?sample.mt_dna:sample.y_dna)||'').trim();
    const raw=mt?sample.full_mtDNA_path:(real(sample.full_snp_path)?sample.full_snp_path:sample.snp_path);
    if(!real(raw))return real(terminal)?terminal:'—';
    const parts=String(raw).split(/\s*>\s*/).map(x=>x.trim()).filter(real);
    if(!parts.length)return real(terminal)?terminal:'—';
    // A mismatched terminal is a source disagreement, not permission to invent a path.
    const equivalent=(block,label)=>String(block).split(/[\/,]/).some(x=>clean(x)===clean(label));
    if(real(terminal)&&!equivalent(parts.at(-1),terminal))return terminal;
    const anchors=mt?MT_ANCHORS:Y_ANCHORS;
    let first=-1;
    for(const anchor of anchors){first=parts.findIndex(p=>equivalent(p,anchor));if(first>=0)break;}
    if(first<0)first=parts.findIndex(p=>!(/^(?:Y-Adam|mt-Eve|A0-T|A1|A1b|BT|CT|CF|DE|F|GHIJK|HIJK|IJK|IJ|JK|K|LT|L|L3|N|R|[A-T][12]?)$/i.test(p)));
    if(first<0)first=parts.length-1;
    const shown=parts.slice(first);
    if(!mt){
      const prefix=(terminal.match(/^([A-T])-/i)||String(raw).match(/\b([A-T])-/i))?.[1]?.toUpperCase();
      if(prefix)return shown.map((p,i)=>i===0?prefix+'-'+p.replace(new RegExp('^'+prefix+'-','i'),''):p.replace(new RegExp('^'+prefix+'-','i'),'')).join(' > ');
    }
    return shown.join(' > ');
  }
  function providers(sample){
    const result=new Set(sample.__providers||[]);
    for(const k of sample.__identity_keys||[]){if(k.startsWith('ftdna:'))result.add('ftdna');if(k.startsWith('yfull:'))result.add('yfull');}
    if(/^YF\d+$/i.test(sample.yfull_id||'')||/^YF\d+$/i.test(sample.kit_number||''))result.add('yfull');
    else if(/^[A-Z]{0,3}\d+$/i.test(sample.kit_number||''))result.add('ftdna');
    return [...result].filter(x=>['ftdna','yfull'].includes(x));
  }
  function newResults(samples,provider='',query='',now=Date.now()){
    return samples.filter(s=>!s.anonymous&&s.identityStatus!=='anonymous'&&Date.parse(s.__new_until)>now&&providers(s).length>0&&(!provider||providers(s).includes(provider))&&
      (!query||[s.name,s.kit_number,s.yfull_id,s.y_dna,s.mt_dna,s.governorate,...(s.__projects||[])].join(' ').toLowerCase().includes(query.toLowerCase())))
      .sort((a,b)=>Date.parse(b.__tracked_at||b.__new_until)-Date.parse(a.__tracked_at||a.__new_until));
  }
  function strRows(observations){
    const seen=new Set(),rows=[];
    for(const o of observations){
      if(o.published===false)continue;
      for(const [i,m] of (o.payload?.str_markers||[]).entries()){
        const row={...m,position:m.position??i,source:o.payload.source_url,date:o.last_seen_at,current:o.is_current===true};
        const key=JSON.stringify([row.marker,row.source_label,row.position,row.value,row.source,row.current]);
        if(!seen.has(key)){seen.add(key);rows.push(row);}
      }
    }
    return rows.sort((a,b)=>Number(b.current)-Number(a.current)||a.position-b.position);
  }
  function csv(rows){
    const cell=v=>'"'+String(v??'').replace(/^(\s*[=+@-])/i,"'$1").replace(/"/g,'""')+'"';
    return [['Marker','Source label','Alleles','Source URL','Observed at','Evidence status'],
      ...rows.map(r=>[r.marker,r.source_label,r.value??'',r.source,r.date,r.current?'current':'earlier'])]
      .map(row=>row.map(cell).join(',')).join('\r\n');
  }
  const api={terminalPath,providers,newResults,strRows,csv,escape:esc};
  if(typeof module==='object'){module.exports=api;return;}
  root.YDNAProfiles=api;
  let visibleLimit=50;
  root.renderTrackedResults=function(){
    const target=document.getElementById('tracked-results-list');if(!target)return;
    const provider=document.getElementById('tracked-provider').value,query=document.getElementById('tracked-search').value;
    const found=newResults(modernSamples,provider,query);
    document.getElementById('tracked-results-count').textContent=found.length+' newly added public profiles';
    target.innerHTML=found.slice(0,visibleLimit).map(s=>`<article class="tracked-profile"><div class="tracked-profile-heading"><strong>${esc(YDNASync.publicId(s)==='—'?YDNASync.displayName(s):YDNASync.publicId(s))}</strong><span class="project-new-badge">NEW · 30 days</span></div><p>${esc(providers(s).map(p=>p==='ftdna'?'FamilyTreeDNA':'YFull').join(' · '))} · ${esc(s.governorate||'Origin unspecified')}</p><p>${esc(terminalPath(s))}</p><p>${esc((s.__projects||[]).join(' · '))}</p><button type="button" class="ctrl-btn" data-uid="${esc(s.__uid)}" onclick="openSampleModalByUid(this.dataset.uid,'y')">Open profile · STRs & sources</button></article>`).join('')||'<p class="tracked-empty">No new public profiles match this selection. The existing archive is a baseline. Anonymous count increases and source updates do not create named people.</p>';
    const more=document.getElementById('tracked-load-more');more.hidden=found.length<=visibleLimit;more.onclick=()=>{visibleLimit+=50;renderTrackedResults();};
    const history=document.getElementById('tracked-count-changes');
    if(typeof countryTrackerHistory!=='undefined'){
      const recent=countryTrackerHistory.flatMap(s=>s.changes.map(c=>({...c,date:s.observed_at}))).filter(c=>c.kind!=='baseline'&&Date.parse(c.date)>Date.now()-30*86400000);
      history.innerHTML=recent.length?'<ul>'+recent.map(c=>`<li>${esc(YDNACountryTree.changeLabel(c))} · ${esc(countryDate(c.date))}</li>`).join('')+'</ul>':'<p>No published anonymous count changes in the last 30 days. A source baseline is not a newly identified person.</p>';
    }
  };
  root.exportProfileSTRs=function(){
    const profile=document.getElementById('sample-sync-details')?.__strProfile;if(!profile)return;
    const url=URL.createObjectURL(new Blob(['\uFEFF'+csv(profile.markers)],{type:'text/csv;charset=utf-8'}));
    const a=document.createElement('a');a.href=url;a.download='public-profile-STR-evidence.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  };
  document.addEventListener('DOMContentLoaded',()=>{
    const nav=document.getElementById('nav-archive');
    const button=document.createElement('button');button.type='button';button.id='nav-new';button.className=nav.className;button.textContent='New results';
    button.onclick=()=>{showSection('new');renderTrackedResults();loadCountryTracker().then(renderTrackedResults);};nav.after(button);
    const section=document.createElement('main');section.id='section-new';section.className='page-section tracked-results';
    section.innerHTML=`<header><p class="tracked-kicker">Automatic tracking</p><h2>New results</h2><p>New public profiles added in the last 30 days, with source-backed identities, project evidence, STRs and documented terminal paths.</p></header><div class="tracked-controls"><label>Provider <select id="tracked-provider"><option value="">FTDNA & YFull</option><option value="ftdna">FamilyTreeDNA</option><option value="yfull">YFull</option></select></label><label>Search <input type="search" id="tracked-search" placeholder="Kit, branch, place or project"></label></div><p id="tracked-results-count"></p><div id="tracked-results-list" class="tracked-results-grid"></div><button id="tracked-load-more" type="button" class="ctrl-btn" hidden>Show more results</button><section class="tracked-anonymous"><h3>Anonymous reported result changes</h3><p>These are aggregate source changes, separate from identified profiles. A shared branch does not identify an anonymous result.</p><div id="tracked-count-changes"></div></section><p class="tracked-source-note">Only approved feeds and verified saved project evidence are imported. Direct provider sources awaiting permission remain restricted. Open a profile for its actual source dates and STR values.</p>`;
    document.querySelector('footer').before(section);
    for(const id of ['tracked-provider','tracked-search'])document.getElementById(id).addEventListener(id==='tracked-search'?'input':'change',()=>{visibleLimit=50;renderTrackedResults();});
    renderTrackedResults();
  });
})(typeof window==='object'?window:globalThis);
