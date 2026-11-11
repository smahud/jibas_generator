"""Reproduce the unmodified importer -> cache-loader -> serial-validator replay.

Windows/.NET Framework 4.8 required. Harness EXEs and target copies are created
only under temporary directories. No Main/UI/database methods are invoked.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
import fingerprint_codec as codec

TARGETS = {
    "manager": (Path(r"C:\Program Files\YIM\JIBAS Face & Fingerprint Manager 16.5"), "FaceFingerManager.exe", "license.enc"),
    "client14": (Path(r"C:\Program Files (x86)\YIM\JIBAS Fingerprint Client 14.0"), "Yim.Jibas.Sat.Fgr.Client.exe", "license.enc"),
    "client16": (Path(r"C:\Program Files\YIM\JIBAS Face & Fingerprint Client 16.10"), "FaceFgrClient.exe", "licensefgr.enc"),
}


def inventory():
    return {kind: {name: {"sha256": hashlib.sha256((directory / name).read_bytes()).hexdigest(),
                          "size": (directory / name).stat().st_size,
                          "mtime_ns": (directory / name).stat().st_mtime_ns}
                   for name in (exe, cache, "config.ini", exe + ".config") if (directory / name).is_file()}
            for kind, (directory, exe, cache) in TARGETS.items()}


def main():
    before = inventory()
    (HERE / "inventory_before_final_replay.json").write_text(json.dumps(before, indent=2), encoding="utf-8")
    summary = {}
    with tempfile.TemporaryDirectory(prefix="codex-fingerprint-runner-") as work:
        work = Path(work)
        compiler = Path(r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe")
        for stem in ("FingerProbe", "Finger16Probe"):
            subprocess.run([str(compiler), "/nologo", "/r:System.Data.dll", "/r:System.Web.Extensions.dll",
                            f"/out:{work / (stem + '.exe')}", str(HERE / (stem + ".cs"))], check=True)
        candidate = work / "common.lic"
        codec.generate_license(serial="{01234567-89AB-CDEF}", license_scope="both",
                               client_name="Sekolah & École", output_path=candidate)
        for kind in TARGETS:
            harness = "Finger16Probe.exe" if kind == "client16" else "FingerProbe.exe"
            result = json.loads(subprocess.run([str(work / harness), kind, "import", str(candidate)],
                                               check=True, capture_output=True, text=True).stdout)
            (HERE / f"{kind}_final_replay.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            attempt = result["attempts"][0]
            summary[kind] = {key: attempt[key] for key in ("result", "rows", "cache_exists", "cache_reloaded", "same_serial", "wrong_serial")}
            assert summary[kind] == {"result": True, "rows": 1, "cache_exists": True, "cache_reloaded": True,
                                     "same_serial": True, "wrong_serial": False}
    after = inventory()
    (HERE / "inventory_after_final_replay.json").write_text(json.dumps(after, indent=2), encoding="utf-8")
    integrity = {"unchanged": before == after, "scope": "Target EXE, existing config, and fingerprint cache bytes/size/mtime_ns", "products": list(TARGETS)}
    (HERE / "live_integrity.json").write_text(json.dumps(integrity, indent=2), encoding="utf-8")
    assert integrity["unchanged"]
    (HERE / "final_replay_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({"results": summary, "integrity": integrity}, indent=2))


if __name__ == "__main__":
    main()
