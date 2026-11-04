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
  function deduplicate(samples) {
    const map = new Map();
    const score = s => ['y_dna','full_snp_path','name','governorate','test_type'].filter(k=>real(s[k])).length;
    for (const sample of samples) {
      // Dash placeholders are not identities. Never deduplicate by a name or shared haplogroup.
      const key = real(sample.kit_number) ? 'ftdna:'+sample.kit_number.trim().toUpperCase() :
        real(sample.yfull_id) ? 'yfull:'+sample.yfull_id.trim().toUpperCase() : 'row:'+sample.id;
      if (!map.has(key)) {map.set(key, sample); continue;}
      const prior = map.get(key);
      const newerDescendant = documentedDescendant(prior, sample);
      const olderDescendant = documentedDescendant(sample, prior);
      const sameCall = normalizedSnp(prior.y_dna) === normalizedSnp(sample.y_dna);
      const conflict = real(prior.y_dna) && real(sample.y_dna) &&
        !sameCall && !newerDescendant && !olderDescendant;
      // Prefer a documented descendant over an older upstream call, not the first row.
      const chooseNew = newerDescendant || (!olderDescendant && !conflict &&
        (sameCall || !real(prior.y_dna)) && score(sample)>score(prior));
      const chosen = chooseNew ? sample : prior;
      map.set(key, {...chosen, __duplicate_count:(prior.__duplicate_count||1)+1,
        __duplicate_conflict:Boolean(prior.__duplicate_conflict || conflict)});
    }
    return [...map.values()];
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
    return [sample.name,sample.yfull_id,sample.kit_number,sample.sample_id].find(real)||'—';
  }
  function publicId(sample) {
    return [sample.kit_number,sample.yfull_id,sample.sample_id].find(real)||'—';
  }
  const api = {status,labels,deduplicate,yFamily,documentedDescendant,matches,nodeCounts,terminalPath,knownTerminalPaths,inCountScope,reconcileCountryCount,officialPath,officialPlacement,displayName,publicId};
  if (typeof module === 'object') module.exports=api;
  else root.YDNASync=api;
})(typeof window === 'object' ? window : globalThis);
