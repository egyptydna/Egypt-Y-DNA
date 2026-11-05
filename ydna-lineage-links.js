/* Navigation to a lineage never establishes an individual's provider identity. */
(function(root){
 'use strict';
 const safeURL=value=>{try{const u=new URL(value);return u.protocol==='https:'&&!u.username&&!u.password?u:null;}catch{return null;}};
 const typedFTDNA=value=>/^[A-Z]{0,3}[0-9]+$/i.test(String(value||'').trim())&&!/^YF[0-9]+$/i.test(String(value||'').trim());
 function ftdnaFirst(sample){
  return typedFTDNA(sample.kit_number)||
   (sample.__identity_keys||[]).some(key=>String(key).startsWith('ftdna:')&&typedFTDNA(String(key).slice(6)))||
   (sample.__providers||[]).some(provider=>String(provider).toLowerCase()==='ftdna')||
   /\b(?:FTDNA|Family\s*Tree\s*DNA|Family\s*Finder|Big\s*Y)\b|^Y[- ]?(?:DNA)?\s*(?:12|25|37|67|111)\b/i.test(String(sample.test_type||''));
 }
 function links(sample,type='y',reference={}){
  const mt=type==='mt',input=String((mt?sample.mt_dna:sample.y_dna)||'').trim().replace(/\*+$/,''),raw=mt?input:input.toUpperCase();
  if(!(mt?/^[A-Z][A-Za-z0-9.+_-]{0,70}$/:/^[A-T](?:-[A-Z0-9][A-Z0-9.+_-]{0,70}|[0-9][A-Z0-9.]{0,40})?$/).test(raw))return [];
  const explicit=(mt?[sample.mt_link_1,sample.mt_link_2]:[sample.y_link_1,sample.y_link_2,sample.yfull_reference_url]).map(safeURL).filter(Boolean);
  const match=reference.release?.metadata?.matches?.[raw];
  const canonical=!mt&&(reference.nodes?.has(raw)?raw:match&&['exact','equivalent_snp'].includes(match.status)&&reference.nodes?.has(match.label)?match.label:null);
  const yf=explicit.find(u=>['www.yfull.com','yfull.com'].includes(u.hostname)&&u.pathname.startsWith(mt?'/mtree/':'/tree/'));
  const ft=explicit.find(u=>u.hostname==='discover.familytreedna.com'&&u.pathname.toLowerCase().startsWith('/y-dna/'));
  const result=[{provider:'yfull',label:'YFull',url:yf?.href||'https://www.yfull.com/'+(mt?'mtree/':'tree/')+encodeURIComponent(canonical||raw)+'/',status:yf||canonical?'reference':'lookup',branch:canonical||raw}];
  if(!mt)result.push({provider:'ftdna',label:'FamilyTreeDNA Discover',url:ft?.href||'https://discover.familytreedna.com/y-dna/'+encodeURIComponent(raw)+'/tree',status:ft?'reference':'lookup',branch:raw});
  else{const source=explicit.find(u=>u.hostname==='www.familytreedna.com'||u.hostname==='familytreedna.com');if(source)result.push({provider:'ftdna',label:'FamilyTreeDNA source',url:source.href,status:'reference',branch:raw});}
  const preferred=ftdnaFirst(sample)?'ftdna':'yfull';
  return result.sort((a,b)=>Number(a.provider!==preferred)-Number(b.provider!==preferred));
 }
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 function html(sample,type='y',compact=false,reference={}){const found=links(sample,type,reference);return found.length?`<span class="lineage-provider-links ${compact?'lineage-provider-compact':''}">${found.map(l=>`<a href="${esc(l.url)}" target="_blank" rel="noopener noreferrer" data-lineage-provider="${l.provider}" data-link-status="${l.status}" title="${esc(l.status==='reference'?'Lineage target from a published reference / source':'Open this lineage at the provider; current availability is not verified')}">${compact?(l.provider==='yfull'?'YF':'FTDNA'):esc(l.label)} ↗${!compact&&l.status==='lookup'?' <small>Linie prüfen</small>':''}</a>`).join('')}</span>`:'';}
 const api={links,html};if(typeof module==='object')module.exports=api;else{root.YDNALineageLinks=api;root.lineageLinkHTML=(sample,type='y',compact=false)=>html(sample,type,compact,{release:typeof syncOfficialRelease==='undefined'?null:syncOfficialRelease,nodes:typeof syncOfficialNodes==='undefined'?null:syncOfficialNodes});}
})(typeof window==='object'?window:globalThis);
