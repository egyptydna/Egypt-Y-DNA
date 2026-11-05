// Exclusively synthetic fixtures: no real sample IDs or individual genetic records.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const ui=require('../../ydna-sync-ui.js');
const census=require('../../ydna-country-tree.js');
test('combined tree adds missing YFull and ancient branches without changing anonymous counts',()=>{
 const original=census.build({total_count:3,nodes:[{label:'E-COUNT',count:3,path:['E-V13','E-COUNT']}]});
 const entries=[{sample:{__uid:'yf',yfull_id:'SYNTHETIC-YFULL-ONLY'},path:['Y-Adam','J-M267','J-PROFILE']},{sample:{__uid:'ancient',__sourceType:'ancient'},path:['Y-Adam','E-V13']},{sample:{__uid:'new'},path:['Y-Adam','E-V13','E-NEW']}];
 const tree=census.overlay(original,[...entries,entries[0]]);
 assert.equal(tree.count,3);assert.equal(tree.profileCount,3);
 assert.equal(census.flatten(tree).filter(n=>n.samples.length).length,3);
 assert.equal(census.flatten(tree).find(n=>n.display==='E-NEW').parent.display,'E-V13');
 assert.equal(census.flatten(tree).find(n=>n.display==='J-PROFILE').samples[0].yfull_id,'SYNTHETIC-YFULL-ONLY');
 assert.equal(census.flatten(original).length,3);assert.equal(original.samples.length,0);
 assert(census.flatten(census.compact(tree)).some(n=>n.display==='E-V13'&&n.samples.length===1));
});
test('J/R/Q subgroups use documented defining ancestry and preserve uncertain roots',()=>{
 for(const [marker,wanted] of [['J-M267','J1'],['J-M172','J2'],['R-M417','R1A'],['R-M269','R1B'],['R-M124','R2'],['Q-L472','Q1'],['Q-L275','Q2']]){
  assert.equal(ui.yFamily({y_dna:marker}),wanted);
  assert.equal(ui.yFamily({y_dna:marker[0]+'-FIXTURE',full_snp_path:'Y-Adam>'+marker+'>'+marker[0]+'-FIXTURE'}),wanted);
 }
 assert.equal(ui.yFamily({y_dna:'Q-UNKNOWN'}),'Q');
 assert.equal(ui.yFamily({y_dna:'R-M269',full_snp_path:'Y-Adam>R-M417>R-M269'}),'R');
});
