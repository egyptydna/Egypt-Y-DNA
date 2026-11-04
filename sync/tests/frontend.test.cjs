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
