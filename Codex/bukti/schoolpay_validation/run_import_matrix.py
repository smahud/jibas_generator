"""Original official UI importer 0757 and cache loader 0756 in isolated processes."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
import schoolpay_codec as schoolpay
import license_codec as face

source = HERE / 'SchoolPayImportProbe.cs'
exe = HERE / 'SchoolPayImportProbe.exe'
subprocess.run([r'C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe','/nologo','/platform:x86',
                '/r:System.Web.Extensions.dll','/out:'+str(exe),str(source)],check=True)
inputs = HERE/'generated'
inputs.mkdir(exist_ok=True)


def make(label, dbid='7VJM4', systemid='DDCB4', **kwargs):
    path=inputs/(label+'.lic')
    schoolpay.generate_license(database_id=dbid,system_id=systemid,expires='2030-12-31',
        capacity=100,output_path=path,overwrite=True,**kwargs)
    return path


def mutate(label, original, edits=None, for_import=True):
    fields=schoolpay.inspect_license(original)['fields']
    fields.update(edits or {})
    path=inputs/(label+'.lic')
    path.write_bytes(schoolpay.IMPORT_HEADER + face._encrypt(schoolpay._serialize(fields,for_import=for_import)))
    return path


def run(label, dbid, systemid, paths):
    sandbox=tempfile.mkdtemp(prefix='codex-schoolpay-'+label+'-')
    result=subprocess.run([str(exe),sandbox,dbid,systemid,'06000757',*map(str,paths)],
                          check=True,capture_output=True,text=True,encoding='utf-8')
    value=json.loads(result.stdout)
    value['label']=label
    (HERE/(label+'.json')).write_text(json.dumps(value,indent=2),encoding='utf-8')
    return value


cases=[]
for dbid,systemid in [('7VJM4','DDCB4'),('ABCDE','ABCDE'),('12345','12345')]:
    base=make(dbid+'_new',dbid,systemid)
    renewal=make(dbid+'_renew',dbid,systemid,previous_license_path=base)
    other=mutate(dbid+'_otherclient',renewal,{'KlienId':'ANOTHER_CLIENT','Sequence':'3'})
    down=mutate(dbid+'_lowerseq',base,{'Sequence':'0'})
    for label,db,system,paths in [
        ('fresh',dbid,systemid,[base]),
        ('renewal',dbid,systemid,[base,renewal]),
        ('same_sequence',dbid,systemid,[base,base]),
        ('decreased_sequence',dbid,systemid,[base,down]),
        ('different_client',dbid,systemid,[base,other]),
        ('wrong_database','ZZZZZ',systemid,[base]),
        ('wrong_system',dbid,'00000',[base])]:
        cases.append(run(dbid+'_'+label,db,system,paths))
base=inputs/'7VJM4_new.lic'
noheader=inputs/'noheader.lic';noheader.write_bytes(base.read_bytes().split(b'\n',1)[1])
wrongheader=inputs/'wrongheader.lic';wrongheader.write_bytes(b'# ANOTHER PRODUCT\r\n'+noheader.read_bytes())
broken=inputs/'broken.lic';broken.write_bytes(b'Invalid base64 ciphertext!\r\n')
schema_only=inputs/'flag_schema_only.lic'
xml=ET.fromstring(schoolpay._load(base)[1])
row=xml.find(schoolpay.TABLE)
row.remove(row.find('ForSchoolPay'))
schema_only.write_bytes(schoolpay.IMPORT_HEADER+face._encrypt(ET.tostring(xml,encoding='ascii').decode('ascii')))
for label,path in [
    ('no_header',noheader),('arbitrary_comment_header',wrongheader),('broken_ciphertext',broken),
    ('no_for_schoolpay',mutate('no_flag',base,for_import=False)),
    ('flag_zero',mutate('flag_zero',base,{'ForSchoolPay':'0'})),
    ('flag_false',mutate('flag_false',base,{'ForSchoolPay':'false'})),
    ('flag_empty',mutate('flag_empty',base,{'ForSchoolPay':''})),
    ('flag_schema_only',schema_only),
    ('capacity_int32_overflow',mutate('capacity_overflow',base,{'MaxVendor':'2147483648'})),
    ('already_expired',mutate('expired',base,{'LicenseLimit':'2020-01-01','LicenseLimitDate':'2020-01-01T23:59:00+07:00'}))]:
    cases.append(run(label,'7VJM4','DDCB4',[path]))
(HERE/'matrix_results.json').write_text(json.dumps(cases,indent=2),encoding='utf-8')
expectations = {
    'same_sequence': [True,False], 'decreased_sequence': [True,False],
    'different_client': [True,False], 'wrong_database': [False],
    'broken_ciphertext': [False], 'no_for_schoolpay': [False],
    'capacity_int32_overflow': [False], 'renewal': [True,True],
}
errors = {
    'same_sequence':'Sequence lisensi sama', 'decreased_sequence':'Sequence lisensi lebih kecil',
    'different_client':'Client Id tidak sama', 'wrong_database':'Database Id tidak sama',
    'broken_ciphertext':'Base-64', 'no_for_schoolpay':'ForSchoolPay',
    'capacity_int32_overflow':'Int32',
}
for case in cases:
    print(case['label'],[(r['accepted'],r.get('exception')) for r in case['attempts']])
    suffix=next((key for key in expectations if case['label'].endswith(key)),None)
    expected=expectations[suffix] if suffix else [True]
    assert [r['accepted'] for r in case['attempts']] == expected, case['label']
    for attempt in case['attempts']:
        if attempt['accepted']:
            assert attempt['cache_exists'] and attempt['cache_loader_returned'],case['label']
        elif suffix in errors:
            assert errors[suffix] in attempt['exception'],case['label']
summary={'scenario_count':len(cases),'attempt_count':sum(len(c['attempts']) for c in cases),
         'all_expected_outcomes':True,'original_importer':'0x06000757',
         'original_cache_loader':'0x06000756',
         'full_runtime_activation_tested':False,
         'limitation':'Runtime 09D0 is opaque VM with no proven safe online/DB guard; it was not executed.'}
(HERE/'matrix_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary))
