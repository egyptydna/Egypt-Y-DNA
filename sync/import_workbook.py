"""Read an owner-provided XLSX locally. No provider crawling or invented kit IDs.

Only name, paternal ancestor/country and terminal Y haplogroup are retained.
Unlinked source records never enter the identified-person statistics.
"""
import argparse
import hashlib
import json
import re
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from .normalize import Gazetteer,normalized
from .topology import YFullTree

NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
REQUIRED=['Name','Y-DNA haplogroup','Paternal ancestor name','Paternal country']
def digest(value):return hashlib.sha256(value).hexdigest()

def public_text(value):
    value=' '.join(str(value or '').split())
    value=re.sub(r'\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b','[contact omitted]',value)
    def contact(match):
        text=match.group(0)
        years=re.fullmatch(r'(\d{4})\s*-\s*(\d{4})',text)
        return text if years and all(1000<=int(y)<=2099 for y in years.groups()) else '[contact omitted]'
    value=re.sub(r'(?<!\w)\+?\d[\d ()-]{7,}\d(?!\w)',contact,value)
    return value[:2000]

def read_xlsx(path):
    """Minimal OOXML reader: never execute formulas, macros or external links."""
    with zipfile.ZipFile(path) as z:
        if sum(x.file_size for x in z.infolist())>32_000_000:raise ValueError('Workbook too large')
        if any(x.filename.endswith('vbaProject.bin') for x in z.infolist()):raise ValueError('Macros unsupported')
        strings=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            strings=[''.join(t.text or '' for t in si.findall('.//s:t',NS)) for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si',NS)]
        sheets=ET.fromstring(z.read('xl/workbook.xml')).findall('s:sheets/s:sheet',NS)
        rels={r.get('Id'):r.get('Target') for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
        for sheet in sheets:
            target=rels[sheet.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')]
            name=target.lstrip('/') if target.startswith('/') else 'xl/'+target
            if '..' in Path(name).parts:raise ValueError('Invalid sheet path')
            rows=ET.fromstring(z.read(name)).findall('s:sheetData/s:row',NS)
            header=None
            for row in rows:
                cells={}
                for c in row.findall('s:c',NS):
                    column=re.sub(r'\d+$','',c.get('r',''))
                    value=c.find('s:v',NS)
                    text=value.text if value is not None else ''.join(t.text or '' for t in c.findall('.//s:t',NS))
                    if c.get('t')=='s':text=strings[int(text)]
                    cells[column]=text or ''
                    if c.find('s:f',NS) is not None and header and header.get(column) in REQUIRED:raise ValueError('Formula in imported field')
                if header is None:
                    header={k:v.strip() for k,v in cells.items()}
                    if not set(REQUIRED).issubset(header.values()):raise ValueError('Unsupported workbook headers')
                    continue
                values={header.get(k):v for k,v in cells.items() if header.get(k) in REQUIRED}
                if any(values.values()):yield sheet.get('name'),int(row.get('r')),values

def paternal_location(text,gaz):
    """Exact gazetteer components after explicit location cues; never surnames."""
    result=gaz.resolve(text,'Egypt')
    if result['status']=='resolved':return result
    parts=re.split(r'[,;،\n]|\s[-–—>]\s',text)
    cues=r'\b(?:محافظة|محافظه|مركز|قرية|قريه|مدينة|مدينه|الأصل من|الاصل من)\s+'
    for m in re.finditer(cues,text):
        tail=text[m.end():]
        tail=re.split(cues,tail)[0]
        tail=re.split(r'[,;،\n\-–—>]',tail)[0]
        tail=re.sub(r'\s+(?:بمصر|في مصر|مصر)$','',tail).strip()
        if tail:parts.append(tail)
    # Intersect unambiguous matching components, retaining conflicts for review.
    location=gaz.resolve(','.join(p for p in parts if normalized(p) in gaz.index),'Egypt')
    return location

def reference_index(snapshot):
    refs={};conflicts=set()
    for fact in snapshot.get('nodes',[]):
        for i,label in enumerate(fact.get('path') or []):
            item={'path':fact['path'][:i+1],'url':fact.get('path_source_url'),'date':fact.get('path_observed_at')}
            if label.upper() in refs and refs[label.upper()]['path']!=item['path']:conflicts.add(label.upper())
            refs[label.upper()]=item
    return {k:v for k,v in refs.items() if k not in conflicts}

def plan(path,snapshot=None,archive=None,yfull=None,yfull_url=None):
    raw=Path(path).read_bytes();file_hash=digest(raw);gaz=Gazetteer();refs=reference_index(snapshot or {})
    rows=[];seen=set();excluded=0;duplicate_rows=0
    for sheet,number,values in read_xlsx(path):
        if normalized(values.get('Paternal country')) not in ('egypt','eg','مصر'):excluded+=1;continue
        name=public_text(values.get('Name'));ancestor=public_text(values.get('Paternal ancestor name'))
        label=str(values.get('Y-DNA haplogroup','')).strip().upper()
        if not name or not re.fullmatch(r'[A-T]-[A-Z0-9*.+_-]+',label):raise ValueError('Invalid uploaded Y-DNA row')
        row_key=digest(json.dumps([name,ancestor,label,'Egypt'],ensure_ascii=False).encode())
        if row_key in seen:duplicate_rows+=1;continue
        seen.add(row_key);origin=paternal_location(ancestor,gaz)
        ref=refs.get(label);reference_path=ref['path'] if ref else [];reference_url=ref['url'] if ref else None
        reference_kind='ftdna_archived_reference' if ref else 'terminal_only';alias=None
        if yfull:
            match=yfull.match(label)
            if match['status'] in ('exact','equivalent_snp'):
                alias=match['label'] if match['label']!=label else None
                if not ref:
                    reference_path=yfull.path(match['label']);reference_url=yfull_url;reference_kind='yfull_reference'
        # Similar names are review hints only. They never create identity links.
        candidate_ids=[s['id'] for s in archive or [] if normalized(s.get('name'))==normalized(name)]
        rows.append(dict(record_key=row_key,sheet_name=sheet,row_number=number,name=name,ancestor_name=ancestor,
            y_dna=label,y_dna_alias=alias,yfull_reference_url=yfull_url if alias else None,country_code='EG',origin_raw=ancestor,
            governorate=origin.get('governorate'),governorate_iso=origin.get('governorate_iso'),
            location_status=origin['status'],location_evidence={'place_id':origin.get('place_id'),
                'source_url':next((p['source_url'] for p in gaz.places+gaz.governorates if p['id']==origin.get('place_id')),None)},
            snp_path=reference_path,path_source_url=reference_url,path_kind=reference_kind,
            tree_path=ref['path'] if ref else [],candidate_ids=candidate_ids))
    summary=dict(file_rows=len(rows)+excluded+duplicate_rows,retained_rows=len(rows),excluded_rows=excluded,
        duplicate_source_rows=duplicate_rows,resolved_locations=sum(r['location_status']=='resolved' for r in rows),
        location_reviews=sum(r['location_status'] in ('ambiguous','conflict') for r in rows),
        possible_existing_matches=sum(bool(r['candidate_ids']) for r in rows),
        reference_paths=sum(bool(r['snp_path']) for r in rows),ftdna_tree_paths=sum(bool(r['tree_path']) for r in rows))
    return {'file':{'file_hash':file_hash,'file_name':Path(path).name,'row_count':len(rows)},'rows':rows,'summary':summary}

def sql_batches(value,outdir):
    outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True)
    def literal(v):return "'"+json.dumps(v,ensure_ascii=False).replace("'","''")+"'::jsonb"
    files=[]
    for start in range(0,len(value['rows']),40):
        data={'file':value['file'],'rows':value['rows'][start:start+40]}
        p=outdir/f'{start//40:03}.sql'
        p.write_text('select public.ydna_import_uploaded_profiles('+literal(data)+',false) as result;')
        files.append(str(p))
    (outdir/'plan.json').write_text(json.dumps({'project_id':'lsfmpmfoqdtkgndtaxen','summary':value['summary'],'files':files},indent=2))
    return files

def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('xlsx');p.add_argument('--snapshot');p.add_argument('--archive');p.add_argument('--yfull');p.add_argument('--yfull-url');p.add_argument('--outdir',required=True);args=p.parse_args()
    load=lambda f:json.loads(Path(f).read_text()) if f else None
    value=plan(args.xlsx,load(args.snapshot),load(args.archive),YFullTree(load(args.yfull)) if args.yfull else None,args.yfull_url)
    sql_batches(value,args.outdir)
    Path(args.outdir,'records.json').write_text(json.dumps(value,ensure_ascii=False))
    print(json.dumps(value['summary'],indent=2))

if __name__=='__main__':main()
