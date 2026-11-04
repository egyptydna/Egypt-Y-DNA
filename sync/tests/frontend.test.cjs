const {test}=require('node:test');
const assert=require('node:assert/strict');
const ui=require('../../ydna-sync-ui.js');
const fs=require('node:fs');
const vm=require('node:vm');
test('one kit in three projects counts once',()=>{
  assert.equal(ui.deduplicate([1,2,3].map(id=>({id,kit_number:'990099001'}))).length,1);
});
test('YFull does not establish Big Y',()=>{
  assert.notEqual(ui.status({yfull_id:'YF990099001'}),'confirmed_big_y');
  assert.equal(ui.status({test_type:'Big Y-700'}),'confirmed_big_y');
});
test('terminal only is visible without imaginary branches',()=>{
  assert.equal(ui.terminalPath({y_dna:'J-TEST1'}),'Y-Adam>J-TEST1');
});
test('terminal-only testers reuse an unambiguous published path, never a conflicting one',()=>{
  const known=ui.knownTerminalPaths([{y_dna:'J-TEST1',full_snp_path:'Y-Adam>J>J-TEST1'}]);
  assert.equal(ui.terminalPath({y_dna:'J-TEST1'},known),'Y-Adam>J>J-TEST1');
  const conflict=ui.knownTerminalPaths([{y_dna:'J-TEST1',full_snp_path:'Y-Adam>J>J-TEST1'},{y_dna:'J-TEST1',full_snp_path:'Y-Adam>J1>J-TEST1'}]);
  assert.equal(ui.terminalPath({y_dna:'J-TEST1'},conflict),'Y-Adam>J-TEST1');
});
test('direct and cumulative counts exclude studies and ancient',()=>{
  const s={__sourceType:'modern',test_type:'Big Y-700'};
  assert.deepEqual(ui.nodeCounts({samples:[s],children:[{samples:[s,{__sourceType:'ancient'}]}]}),{direct:1,modern:2,bigY:2});
});
test('search and filters',()=>{
  const s={__sourceType:'modern',test_type:'Big Y-700',kit_number:'990099001',__projects:['Egypt'],governorate:'Port Said'};
  assert.ok(ui.matches(s,'confirmed_big_y','Port Said','Egypt'));
  assert.ok(!ui.matches(s,'str_only','',''));
});
test('all inline scripts are syntactically valid; 27 governorates',()=>{
  const html=fs.readFileSync('index.html','utf8');
  for(const match of html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g))new vm.Script(match[1]);
  const list=html.match(/const GOV_LIST = (\[[\s\S]*?\])\.sort\(\)/)[1];
  const govs=vm.runInNewContext(list).filter(x=>x!=='—');
  assert.equal(govs.length,27);assert.ok(govs.includes('Port Said'));assert.ok(govs.includes('New Valley'));
});
const countFixture={namespace:'ftdna',node_label:'J-FGC1',reported_count:9,count_scope:'inclusive',population:'ftdna_big_y'};
const publicKit={id:1,__sourceType:'modern',kit_number:'990099001',y_dna:'J-FGC1',test_type:'Big Y-700'};
test('nine source records and one public kit are compared as nine, not ten',()=>{
  const r=ui.reconcileCountryCount(countFixture,[publicKit]);
  assert.equal(r.reported,9);assert.equal(r.known,1);assert.equal(r.unresolved,8);
  assert.equal(r.method,'cohort_comparison_only');
});
test('same kit in three projects reduces the arithmetic remainder only once',()=>{
  assert.equal(ui.reconcileCountryCount(countFixture,[publicKit,{...publicKit,id:2},{...publicKit,id:3}]).unresolved,8);
});
test('STR predictions, YFull-only profiles and ancient samples do not identify Big Y counts',()=>{
  const r=ui.reconcileCountryCount(countFixture,[{...publicKit,test_type:'Y-DNA37'},
    {...publicKit,kit_number:'YF990099001',test_type:'YFull sequencing'},
    {...publicKit,__sourceType:'ancient'}]);
  assert.equal(r.known,0);assert.equal(r.unresolved,9);
});
test('direct and descendant-inclusive source counts have different scope',()=>{
  const child={...publicKit,y_dna:'J-TEST2',full_snp_path:'Y-Adam>J>FGC1>TEST2'};
  assert.equal(ui.reconcileCountryCount(countFixture,[child]).known,1);
  assert.equal(ui.reconcileCountryCount({...countFixture,count_scope:'direct'},[child]).known,0);
  assert.equal(ui.reconcileCountryCount(countFixture,[{...child,full_snp_path:''}]).known,0);
});
test('an unknown counted population is never silently equated to tester profiles',()=>{
  const r=ui.reconcileCountryCount({...countFixture,population:'unknown'},[publicKit]);
  assert.equal(r.comparable,false);assert.equal(r.unresolved,null);
});
test('source totals below the known profile count are flagged without deleting profiles',()=>{
  const r=ui.reconcileCountryCount({...countFixture,reported_count:0},[publicKit]);
  assert.equal(r.conflict,true);assert.equal(r.unresolved,null);assert.equal(r.known,1);
});
test('YFull totals reconcile separately without inferring Big Y or merging identities',()=>{
  const r=ui.reconcileCountryCount({namespace:'yfull',node_label:'J-FGC1',reported_count:2,count_scope:'direct',population:'yfull_modern'},
    [publicKit,{...publicKit,yfull_id:'YF990099001',test_type:'YFull sequencing'}]);
  assert.equal(r.known,1);assert.equal(r.unresolved,1);
});
