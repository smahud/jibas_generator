"""Replay the unmodified Letter Store importer; live installation stays read-only."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import letterstore_codec as codec

TARGET = Path(r"C:\Program Files (x86)\YIM\JIBAS Letter Store 7.0")
CSC = Path(r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe")
EXPECTED_SHA256 = "1bdf678980b4ad985838a1b9ce2233550b3e00f49cd578b481dd01c5e5690915"


def hashes():
    return {name: hashlib.sha256((TARGET / name).read_bytes()).hexdigest()
            for name in ("LetterStore.exe", "license.enc", "config.ini")}


def main():
    before = hashes()
    if before["LetterStore.exe"] != EXPECTED_SHA256:
        raise RuntimeError("This oracle is bound to another executable build.")
    fixtures = HERE / "fixtures"
    fixtures.mkdir(exist_ok=True)
    rows = []
    for database_id in ("ABCDE", "12XYZ", "9Z8Y7"):
        path = fixtures / (database_id + ".lic")
        codec.generate_license(database_id=database_id, output_path=path,
                               client_name="Sekolah Uji", overwrite=True)
        rows.append(database_id + "\t" + str(path))
    path = fixtures / "headerless.lic"
    path.write_bytes((fixtures / "ABCDE.lic").read_bytes().split(b"\r\n", 1)[1])
    rows.extend(("ABCDE\t" + str(path), "QWERT\t" + str(fixtures / "ABCDE.lic")))
    fields = codec.inspect_license(fixtures / "ABCDE.lic")["fields"]
    fields["Versi"] = "1.0"
    path = fixtures / "wrong_version.lic"
    path.write_bytes(codec.IMPORT_HEADER + codec._encrypt(codec._serialize(fields)))
    rows.append("ABCDE\t" + str(path))
    path = fixtures / "empty.lic"
    path.write_bytes(codec._encrypt(codec._serialize()))
    rows.append("ABCDE\t" + str(path))
    cases = HERE / "import_cases.tsv"
    cases.write_text("\n".join(rows), encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="codex-letterstore-oracle-") as build:
        harness = Path(build) / "LetterStoreImportProbe.exe"
        subprocess.run([str(CSC), "/nologo", "/r:System.Data.dll", "/r:System.Web.Extensions.dll",
                        "/out:" + str(harness), str(HERE / "LetterStoreImportProbe.cs")], check=True)
        process = subprocess.run([str(harness), str(cases)], capture_output=True,
                                 text=True, check=True, timeout=45)
    result = json.loads(process.stdout)
    assert [row["accepted"] for row in result["attempts"]] == [True, True, True, True, False, False, False]
    for row in result["attempts"][:4]:
        assert row["registered_flag"] and row["reloaded_registered_flag"]
        assert row["cache_loader_returned"]
        assert not row["duplicate_accepted"] and not row["wrong_runtime_id_registered_flag"]
    after = hashes()
    assert before == after, "A live installation file changed during the replay."
    (HERE / "original_import_results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (HERE / "live_integrity.json").write_text(json.dumps({"before": before, "after": after,
        "unchanged": before == after, "scope": "LetterStore.exe, config.ini, license.enc"}, indent=2), encoding="utf-8")
    print("4 original imports accepted; 3 negative imports rejected; cache/registration flag/duplicate checks passed.")
    print("Live executable, config.ini and license.enc hashes unchanged.")


if __name__ == "__main__":
    main()
