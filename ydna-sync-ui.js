/* Shared pure helpers; no service credentials and no source fetching in the browser. */
(function (root) {
  'use strict';
  const real = v => v != null && !['', '—', '-'].includes(String(v).trim());
  function status(s) {
    const explicitBigY=/^Big Y-(500|700)$/i.test(s.test_type || '');
    if(explicitBigY && (!real(s.test_status)||s.sync_published?.test_status===s.test_status)) return 'confirmed_big_y';
    if (real(s.test_status)) return s.test_status;
    if (/^YFull sequencing$/i.test(s.test_type || '')) return 'yfull_sequencing';
    if (/^Y[- ]?(?:DNA)?\s*(12|25|37|67|111)$/i.test(s.test_type || '')) return 'str_only';
    return 'unknown';
  }
  const labels = {confirmed_big_y:'Confirmed Big Y',yfull_sequencing:'YFull sequencing',str_only:'STR-only / predicted',snp_tested:'SNP-tested',unknown:'Test evidence unspecified'};
  const normalizedSnp = v => String(v ?? '').trim().toUpperCase().replace(/^[A-T]-/, '').replace(/\*$/, '');
  function documentedDescendant(ancestor, child) {
    if (!real(ancestor.y_dna) || !real(child.y_dna) || !real(child.full_snp_path)) return false;
    const path = child.full_snp_path.split('>').map(normalizedSnp).filter(Boolean);
    const prior = normalizedSnp(ancestor.y_dna);
    // A longer source path must actually contain the earlier terminal SNP.
    return prior !== normalizedSnp(child.y_dna) &&
      path.at(-1) === normalizedSnp(child.y_dna) && path.indexOf(prior) >= 0 &&
      path.indexOf(prior) < path.length - 1;
  }
  const yfullCode = v => /^YF[0-9]+$/.test(String(v ?? '').trim().toUpperCase());
  function identityKeys(sample) {
    const keys=[];
    const kit=String(sample.kit_number ?? '').trim().toUpperCase();
    const yf=String(sample.yfull_id ?? '').trim().toUpperCase();
    // Legacy archive stored YFull sample IDs in the generic kit_number field.
    if (real(kit)) keys.push(yfullCode(kit) ? 'yfull:'+kit : 'ftdna:'+kit);
    if (yfullCode(yf)) keys.push('yfull:'+yf);
    return [...new Set(keys)];
  }
  function identitySummary(sample) {
    const keys=Array.isArray(sample.__identity_keys) ? sample.__identity_keys : identityKeys(sample);
    const kits=keys.filter(k=>k.startsWith('ftdna:')).map(k=>'FTDNA kit: '+k.slice(6));
    const yf=keys.filter(k=>k.startsWith('yfull:')).map(k=>'YFull ID: '+k.slice(6));
    return [...kits,...yf].join(' · ') || (real(sample.sample_id) ? String(sample.sample_id) : '—');
  }
  function deduplicate(samples) {
    // A lineage label or shared /tree/ URL is not evidence of a shared individual.
    // Only an exact FTDNA kit or YFull sample ID can join records.
    const parent=samples.map((_,i)=>i);
    const groupKeys=samples.map(sample=>new Set(identityKeys(sample)));
    const groupConflict=samples.map(()=>false);
    const find=i=>{while(parent[i]!==i){parent[i]=parent[parent[i]];i=parent[i];}return i;};
    const hasDistinctIds=(a,b,namespace)=>{
      const ids=[...new Set([...groupKeys[a],...groupKeys[b]]
        .filter(key=>key.startsWith(namespace+':')))];
      return ids.length>1;
    };
    const union=(i,j)=>{
      let a=find(i),b=find(j);
      if(a===b)return true;
      // Never let an FTDNA-kit bridge collapse distinct YFull sample IDs,
      // or a YFull-ID bridge collapse distinct FTDNA kits.
      if(hasDistinctIds(a,b,'yfull') || hasDistinctIds(a,b,'ftdna')){
        groupConflict[a]=true;groupConflict[b]=true;
        return false;
      }
      parent[b]=a;
      for(const key of groupKeys[b])groupKeys[a].add(key);
      groupConflict[a] ||= groupConflict[b];
      return true;
    };
    const owners=new Map();
    samples.forEach((sample,i)=>{
      for(const key of identityKeys(sample)){
        // Store ALL owners, not just the first: a conflicting cross-link
        // must not prevent a later record with the same exact ID from joining.
        const matches=owners.get(key)||[];
        for(const peer of matches)union(i,peer);
        matches.push(i);
        owners.set(key,matches);
      }
    });
    const groups=new Map();
    samples.forEach((sample,i)=>{
      const root=find(i);
      if(!groups.has(root))groups.set(root,[]);
      groups.get(root).push(sample);
    });
    const score=s=>['y_dna','full_snp_path','name','governorate','test_type',
      'snp_path','mt_dna','full_mtDNA_path','mt_link_1','origin_raw'].filter(k=>real(s[k])).length
      + (s.sync_managed===false ? 1 : 0);
    return [...groups.values()].map(group=>{
      let chosen=group[0], conflict=false;
      for(const next of group.slice(1)){
        const deeper=documentedDescendant(chosen,next);
        const earlier=documentedDescendant(next,chosen);
        const same=normalizedSnp(chosen.y_dna)===normalizedSnp(next.y_dna);
        if(real(chosen.y_dna)&&real(next.y_dna)&&!same&&!deeper&&!earlier)conflict=true;
        if(deeper || (!earlier&&!conflict&&(same||!real(chosen.y_dna))&&score(next)>score(chosen))) chosen=next;
      }
      const allKeys=[...new Set(group.flatMap(identityKeys))];
      const yfull=allKeys.filter(k=>k.startsWith('yfull:')).map(k=>k.slice(6));
      const ftdna=allKeys.filter(k=>k.startsWith('ftdna:')).map(k=>k.slice(6));
      if(yfull.length>1 || ftdna.length>1)conflict=true;
      // Retain original manually documented mtDNA, aliases, STR-related labels
      // and source links whenever a newer import is missing those values.
      // Never overwrite conflicting public claims or fabricate an mtDNA result.
      const result={...chosen,__identity_keys:allKeys,
        __linked_sample_ids:[...new Set(group.map(x=>x.id).filter(x=>x!=null))],
        __duplicate_count:group.length,
        __duplicate_conflict:Boolean(conflict||groupConflict[find(samples.indexOf(group[0]))]||
          group.some(x=>x.__duplicate_conflict))};
      const preservable=['name','origin_raw','governorate','governorate_iso','ethnic_group',
        'snp_path','full_snp_path','mt_dna','full_mtDNA_path','mt_link_1','mt_link_2',
        'y_link_1','y_link_2','y_dna_alias','description'];
      for(const field of preservable){
        if(!real(result[field])){
          const donor=group.find(row=>real(row[field]));
          if(donor)result[field]=donor[field];
        }
      }
      const mitochondrialCalls=[...new Set(group.map(row=>String(row.mt_dna||'').trim()).filter(real))];
      if(mitochondrialCalls.length>1)result.__duplicate_conflict=true;
      result.__source_snp_paths=group.filter(row=>real(row.full_snp_path))
        .map(row=>({sample_id:row.id,source:row.sync_primary_source||
          (row.sync_managed===false?'Original archive':'imported source'),
          path:row.full_snp_path}))
        .filter((row,i,all)=>all.findIndex(other=>other.path===row.path)===i);
      if(yfull.length===1 && !yfullCode(result.yfull_id))result.yfull_id=yfull[0];
      // A YFull identifier is NOT an FTDNA kit number.
      if(ftdna.length===1 && (!real(result.kit_number)||yfullCode(result.kit_number)))
        result.kit_number=ftdna[0];
      return result;
    });
  }
  function compactSnpPath(sample) {
    // The same visible path style for manually curated and imported profiles.
    // Remove only shared prehistoric ancestors and repeated marker prefixes:
    // no unobserved SNP, alias or intermediate branch may be added.
    if(real(sample?.snp_path))return String(sample.snp_path).trim();
    if(!real(sample?.full_snp_path))return real(sample?.y_dna)?String(sample.y_dna):'—';
    const parts=String(sample.full_snp_path).split('>').map(x=>x.trim()).filter(real);
    const root=String(sample.y_dna||'').trim().toUpperCase().charAt(0);
    let from=parts.findIndex(x=>x.toUpperCase()===root);
    if(root==='J'){
      const j=parts.findIndex(x=>/^J[12]$/i.test(x));
      if(j>=0)from=j;
    }
    if(from<0)from=Math.max(0,parts.length-12);
    const display=parts.slice(from).map((segment,i)=>{
      if(i===0)return segment;
      return segment.replace(new RegExp('^'+root+'-','i'),'');
    });
    return display.join('>');
  }
  function yFamily(sample, release, nodes, knownPaths) {
    const y=String(sample.y_dna||'').trim().toUpperCase();
    const root=y.charAt(0);
    if (!['J','Q','R'].includes(root) || (y.length>1 && !/^([JQR])(?:[12]|-)/.test(y))) return null;
    const terminal= root==='J' ?
      (/^J2/.test(y)||['J-M172','J-M410','J-L26','J-M319'].includes(y)?'J2':
        /^J1/.test(y)||['J-M267','J-P58'].includes(y)?'J1':null) :
      root==='Q' ? (/^Q1/.test(y)?'Q1':/^Q2/.test(y)?'Q2':null) :
      (/^R1A/.test(y)?'R1A':/^R1B/.test(y)?'R1B':/^R2/.test(y)?'R2':/^R1/.test(y)?'R1':null);
    const classify=value=>{
      const steps=String(value||'').split('>').map(v=>v.trim().toUpperCase());
      if (root==='J') {
        const j2=steps.some(v=>/^J2/.test(v)||['J-M172','J-M410','J-L26','J-M319'].includes(v));
        const j1=steps.some(v=>/^J1/.test(v)||['J-M267','J-P58'].includes(v));
        return j1&&j2?'conflict':j2?'J2':j1?'J1':null;
      }
      if (root==='Q') {
        const q1=steps.some(v=>/^Q1/.test(v)),q2=steps.some(v=>/^Q2/.test(v));
        return q1&&q2?'conflict':q1?'Q1':q2?'Q2':null;
      }
      const a=steps.some(v=>/^R1A/.test(v)),b=steps.some(v=>/^R1B/.test(v));
      const r1=steps.some(v=>v==='R1'),r2=steps.some(v=>/^R2/.test(v));
      return (a&&b)||(r2&&(r1||a||b))?'conflict':a?'R1A':b?'R1B':r2?'R2':r1?'R1':null;
    };
    const publishedPath=real(sample.full_snp_path)?sample.full_snp_path:
      real(sample.snp_path)?sample.snp_path:
      knownPaths?.get(y) || '';
    const source=classify(publishedPath);
    const official=officialPath(sample,release,nodes);
    const reference=official?classify(official.path.join('>')):null;
    const labels=[source,reference,terminal].filter(Boolean);
    if (labels.includes('conflict')) return root;
    const incompatible=(a,b)=>a!==b && !(root==='R' &&
      ((a==='R1'&&['R1A','R1B'].includes(b))||(b==='R1'&&['R1A','R1B'].includes(a))));
    if (labels.some((a,i)=>labels.slice(i+1).some(b=>incompatible(a,b)))) return root;
    // Prefer complete published / licensed phylogeny. A root-only J-, Q- or R-
    // label must not be silently classified as J1, Q1 or R2.
    return labels.find(v=>!['R1'].includes(v)) || labels[0] || root;
  }
  function matches(sample, kind, governorate, query, newAfter) {
    if (kind && (kind === 'new' ? !(sample.sync_managed && Date.parse(sample.created_at)>newAfter) :
      kind === 'modern' ? sample.__sourceType !== 'modern' :
      kind === 'yfull' ? !real(sample.yfull_id) && status(sample)!=='yfull_sequencing' : status(sample)!==kind)) return false;
    if (governorate && sample.governorate !== governorate) return false;
    if (query) {
      const text = [sample.name,sample.kit_number,sample.yfull_id,sample.y_dna,sample.y_dna_alias,
        sample.full_snp_path,sample.origin_raw,sample.governorate,...(sample.__projects||[])].join(' ').toLocaleLowerCase();
      if (!text.includes(query.toLocaleLowerCase())) return false;
    }
    return true;
  }
  function nodeCounts(node) {
    let modern = 0, bigY = 0;
    const walk = n => {
      for (const s of n.samples || []) if (s.__sourceType === 'modern') { modern++; if(status(s)==='confirmed_big_y') bigY++; }
      for (const c of n.children || []) walk(c);
    };
    walk(node);
    return {direct:(node.samples||[]).filter(s=>s.__sourceType==='modern').length,modern,bigY};
  }
  function terminalPath(sample, knownPaths) {
    const path = real(sample.full_snp_path) ? sample.full_snp_path : real(sample.snp_path) ? sample.snp_path : '';
    if (!real(sample.full_snp_path) && knownPaths?.has(String(sample.y_dna||'').toUpperCase())) return knownPaths.get(String(sample.y_dna||'').toUpperCase());
    // A terminal-only record remains visible; no intermediate branches are invented.
    return path || (real(sample.y_dna) ? 'Y-Adam>'+sample.y_dna : '');
  }
  function knownTerminalPaths(samples) {
    const options=new Map();
    for(const s of samples) if(real(s.full_snp_path) && real(s.y_dna)) {
      const path=s.full_snp_path.trim();
      const last=path.split('>').at(-1).trim().toUpperCase().replace(/^[A-T]-/,'');
      const terminal=s.y_dna.trim().toUpperCase().replace(/^[A-T]-/,'');
      if(last!==terminal) continue;
      const key=s.y_dna.toUpperCase();
      if(!options.has(key)) options.set(key,new Set());
      options.get(key).add(path);
    }
    return new Map([...options].filter(([,paths])=>paths.size===1).map(([label,paths])=>[label,[...paths][0]]));
  }
  function inCountScope(sample, fact, knownPaths) {
    const target=String(fact.node_label||'').toUpperCase();
    const terminal=String(sample.y_dna||'').toUpperCase();
    if(terminal===target) return true;
    if(fact.count_scope!=='inclusive') return false;
    // Only a published path (or an unambiguous previously published path) establishes descent.
    const path=terminalPath(sample,knownPaths).toUpperCase().split('>').map(s=>s.trim());
    const head=target.split('-')[0];
    if(target.includes('-') && terminal.split('-')[0]!==head) return false;
    return path.some(s=>s===target || (target.includes('-') && s===target.slice(target.indexOf('-')+1)));
  }
  function reconcileCountryCount(fact, samples, knownPaths) {
    const comparable=(fact.namespace==='ftdna' && fact.population==='ftdna_big_y') ||
      (fact.namespace==='yfull' && fact.population==='yfull_modern');
    const ids=new Set();
    for(const sample of samples) {
      if(sample.__sourceType!=='modern' || !inCountScope(sample,fact,knownPaths)) continue;
      if(fact.namespace==='ftdna' && status(sample)==='confirmed_big_y' &&
        /^[A-Z]{0,3}\d+$/i.test(sample.kit_number||'') && !/^YF\d+$/i.test(sample.kit_number)) {
        ids.add(String(sample.kit_number).toUpperCase());
      }
      if(fact.namespace==='yfull') {
        const id=/^YF\d+$/i.test(sample.yfull_id||'')?sample.yfull_id:
          /^YF\d+$/i.test(sample.kit_number||'')?sample.kit_number:null;
        if(id) ids.add(String(id).toUpperCase());
      }
    }
    const known=ids.size, reported=Number(fact.reported_count);
    const conflict=comparable && known>reported;
    return {reported,known,comparable,conflict,
      unresolved:comparable&&!conflict?reported-known:null,
      method:'cohort_comparison_only'};
  }
  function officialPath(sample,release,nodes) {
    if(!release || !nodes?.size) return null;
    const queries=[sample.y_dna,...String(sample.y_dna_alias||'').split(/[,;/|\s]+/)].filter(real);
    const found=new Set();
    for(const query of queries) {
      const label=String(query).toUpperCase();
      const match=release.metadata?.matches?.[label];
      if (match) {
        if (['exact','equivalent_snp'].includes(match.status) && nodes.has(match.label)) found.add(match.label);
      } else if (nodes.has(label)) {
        // The licensed, versioned tree itself is evidence for an exact SNP label,
        // including nodes that were not in the older archive when matches were built.
        found.add(label);
      }
    }
    if(found.size!==1) return null;
    const label=[...found][0],path=[],seen=new Set();let current=label;
    while(current!=null) {
      if(seen.has(current) || !nodes.has(current)) return null;
      seen.add(current);path.push(current);current=nodes.get(current).parent_label;
    }
    if(path.at(-1)!=='Y-Adam') return null;
    return {label,path:path.reverse(),version:release.version};
  }
  function officialPlacement(sample,release,nodes,mode,knownPaths) {
    if(mode==='published') return null;
    if(mode==='auto' && (real(sample.full_snp_path)||real(sample.snp_path)||knownPaths?.has(String(sample.y_dna||'').toUpperCase()))) return null;
    return officialPath(sample,release,nodes);
  }
  function displayName(sample) {
    return [sample.name,sample.yfull_id,
      yfullCode(sample.kit_number) ? sample.kit_number : null,
      sample.kit_number,sample.sample_id].find(real)||'—';
  }
  function publicId(sample) {
    const keys=Array.isArray(sample.__identity_keys) ? sample.__identity_keys : identityKeys(sample);
    const kit=keys.find(k=>k.startsWith('ftdna:'));
    const yf=keys.find(k=>k.startsWith('yfull:'));
    return kit?.slice(6) || yf?.slice(6) || (real(sample.sample_id)?sample.sample_id:'—');
  }
  const api = {status,labels,deduplicate,identityKeys,identitySummary,compactSnpPath,yFamily,documentedDescendant,matches,nodeCounts,terminalPath,knownTerminalPaths,inCountScope,reconcileCountryCount,officialPath,officialPlacement,displayName,publicId};
  if (typeof module === 'object') module.exports=api;
  else root.YDNASync=api;
})(typeof window === 'object' ? window : globalThis);
