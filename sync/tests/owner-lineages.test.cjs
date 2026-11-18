const {test}=require('node:test'),assert=require('node:assert/strict');
global.YDNAProfiles=require('../../ydna-profile-tools.js');
const refs=require('../../ydna-owner-lineages.js');
const record={record_key:'x',dna_type:'y',canonical_label:'E-FIXTURE',aliases:['E-SYNONYM','BARE'],match_labels:['E-FIXTURE','E-SYNONYM','BARE','E-BARE'],owner_active:true,source_url:'https://example.invalid/ref',note:'Synthetic owner reference'};
test('owner synonyms resolve for all matching samples without changing their source data',()=>{
 refs.setRecords([record]);const sample={y_dna:'E-SYNONYM',name:'Synthetic participant'};const before=JSON.stringify(sample);
 assert.deepEqual(refs.names('E-SYNONYM'),['E-FIXTURE','BARE']);assert.equal(refs.info('e-bare').canonical_label,'E-FIXTURE');assert.ok(refs.matches(sample,'fixture'));assert.match(refs.terms(sample),/E-FIXTURE/);assert.equal(JSON.stringify(sample),before);
});
test('DNA types and inactive mappings stay separate',()=>{
 refs.setRecords([record,{...record,record_key:'z',dna_type:'mt',canonical_label:'H1a',aliases:['H1ALT'],match_labels:['H1A','H1ALT']},{...record,record_key:'off',canonical_label:'E-OFF',aliases:['E-HIDDEN'],match_labels:['E-OFF','E-HIDDEN'],owner_active:false}]);
 assert.equal(refs.info('H1ALT','y'),undefined);assert.equal(refs.info('H1ALT','mt').canonical_label,'H1a');assert.equal(refs.info('E-HIDDEN'),undefined);
});
test('public notes escape owner text and reject unsafe source URLs',()=>{
 refs.setRecords([{...record,note:'<script>synthetic</script>',source_url:'javascript:alert(1)'}]);const html=refs.html({y_dna:'E-FIXTURE'});assert.match(html,/Betreiberergänzung/);assert.match(html,/&lt;script&gt;/);assert.doesNotMatch(html,/<script>|javascript:/);
 refs.setRecords([{...record,source_url:'https://user:secret@example.invalid/'}]);assert.doesNotMatch(refs.html({y_dna:'E-FIXTURE'}),/href=/);
});
