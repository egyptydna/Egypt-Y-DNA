const {test}=require('node:test'),assert=require('node:assert/strict');
const tools=require('../../ydna-owner-tools.js'),lineage=require('../../ydna-lineage-links.js');
test('Excel paste, CSV quotes and normalized IDs preserve text without evaluating formulas',()=>{
 const r=tools.parse('Kitnummer\tName\tY-DNA\tGouvernement\tAbout me\nmi990001\t"Synthetic\tparticipant"\tj-fixture\tCairo\tignored');
 assert.deepEqual(r.rows,[{kit_number:'MI990001',name:'Synthetic\tparticipant',y_dna:'J-FIXTURE',governorate:'Cairo'}]);assert.deepEqual(r.ignored,['About me']);
 assert.equal(tools.parse('kit_number,name\n990001,"A, ""B"""').rows[0].name,'A, "B"');
 assert.equal(tools.parse('name;y_dna\n=untouched;E-FIXTURE','collected','New Valley').rows[0].name,'=untouched');
});
test('imports reject malformed CSV, duplicate headers, excessive rows and missing headers',()=>{
 assert.throws(()=>tools.parse('kit;name\n1;"unclosed'),/geschlossen/);
 assert.throws(()=>tools.parse('kit;kit_number\n1;2'),/mehrfach/);
 assert.throws(()=>tools.parse('name\n'+Array(201).fill('Synthetic').join('\n')),/200/);
 assert.throws(()=>tools.parse('unknown\nvalue'),/Spalten/);
 assert.throws(()=>tools.parse('name;kit\nA;1;extra'),/mehr Werte/);
});
test('collected import ignores unsupported individual data; templates contain headers only',()=>{
 const r=tools.parse('name;y_dna;kit;mt_dna\nSynthetic;E-FIXTURE;990001;H1','collected');assert.deepEqual(r.rows,[{name:'Synthetic',y_dna:'E-FIXTURE'}]);assert.equal(tools.template().trim().split(/\r?\n/).length,1);
});
test('lineage links prefer published YFull aliases and retain independent Discover label',()=>{
 const reference={nodes:new Map([['E-REF',{}]]),release:{metadata:{matches:{'E-FIXTURE':{status:'equivalent_snp',label:'E-REF'}}}}};
 const r=lineage.links({y_dna:'E-FIXTURE'},'y',reference);assert.equal(r[0].url,'https://www.yfull.com/tree/E-REF/');assert.equal(r[0].status,'reference');assert.equal(r[1].url,'https://discover.familytreedna.com/y-dna/E-FIXTURE/tree');assert.equal(r[1].status,'lookup');
});
test('unknown lineages are explicit lookups, never fabricated provider sample links',()=>{
 const r=lineage.links({y_dna:'J-NEWTEST'});assert.equal(r.length,2);assert.ok(r.every(x=>x.status==='lookup'));assert.match(lineage.html({y_dna:'J-NEWTEST'}),/Linie prüfen/);assert.equal(lineage.links({y_dna:'<script>'}).length,0);assert.equal(lineage.links({y_dna:'—'}).length,0);
});
test('mtDNA links retain case and never invent a Discover mtDNA endpoint',()=>{
 const r=lineage.links({mt_dna:'H1a1'},'mt');assert.equal(r.length,1);assert.equal(r[0].url,'https://www.yfull.com/mtree/H1a1/');
 const y=lineage.links({y_dna:'E-FIXTURE',y_link_1:'javascript:alert(1)'});assert.ok(y.every(x=>x.url.startsWith('https://')));
});

test('legacy YFull IDs move to the typed YFull field without mutating or discarding conflicting identities',()=>{
 const source={kit_number:'YF990001',yfull_id:'—'};assert.deepEqual(tools.formValues(source),{kit_number:'',yfull_id:'YF990001'});assert.equal(source.kit_number,'YF990001');assert.equal(tools.formValues({kit_number:'990001'}).kit_number,'990001');assert.equal(tools.formValues({kit_number:'YF990001',yfull_id:'YF990002'}).kit_number,'YF990001');
});
