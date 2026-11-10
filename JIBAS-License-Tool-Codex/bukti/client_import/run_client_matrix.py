"""Controlled replay against the unmodified client importer; no live DB writes."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from license_codec import generate_license, _load, _serialize, _encrypt, IMPORT_HEADER

inputs = HERE / "inputs"
inputs.mkdir(exist_ok=True)

def make(name, dbid, sysid, **kw):
    p = inputs / (name + ".lic")
    result = generate_license(database_id=dbid, system_id=sysid, expires="2028-12-31", capacity=100,
                              output_path=p, overwrite=True, **kw)
    return p, result

new, nr = make("v4yne_new", "V4YNE", "DDCB4")
renew, _ = make("v4yne_renew", "V4YNE", "DDCB4", previous_license_path=new)
_, _, _, fields = _load(renew)
changed = inputs / "v4yne_changed_client.lic"
fields["KlienId"] = "DIFFERENT_CLIENT"
fields["Sequence"] = 3
changed.write_bytes(IMPORT_HEADER + _encrypt(_serialize(fields)))
missing = inputs / "missing_header.lic"
missing.write_bytes(new.read_bytes().split(b"\n", 1)[1])
wrong = inputs / "wrong_header.lic"
wrong.write_bytes(b"# LISENSI PRODUK LAIN\r\n" + missing.read_bytes())
lower = inputs / "lowercase_header.lic"
lower.write_bytes(b"# lisensi jibas spt face\r\n" + missing.read_bytes())
abcdef, _ = make("abcde_new", "ABCDE", "ABCDE")
digits, _ = make("12345_new", "12345", "12345")
different_system, _ = make("v4yne_different_system", "V4YNE", "00000")

cases = [
    ("headerless_rejected", "V4YNE", [missing]),
    ("wrong_header_rejected", "V4YNE", [wrong]),
    ("lowercase_header", "V4YNE", [lower]),
    ("fresh_renewal", "V4YNE", [new, new, renew, changed]),
    ("mismatched_db", "VWXYZ", [new]),
    ("different_id_abcde", "ABCDE", [abcdef]),
    ("different_id_digits", "12345", [digits]),
    ("different_system_id_accepted_by_importer", "V4YNE", [different_system]),
]
results = []
for label, dbid, paths in cases:
    sandbox = HERE / ("verify_" + label)
    if sandbox.exists():
        sandbox = Path(tempfile.mkdtemp(prefix="verify_" + label + "_", dir=HERE))
    completed = subprocess.run([str(HERE / "ClientImportVerify.exe"), str(sandbox), dbid,
                                *map(str, paths)], check=True, capture_output=True, text=True)
    result = json.loads(completed.stdout)
    result["label"] = label
    (HERE / (label + ".json")).write_text(json.dumps(result, indent=2), encoding="utf-8")
    results.append(result)
(HERE / "matrix_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
for r in results:
    print(r["label"], [(a["accepted"], a.get("exception"), a["cache_validator_returned"]) for a in r["attempts"]])
