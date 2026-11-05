let uploadedProfiles=[],uploadedProfilesLoading=null,uploadedQuery='',uploadedLoadError='';
function isUploadedTree(){return currentTreeType==='y'&&countryTreeMode==='uploaded';}
async function loadUploadedProfiles(){
  if(uploadedProfilesLoading)return uploadedProfilesLoading;
  uploadedProfilesLoading=(async()=>{
    try{
      const rows=[];
      for(let offset=0;;offset+=1000){
        const page=await _sb.from('ydna_uploaded_profiles').select('*').order('record_key').range(offset,offset+999);
        if(page.error)throw Error('Uploaded source profiles unavailable');
        rows.push(...page.data);if(page.data.length<1000)break;
      }
      uploadedProfiles=rows;
      document.querySelector('#treeDataset option[value="uploaded"]').textContent=`Uploaded profiles · ${rows.length}`;
      document.querySelector('#treeDataset option[value="uploaded"]').hidden=rows.length===0;
      document.querySelector('#treeDataset option[value="uploaded"]').disabled=rows.length===0;
    }catch{uploadedLoadError='Uploaded source profiles are temporarily unavailable.';}
    if(document.getElementById('section-tree')?.classList.contains('active'))renderTree();
  })();return uploadedProfilesLoading;
}
function uploadedMatches(s,query){
  const text=[s.name,s.ancestor_name,s.y_dna,s.y_dna_alias,s.origin_raw,s.governorate].join(' ').toLocaleLowerCase();
  return text.includes(String(query).toLocaleLowerCase());
}
function uploadedSnapshot(rows){
  const groups=new Map();
  for(const s of rows){
    if(!groups.has(s.y_dna))groups.set(s.y_dna,{label:s.y_dna,count:0,path:s.tree_path||[]});
    groups.get(s.y_dna).count++;
  }
  return {total_count:rows.length,nodes:[...groups.values()]};
}
function uploadedProfileRow(s){
  return `<li class="phylo-sample"><button class="tree-sample-card phylo-sample-row uploaded-profile-row" data-record="${esc(s.record_key)}" onclick="openUploadedProfile(this.dataset.record)"><span class="phylo-sample-id">${esc(s.name)}</span><span class="phylo-sample-country">🇪🇬 EGY</span><span class="phylo-sample-origin">${esc(s.governorate||'Governorate unknown')}</span><span class="phylo-sample-test">Uploaded source · identity unlinked</span><span class="phylo-detail-hint">Details ›</span></button></li>`;
}
function renderUploadedPanel(){
  const p=document.getElementById('country-tracker-panel');p.hidden=false;
  if(!uploadedProfilesLoading)loadUploadedProfiles();
  p.innerHTML=`<div class="country-tracker-heading"><strong>Egypt Kits.xlsx · ${uploadedProfiles.length} source records</strong><span>Owner-provided workbook</span></div><p>Names, paternal origin and published terminal haplogroups from the supplied file. Kit numbers, STRs and test types were not supplied. Identity links are unverified: these records are excluded from identified-person and regional statistics.</p><p>Search names, SNPs and paternal places above. Source paths are dated references, not additional individual SNP test results. ${esc(uploadedLoadError)}</p>`;
}
function renderUploadedTree(){
  renderUploadedPanel();
  document.getElementById('official-tree-panel').innerHTML='';document.getElementById('tree-summary-grid').innerHTML='';document.getElementById('tree-stats').innerHTML='';document.getElementById('tree-pills').innerHTML='';
  const selected=uploadedProfiles.filter(s=>uploadedMatches(s,uploadedQuery)),snapshot=uploadedSnapshot(selected);
  const root=YDNACountryTree.build(snapshot);lastTreeRawRoot=root;
  const focus=YDNACountryTree.find(root,treeFocusPath)||root;
  const options={...compactTreeOptions(),names:n=>({primary:n.display,secondary:''}),countLabel:n=>`${n.count} uploaded records`,
    counts:n=>n.directCount?`<span class="tree-count">${n.directCount} direct</span>`:'',aliases:()=>'',age:()=>'',country:()=>'',hasEvidence:()=>false,
    group:n=>selected.filter(s=>s.y_dna===n.display).map(uploadedProfileRow).join('')};
  document.getElementById('tree-inner').innerHTML=selected.length?DNATreeView.node(YDNACountryTree.compact(focus,treeMode==='full'),options,true):`<p>${esc(uploadedLoadError||'No matching uploaded source records.')}</p>`;
  document.getElementById('btn-tree-back').classList.toggle('hidden',focus===root);
  updateTreeFloatingToggle();
}
function searchUploadedTree(query){
  uploadedQuery=query;treeFocusPath=null;treeSearchTargetPath=null;treeSearchResultPath='';collapsedNodes.clear();
  document.getElementById('tree-result-path').classList.remove('active');renderTree();updateShareUrl({section:'ytree'});return true;
}
function openUploadedProfile(key){
  const s=uploadedProfiles.find(r=>r.record_key===key);if(!s)return;
  let dialog=document.getElementById('uploaded-profile-dialog');
  if(!dialog){dialog=document.createElement('dialog');dialog.id='uploaded-profile-dialog';dialog.className='uploaded-profile-dialog';document.body.append(dialog);}
  dialog.innerHTML=`<form method="dialog"><button class="ctrl-btn country-close">Close ×</button></form><h3>${esc(s.name)}</h3>
    <p><strong>${esc(s.y_dna)}</strong>${s.y_dna_alias?` · YFull reference: ${esc(s.y_dna_alias)}`:''}</p>
    <p>Paternal ancestor: ${esc(s.ancestor_name||'Not supplied')}</p><p>Original paternal origin text: ${esc(s.origin_raw||'Not supplied')}</p>
    <p>Paternal country: Egypt · Governorate: ${esc(s.governorate||'Unknown / pending review')}</p>
    <p>Kit number: not supplied · Test type: not supplied · STR values: not supplied</p>
    <p>Reference SNP path: ${esc(s.snp_path?.join(' → ')||'Terminal only; verified ancestry unavailable')}</p>
    <p>${countryLink(s.path_source_url,'SNP reference source')} ${countryLink(s.yfull_reference_url,'Dated YFull / YFullTeam reference · CC BY 4.0')} ${countryLink(s.location_evidence?.source_url,'Place reference')}</p>
    <p>Source: Egypt Kits.xlsx · ${esc(s.sheet_name)} · row ${s.row_number}. Imported: ${esc(countryDate(s.imported_at))}.</p>
    <p>Source record without a verified external identity. No match to an anonymous FTDNA result or existing kit is inferred from a name or shared haplogroup. Excluded from identified-person statistics until identity verification.</p>`;
  dialog.showModal();
}
