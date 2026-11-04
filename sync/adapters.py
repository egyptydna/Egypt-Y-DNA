import json
import csv
import io
import re
import urllib.parse
from pathlib import Path
from bs4 import BeautifulSoup
from .http import Unavailable, SourceRestricted
from .normalize import marker_name, str_value
from .github_sources import collect_yfull_github, collect_ftdnastat
from .github_files import GitHubFiles


def public_projects(html):
    soup = BeautifulSoup(html, 'html.parser')
    projects = set()
    for link in soup.select('a[href]'):
        match = re.fullmatch(r'(?:https://www\.familytreedna\.com)?/public/([\w-]+)(?:[/?].*)?', link['href'])
        if match: projects.add(match[1])
    return sorted(projects)


def parse_ftdna(html, source):
    soup = BeautifulSoup(html, 'html.parser')
    if 'visible to group members only' in soup.get_text(' ', strip=True):
        raise Unavailable('Results visible to members only')
    header_row = next((tr for tr in soup.select('tr') if any(
        td.get_text(' ', strip=True) == 'Kit Number' for td in tr.find_all(['th', 'td'], recursive=False))), None)
    if header_row is None: raise Unavailable('No supported public result table; no internal API used')
    table = header_row.find_parent('table')
    headers = [td.get_text(' ', strip=True) for td in header_row.find_all(['th', 'td'], recursive=False)]
    records = []
    for tr in table.select('tr'):
        cells = tr.find_all(['td', 'th'], recursive=False)
        if len(cells) != len(headers): continue
        values = [td.get_text(' ', strip=True) for td in cells]
        row = dict(zip(headers, values))
        kit = row.get('Kit Number', '')
        if not re.fullmatch(r'[A-Za-z]{0,3}\d+', kit): continue
        country = row.get('Country', '')
        # Source's country field describes paternal ancestry. No name-based classification.
        if country.strip().lower() not in ('egypt', 'مصر', 'egypt (arab republic of)'): continue
        markers = []
        for position, (label, value) in enumerate(zip(headers, values)):
            marker = marker_name(label)
            if marker:
                markers.append(dict(marker=marker, source_label=label, position=position, value=str_value(value)))
        hcell = cells[headers.index('Haplogroup')] if 'Haplogroup' in headers else None
        status = 'unknown'
        if hcell:
            # FTDNA public legend: green confirmed, red predicted. Unknown styling stays unknown.
            markup = str(hcell).lower()
            if re.search(r'(?:#008000|color:\s*green|color="green")', markup): status = 'confirmed'
            elif re.search(r'(?:#ff0000|color:\s*red|color="red")', markup): status = 'predicted'
        records.append(dict(namespace='ftdna', external_id=kit, name=row.get('Name') or row.get('Paternal Ancestor Name', ''),
            ancestor_name=row.get('Paternal Ancestor Name', ''), country=country, origin_raw=row.get('Paternal Ancestor Name', ''),
            origin_kind='paternal', sample_kind='modern', y_dna=row.get('Haplogroup', ''),
            haplogroup_status=status, test_type=row.get('Test', ''), str_markers=markers,
            source_url=source['url'], source_id=source['id'], project=source.get('project', ''),
            permission_url=source.get('permission_url') or '',
            publication_allowed=source.get('publication_allowed', False)))
    return records


def country_form(html):
    """Use only the ordinary public search form exposed by the result page."""
    soup = BeautifulSoup(html, 'html.parser')
    form = soup.find('form')
    if not form: return None
    fields = {}
    for element in form.select('input[name], select[name]'):
        name = element['name']
        if element.name == 'select':
            option = element.select_one('option[selected]') or element.select_one('option')
            if option: fields[name] = option.get('value', '')
        elif element.get('type') not in ('checkbox', 'radio') or element.has_attr('checked'):
            fields[name] = element.get('value', '')
    category = next((k for k in fields if k.endswith('$searchCategoryDropDownList')), None)
    term = next((k for k in fields if k.endswith('$searchTermTextBox')), None)
    if not category or not term: return None
    fields[category], fields[term] = 'Country', 'Egypt'
    for k in fields:
        if k.endswith('$accuracyDropDownList'): fields[k] = 'exactly matches'
        if k.endswith('$tbPageSize'): fields[k] = '500'
    return urllib.parse.urlencode(fields).encode()


def collect_ftdna(source, http):
    if not source.get('automated_access_allowed') or not str(source.get('access_permission_url') or '').startswith('https://'):
        raise SourceRestricted('FTDNA terms prohibit automated monitoring/copying without permission; no result page requested')
    raw = http.get(source['url'], incremental=False)
    if raw is None: return [], []
    html = raw.decode('utf-8', 'replace')
    # Detect private projects before submitting any form.
    records = parse_ftdna(html, source)
    form = country_form(html)
    if form:
        filtered = http.get(source['url'], incremental=False, data=form)
        records = parse_ftdna(filtered.decode('utf-8', 'replace'), source)
    # Treat snapshots as partial: disappearance is reviewed, never interpreted as deletion.
    return records, public_projects(html)


def collect_export(source, http=None):
    """Authorized, normalized JSON exchange. Not a crawler or a private admin export."""
    path = Path(source['path']).resolve()
    root = (Path(__file__).parent/'imports').resolve()
    if root not in path.parents: raise Unavailable('Exports must be in sync/imports/')
    payload = json.loads(path.read_text())
    return parse_authorized_exchange(payload,source),[]


def parse_authorized_exchange(payload,source):
    if payload.get('schema_version') != 1 or not payload.get('permission_url'):
        raise Unavailable('Missing exchange version or public permission evidence')
    if not source.get('publication_allowed'): raise Unavailable('Export republication not approved')
    records = []
    for item in payload['records']:
        record = dict(item, source_id=source['id'], publication_allowed=True, permission_url=payload['permission_url'])
        if source['adapter'] == 'yfull_export' and record.get('namespace') != 'yfull':
            raise ValueError('YFull export contains another namespace')
        if len(record.get('verified_ids', [])) > 1 and not record.get('identity_evidence_url'):
            raise ValueError('Cross-platform identity requires public linking evidence')
        records.append(record)
    return records


def parse_consent_csv(text,source,file_url):
    reader=csv.DictReader(io.StringIO(text))
    required={'namespace','external_id','country','origin_kind','sample_kind','publication_consent','source_url'}
    if not required.issubset(reader.fieldnames or []): raise ValueError('CSV requires identity, paternal origin and publication consent columns')
    if len(set(reader.fieldnames))!=len(reader.fieldnames): raise ValueError('Duplicate CSV column names')
    rows=[]
    for row in reader:
        consent=str(row.get('publication_consent','')).strip().lower() in ('true','yes','1')
        markers=[]
        for position,label in enumerate(reader.fieldnames):
            canonical=marker_name(label)
            if canonical: markers.append({'marker':canonical,'source_label':label,'position':position,'value':str_value(row[label])})
        record={key:row.get(key,'') for key in ['namespace','external_id','name','ancestor_name','country','origin_raw','origin_kind','sample_kind','y_dna','y_dna_alias','test_type','haplogroup_status','path_source_url']}
        record.update(source_id=source['id'],source_url=row['source_url'] or file_url,project=row.get('project',''),
            publication_allowed=bool(source.get('publication_allowed') and consent),permission_url=source.get('permission_url') or '',
            str_markers=markers,snp_path=[p.strip() for p in row.get('full_snp_path','').split('>') if p.strip()])
        rows.append(record)
    return rows


def collect_github_export(source,http=None):
    if not source.get('publication_allowed') or not str(source.get('permission_url') or '').startswith('https://'):
        raise SourceRestricted('Public export feed lacks republication approval')
    files=GitHubFiles(source['repo'],source.get('branch','main'));files.resolve_head()
    data=files.file(source['path']).decode('utf-8-sig')
    if source.get('format','json')=='csv': return parse_consent_csv(data,source,files.permalink(source['path'])),[]
    if source.get('format','json')!='json': raise ValueError('Only explicitly configured JSON or CSV exports are supported')
    return parse_authorized_exchange(json.loads(data),source),[]


ADAPTERS = {'ftdna_project': collect_ftdna, 'public_export': collect_export, 'yfull_export': collect_export,
            'yfull_github':collect_yfull_github,'ftdnastat_github':collect_ftdnastat,'github_public_export':collect_github_export}
