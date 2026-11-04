"""Build offline CC-BY GeoNames gazetteer: python scripts/build_gazetteer.py EG.zip."""
import hashlib
import json
import sys
import zipfile
from pathlib import Path

TARGET = Path(__file__).resolve().parents[1] / 'sync/data'
# GeoNames ADM1 codes -> ISO 3166-2:EG, and existing frontend labels.
GOVS = [
 ('01','DK','Ad Daqahlīyah','الدقهلية|Dakahlia|Dakahliya|Dakahleya'),
 ('02','BA','Al Bahr al Ahmar','البحر الأحمر|Red Sea'),
 ('03','BH','Al Buhayrah','البحيرة|Beheira'),
 ('04','FYM','Al Fayyūm','الفيوم|Faiyum|Fayoum'),
 ('05','GH','Al Gharbīyah','الغربية|Gharbia'),
 ('06','ALX','Al Iskandarīyah','الإسكندرية|Alexandria'),
 ('07','IS','Al Ismā`īlīyah','الإسماعيلية|Ismailia'),
 ('08','GZ','Al Jīzah','الجيزة|Giza'),
 ('09','MNF','Al Minūfīyah','المنوفية|Monufia|Menofia'),
 ('10','MN','Al Minyā','المنيا|Minya'),
 ('11','C','Cairo','القاهرة|Al Qahira|Cairo'),
 ('12','KB','Al Qalyūbīyah','القليوبية|Qalyubia'),
 ('13','WAD','New Valley','الوادي الجديد|Al Wadi al Jadid'),
 ('14','SHR','Ash Sharqīyah','الشرقية|Sharqia|Sharkeya|Sharkia|Ash Sharqiyah'),
 ('15','SUZ','As Suways','السويس|Suez'),
 ('16','ASN','Aswān','أسوان|Aswan'),
 ('17','AST','Asyūt','أسيوط|Assiut|Asyut'),
 ('18','BNS','Banī Suwayf','بني سويف|Beni Suef'),
 ('19','PTS','Port Said','بورسعيد|Bur Said'),
 ('20','DT','Dumyāt','دمياط|Damietta'),
 ('21','KFS','Kafr ash Shaykh','كفر الشيخ|Kafr el Sheikh'),
 ('22','MT','Matrouh','مطروح|Marsa Matruh'),
 ('23','KN','Qinā','قنا|Qena|Qina'),
 ('24','SHG','Sūhāj','سوهاج|Sohag|Suhag|Suhaj'),
 ('26','JS','Janūb Sīnā\'','جنوب سيناء|South Sinai'),
 ('27','SIN','Shamal Sīnā\'','شمال سيناء|North Sinai'),
 ('28','LX','Luxor','الأقصر|Al Uqsur'),
]


def build(archive):
    mapping = {code: ('EG-'+iso, name, aliases.split('|')) for code, iso, name, aliases in GOVS}
    rows = [line.split('\t') for line in zipfile.ZipFile(archive).read('EG.txt').decode().splitlines()]
    governors = []
    places = []
    for r in rows:
        if r[8] != 'EG' or r[10] not in mapping: continue
        iso, label, extra = mapping[r[10]]
        if r[6] not in ('A', 'P'): continue
        place = dict(id='geonames:'+r[0], name=r[1], aliases=sorted(set([r[2], *r[3].split(',')])),
                     iso=iso, district=r[11] or None, feature=r[7], lat=r[4], lon=r[5],
                     source_url='https://www.geonames.org/'+r[0]+'/')
        if r[7] == 'ADM1':
            governors.append(dict(place, name=label, aliases=sorted(set([r[1],*place['aliases'],*extra]))))
        else: places.append(place)
    assert len(governors) == 27
    for name, value in [('places', places), ('governorates', governors)]:
        (TARGET/(name+'.json')).write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':'))+'\n')
    (TARGET/'LICENSE.md').write_text('GeoNames Egypt extract, CC BY 4.0. Source: https://download.geonames.org/export/dump/EG.zip\n'
        'Retrieved 2026-11-04. Original archive SHA-256: '+hashlib.sha256(Path(archive).read_bytes()).hexdigest()+
        '\nAttribution: GeoNames (https://www.geonames.org/), https://creativecommons.org/licenses/by/4.0/\n'
        'Includes administrative units and populated places. Coverage and historical aliases are incomplete; no fuzzy automatic assignments.\n'
        'ISO crosswalk: https://www.iso.org/obp/ui/#iso:code:3166:EG\n')
    print(f'{len(governors)} governorates, {len(places)} places')


if __name__ == '__main__': build(sys.argv[1])
