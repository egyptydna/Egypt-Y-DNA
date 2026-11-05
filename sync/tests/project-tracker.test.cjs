const assert=require('node:assert/strict');
const {test}=require('node:test');
const tracker=require('../../ydna-project-tracker.js');
const sync=require('../../ydna-sync-ui.js');
test('tracker escapes source labels and never describes partial runs as a census',()=>{
  const html=tracker.summaryHTML({state:'partial',summary:{projectSearch:{queued:7,exactKitMatches:3},projectDirectory:{trackedProjects:10},sourcePartialRuns:[{id:'<script>bad</script>',status:'restricted',records:0}]}});
  assert(!html.includes('<script>'));assert(html.includes('&lt;script&gt;'));
  assert(html.includes('never a complete census'));assert(html.includes('remain anonymous'));
  assert(html.includes('No source run saved'));assert(!html.includes('undefined'));
});
test('only actual FTDNA public project links can be rendered',()=>{
  assert(tracker.safeProjectURL('https://www.familytreedna.com/public/Egypt?iframe=ydna-results-overview'));
  for(const url of ['javascript:alert(1)','https://evil.org/public/Egypt','https://www.familytreedna.com.evil.org/public/X','https://user:password@www.familytreedna.com/public/X'])assert.equal(tracker.safeProjectURL(url),null);
});
test('NEW lasts 30 days from the saved first discovery and does not use each poll time',()=>{
  const now=Date.parse('2026-11-05T00:00:00Z');
  assert(sync.isNew({__new_until:'2026-11-06T00:00:00Z'},now));
  assert(!sync.isNew({__new_until:'2026-11-04T00:00:00Z'},now));
  assert(!sync.isNew({created_at:'2026-11-05T00:00:00Z',sync_managed:true},now));
  assert(sync.matches({__new_until:new Date(Date.now()+86400000).toISOString()},'new','','',Infinity));
  assert(!sync.matches({sync_managed:true,created_at:new Date().toISOString()},'new','','',0));
});
