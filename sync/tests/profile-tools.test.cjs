const {test}=require('node:test');const assert=require('node:assert/strict');
const ui=require('../../ydna-profile-tools.js');
test('E-V13 path starts at the documented major branch and keeps the exact terminal chain',()=>{
 const sample={y_dna:'E-TEST1',full_snp_path:'Y-Adam>CT>E>M35>M78>V13>CTS1>TEST1'};
 assert.equal(ui.terminalPath(sample),'E-V13 > CTS1 > TEST1');
 assert.equal(sample.full_snp_path,'Y-Adam>CT>E>M35>M78>V13>CTS1>TEST1');
 assert.equal(ui.terminalPath({y_dna:'E-TEST1',full_snp_path:'Y-Adam>E>M35>TEST1'}),'E-M35 > TEST1');
 assert.equal(ui.terminalPath({y_dna:'E-V13'}),'E-V13');
 assert.equal(ui.terminalPath({y_dna:'E-OTHER',full_snp_path:'Y-Adam>E>M78>V13>TEST1'}),'E-OTHER');
});
test('mtDNA starts at a documented haplogroup and never at mt-Eve by default',()=>{
 assert.equal(ui.terminalPath({mt_dna:'U3b3d2a',full_mtDNA_path:'mt-Eve>L>L3>N>R>U>U3>U3b>U3b3>U3b3d2a'},'mt'),'U3 > U3b > U3b3 > U3b3d2a');
 assert.equal(ui.terminalPath({mt_dna:'H1c'},'mt'),'H1c');
});
test('new results filter by saved 30-day window and typed provider, not anonymous counts',()=>{
 const now=Date.parse('2026-11-05T00:00:00Z'),fresh='2026-11-10T00:00:00Z';
 const rows=[{kit_number:'990001',__new_until:fresh,__projects:['Egypt']},{yfull_id:'YF990002',__new_until:fresh},{kit_number:'990003',__new_until:'2026-11-04T00:00:00Z'},{anonymous:true,kit_number:'990004',observed_count:3,__new_until:fresh}];
 assert.equal(ui.newResults(rows,'','',now).length,2);
 assert.equal(ui.newResults(rows,'ftdna','Egypt',now).length,1);
 assert.equal(ui.newResults(rows,'yfull','',now)[0].yfull_id,'YF990002');
 assert.equal(ui.providers({kit_number:'YF990002'})[0],'yfull');
});
test('STR evidence keeps zeroes, microvariants, multicopy alleles, positions and conflicting sources',()=>{
 const a={is_current:true,published:true,last_seen_at:'2026-11-05',payload:{source_url:'https://example.org/a',str_markers:[{marker:'DYS425',source_label:'DYS425',position:0,value:'0'},{marker:'DYS464',source_label:'DYS464',position:1,value:'14-16-17-17'},{marker:'DYS458',source_label:'DYS458',position:2,value:'18.2'}]}};
 const b={...a,payload:{source_url:'https://example.org/b',str_markers:[{marker:'DYS425',source_label:'DYS425',position:0,value:'1'}]}};
 const rows=ui.strRows([a,a,b]);assert.equal(rows.length,4);
 assert(rows.some(r=>r.value==='0'));assert(rows.some(r=>r.value==='18.2'));assert(rows.some(r=>r.value==='14-16-17-17'));
 assert.equal(ui.strRows([{...a,published:false}]).length,0);
 const repeated={...a,payload:{source_url:'https://example.org/a',str_markers:[{marker:'DYS464',source_label:'DYS464',position:0,value:'14'},{marker:'DYS464',source_label:'DYS464',position:1,value:'14'}]}};
 assert.equal(ui.strRows([repeated]).length,2);
 const csv=ui.csv(rows);assert(csv.includes('"0"'));assert(csv.includes('https://example.org/b'));
 assert(ui.csv([{marker:'=1+1'}]).includes("'=1+1"));
});
test('copy STRs preserves one current panel order, zeroes and multicopy alleles',()=>{
 const rows=[{source:'a',source_label:'DYS425',position:0,value:'0',current:true},{source:'b',source_label:'DYS425',position:0,value:'1',current:true},{source:'a',source_label:'DYS464',position:1,value:'14-16',current:true},{source:'a',source_label:'DYS458',position:2,value:'18.2',current:false}];
 assert.equal(ui.strText(rows),'DYS425\t0\nDYS464\t14-16');
 assert.equal(ui.strText(rows.filter(r=>!r.current)),'');
});
test('archive sorting is stable and supports main group, name and newest',()=>{
 const rows=[{id:1,name:'Zeta',y_dna:'R-B',created_at:'2026-01-01'},{id:2,name:'Alpha',y_dna:'E-X',created_at:'2026-02-01'},{id:3,name:'Beta',y_dna:'J-X',created_at:'2026-03-01'}];
 assert.deepEqual(ui.sortProfiles(rows,'name').map(s=>s.id),[2,3,1]);
 assert.deepEqual(ui.sortProfiles(rows,'newest').map(s=>s.id),[3,2,1]);
 assert.deepEqual(['R2','R1B','J2','E','Q2','R1A','J1','Q1','A'].sort(ui.groupCompare),['A','E','J1','J2','Q1','Q2','R1A','R1B','R2']);
 assert.deepEqual(rows.map(s=>s.id),[1,2,3]);
});
