import json
import re
import unicodedata
from pathlib import Path

DATA = Path(__file__).parent / 'data'


def normalized(value):
    value = unicodedata.normalize('NFKD', str(value or '')).lower()
    value = ''.join(c for c in value if not unicodedata.combining(c))
    value = value.translate(str.maketrans({'أ': 'ا', 'إ': 'ا', 'آ': 'ا', 'ى': 'ي', 'ـ': ''}))
    return ' '.join(re.sub(r'[^\w\s]', ' ', value).split())


def external_id(namespace, value):
    value = str(value).strip().upper()
    pattern = r'YF\d+' if namespace == 'yfull' else r'(?:[A-Z]{0,3})\d+'
    if namespace not in ('ftdna', 'yfull') or not re.fullmatch(pattern, value):
        raise ValueError('Invalid external ID')
    return value


def marker_name(label):
    # Explicit reviewed aliases; never collapse I into II or split multi-copy alleles.
    key = re.sub(r'[\s_\-]', '', label).upper()
    aliases = {'DYS389I': 'DYS389I', 'DYS389II': 'DYS389II', 'DYS19': 'DYS19',
               'DYS394': 'DYS19', 'YGATAH4': 'Y-GATA-H4', 'YCAII': 'YCAII', 'CDY': 'CDY'}
    if key in aliases:
        return aliases[key]
    if re.fullmatch(r'(?:DYS|DYF)\d+(?:S\d+)?[AB]?', key):
        return key
    if key in ('YGATAA10', 'YGGAAT1B07'):
        return {'YGATAA10': 'Y-GATA-A10', 'YGGAAT1B07': 'Y-GGAAT-1B07'}[key]
    return None


def str_value(value):
    if value is None:
        return None
    text = str(value).strip()
    if text in ('', '-', '—', '?', 'null'):
        return None
    if not re.fullmatch(r'\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)*', text):
        raise ValueError('Unrecognized STR allele format')
    return text


class Gazetteer:
    def __init__(self, places=None):
        self.governorates = json.loads((DATA / 'governorates.json').read_text())
        self.places = places if places is not None else json.loads((DATA / 'places.json').read_text())
        self.index = {}
        for place in self.places + self.governorates:
            for alias in [place['name'], *place.get('aliases', [])]:
                key = normalized(alias)
                if key:
                    self.index.setdefault(key, {})[str(place['id'])] = place

    def resolve(self, raw, country='', paternal=True):
        result = {'raw': raw, 'status': 'unknown', 'country': None, 'governorate_iso': None,
                  'governorate': None, 'place_id': None, 'candidates': []}
        if not paternal:
            return result
        # Exact component matches only. Names and haplogroups never establish nationality.
        egypt = normalized(country) in ('egypt', 'eg', 'مصر', 'egypt arab republic of')
        parts = [normalized(p) for p in re.split(r'[,;/،\n]', raw or '') if normalized(p)]
        egypt |= any(p in ('egypt', 'مصر') for p in parts)
        matches = []
        for p in parts:
            if p in ('egypt', 'مصر'):
                continue
            if p in self.index:
                matches.append(list(self.index[p].values()))
        # A governorate component can disambiguate a village component.
        codes = None
        for group in matches:
            found = {p['iso'] for p in group}
            codes = found if codes is None else codes & found
        if matches and not codes:
            result['status'] = 'conflict'
        elif codes and len(codes) == 1:
            iso = next(iter(codes))
            # Gazetteer alone does not prove Egypt for globally ambiguous place names.
            if egypt:
                place = next(p for g in matches for p in g if p['iso'] == iso)
                gov = next(g for g in self.governorates if g['iso'] == iso)
                result.update(status='resolved', country='EG', governorate_iso=iso,
                              governorate=gov['name'], place_id=place['id'])
        elif codes:
            result['status'] = 'ambiguous'
        if egypt:
            result['country'] = 'EG'
        result['candidates'] = sorted(codes or [])
        return result


def prepare(record, gazetteer):
    record = dict(record)
    record['external_id'] = external_id(record['namespace'], record['external_id'])
    record['origin'] = gazetteer.resolve(record.get('origin_raw', ''), record.get('country', ''),
                                        record.get('origin_kind') == 'paternal')
    reasons = []
    positions = set()
    for marker in record.get('str_markers', []):
        label = marker.get('source_label') or marker.get('marker', '')
        canonical = marker_name(label)
        if not canonical:
            reasons.append('unreviewed_marker_alias')
            continue
        marker['source_label'], marker['marker'] = label, canonical
        marker['value'] = str_value(marker.get('value'))
        position = marker.get('position')
        if not isinstance(position, int) or position < 0 or position in positions:
            reasons.append('invalid_str_marker_order')
        positions.add(position)
    if record['origin']['country'] != 'EG': reasons.append('egyptian_paternal_origin_unproven')
    if record.get('sample_kind', 'unknown') != 'modern': reasons.append('not_confirmed_modern_customer')
    if not record.get('publication_allowed'): reasons.append('publication_permission_unverified')
    if record.get('publication_allowed') and not record.get('permission_url', '').startswith('https://'):
        reasons.append('publication_permission_evidence_missing')
    if not record.get('source_url', '').startswith('https://'): reasons.append('missing_public_evidence')
    haplo = record.get('y_dna', '').strip()
    if haplo and not re.fullmatch(r'[A-T][A-Za-z0-9*.+_\-]*', haplo): reasons.append('invalid_haplogroup')
    if not haplo and not record.get('str_markers'): reasons.append('no_y_result')
    path = record.get('snp_path', [])
    if path and (not isinstance(path, list) or not str(record.get('path_source_url') or '').startswith('https://') or path[-1] != haplo):
        reasons.append('unverified_snp_path')
        record['snp_path'] = []
    for identity in record.get('verified_ids', []):
        identity['external_id'] = external_id(identity['namespace'], identity['external_id'])
    if record.get('verified_ids') and not record.get('identity_evidence_url', '').startswith('https://'):
        reasons.append('public_identity_link_missing')
    test = record.get('test_type', '')
    record['test_status'] = ('confirmed_big_y' if re.fullmatch(r'Big Y-(500|700)', test) and record['namespace'] == 'ftdna'
                             else 'yfull_sequencing' if record['namespace'] == 'yfull'
                             else 'snp_tested' if record.get('haplogroup_status') == 'confirmed'
                             else 'str_only' if record.get('haplogroup_status') == 'predicted' or not haplo or re.fullmatch(r'Y-DNA(?:12|25|37|67|111)', test)
                             else 'unknown')
    if record['test_status'] == 'confirmed_big_y': record['haplogroup_status'] = 'confirmed'
    if record['test_status'] == 'yfull_sequencing': record['test_type'] = 'YFull sequencing'
    if record['origin']['status'] in ('ambiguous', 'conflict'): record['location_review'] = True
    record['review_reasons'] = reasons
    record['accepted'] = not reasons
    return record
