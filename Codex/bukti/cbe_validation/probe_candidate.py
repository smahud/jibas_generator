"""Exploratory original-18-column candidate, before final codec construction."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT))
import license_codec as face

format=json.loads((ROOT/'bukti/cbe/format_probe.json').read_text(encoding='utf-8-sig'))
schema=ET.fromstring(format['schema_xml'])
fields=dict(Versi='26.5',KlienId='CBE-SYNTHETIC-CLIENT',Klien='CBE TEST',Tanggal='2026-11-10',
            Model='CBE',Seri='DDCB4',Size='100',Sequence='1',KodeRs='',KodeTx='',DbId='ABCDE',
            LicenseLimit='2030-12-31',LicenseLimitDate='2030-12-31T23:59:00+07:00',
            MaxClient='100',Keterangan='',Info1='DDCB4',Info2='',Info3='')
row=ET.SubElement(schema,format['table'])
for name in fields: ET.SubElement(row,name).text=fields[name]
candidate=HERE/'candidate_18.lic'
candidate.write_bytes(b'# LISENSI JIBAS CBE\r\n'+face._encrypt(ET.tostring(schema,encoding='ascii').decode('ascii')))
sandbox=tempfile.mkdtemp(prefix='codex-cbe-candidate-')
result=subprocess.run([str(HERE/'CbeImportProbe.exe'),sandbox,'ABCDE','060005C0',str(candidate)],
                      capture_output=True,text=True,encoding='utf-8',timeout=20)
if result.returncode: raise RuntimeError(result.stderr)
data=json.loads(result.stdout)
(HERE/'candidate_18_result.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
print(json.dumps(data))
