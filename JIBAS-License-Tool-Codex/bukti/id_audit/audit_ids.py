"""Reproduce ID oracle checks on an isolated MariaDB instance at 127.0.0.1:3435.

Requires a separately initialized mysql_sandbox datadir. Never points mutations
at production: port is fixed to 3435 and the live 3434 snapshot is read-only.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent.parent
sys.path.insert(0, str(TOOL))
from id_detect import DbIdDetector, SystemIdDetector
from dbid_recipe import RECIPE
import pymysql

PORT = 3435
PASSWORD = "codex_isolated_test"

def oracle():
    env = dict(os.environ, ID_AUDIT_MYSQL_PASSWORD=PASSWORD)
    p = subprocess.run([str(HERE / "IdOracle.exe"), "db", str(PORT)],
                       capture_output=True, text=True, env=env)
    if p.returncode:
        return {"exit_code": p.returncode, "error": p.stderr.strip()}
    return json.loads(p.stdout)

def snapshot(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT ROUTINE_NAME, ROUTINE_DEFINITION FROM information_schema.ROUTINES "
                    "WHERE ROUTINE_SCHEMA='jbssat' ORDER BY ROUTINE_NAME")
        return [{"name": n, "sha256": hashlib.sha256((body or '').encode()).hexdigest()}
                for n, body in cur.fetchall()]

def main():
    # All live-db operations in this script are SELECT statements.
    live = pymysql.connect(host="127.0.0.1", port=3434, user="root",
                           password="kebersamaan", charset="utf8mb4")
    before = snapshot(live)
    result = {"live_port":3434, "isolated_port":PORT,
              "live_routines_before": before, "cases":[]}
    db = pymysql.connect(host="127.0.0.1", port=PORT, user="root", password=PASSWORD,
                         charset="utf8mb4", autocommit=True)
    with db.cursor() as cur:
        cur.execute("CREATE USER IF NOT EXISTS 'root'@'%%' IDENTIFIED BY %s", (PASSWORD,))
        cur.execute("GRANT ALL PRIVILEGES ON jbssat.* TO 'root'@'%'")
        # This destructive reset is confined to our freshly created sandbox.
        cur.execute("DROP DATABASE IF EXISTS jbssat")
        cur.execute("CREATE DATABASE IF NOT EXISTS jbssat")
        cur.execute("USE jbssat")
        cur.execute("CREATE TABLE IF NOT EXISTS codex_nonempty (id INT)")
        # The original AC3 generates the initial routine payloads itself.
        result["bootstrap_original"] = oracle()
        cur.execute("SELECT COUNT(*) FROM information_schema.ROUTINES WHERE ROUTINE_SCHEMA='jbssat'")
        result["bootstrap_routine_count"] = cur.fetchone()[0]
        result["bootstrap_detector"] = DbIdDetector(port=PORT,password=PASSWORD).detect()[0]
        for wanted in ["V4YNE", "ABCDE", "WRK9T", "Z9X8W", "a1b2c"]:
            for proc in range(1,13):
                cur.execute(f"DROP PROCEDURE IF EXISTS jbssat.splang{proc:02}")
                payloads = [list("X"*64) for _ in range(9)]
                for k,(p,out,pos) in enumerate(RECIPE):
                    if p==proc: payloads[out][pos]=wanted[k]
                outputs = ','.join(f"OUT uh{c} VARCHAR(128)" for c in "abcdefghi")
                assignments=';'.join(f"SET uh{c}='{''.join(payloads[i]).encode('ascii').hex()}'"
                                     for i,c in enumerate("abcdefghi"))
                cur.execute(f"CREATE PROCEDURE jbssat.splang{proc:02}({outputs}) BEGIN {assignments}; END")
            real=oracle()
            python_id,details=DbIdDetector(port=PORT,password=PASSWORD).detect()
            result["cases"].append({"fixture_id":wanted,"original":real,"python":python_id,
                                    "match":real.get('original_AC3')==python_id==wanted.upper(),
                                    "recipe_pieces":details['pieces']})
        cur.execute("DROP PROCEDURE jbssat.splang12")
        result["missing_one_original"]=oracle()
    result["live_routines_after"]=snapshot(live)
    result["live_routines_unchanged"]=(result["live_routines_after"]==before)
    db.close();live.close()
    hardware=json.loads((HERE/'original_hardware_vectors.json').read_text(encoding='utf-8-sig'))
    result['system_hash_vectors']=[dict(v, python_digest=SystemIdDetector._md5_hex(v['input']),
          match=SystemIdDetector._md5_hex(v['input'])==v['digest']) for v in hardware['vectors']]
    result['live_detector']={'database_id':DbIdDetector().detect()[0],
                             'system_id':SystemIdDetector().detect()[0]}
    (HERE/'isolated_db_matrix.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({"cases":len(result['cases']),"all_match":all(c['match'] for c in result['cases']),
                      "hardware_vectors_match":all(c['match'] for c in result['system_hash_vectors']),
                      "live_routines_unchanged":result['live_routines_unchanged'],
                      "live_detector":result['live_detector'],
                      "bootstrap":result['bootstrap_original'],
                      "bootstrap_detector":result['bootstrap_detector']}))
    assert all(c['match'] for c in result['cases'])
    assert all(c['match'] for c in result['system_hash_vectors'])
    assert result['live_routines_unchanged']

if __name__=='__main__': main()
