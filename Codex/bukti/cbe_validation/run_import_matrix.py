"""Replay original CBE UI importer 05C0 and cache loader 05BE in isolated processes."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT))
import cbe_codec as cbe
import license_codec as face
import schoolpay_codec as schoolpay

source=HERE/'CbeImportProbe.cs'
exe=HERE/'CbeImportProbe.exe'
subprocess.run([r'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe','/nologo','/platform:x64',
    '/r:System.Web.Extensions.dll','/r:System.Data.dll','/out:'+str(exe),str(source)],check=True)
inputs=HERE/'generated'
inputs.mkdir(exist_ok=True)


def make(label,dbid='ABCDE',systemid='DDCB4',**kwargs):
    p=inputs/(label+'.lic')
    cbe.generate_license(database_id=dbid,system_id=systemid,expires='2030-12-31',capacity=100,
                         output_path=p,overwrite=True,**kwargs)
    return p


def mutate(label,base,edits=None,remove=()):
    fields=cbe.inspect_license(base)['fields']
    fields.update(edits or {})
    root=ET.fromstring(cbe._serialize(fields))
    row=root.find(cbe.TABLE)
    for name in remove:
        if row.find(name) is not None:row.remove(row.find(name))
    p=inputs/(label+'.lic')
    p.write_bytes(cbe.IMPORT_HEADER+face._encrypt(ET.tostring(root,encoding='ascii').decode('ascii')))
    return p


def run(label,dbid,paths,expected):
    sandbox=tempfile.mkdtemp(prefix='codex-cbe-'+label+'-')
    r=subprocess.run([str(exe),sandbox,dbid,'060005C0',*map(str,paths)],
                     check=True,capture_output=True,text=True,encoding='utf-8',timeout=25)
    value=json.loads(r.stdout)
    value['label']=label
    value['expected_acceptance']=expected
    (HERE/(label+'.json')).write_text(json.dumps(value,indent=2),encoding='utf-8')
    print(label,[(a['accepted'],a.get('exception')) for a in value['attempts']])
    assert [a['accepted'] for a in value['attempts']]==expected,label
    for a in value['attempts']:
        if a['accepted']:
            assert a['cache_exists'] and a['cache_loader_returned'],label
            assert a['after_client']==a['reloaded_client'],label
            assert a['after_sequence']==a['reloaded_sequence'],label
    return value


cases=[]
for dbid,systemid in [('ABCDE','DDCB4'),('V4YNE','ABCDE'),('Z9X8W','123AB')]:
    base=make(dbid+'_new',dbid,systemid)
    renewal=make(dbid+'_renew',dbid,systemid,previous_license_path=base)
    other=mutate(dbid+'_different_client',renewal,{'KlienId':'SYNTHETIC_OTHER_CLIENT','Sequence':'3'})
    down=mutate(dbid+'_lowerseq',base,{'Sequence':'0'})
    for label,db,paths,expected in [
        ('fresh',dbid,[base],[True]),('renewal',dbid,[base,renewal],[True,True]),
        ('same_sequence',dbid,[base,base],[True,False]),
        ('decreased_sequence',dbid,[base,down],[True,False]),
        ('different_client',dbid,[base,other],[True,False]),
        ('wrong_database','ZZZZZ',[base],[False])]:
        cases.append(run(dbid+'_'+label,db,paths,expected))

base=inputs/'ABCDE_new.lic'
payload=base.read_bytes().split(b'\n',1)[1]
noheader=inputs/'no_header.lic';noheader.write_bytes(payload)
arbitrary=inputs/'arbitrary_comment.lic';arbitrary.write_bytes(b'# ANOTHER PRODUCT\r\n'+payload)
lower=inputs/'lowercase_comment.lic';lower.write_bytes(b'# lisensi jibas cbe\r\n'+payload)
broken=inputs/'broken.lic';broken.write_bytes(b'Invalid base64 ciphertext!\r\n')
face_file=inputs/'face_product.lic'
face.generate_license(database_id='ABCDE',system_id='DDCB4',expires='2030-12-31',capacity=100,
                      output_path=face_file,overwrite=True)
schoolpay_file=inputs/'schoolpay_product.lic'
schoolpay.generate_license(database_id='ABCDE',system_id='DDCB4',expires='2030-12-31',capacity=100,
                           output_path=schoolpay_file,overwrite=True)
for label,p,expected in [
    ('no_header',noheader,True),('arbitrary_comment',arbitrary,True),('lowercase_comment',lower,True),
    ('broken_ciphertext',broken,False),('face_product_compatible_schema',face_file,True),
    ('schoolpay_product_incompatible_schema',schoolpay_file,False),
    ('model_face',mutate('model_face',base,{'Model':'SPTFACE'}),True),
    ('model_empty',mutate('model_empty',base,{'Model':''}),True),
    ('model_row_missing',mutate('model_row_missing',base,remove=('Model',)),True),
    ('wrong_info1',mutate('wrong_info1',base,{'Info1':'00000'}),True),
    ('wrong_seri',mutate('wrong_seri',base,{'Seri':'00000'}),True),
    ('already_expired',mutate('expired',base,{'LicenseLimit':'2020-01-01','LicenseLimitDate':'2020-01-01T23:59:00+07:00'}),True),
    ('capacity_overflow',mutate('capacity_overflow',base,{'MaxClient':'2147483648'}),False),
    ('sequence_overflow',mutate('sequence_overflow',base,{'Sequence':'2147483648'}),False),
    ('missing_maxclient',mutate('missing_maxclient',base,remove=('MaxClient',)),False),
    ('missing_info1',mutate('missing_info1',base,remove=('Info1',)),True),
]:
    cases.append(run(label,'ABCDE',[p],[expected]))

summary={'scenario_count':len(cases),'attempt_count':sum(len(c['attempts']) for c in cases),
         'accepted_attempts':sum(a['accepted'] for c in cases for a in c['attempts']),
         'all_expected_outcomes':True,'original_importer':'0x060005C0','official_ui_handler':'0x06000BB6',
         'original_cache_loader':'0x060005BE','current_database_holder':'0x040003F3',
         'target_binary_unmodified':True,'hooks_or_patches_used':False,
         'runtime_activated':False,
         'scope':'Controlled importer/cache replay only; target Main/UI, database, and online activation workflow not executed.'}
(HERE/'matrix_results.json').write_text(json.dumps(cases,indent=2),encoding='utf-8')
(HERE/'matrix_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary))
