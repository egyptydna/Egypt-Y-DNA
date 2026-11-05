/* Shared compact phylogeny view. Data and placement remain in the archive model. */
(function(root) {
  'use strict';
  const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function sample(row,options) {
    const identity=options.identity(row),name=options.name(row);
    const kind=row.__sourceType||'modern';
    return `<li class="phylo-sample" data-kind="${escape(kind)}"><button type="button" class="tree-sample-card phylo-sample-row" data-uid="${escape(row.__uid)}" data-dna="${escape(options.type)}" onclick="openSampleModalByUid(this.dataset.uid,this.dataset.dna)">
      ${kind==='modern'?'<svg class="phylo-person-icon" aria-hidden="true" viewBox="0 0 12 12"><circle cx="6" cy="3" r="2"/><path d="M2 11V9a4 4 0 0 1 8 0v2z"/></svg>':`<span class="phylo-cohort-symbol phylo-cohort-${escape(kind)}" role="img" aria-label="${escape({study:'Study sample',ancient:'Ancient Egyptian sample',related:'Related ancient reference'}[kind]||'Source record')}">${{study:'▤',ancient:'†',related:'◇'}[kind]||'·'}</span>`}<span class="phylo-sample-id">${escape(identity||name)}</span>
      ${identity&&name!==identity&&name!=='—'?`<span class="phylo-sample-person">${escape(name)}</span>`:''}
      ${options.countryLabel?.(row)?`<span class="phylo-sample-country">${escape(options.countryLabel(row))}</span>`:''}<span class="phylo-sample-origin">${escape(options.location(row))}</span>
      <span class="phylo-sample-test">${escape(options.test(row))}</span>
      ${options.providers?.(row)?.map(p=>`<span class="phylo-provider">${escape(p==='yfull'?'YFull':'FTDNA')}</span>`).join('')||''}
      ${options.isNew?.(row)?'<span class="project-new-badge">NEW · 30 days</span>':''}
      ${kind!=='modern'?`<span class="phylo-kind phylo-kind-${escape(kind)}">${escape({related:'Related ancient',ancient:'Egyptian ancient',study:'Study'}[kind]||kind)}</span>`:''}
      ${row.__duplicate_conflict?'<span class="phylo-warning">Conflicting results · review</span>':''}
      ${options.issue(row)?`<span class="phylo-warning">${escape(options.issue(row))}</span>`:''}
      <span class="phylo-detail-hint">Details ›</span>
    </button></li>`;
  }
  function node(row,options,isRoot=false) {
    const open=!options.collapsed.has(row.pathKey),expandable=row.children.length||row.samples.length||row.directCount||options.hasGroup?.(row);
    const names=options.names(row),encoded=escape(encodeURIComponent(row.pathKey));
    const lazy=typeof options.hasEvidence==='function';
    const evidence=lazy?options.hasEvidence(row):options.evidence(row),age=options.age(row);
    const aliases=options.aliases(row);
    const body=open?(options.group?options.group(row):'')+(options.sampleGroup?options.sampleGroup(row):(options.sortSamples?options.sortSamples(row.samples):row.samples).map(s=>sample(s,options)).join(''))+options.sort(row.children).map(n=>node(n,options)).join(''):'';
    const header=`<div class="tree-row phylo-node-row">
      <button type="button" class="phylo-toggle" aria-label="${open?'Collapse':'Expand'} ${escape(names.primary)}" aria-expanded="${!!open}" ${expandable?'':'disabled'} data-path="${encoded}" onclick="return handleTreeToggleClick(event)">${expandable?(open?'−':'+'):'·'}</button>
      <button type="button" class="phylo-node-name" data-path="${encoded}" onclick="return handleTreePathClick(event)">${escape(names.primary)}</button>
      ${aliases?`<span class="phylo-snps" aria-label="Published defining variants">${aliases}</span>`:''}
      ${names.secondary?`<span class="phylo-platform-names" title="${escape(names.note||'Published source branch names')}">${escape(names.secondary)}</span>`:''}
      <span class="phylo-count" title="${options.countLabel?'Source-reported results including descendants':'Profiles in the displayed subtree, including this node'}">${options.countLabel?escape(options.countLabel(row)):row.count+(row.count===1?' profile':' profiles')}</span>
      ${options.counts(row)}
      ${options.country?options.country(row):''}
      ${age?`<span class="phylo-age" title="${escape(options.ageTitle?.(row)||'Published lineage age estimate, not the age of an individual sample')}">${escape(age)}</span>`:''}
      ${evidence?`<details class="phylo-evidence" data-node-path="${encoded}" data-node-label="${escape(row.display)}" ${lazy?'ontoggle="loadPhyloEvidence(this)"':''}><summary>info</summary><div class="phylo-evidence-body">${lazy?'Open to load source details.':evidence}</div></details>`:''}
    </div>`;
    const inner=header+(body?`<ul class="${isRoot?'tree-ul focused-root-list':'phylo-children'}">${body}</ul>`:'');
    return isRoot?`<div class="phylo-reference-bar"><strong>${options.type==='mt'?'Egypt mtDNA Tree':'Egypt Y-DNA Tree'}</strong><span>View:</span><button type="button" onclick="setTreeMode('direct')">compact</button><button type="button" onclick="setTreeMode('full')">full path</button><span class="phylo-reference-credit">Public archive · source-backed branches</span></div><div class="phylo-root" data-tree="${escape(options.type)}" data-root-label="${escape(row.display)}">${inner}</div>`:`<li class="phylo-node">${inner}</li>`;
  }
  const api={node,sample,escape};
  if(typeof module==='object')module.exports=api;else root.DNATreeView=api;
})(typeof window==='object'?window:globalThis);
