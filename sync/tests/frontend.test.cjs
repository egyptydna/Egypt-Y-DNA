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
test('weaker automatic evidence cannot hide an explicit Big-Y test; a manual status override wins',()=>{
  const sample={test_type:'Big Y-700',test_status:'yfull_sequencing',sync_published:{test_status:'yfull_sequencing'}};
  assert.equal(ui.status(sample),'confirmed_big_y');
  assert.equal(ui.status({...sample,test_status:'str_only'}),'str_only');
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
const officialRelease={version:'14.06.0',metadata:{matches:{
  'J-TEST1':{status:'exact',label:'J-TEST1'},
  'J-ALIAS1':{status:'equivalent_snp',label:'J-TEST1'},
  'E-M35':{status:'exact',label:'E-M35'},
  'J-AMBIGUOUS1':{status:'ambiguous',candidates:['J-TEST1','E-M35']}
}}};
const officialNodes=new Map([
  ['Y-Adam',{parent_label:null}],['J-M1',{parent_label:'Y-Adam'}],
  ['J-TEST1',{parent_label:'J-M1'}],['E-M35',{parent_label:'Y-Adam'}]
]);
test('official paths use exact and source-proven equivalent branch names without altering profiles',()=>{
  const sample={y_dna:'J-ALIAS1',full_snp_path:'Y-Adam>J-ALIAS1',kit_number:'990099001'};
  const original=structuredClone(sample);
  assert.deepEqual(ui.officialPath(sample,officialRelease,officialNodes),{
    label:'J-TEST1',path:['Y-Adam','J-M1','J-TEST1'],version:'14.06.0'
  });
  assert.deepEqual(sample,original);
});
test('ambiguous, conflicting and missing official labels preserve existing placement',()=>{
  for(const sample of [{y_dna:'J-AMBIGUOUS1'},{y_dna:'R-UNKNOWN1'},
    {y_dna:'J-TEST1',y_dna_alias:'E-M35'}]) {
    assert.equal(ui.officialPath(sample,officialRelease,officialNodes),null);
  }
});
test('official paths reject missing ancestors, cycles and disconnected roots',()=>{
  const nodes=new Map(officialNodes);nodes.delete('J-M1');
  assert.equal(ui.officialPath({y_dna:'J-TEST1'},officialRelease,nodes),null);
  nodes.set('J-M1',{parent_label:'J-TEST1'});
  assert.equal(ui.officialPath({y_dna:'J-TEST1'},officialRelease,nodes),null);
  nodes.set('J-M1',{parent_label:null});
  assert.equal(ui.officialPath({y_dna:'J-TEST1'},officialRelease,nodes),null);
});
test('newer verified paths take priority over an older GitHub reference in the default view',()=>{
  const sample={y_dna:'J-TEST1',full_snp_path:'Y-Adam>J-NEW1>J-TEST1'};
  assert.equal(ui.officialPlacement(sample,officialRelease,officialNodes,'auto'),null);
  assert.equal(ui.officialPlacement(sample,officialRelease,officialNodes,'yfull').label,'J-TEST1');
  assert.equal(ui.officialPlacement({...sample,full_snp_path:''},officialRelease,officialNodes,'auto').label,'J-TEST1');
  assert.equal(ui.officialPlacement({...sample,full_snp_path:''},officialRelease,officialNodes,'published'),null);
});
test('unnamed YFull and kit profiles display their actual public identifier',()=>{
  assert.equal(ui.displayName({name:'—',kit_number:'—',yfull_id:'YF990099001'}),'YF990099001');
  assert.equal(ui.displayName({name:'—',kit_number:'990099001'}),'990099001');
  assert.equal(ui.displayName({name:'Published ancestor',yfull_id:'YF990099001'}),'Published ancestor');
  assert.equal(ui.publicId({kit_number:'—',yfull_id:'YF990099001'}),'YF990099001');
});

test('J-M319 belongs to J2a rather than J1, including the imported YF149485 path',()=>{
  const sample={y_dna:'J-M319',full_snp_path:'Y-Adam>J>J2>J-M410>J-L26>J-M319'};
  assert.equal(ui.yFamily(sample,null,null),'J2');
  assert.equal(ui.yFamily({y_dna:'J-M319'},null,null),'J2');
  assert.equal(ui.yFamily({y_dna:'J-M319',full_snp_path:'Y-Adam>J>J1>J-M319'},null,null),'J');
});
test('unknown J, Q and R SNPs are not guessed into J1, Q1 or R2',()=>{
  assert.equal(ui.yFamily({y_dna:'J-UNKNOWN'},null,null),'J');
  assert.equal(ui.yFamily({y_dna:'Q-UNKNOWN'},null,null),'Q');
  assert.equal(ui.yFamily({y_dna:'R-UNKNOWN'},null,null),'R');
  assert.equal(ui.yFamily({y_dna:'Q-TEST',full_snp_path:'Y-Adam>Q>Q2>Q-TEST'},null,null),'Q2');
  assert.equal(ui.yFamily({y_dna:'R-TEST',full_snp_path:'Y-Adam>R>R1>R1b>R-TEST'},null,null),'R1B');
  assert.equal(ui.yFamily({y_dna:'R-TEST',full_snp_path:'Y-Adam>R>R1>R2>R-TEST'},null,null),'R');
});
test('new FTDNA-only terminal uses a licensed exact SNP path even if not in old release mapping',()=>{
  const release={version:'14.06.0',metadata:{matches:{}}};
  const nodes=new Map([['Y-Adam',{parent_label:null}],['J',{parent_label:'Y-Adam'}],
    ['J2',{parent_label:'J'}],['J-M410',{parent_label:'J2'}],['J-M319',{parent_label:'J-M410'}]]);
  const kit={kit_number:'990099001',y_dna:'J-M319',full_snp_path:'—'};
  assert.deepEqual(ui.officialPath(kit,release,nodes),{
    label:'J-M319',path:['Y-Adam','J','J2','J-M410','J-M319'],version:'14.06.0'
  });
  assert.equal(ui.officialPlacement(kit,release,nodes,'auto').label,'J-M319');
  assert.equal(ui.yFamily(kit,release,nodes),'J2');
});
test('same kit gets the verified deeper SNP and only one visible row, placeholders never merge',()=>{
  const old={id:36,kit_number:'MI33015',y_dna:'J-FT121878',full_snp_path:'Y-Adam>J>J1>FT121878>'};
  const newer={id:50,kit_number:'MI33015',y_dna:'J-FT120805',full_snp_path:'Y-Adam>J>J1>FT121878>FGC74170>FT120805'};
  const merged=ui.deduplicate([old,newer]);
  assert.equal(merged.length,1);
  assert.equal(merged[0].id,50);
  assert.equal(merged[0].__duplicate_count,2);
  assert.equal(merged[0].__duplicate_conflict,false);
  assert.equal(ui.deduplicate([{id:1,kit_number:'—'},{id:2,kit_number:'—'}]).length,2);
});
test('two contradictory terminal SNPs with the same kit are flagged for review',()=>{
  const rows=ui.deduplicate([{id:1,kit_number:'990099001',y_dna:'J-TESTA'},
    {id:2,kit_number:'990099001',y_dna:'J-TESTB'}]);
  assert.equal(rows.length,1);
  assert.equal(rows[0].__duplicate_conflict,true);
});

test('FTDNA terminal count path restores classification without inventing tester SNP values',()=>{
  const sample={kit_number:'990099001',y_dna:'J-NEWTERM',full_snp_path:'—',snp_path:'—'};
  const references=new Map([['J-NEWTERM','Y-Adam>J>J2>J-M410>J-NEWTERM']]);
  assert.equal(ui.yFamily(sample,null,null,references),'J2');
  assert.equal(ui.yFamily({...sample,full_snp_path:'Y-Adam>J>J1>J-NEWTERM'},null,null,references),'J1');
  assert.equal(sample.full_snp_path,'—');
});
test('conflicting sample path takes precedence over country aggregate reference',()=>{
  const sample={y_dna:'J-NEWTERM',full_snp_path:'Y-Adam>J>J1>J-NEWTERM'};
  const references=new Map([['J-NEWTERM','Y-Adam>J>J2>J-M410>J-NEWTERM']]);
  assert.equal(ui.yFamily(sample,null,null,references),'J1');
});

test('modern archive renders terminal IDs instead of dash placeholders and labels references',()=>{
  const html=fs.readFileSync('index.html','utf8');
  assert.match(html,/function archiveLineagePreview\(sample\)/);
  assert.match(html,/isRealValue\(sample\.snp_path\)\?sample\.snp_path/);
  assert.match(html,/Source-backed Reference SNP Path \(not a complete individual test\)/);
  assert.match(html,/archiveLineagePreview\(s\)/);
});

test('legacy YFull kit_number and new YFull yfull_id refer to one canonical sample',()=>{
  const old={id:1,kit_number:'YF123456',yfull_id:null,y_dna:'J-M319',
    name:'Archived profile',full_snp_path:'Y-Adam>J>J2>J-M319'};
  const imported={id:2,kit_number:'—',yfull_id:'YF123456',y_dna:'J-M319',
    name:'—',full_snp_path:'Y-Adam>J>J2>J-M319',test_type:'YFull sequencing'};
  const rows=ui.deduplicate([old,imported]);
  assert.equal(rows.length,1);
  assert.equal(rows[0].__duplicate_count,2);
  assert.deepEqual(rows[0].__linked_sample_ids,[1,2]);
  assert.equal(rows[0].yfull_id,'YF123456');
  assert.equal(ui.identitySummary(rows[0]),'YFull ID: YF123456');
});
test('different YFull IDs remain separate even under exactly the same tree branch and URL',()=>{
  const shared='https://www.yfull.com/tree/J-M319/';
  const rows=ui.deduplicate([{id:1,yfull_id:'YF123456',kit_number:'—',
    y_dna:'J-M319',y_link_1:shared,full_snp_path:'Y-Adam>J>J2>J-M319'},
    {id:2,yfull_id:'YF123457',kit_number:'—',
    y_dna:'J-M319',y_link_1:shared,full_snp_path:'Y-Adam>J>J2>J-M319'}]);
  assert.equal(rows.length,2);
  assert.notEqual(ui.identitySummary(rows[0]),ui.identitySummary(rows[1]));
});
test('a documented cross-ID link allows safe FTDNA+YFull merging without losing either ID',()=>{
  const linked={id:1,kit_number:'990099001',yfull_id:'YF123456',y_dna:'J-P58',
    name:'Archived tester'};
  const source={id:2,kit_number:'—',yfull_id:'YF123456',y_dna:'J-P58',name:'—',
    full_snp_path:'Y-Adam>J>J1>J-P58'};
  const all=ui.deduplicate([linked,source]);
  assert.equal(all.length,1);
  assert.match(ui.identitySummary(all[0]),/FTDNA kit: 990099001/);
  assert.match(ui.identitySummary(all[0]),/YFull ID: YF123456/);
  assert.equal(all[0].kit_number,'990099001');
});
test('conflicting linked sample identity claims are flagged instead of silently overwritten',()=>{
  const rows=ui.deduplicate([{id:1,kit_number:'990099001',yfull_id:'YF123456',y_dna:'J-P58'},
    {id:2,kit_number:'990099001',yfull_id:'YF123457',y_dna:'J-P58'}]);
  assert.equal(rows.length,1);
  assert.equal(rows[0].__duplicate_conflict,true);
  assert.equal(rows[0].__identity_keys.filter(k=>k.startsWith('yfull:')).length,2);
});
test('YFull is never misrepresented as an FTDNA kit',()=>{
  assert.deepEqual(ui.identityKeys({kit_number:'YF123456',yfull_id:'YF123456'}),['yfull:YF123456']);
  assert.equal(ui.publicId({kit_number:'—',yfull_id:'YF123456'}),'YF123456');
  assert.equal(ui.identitySummary({kit_number:'YF123456'}),'YFull ID: YF123456');
  assert.equal(ui.deduplicate([{id:1,kit_number:'—'},{id:2,kit_number:'—'}]).length,2);
});
test('archive and modal expose existing YFull source SNP paths',()=>{
  const html=fs.readFileSync('index.html','utf8');
  assert.match(html,/Published YFull SNP tree path/);
  assert.match(html,/isRealValue\(sample\.full_snp_path\)\?sample\.full_snp_path:null/);
  assert.match(html,/samplePathMode = sample\.__sourceType === "modern"/);
  assert.match(html,/YDNASync\.identitySummary\(sample\)/);
  const details=fs.readFileSync('ydna-sync-details.js','utf8');
  assert.match(details,/\.in\('sample_id',sample\.__linked_sample_ids\|\|\[sample\.id\]\)/);
});

test('user-confirmed C-Y255870 duplicate keeps maternal U3b3d2a and canonical YF129136 ID',()=>{
  const original={id:91,name:'—',kit_number:'—',yfull_id:'YF129136',
    y_dna:'C-Y255870',governorate:'Sūhāj',sync_managed:false,
    test_type:'YSEQ',snp_path:'C-M216>F3393>CTS11043>Y255870',
    full_snp_path:'Y-Adam>BT>CT>CF>C>F3393>CTS11043>Y255870',
    mt_dna:'U3b3d2a',full_mtDNA_path:'mt-Eve>U>U3>U3b3d2a',
    mt_link_1:'https://www.yfull.com/mtree/U3b3d2a/'};
  const imported={id:519,name:'—',kit_number:'—',yfull_id:'YF129136',
    y_dna:'C-Y255870',governorate:'Sūhāj',sync_managed:true,
    test_type:'YFull sequencing',snp_path:'—',
    full_snp_path:'Y-Adam>BT>CT>CF>C>C-F3393>C-CTS11043>C-Y11591>C-Y255870',
    mt_dna:'—',full_mtDNA_path:'—'};
  const merged=ui.deduplicate([original,imported]);
  assert.equal(merged.length,1);
  assert.equal(merged[0].id,91);
  assert.equal(merged[0].yfull_id,'YF129136');
  assert.equal(merged[0].mt_dna,'U3b3d2a');
  assert.equal(merged[0].full_mtDNA_path,original.full_mtDNA_path);
  assert.equal(merged[0].mt_link_1,original.mt_link_1);
  assert.equal(merged[0].__duplicate_count,2);
  assert.deepEqual(merged[0].__linked_sample_ids,[91,519]);
  assert.equal(merged[0].__source_snp_paths.length,2);
  assert.equal(ui.compactSnpPath(merged[0]),original.snp_path);
});
test('automatically imported YFull SNP paths show meaningful lineage, not just J-terminal',()=>{
  assert.equal(ui.compactSnpPath({snp_path:'—',y_dna:'J-Y8537',
    full_snp_path:'Y-Adam>A0-T>BT>CT>F>J>J1>J-Z2215>J-Y8537'}),'J1>Z2215>Y8537');
  assert.equal(ui.compactSnpPath({snp_path:'—',y_dna:'C-Y255870',
    full_snp_path:'Y-Adam>BT>CT>CF>C>C-F3393>C-CTS11043>C-Y255870'}),'C>F3393>CTS11043>Y255870');
  assert.equal(ui.compactSnpPath({snp_path:'—',y_dna:'C-Y255870',full_snp_path:'—'}),'C-Y255870');
});
test('different YFull sample IDs and identical haplogroups do not merge',()=>{
  const rows=ui.deduplicate([{id:1,kit_number:'—',yfull_id:'YF000001',y_dna:'J-M319',governorate:'Sūhāj'},
    {id:2,kit_number:'—',yfull_id:'YF000002',y_dna:'J-M319',governorate:'Sūhāj'}]);
  assert.equal(rows.length,2);
});
test('source details disclose both reference paths on confirmed duplicate merge',()=>{
  const details=fs.readFileSync('ydna-sync-details.js','utf8');
  assert.match(details,/Compare documented source tree paths/);
  assert.match(details,/__source_snp_paths/);
  const html=fs.readFileSync('index.html','utf8');
  assert.match(html,/YDNASync\.compactSnpPath\(sample\)/);
  assert.match(html,/Verified linked records combined/);
});
