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
    if (!real(sample.full_snp_path) && knownPaths?.has(sample.y_dna)) return knownPaths.get(sample.y_dna);
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
      if(!options.has(s.y_dna)) options.set(s.y_dna,new Set());
      options.get(s.y_dna).add(path);
    }
    return new Map([...options].filter(([,paths])=>paths.size===1).map(([label,paths])=>[label,[...paths][0]]));
  }
  const api = {status,labels,deduplicate,matches,nodeCounts,terminalPath,knownTerminalPaths};
  if (typeof module === 'object') module.exports=api;
  else root.YDNASync=api;
})(typeof window === 'object' ? window : globalThis);
