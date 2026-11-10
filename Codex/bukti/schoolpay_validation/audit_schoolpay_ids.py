"""Read-only live ID and original date arithmetic comparison."""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import os
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
import schoolpay_id_detect as ids
import license_codec as face
import schoolpay_codec as schoolpay
import pymysql

password = os.environ.get('ID_AUDIT_MYSQL_PASSWORD') or os.environ['JIBAS_DB_PASSWORD']


def routine_hashes():
    with pymysql.connect(host='127.0.0.1',port=3434,user='root',password=password) as connection:
        with connection.cursor() as cursor:
            cursor.execute('SELECT SPECIFIC_NAME,ROUTINE_DEFINITION FROM information_schema.ROUTINES '
                           'WHERE ROUTINE_SCHEMA=%s ORDER BY SPECIFIC_NAME', ('jbsfina',))
            return [{'name': name, 'sha256': hashlib.sha256((definition or '').encode()).hexdigest()}
                    for name, definition in cursor.fetchall()]


def oracle(*arguments):
    result = subprocess.run([str(HERE/'SchoolPayIdProbe.exe'),*arguments], capture_output=True,
                            text=True, encoding='utf-8', check=True)
    return json.loads(result.stdout)


before = routine_hashes()
assert {r['name'] for r in before} == {f'splang{i:02d}' for i in range(1,13)}, 'Refuse bootstrap-capable original call'
environment = dict(os.environ,ID_AUDIT_MYSQL_PASSWORD=password)
raw = subprocess.run([str(HERE/'SchoolPayIdProbe.exe'),'db','3434'], capture_output=True,
                     text=True,encoding='utf-8',check=True,env=environment)
original_dbid = json.loads(raw.stdout)['value']
detected_dbid, detail = ids.DbIdDetector(password=password).detect()
hardware = oracle('hardware')
hardware['python_system_id'] = ids.SystemIdDetector.compute(hardware['disk_serial_raw'],hardware['uuid'])
stamps = ['2026-11-10T12:00','2028-12-31T23:59','2029-01-01T23:59','2100-03-01T00:00',
          '2000-02-29T00:00','2030-01-01T00:00','4084-01-01T00:00',
          '4085-01-01T00:00','9999-12-31T23:59']
dates = oracle('dates',','.join(stamps))
vectors = [{'date': stamp, 'original_0708': dates[stamp],
            'python_schoolpay_legacy_minute':schoolpay._legacy_minute(datetime.fromisoformat(stamp)),
            'python_face_legacy_minute_reference':face._legacy_minute(datetime.fromisoformat(stamp))}
           for stamp in stamps]
after = routine_hashes()
result = {'original_dbid_0824': original_dbid,'python_dbid':detected_dbid,
          'recipe':detail,'hardware':hardware,'minute_vectors':vectors,
          'live_routines_before':before,'live_routines_after':after,
          'routines_unchanged':before==after,
          'all_comparisons_match':original_dbid==detected_dbid and
           hardware['original_system_id']==hardware['python_system_id'] and
           all(v['original_0708']==v['python_schoolpay_legacy_minute'] for v in vectors)}
(HERE/'id_date_oracle.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({k:result[k] for k in ['original_dbid_0824','python_dbid','routines_unchanged','all_comparisons_match']}))
assert result['all_comparisons_match'] and result['routines_unchanged']
