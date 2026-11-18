/* Owner-curated equivalent branch names. Raw test results are retained. */
(function(root){
 'use strict';
 let records=[];const index=new Map();let loading=null;
 const key=(type,label)=>type+':'+String(label||'').trim().toUpperCase();
 const esc=v=>YDNAProfiles.escape(v);
 function setRecords(rows){records=rows.filter(r=>r.owner_active!==false);index.clear();for(const r of records)for(const label of r.match_labels||[r.canonical_label,...r.aliases])index.set(key(r.dna_type,label),r);}
 function info(label,type='y'){return index.get(key(type,label));}
 function names(label,type='y'){const r=info(label,type);return r?[...new Set([r.canonical_label,...r.aliases])].filter(v=>v.toUpperCase()!==String(label||'').toUpperCase()):[];}
 function terms(sample){return [sample.y_dna,...names(sample.y_dna,'y'),sample.mt_dna,...names(sample.mt_dna,'mt')].filter(Boolean).join(' ');}
 function matches(sample,q){return !!q&&[...names(sample.y_dna,'y'),...names(sample.mt_dna,'mt')].some(v=>v.toLowerCase().includes(String(q).trim().toLowerCase()));}
 async function load(force=false){if(loading&&!force)return loading;loading=(async()=>{const rows=[];for(let offset=0;;offset+=1000){const r=await _sb.from('ydna_owner_lineages').select('record_key,dna_type,canonical_label,aliases,match_labels,source_url,note,owner_active,owner_modified_at').order('record_key').range(offset,offset+999);if(r.error)return;rows.push(...r.data);if(r.data.length<1000)break;}setRecords(rows);})();return loading;}
 function html(sample,type='y'){const label=type==='mt'?sample.mt_dna:sample.y_dna,r=info(label,type);if(!r||(!names(label,type).length&&!r.note&&!r.source_url))return '';let url='';try{const u=new URL(r.source_url);if(u.protocol==='https:'&&!u.username&&!u.password)url=u.href;}catch{}return `<div class="owner-lineage-note"><strong>Weitere Namen dieser Linie</strong><p>${esc([r.canonical_label,...r.aliases].join(' / '))}</p><small>Betreiberergänzung; ursprüngliche Quellenbezeichnung: ${esc(label)}</small>${r.note?`<p>${esc(r.note)}</p>`:''}${url?`<p><a href="${esc(url)}" target="_blank" rel="noopener noreferrer">Quelle der zusätzlichen Namen ↗</a></p>`:''}</div>`;}
 const api={setRecords,info,names,terms,matches,load,html};
 if(typeof module==='object')module.exports=api;else{root.YDNAOwnerLineages=api;root.loadOwnerLineages=load;root.ownerLineageInfoHTML=html;}
})(typeof window==='object'?window:globalThis);
