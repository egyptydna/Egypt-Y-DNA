/* Shared pure helpers; no service credentials and no source fetching in the browser. */
(function (root) {
  'use strict';
  const real = v => v != null && !['', '—', '-'].includes(String(v).trim());
  function status(s) {
    if (real(s.test_status)) return s.test_status;
    if (/^Big Y-(500|700)$/i.test(s.test_type || '')) return 'confirmed_big_y';
    if (/^YFull sequencing$/i.test(s.test_type || '')) return 'yfull_sequencing';
    if (/^Y[- ]?(?:DNA)?\s*(12|25|37|67|111)$/i.test(s.test_type || '')) return 'str_only';
    return 'unknown';
  }
  const labels = {confirmed_big_y:'Confirmed Big Y',yfull_sequencing:'YFull sequencing',str_only:'STR-only / predicted',snp_tested:'SNP-tested',unknown:'Test evidence unspecified'};
  function deduplicate(samples) {
    const map = new Map();
    for (const sample of samples) {
      const key = real(sample.kit_number) ? 'ftdna:'+sample.kit_number.trim().toUpperCase() :
        real(sample.yfull_id) ? 'yfull:'+sample.yfull_id.trim().toUpperCase() : 'row:'+sample.id;
      if (!map.has(key)) map.set(key, sample);
      else {
        const prior = map.get(key);
        // Same published ID only. Keep the richer profile without combining conflicting values.
        const score = s => ['y_dna','full_snp_path','name','governorate'].filter(k=>real(s[k])).length;
        if (score(sample)>score(prior)) map.set(key,sample);
      }
    }
    return [...map.values()];
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
      const match=release.metadata?.matches?.[String(query).toUpperCase()];
      if(match && ['exact','equivalent_snp'].includes(match.status) && nodes.has(match.label)) found.add(match.label);
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
  const api = {status,labels,deduplicate,matches,nodeCounts,terminalPath,knownTerminalPaths,inCountScope,reconcileCountryCount,officialPath};
  if (typeof module === 'object') module.exports=api;
  else root.YDNASync=api;
})(typeof window === 'object' ? window : globalThis);
