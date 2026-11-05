/* Owner import parsing. CSV text is data, never a formula or executable input. */
(function(root){
 'use strict';
 const aliases={kit:'kit_number',kitnummer:'kit_number',kitnumber:'kit_number',ftdnakit:'kit_number',ftdnakitnummer:'kit_number',kit_number:'kit_number',name:'name',proband:'name',ydna:'y_dna',ydnalinie:'y_dna',y_dna:'y_dna',haplogroup:'y_dna',ydnahaplogroup:'y_dna',mtdna:'mt_dna',mt_dna:'mt_dna',mtdnalinie:'mt_dna',governorate:'governorate',gouvernement:'governorate',bundesland:'governorate',testtype:'test_type',testtyp:'test_type',test_type:'test_type',yfullid:'yfull_id',yfull_id:'yfull_id',yfull:'yfull_id',ancestorname:'ancestor_name',ancestor_name:'ancestor_name',paternalancestorname:'ancestor_name',väterlichervorfahr:'ancestor_name',origin:'origin_raw',origin_raw:'origin_raw',herkunft:'origin_raw',paternalcountry:'origin_raw'};
 function parse(text,kind='modern',defaultGovernorate=''){
  text=String(text).replace(/^\uFEFF/,'');if(text.length>1000000)throw Error('Die Datei ist zu groß. Bitte höchstens 200 Zeilen je Import verwenden.');
  const first=text.split(/\r?\n/,1)[0],delimiter=first.includes('\t')?'\t':(first.match(/;/g)||[]).length>(first.match(/,/g)||[]).length?';':',';
  let rows=[],row=[],value='',quoted=false,closed=false;
  for(let i=0;i<=text.length;i++){
   const c=text[i];
   if(quoted){if(c===undefined)throw Error('Ein Anführungszeichen in der Datei wurde nicht geschlossen.');if(c==='"'){if(text[i+1]==='"'){value+='"';i++;}else{quoted=false;closed=true;}}else value+=c;continue;}
   if(c==='"'&&!value&&!closed){quoted=true;continue;}
   if(c===delimiter||c==='\r'||c==='\n'||c===undefined){row.push(value.trim());value='';closed=false;if(c!==delimiter){if(row.some(Boolean))rows.push(row);row=[];if(c==='\r'&&text[i+1]==='\n')i++;}continue;}
   if(closed&&!/\s/.test(c))throw Error('Ungültiges CSV-Zeichen nach einem Anführungszeichen.');value+=c;
  }
  if(rows.length<2)throw Error('Bitte eine Kopfzeile und mindestens eine Probe einfügen.');
  if(rows.length>201)throw Error('Bitte höchstens 200 Proben auf einmal hinzufügen.');
  const headers=rows.shift(),allowed=new Set(kind==='collected'?['name','ancestor_name','origin_raw','y_dna','governorate']:['name','kit_number','yfull_id','test_type','y_dna','mt_dna','governorate','origin_raw']);
  const fields=headers.map(h=>aliases[h.trim().toLowerCase().replace(/[\s-]+/g,'')]);
  const usable=fields.filter(x=>x&&allowed.has(x));if(!usable.length)throw Error('Keine passenden Spalten erkannt. Bitte die CSV-Vorlage verwenden.');
  if(new Set(usable).size!==usable.length)throw Error('Eine Spalte ist mehrfach enthalten. Bitte jede Angabe nur einmal aufführen.');
  const patches=rows.map((values,i)=>{if(values.length>headers.length&&values.slice(headers.length).some(Boolean))throw Error('Zeile '+(i+2)+' enthält mehr Werte als Spalten.');const patch={};fields.forEach((f,j)=>{if(f&&allowed.has(f)&&String(values[j]||'').trim())patch[f]=String(values[j]).trim();});if(!patch.governorate&&defaultGovernorate)patch.governorate=defaultGovernorate;for(const f of ['kit_number','yfull_id','y_dna'])if(patch[f])patch[f]=patch[f].toUpperCase();return patch;});
  return {rows:patches,ignored:headers.filter((h,i)=>!fields[i]||!allowed.has(fields[i]))};
 }
 function template(kind='modern'){return (kind==='collected'?['name','ancestor_name','origin_raw','y_dna','governorate']:['kit_number','name','y_dna','mt_dna','governorate','test_type','yfull_id']).join(';')+'\r\n';}
 const api={parse,template};if(typeof module==='object')module.exports=api;else root.YDNAOwnerTools=api;
})(typeof window==='object'?window:globalThis);
