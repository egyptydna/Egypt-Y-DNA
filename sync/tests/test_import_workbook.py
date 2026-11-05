import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from sync.import_workbook import public_text,read_xlsx,paternal_location,reference_index,plan
from sync.normalize import Gazetteer

class WorkbookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.gaz=Gazetteer()
    def test_contact_details_are_redacted(self):
        self.assertNotIn('01001234567',public_text('Ancestor, 01001234567'))
        self.assertNotIn('person@example.org',public_text('Ancestor person@example.org'))
        self.assertIn('1830-1884',public_text('Ancestor 1830-1884'))
    def test_paternal_place_cues_use_exact_reviewed_gazetteer(self):
        r=paternal_location('عائلة تجريبية — مركز فاقوس-محافظة الشرقية',self.gaz)
        self.assertEqual(r['governorate_iso'],'EG-SHR')
        self.assertEqual(paternal_location('Test family, Mit Ghamr',self.gaz)['governorate_iso'],'EG-DK')
        self.assertEqual(paternal_location('عائلة القاهرة',self.gaz)['status'],'unknown')
    def test_conflicting_governorates_remain_unassigned(self):
        r=paternal_location('محافظة الشرقية - محافظة الدقهلية',self.gaz)
        self.assertEqual(r['status'],'conflict');self.assertIsNone(r['governorate_iso'])
    def test_reference_conflicts_are_not_used(self):
        refs=reference_index({'nodes':[{'path':['J-M267','J-TEST1']},{'path':['J-M172','J-TEST1']}]})
        self.assertNotIn('J-TEST1',refs)
    def test_xlsx_reads_selected_fields_and_never_interprets_about_me(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'test.xlsx'
            ns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
            def cell(ref,text):return f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>'
            header=['Name','Y-DNA haplogroup','Paternal ancestor name','Paternal country','About me','Maternal ancestor name']
            with zipfile.ZipFile(path,'w') as z:
                z.writestr('xl/workbook.xml',f'<workbook xmlns="{ns}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Test" r:id="s1"/></sheets></workbook>')
                z.writestr('xl/_rels/workbook.xml.rels','<Relationships><Relationship Id="s1" Target="worksheets/sheet1.xml"/></Relationships>')
                z.writestr('xl/worksheets/sheet1.xml',f'<worksheet xmlns="{ns}"><sheetData><row r="1">'+''.join(cell(chr(65+i)+'1',v) for i,v in enumerate(header))+'</row><row r="2">'+''.join(cell(chr(65+i)+'2',v) for i,v in enumerate(['SYNTHETIC SOURCE ROW','J-TEST1','Test, Mit Ghamr','Egypt','01001234567','DO NOT IMPORT']))+'</row></sheetData></worksheet>')
            value=plan(path,archive=[{'id':1,'name':'SYNTHETIC SOURCE ROW','kit_number':'990099001'}])
            self.assertEqual(len(value['rows']),1);r=value['rows'][0]
            self.assertEqual(r['candidate_ids'],[1]);self.assertNotIn('kit_number',r)
            self.assertNotIn('01001234567',json.dumps(value));self.assertNotIn('DO NOT IMPORT',json.dumps(value))
            self.assertEqual(r['governorate_iso'],'EG-DK')
            self.assertEqual(r['snp_path'],[])
