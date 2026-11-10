"""Replay original server importer/runtime against multiple generated IDs.

Run with Python; requires Windows .NET Framework compiler. No live writes.
"""
from pathlib import Path
import sys, subprocess, json

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent.parent
sys.path.insert(0, str(TOOL))
import license_codec as lc

def main():
    csc = Path(r'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe')
    exe = HERE / 'ServerMatrixProbe.exe'
    subprocess.run([str(csc), '/nologo', '/r:System.Web.Extensions.dll', '/r:System.Data.dll',
                    '/out:' + str(exe), str(HERE/'ServerMatrixProbe.cs')], check=True)
    gen = HERE / 'generated'
    gen.mkdir(exist_ok=True)
    scenarios = []
    def make(name, db, system, **kwargs):
        path = gen/(name+'.lic')
        lc.generate_license(database_id=db, system_id=system, expires='2028-12-31',
                            capacity=123, output_path=path, overwrite=True, **kwargs)
        return path
    def run(name, candidate, db, system, expected_import, previous=None, expected_runtime=True):
        args = [str(exe), str(candidate), db, system]
        if previous: args.append(str(previous))
        proc = subprocess.run(args, capture_output=True, text=True, timeout=40)
        if proc.returncode: raise RuntimeError(proc.stderr)
        obj = json.loads(proc.stdout)
        obj['scenario'] = name
        passed = (obj['candidate_import'] is True if expected_import else
                  (obj['candidate_import'] is False or isinstance(obj['candidate_import'], str)))
        if not expected_import:
            expected_error = next((message for suffix, message in [
                ('_db_mismatch','Database Id tidak sama'),
                ('_renewal_equal_sequence','Sequence lisensi sama'),
                ('_renewal_changed_client','Client Id tidak sama'),
                ('_renewal_decreased_sequence','Sequence lisensi lebih kecil'),
                ('server_corrupt','FormatException:'),
                ('server_wrong_crypto','CryptographicException:'),
            ] if name.endswith(suffix)), None)
            if expected_error:
                obj['expected_error_substring'] = expected_error
                passed = passed and expected_error in str(obj['candidate_import'])
            passed = passed and (obj['after_sequence'] == obj['before_sequence'])
            passed = passed and (obj['after_client'] == obj['before_client'])
            if not previous: passed = passed and not obj['cache_written']
        if previous: passed = passed and obj['previous_import'] is True
        if expected_import:
            observed = {c['name']:c['accepted'] for c in obj['runtime_cases']}
            expected = dict(actual_injected_environment=expected_runtime,
                            matching_license_environment=True, wrong_database=False,
                            wrong_system=False, legacy_day_after_expiry=True,
                            expired=False, at_capacity=True,
                            over_capacity=False, trial=False)
            obj['runtime_expectations'] = expected
            passed = passed and observed == expected
        obj['assertions_passed'] = passed
        (HERE/(name+'.json')).write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding='utf-8')
        scenarios.append(dict(name=name, passed=passed, importer=obj['candidate_import']))
    for db, system in [('V4YNE','DDCB4'), ('ABCDE','DDCB4'), ('Z9X8W','123AB'), ('V4YNE','7738F')]:
        prefix = db+'_'+system
        fresh = make(prefix,db,system)
        run(prefix+'_fresh',fresh,db,system,True)
        run(prefix+'_db_mismatch',fresh,'WRK9T',system,False)
        run(prefix+'_system_mismatch',fresh,db,'FFFFF',True,expected_runtime=False)
        renewed = make(prefix+'_renewal',db,system,previous_license_path=fresh)
        run(prefix+'_renewal_ok',renewed,db,system,True,previous=fresh)
        run(prefix+'_renewal_equal_sequence',fresh,db,system,False,previous=fresh)
        changed = make(prefix+'_client_changed',db,system,sequence=2)
        run(prefix+'_renewal_changed_client',changed,db,system,False,previous=fresh)
        run(prefix+'_renewal_decreased_sequence',fresh,db,system,False,previous=renewed)
    # Server importer tolerates comment/blank/split lines; internal cache loader differs.
    fresh = gen/'V4YNE_DDCB4.lic'
    text=fresh.read_text().strip()
    wrapped=gen/'server_comments.lic'
    wrapped.write_text('# comment\n\n'+text[:100]+'\n'+text[100:]+'\n',encoding='ascii')
    run('server_comments_multiline',wrapped,'V4YNE','DDCB4',True)
    corrupt=gen/'corrupt.lic'
    corrupt.write_bytes(b'not a license!')
    run('server_corrupt',corrupt,'V4YNE','DDCB4',False)
    fields=lc.inspect_license(fresh)['fields']
    wrong=gen/'wrong_crypto.lic'
    wrong.write_bytes(lc._encrypt(lc._serialize(fields),profile='client_fgr'))
    run('server_wrong_crypto',wrong,'V4YNE','DDCB4',False)
    report=dict(scenarios=scenarios, total=len(scenarios),
                all_passed=all(x['passed'] for x in scenarios),
                scope='Original methods, controlled environment field injection; not live production activation')
    (HERE/'matrix_summary.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
    return 0 if report['all_passed'] else 1

if __name__ == '__main__': raise SystemExit(main())
