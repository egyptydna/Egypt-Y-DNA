const {test}=require('node:test');
const assert=require('node:assert/strict');
const ui=require('../../ydna-sync-ui.js');
const fs=require('node:fs');
const vm=require('node:vm');
const view=require('../../dna-tree-view.js');
test('a unique tester search opens its branch; results across branches remain a tree',()=>{
  const leaf={pathKey:'Y-Adam>J>J-M319',samples:[{id:1}],children:[]};
  const root={pathKey:'Y-Adam',samples:[],children:[{pathKey:'Y-Adam>J',samples:[],children:[leaf]}]};
  assert.equal(ui.sampleFocusPath(root),leaf.pathKey);
  leaf.samples.push({id:2});assert.equal(ui.sampleFocusPath(root),leaf.pathKey);
  root.children.push({pathKey:'Y-Adam>E',samples:[{id:3}],children:[]});
  assert.equal(ui.sampleFocusPath(root),null);
});
test('explicit public Big Y evidence extends an existing tester without changing curated fields',()=>{
  const s={test_type:'Y-DNA37',test_status:'str_only',sync_published:{test_status:'str_only'}};
  ui.addObservation(s,{namespace:'ftdna',published:true,is_current:true,test_type:'Big Y-700',project:'Synthetic project'});
  assert.equal(ui.status(s),'confirmed_big_y');assert.equal(ui.preferredTest(s),'Big Y-700');
  assert.equal(s.test_type,'Y-DNA37');assert.equal(s.test_status,'str_only');
  assert.deepEqual(s.__projects,['Synthetic project']);
  assert.equal(ui.status({...s,test_status:'snp_tested'}),'snp_tested');
});
test('YFull, withdrawn sources and project names alone do not establish Big Y',()=>{
  for(const evidence of [
    {namespace:'yfull',published:true,is_current:true,test_type:'Big Y-700'},
    {namespace:'ftdna',published:false,is_current:true,test_type:'Big Y-700'},
    {namespace:'ftdna',published:true,is_current:false,test_type:'Big Y-700'},
    {namespace:'ftdna',published:true,is_current:true,test_type:'Y-DNA37',project:'Big Y group'}
  ]){
    const s={test_type:'Y-DNA37'};ui.addObservation(s,evidence);assert.equal(ui.status(s),'str_only');
  }
});
test('J-M319 source ancestry cannot place a J2a tester under J1',()=>{
  const bad={y_dna:'J-M319',full_snp_path:'Y-Adam>J>J1>P58>M319'};
  assert.equal(ui.pathIssue(bad),'Conflicting J1 / J2 ancestry');
  assert.deepEqual(ui.safePlacement(bad,null,new Map(),'auto').path,['Y-Adam','J-M319']);
  assert.equal(ui.yFamily({y_dna:'J-TEST1',full_snp_path:'Y-Adam>J>M172>M410>TEST1'}),'J2');
  assert.equal(ui.pathIssue({y_dna:'J-M319',full_snp_path:'Y-Adam>J>J2>M172>M410>M319>'}),'');
});
test('wrong major ancestry and incomplete terminal paths are not silently used',()=>{
  assert.equal(ui.pathIssue({y_dna:'J-M319',full_snp_path:'Y-Adam>E-M35>J-M319'}),'Incompatible source ancestry');
  assert.equal(ui.pathIssue({y_dna:'J-TEST2',full_snp_path:'Y-Adam>J>J-TEST1'}),'Source path does not end at the published terminal');
  assert.equal(ui.pathIssue({y_dna:'R-TEST2',full_snp_path:'Y-Adam>A-L1098>F-M89>K-M9>P-M45>R-TEST2'}),'');
  assert.equal(ui.pathIssue({y_dna:'Q-TEST2',full_snp_path:'Y-Adam>F-M89>K-M9>P-M45>Q-TEST2'}),'');
});
test('compact view renders real samples for either tree, escapes content and respects collapse',()=>{
  const sample={__uid:'id" onclick="bad()',name:'<script>bad()</script>',__sourceType:'modern'};
  const node={display:'J-M319',pathKey:'Y-Adam>J-M319',samples:[sample],children:[],count:1};
  const options={type:'y',collapsed:new Set(),names:n=>({primary:n.display,secondary:'YFull: J-M319'}),identity:()=> 'YF99001122',name:s=>s.name,location:()=> 'Egypt',test:()=> 'YFull sequencing',issue:()=>'',sort:xs=>xs,counts:()=>'',aliases:()=>'',age:()=>'',evidence:()=>''};
  const html=view.node(node,options,true);
  assert.ok(html.includes('YF99001122'));assert.ok(html.includes('&lt;script&gt;'));
  assert.ok(!html.includes('<script>bad()'));
  assert.ok(html.includes('aria-expanded="true"'));
  options.collapsed.add(node.pathKey);
  assert.ok(!view.node(node,options,true).includes('YF99001122'));
  options.type='mt';options.collapsed.clear();node.display='U3b3d2a';
  assert.ok(view.node(node,options,true).includes('data-tree="mt"'));
});
test('platform labels prefer an unambiguous FTDNA name without conflating split branches',()=>{
  const source=fs.readFileSync('dna-tree-integration.js','utf8');
  const context={YDNASync:ui,currentTreeType:'y',syncOfficialRelease:{version:'test',metadata:{matches:{'J-FT1':{status:'equivalent_snp',label:'J-Y1'},'J-FT2':{status:'equivalent_snp',label:'J-Y1'}}}},syncOfficialNodes:new Map([['Y-Adam',{parent_label:null}],['J-Y1',{parent_label:'Y-Adam'}]]),syncCountryCounts:[{namespace:'ftdna',node_label:'J-FT1'}]};
  vm.createContext(context);vm.runInContext(source,context);
  assert.equal(vm.runInContext("treePlatformNames({display:'J-Y1'}).primary",context),'J-FT1');
  assert.match(vm.runInContext("treePlatformNames({display:'J-Y1'}).secondary",context),/YFull: J-Y1/);
  context.syncCountryCounts=[...context.syncCountryCounts,{namespace:'ftdna',node_label:'J-FT2'}];
  assert.equal(vm.runInContext("treePlatformNames({display:'J-Y1'}).primary",context),'J-Y1');
  assert.match(vm.runInContext("treePlatformNames({display:'J-Y1'}).secondary",context),/distinct source branches retained/);
});
test('a published FTDNA parent link is not an alternative terminal branch name',()=>{
  const source=fs.readFileSync('dna-tree-integration.js','utf8');
  const context={URL,YDNASync:ui,currentTreeType:'y',syncOfficialRelease:{version:'fixture'},syncCountryCounts:[],modernSamples:[{y_dna:'J-Y2',y_link_1:'https://discover.familytreedna.com/y-dna/J-FT1/tree'}],syncOfficialNodes:new Map([['Y-Adam',{parent_label:null}],['J-Y1',{parent_label:'Y-Adam',snp_groups:[['FT1']]}],['J-Y2',{parent_label:'J-Y1',snp_groups:[['FT2']]}]])};
  vm.createContext(context);vm.runInContext(source,context);
  assert.equal(vm.runInContext("treePlatformNames({display:'J-Y2'}).primary",context),'J-Y2');
  context.modernSamples=[{y_dna:'J-Y2',y_link_1:'https://discover.familytreedna.com/y-dna/J-FT2/tree'}];
  assert.equal(vm.runInContext("treePlatformNames({display:'J-Y2'}).primary",context),'J-FT2');
});
test('FTDNA country totals stay separate from identified profiles and are not added twice',()=>{
  const source=fs.readFileSync('dna-tree-integration.js','utf8');
  const facts=[{namespace:'ftdna',count_scope:'direct',reported_count:4,observed_at:'2026-11-04T00:00:00Z'},
    {namespace:'ftdna',count_scope:'inclusive',reported_count:9,observed_at:'2026-11-04T00:00:00Z'}];
  const context={currentTreeType:'y',syncCountryFacts:()=>facts,esc:view.escape};
  vm.createContext(context);vm.runInContext(source,context);
  const html=vm.runInContext('treeCountryCountBadge({})',context);
  assert.match(html,/FTDNA: 9 incl\./);assert.ok(!html.includes('13'));
  facts.push({...facts[1],reported_count:10});
  assert.match(vm.runInContext('treeCountryCountBadge({})',context),/differing source counts/);
  context.currentTreeType='mt';assert.equal(vm.runInContext('treeCountryCountBadge({})',context),'');
});
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
test('co-defining SNP blocks resolve branch labels without inventing SNP identity',()=>{
  const nodes=new Map([['Y-Adam',{parent_label:null}],['G-Y100',{parent_label:'Y-Adam',snp_groups:[['Y100'],['FTA100','Y101']]}]]);
  const release={version:'fixture',metadata:{matches:{}}};
  assert.equal(ui.officialPath({y_dna:'G-FTA100'},release,nodes).label,'G-Y100');
  assert.equal(ui.officialPath({y_dna:'G-Y100*'},release,nodes).label,'G-Y100');
  assert.equal(ui.pathIssue({y_dna:'G-Y100',full_snp_path:'Y-Adam>G-FTA100'},undefined,release,nodes),'');
  assert.equal(ui.pathIssue({y_dna:'G-Y100',full_snp_path:'Y-Adam>G-UNKNOWN1'},undefined,release,nodes),'Source path does not end at the published terminal');
});
test('a recurrent SNP in two official branches is not an unambiguous alias',()=>{
  const nodes=new Map([['Y-Adam',{parent_label:null}],['G-Y100',{parent_label:'Y-Adam',snp_groups:[['RECUR100']]}],['G-Y200',{parent_label:'Y-Adam',snp_groups:[['RECUR100']]}]]);
  assert.equal(ui.officialPath({y_dna:'G-RECUR100'},{version:'fixture'},nodes),null);
});
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
  assert.match(html,/YDNASync\.compactSnpPath\(sample\)/);
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
test('different YFull sample IDs never collapse through a shared FTDNA kit',()=>{
  const rows=ui.deduplicate([{id:1,kit_number:'990099001',yfull_id:'YF123456',y_dna:'J-P58'},
    {id:2,kit_number:'990099001',yfull_id:'YF123457',y_dna:'J-P58'}]);
  assert.equal(rows.length,2);
  assert.ok(rows.every(row=>row.__duplicate_conflict===true));
  assert.deepEqual(rows.map(row=>row.yfull_id),['YF123456','YF123457']);
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
test('automatically imported paths start with the first documented SNP not J1 or Y-Adam',()=>{
  assert.equal(ui.compactSnpPath({snp_path:'—',y_dna:'J-Y8537',
    full_snp_path:'Y-Adam>A0-T>BT>CT>F>J>J1>J-Z2215>J-Y8537'}),'J-Z2215>Y8537');
  assert.equal(ui.compactSnpPath({snp_path:'—',y_dna:'C-Y255870',
    full_snp_path:'Y-Adam>BT>CT>CF>C>C-F3393>C-CTS11043>C-Y255870'}),'C-F3393>CTS11043>Y255870');
  assert.equal(ui.compactSnpPath({snp_path:'—',y_dna:'C-Y255870',full_snp_path:'—'}),'C-Y255870');
});
test('requested J-FGC1723>step>step>terminal style is preserved exactly',()=>{
  const path='J-FGC1723>FGC1695>FGC1707>FGC1705>FGC1721>FGC1696>FGC23310>FGC5>FGC1>FGC43128';
  assert.equal(ui.compactSnpPath({y_dna:'J-FGC43128',snp_path:path,full_snp_path:'Y-Adam>J>J1>J-FGC1723>J-FGC1695>J-FGC43128'}),path);
});
test('imported full chain anchored at real FGC1723 is compact and not truncated',()=>{
  const path='Y-Adam>A0-T>BT>CT>F>J>J1>J-FGC1723>J-FGC1695>J-FGC1707>J-FGC43128';
  assert.equal(ui.compactSnpPath({y_dna:'J-FGC43128',snp_path:'—',full_snp_path:path}),
    'J-FGC1723>FGC1695>FGC1707>FGC43128');
});
test('other J subbranches must not be mislabeled as FGC1723',()=>{
  assert.equal(ui.compactSnpPath({y_dna:'J-M319',snp_path:'—',
    full_snp_path:'Y-Adam>BT>CT>F>J>J2>J-M410>J-L26>J-M319'}),'J-M410>L26>M319');
});
test('E imported profile card shows every sourced SNP between start and terminal',()=>{
  const path='Y-Adam>BT>CT>DE>E>E-M5479>E-P147>E-P177>E-M35>E-L539>E-M78>E-Z1902>E-V12>E-Y2863>E-CTS693>E-A40481';
  assert.equal(ui.compactSnpPath({y_dna:'E-A40481',snp_path:'—',full_snp_path:path}),
    'E-M5479>P147>P177>M35>L539>M78>Z1902>V12>Y2863>CTS693>A40481');
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

test('YFull ID on unnamed imported cards is shown once, not repeated as name and subtitle',()=>{
  const html=fs.readFileSync('index.html','utf8');
  assert.match(html,/const idIsTitle=primaryName!== '—'/);
  assert.match(html,/YFull sample · public ID shown above/);
  assert.match(html,/Sample ID not published/);
});

test('ten unique YFull sample IDs at one branch are ten separate testers',()=>{
  const rows=Array.from({length:10},(_,i)=>({
    id:i+1,yfull_id:'YF'+String(100001+i),kit_number:'—',
    y_dna:'J-P58',governorate:'Sūhāj',y_link_1:'https://www.yfull.com/tree/J-P58/'
  }));
  assert.equal(ui.deduplicate(rows).length,10);
});
test('ten rows with one identical YFull ID count as one tester',()=>{
  const rows=Array.from({length:10},(_,i)=>({
    id:i+1,yfull_id:'YF100001',kit_number:'—',
    y_dna:'J-P58',governorate:'Sūhāj',y_link_1:'https://www.yfull.com/tree/J-P58/'
  }));
  const result=ui.deduplicate(rows);
  assert.equal(result.length,1);
  assert.equal(result[0].__duplicate_count,10);
  assert.equal(result[0].__linked_sample_ids.length,10);
});
test('ten rows with identical FTDNA kit number count as one tester',()=>{
  const rows=Array.from({length:10},(_,i)=>({
    id:i+1,kit_number:'990099001',yfull_id:'—',y_dna:'R-M269'
  }));
  assert.equal(ui.deduplicate(rows).length,1);
});
test('ambiguous cross-linked kit cannot hide a second exact-ID duplicate',()=>{
  const rows=[
    {id:1,kit_number:'990099001',yfull_id:'YF100001',y_dna:'J-P58'},
    {id:2,kit_number:'990099001',yfull_id:'YF100002',y_dna:'J-P58'},
    {id:3,kit_number:'—',yfull_id:'YF100002',y_dna:'J-P58'},
    {id:4,kit_number:'—',yfull_id:'YF100001',y_dna:'J-P58'}
  ];
  const result=ui.deduplicate(rows);
  assert.equal(result.length,2);
  assert.deepEqual(result.map(x=>x.__linked_sample_ids),[[1,4],[2,3]]);
  assert.ok(result.every(x=>x.__duplicate_conflict));
});

test('subtree counts keep exact sample and Big Y totals after memoization',()=>{
  const leaf={samples:[{__sourceType:'modern',test_type:'Big Y-700'},
    {__sourceType:'ancient',test_type:'Big Y-700'}],children:[]};
  const child={samples:[{__sourceType:'modern',test_type:'YFull sequencing'}],children:[leaf]};
  const root={samples:[{__sourceType:'study'}],children:[child]};
  assert.deepEqual(ui.nodeCounts(root),{direct:0,modern:2,bigY:1});
  assert.deepEqual(ui.nodeCounts(child),{direct:1,modern:2,bigY:1});
  assert.deepEqual(ui.nodeCounts(leaf),{direct:1,modern:1,bigY:1});
  assert.deepEqual(ui.nodeCounts(root),{direct:0,modern:2,bigY:1});
  // Distinct new trees must never inherit an obsolete count.
  assert.deepEqual(ui.nodeCounts({samples:[],children:[]}),{direct:0,modern:0,bigY:0});
});
test('first page does not construct hidden archives or tree and charts are viewport lazy',()=>{
  const html=fs.readFileSync('index.html','utf8');
  const boot=html.slice(html.indexOf('(async function boot()'));
  // Only assert the synchronous first-paint phase: optional metadata can
  // legitimately refresh an active archive/tree after the async boundary.
  const firstPaint=boot.slice(0,boot.indexOf('setTimeout(async()=>{'));
  assert.ok(firstPaint.includes('renderDashboard()'));
  assert.ok(!firstPaint.includes('renderArchive()'));
  assert.ok(!firstPaint.includes('renderAncientArchive()'));
  assert.ok(!firstPaint.includes('renderTree()'));
  assert.match(html,/IntersectionObserver\(entries/);
  assert.match(html,/regionChartObserver\.observe\(canvas\)/);
  assert.match(html,/if\(id==='archive'&&!sectionRendered\.archive\)/);
  assert.match(html,/if\(id==='ancient'&&!sectionRendered\.ancient\)/);
});
test('full archive is preserved under pagination and next batch is user controlled',()=>{
  const html=fs.readFileSync('index.html','utf8');
  assert.match(html,/const ARCHIVE_PAGE_SIZE=100/);
  assert.match(html,/function loadMoreArchive\(\)/);
  assert.match(html,/rows\.slice\(0,archiveVisibleLimit\)\.map/);
  assert.match(html,/rows\.length>archiveVisibleLimit/);
  assert.match(html,/if\(filterKey!==archiveFilterKey\)/);
});
test('optional reference metadata is loaded after base samples without blocking the first paint',()=>{
  const html=fs.readFileSync('index.html','utf8');
  const loader=html.slice(html.indexOf('async function loadAll()'),html.indexOf('function parsePath('));
  assert.ok(!loader.includes('await loadSyncMetadata()'));
  assert.match(html,/setTimeout\(async\(\)=>\{/);
  assert.match(html,/await loadSyncMetadata\(\)/);
  const details=fs.readFileSync('ydna-sync-details.js','utf8');
  assert.match(details,/await Promise\.allSettled\(\[runTask,observationTask,aliasesTask,countsTask,loadOfficialTree\(\)\]\)/);
  assert.match(details,/function resetSyncCountryFactsIndex\(\)/);
});

test('node focus and full/direct toggles reuse the filtered raw DNA tree',()=>{
  const html=fs.readFileSync('index.html','utf8');
  const start=html.indexOf('function renderTree()');
  const end=html.indexOf('function renderTreeNode(',start);
  const render=html.slice(start,end);
  assert.match(render,/const rawRoot = getCachedRawTree\(samples\)/);
  assert.ok(!render.includes('const rawRoot = buildRawTree(samples)'));
  assert.match(html,/function resetRawTreeCache\(\)/);
  assert.match(html,/resetRawTreeCache\(\);\s*syncLineagePathCache=syncKnownTerminalPaths\(\)/);
  assert.match(html,/const signature=JSON\.stringify\(\[/);
});
