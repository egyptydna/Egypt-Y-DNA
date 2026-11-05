/* Anonymous country census. Counts are never manufactured individual profiles. */
(function(root){
  'use strict';
  const key=s=>String(s).toUpperCase();
  function build(snapshot){
    const make=(label,path,parent=null)=>({raw:label,display:label,pathKey:path,children:[],samples:[],count:0,directCount:0,parent,aliases:[]});
    const tree=make('Y-Adam','Y-Adam'),terminals=new Set(),parents=new Map();
    let total=0;
    for(const fact of snapshot.nodes){
      if(!Number.isInteger(fact.count)||fact.count<0||terminals.has(key(fact.label)))throw Error('Invalid country counts');
      terminals.add(key(fact.label));total+=fact.count;
      let path=fact.path?.length?[...fact.path]:[fact.label];
      if(key(path.at(-1))!==key(fact.label)||new Set(path.map(key)).size!==path.length)throw Error('Invalid published ancestry');
      if(path[0]==='Y-Adam')path.shift();
      for(let i=0;i<path.length;i++){
        const label=key(path[i]),parent=i?key(path[i-1]):'Y-ADAM';
        if(parents.has(label)&&parents.get(label)!==parent)throw Error('Conflicting reference parents');
        parents.set(label,parent);
      }
      let node=tree;
      for(const label of path){
        let child=node.children.find(n=>key(n.display)===key(label));
        if(!child){child=make(label,node.pathKey+'>'+label,node);node.children.push(child);}
        node=child;
      }
      node.directCount=fact.count;node.fact=fact;
    }
    if(total!==snapshot.total_count)throw Error('Incomplete country snapshot');
    function sum(node){node.count=node.directCount+node.children.reduce((n,c)=>n+sum(c),0);return node.count;}
    sum(tree);return tree;
  }
  function compact(node,full=false,keepLabels=new Set()){
    const children=node.children.map(c=>compact(c,full,keepLabels));
    if(!full&&node.display!=='Y-Adam'&&!node.directCount&&!keepLabels.has(key(node.display))&&children.length===1)return children[0];
    return {...node,parent:null,children};
  }
  function find(node,path){return node.pathKey===path?node:node.children.map(c=>find(c,path)).find(Boolean);}
  function flatten(node){return [node,...node.children.flatMap(flatten)];}
  function profilesByBranch(samples){
    const branches=new Map();
    for(const sample of samples){
      // A dated alias block or shared surname cannot prove a current terminal
      // placement. Use the preserved, exact published terminal only.
      const label=key(String(sample.y_dna||'').trim());
      if(!/^[A-T]-[A-Z0-9*.+_-]+$/.test(label))continue;
      if(!branches.has(label))branches.set(label,[]);
      branches.get(label).push(sample);
    }
    return branches;
  }
  function changeLabel(change){
    const delta=change.after_count-(change.before_count??change.after_count);
    if(change.kind==='baseline')return `Baseline: ${change.after_count} reported results`;
    if(change.kind==='total_increase')return `+${delta} newly reported results · ${change.after_count} total`;
    if(change.kind==='total_decrease')return `${delta} change in reported country total · ${change.after_count} total`;
    if(change.kind==='reference_update')return 'Reference / source update · country total unchanged';
    return `${change.branch_label}: ${change.before_count} → ${change.after_count} · branch count change`;
  }
  const api={build,compact,find,flatten,changeLabel,profilesByBranch};
  if(typeof module==='object')module.exports=api;else root.YDNACountryTree=api;
})(typeof window==='object'?window:globalThis);
