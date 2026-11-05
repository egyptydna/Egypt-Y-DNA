/* Shared compact phylogeny view. Data and placement remain in the archive model. */
(function(root) {
  'use strict';
  const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function sample(row,options) {
    const identity=options.identity(row),name=options.name(row);
    const kind=row.__sourceType||'modern';
    return `<li class="phylo-sample"><button type="button" class="tree-sample-card phylo-sample-row" data-uid="${escape(row.__uid)}" onclick="openSampleModalByUid(this.dataset.uid)">
      <span class="phylo-sample-id">${escape(identity||name)}</span>
      ${identity&&name!==identity&&name!=='—'?`<span class="phylo-sample-person">${escape(name)}</span>`:''}
      <span class="phylo-sample-origin">${escape(options.location(row))}</span>
      <span class="phylo-sample-test">${escape(options.test(row))}</span>
      ${kind!=='modern'?`<span class="phylo-kind phylo-kind-${escape(kind)}">${escape({related:'Related ancient',ancient:'Egyptian ancient',study:'Study'}[kind]||kind)}</span>`:''}
      ${row.__duplicate_conflict?'<span class="phylo-warning">Conflicting results · review</span>':''}
      ${options.issue(row)?`<span class="phylo-warning">${escape(options.issue(row))}</span>`:''}
      <span class="phylo-detail-hint">Details ›</span>
    </button></li>`;
  }
  function node(row,options,isRoot=false) {
    const open=!options.collapsed.has(row.pathKey),expandable=row.children.length||row.samples.length;
    const names=options.names(row),encoded=escape(encodeURIComponent(row.pathKey));
    const lazy=typeof options.hasEvidence==='function';
    const evidence=lazy?options.hasEvidence(row):options.evidence(row),age=options.age(row);
    const body=open?row.samples.map(s=>sample(s,options)).join('')+options.sort(row.children).map(n=>node(n,options)).join(''):'';
    const header=`<div class="tree-row phylo-node-row">
      <button type="button" class="phylo-toggle" aria-label="${open?'Collapse':'Expand'} ${escape(names.primary)}" aria-expanded="${!!open}" ${expandable?'':'disabled'} data-path="${encoded}" onclick="return handleTreeToggleClick(event)">${expandable?(open?'−':'+'):'·'}</button>
      <button type="button" class="phylo-node-name" data-path="${encoded}" onclick="return handleTreePathClick(event)">${escape(names.primary)}</button>
      ${names.secondary?`<span class="phylo-platform-names">${escape(names.secondary)}</span>`:''}
      <span class="phylo-count" title="Profiles in the displayed subtree, including this node">${row.count} profiles</span>
      ${options.counts(row)}
      ${options.country?options.country(row):''}
      ${age?`<span class="phylo-age">${escape(age)}</span>`:''}
      ${evidence?`<details class="phylo-evidence" data-node-path="${encoded}" data-node-label="${escape(row.display)}" ${lazy?'ontoggle="loadPhyloEvidence(this)"':''}><summary>Sources</summary><div class="phylo-evidence-body">${lazy?'Open to load source details.':evidence}</div></details>`:''}
    </div>`;
    const aliases=options.aliases(row);
    const inner=header+(aliases?`<div class="phylo-snps"><span>Published SNPs / names:</span> ${aliases}</div>`:'')+(body?`<ul class="${isRoot?'tree-ul focused-root-list':'phylo-children'}">${body}</ul>`:'');
    return isRoot?`<div class="phylo-root" data-tree="${escape(options.type)}">${inner}</div>`:`<li class="phylo-node">${inner}</li>`;
  }
  const api={node,sample,escape};
  if(typeof module==='object')module.exports=api;else root.DNATreeView=api;
})(typeof window==='object'?window:globalThis);
