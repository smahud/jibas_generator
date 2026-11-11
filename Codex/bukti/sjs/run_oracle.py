"""Reproduce original local SJS import controls; no database or online calls."""
from pathlib import Path
import base64
import hashlib
import json
import subprocess
import sys
import tempfile

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE))
import sjs_codec as codec

TARGET = Path(r"C:\Program Files (x86)\YIM\JIBAS SJS - Sinkronisasi Jendela Sekolah 7.10")
CSC = Path(r"C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe")
EVIDENCE = Path(__file__).resolve().parent


def run():
    sandbox = Path(tempfile.mkdtemp(prefix="codex-sjs-matrix-"))
    exe = sandbox / "SjsImportProbe.exe"
    subprocess.run([str(CSC), "/nologo", "/r:System.Data.dll", "/r:System.Web.Extensions.dll",
                    f"/out:{exe}", str(EVIDENCE / "SjsImportProbe.cs")], check=True, capture_output=True)
    def probe(*args):
        r = subprocess.run([str(exe), str(TARGET), *map(str, args)], check=True,
                           capture_output=True, text=True)
        return json.loads(r.stdout)
    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    live = [TARGET / n for n in ("JsSync.exe", "config.ini", "license.enc")]
    before = {p.name: digest(p) for p in live}
    token = probe("token")
    token_check = codec.inspect_registration_token(token["token"])
    def fixture(name, database="AB123", school="SCHOOL-EXISTING-001", previous=None):
        p = sandbox / (name + ".lic")
        codec.generate_license(database_id=database, registration_token=token["token"],
            school_id=school, client_name="Synthetic test school", expires="2030-12-31",
            capacity=1, output_path=p, previous_license_path=previous)
        return p
    first = fixture("new_ab123")
    renewal = fixture("renewal", previous=first)
    other_school = fixture("other_school", school="SCHOOL-OTHER-002")
    def change(name, field, value, original=first):
        f = codec.inspect_license(original)["fields"]
        f[field] = value
        p = sandbox / (name + ".lic")
        p.write_bytes(codec.IMPORT_HEADER + base64.b64encode(codec._crypto(codec._serialize(f))) + b"\r\n")
        return p
    cases = []
    def case(name, database, candidate, previous="-", expected=True):
        r = probe("import", database, candidate, previous)
        r.update(case=name, expected_acceptance=expected)
        if r.get("accepted") is not expected:
            raise AssertionError((name, r))
        cases.append(r)
    case("new_ab123", "AB123", first)
    for database in ("ZX987", "0A1B2"):
        case("new_" + database.lower(), database, fixture("new_" + database.lower(), database))
    case("wrong_database", "ZZ999", first, expected=False)
    case("expired_first_import_accepted", "AB123", change("expired", "LimitDate", "2020-01-01T00:00:00+07:00"))
    case("expired_renewal_rejected", "AB123", change("expired_renewal", "LimitDate", "2020-01-01T00:00:00+07:00", renewal), first, False)
    case("renewal_positive", "AB123", renewal, first)
    case("renewal_same_sequence", "AB123", first, first, False)
    case("renewal_lower_sequence", "AB123", first, renewal, False)
    case("renewal_other_school", "AB123", change("other_school_seq2", "Sequence", "2", other_school), first, False)
    headerless = sandbox / "headerless.lic"
    headerless.write_bytes(b"\r\n".join(first.read_bytes().splitlines()[1:]) + b"\r\n")
    case("headerless", "AB123", headerless)
    after = {p.name: digest(p) for p in live}
    result = {"target_sha256": before["JsSync.exe"], "mvid": token["mvid"],
              "scope": "Original local importer; DB ID/time supplied as memory fields. No network, DB or Main.",
              "token_fixture": token, "python_token_check": token_check,
              "cases": cases, "live_artifact_hashes_before": before,
              "live_artifact_hashes_after": after, "live_artifacts_unchanged": before == after,
              "all_expected": all(r["accepted"] is r["expected_acceptance"] for r in cases)}
    (EVIDENCE / "oracle_matrix.json").write_text(json.dumps(result, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps({"cases": len(cases), "all_expected": result["all_expected"],
                      "live_artifacts_unchanged": result["live_artifacts_unchanged"]}))


if __name__ == "__main__":
    run()
