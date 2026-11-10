"""Client 16.10 face cache tests (licenseface.enc trial-fix)."""
from __future__ import annotations

import json
import sys
import hashlib
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOL))

import license_codec  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def server_row() -> dict:
    """Row copied from the real installed Face Server license.enc (fixed seed)."""
    return {
        "Versi": "16.5",
        "KlienId": "64860620A8144467B61AE8898DEF4AF5",
        "Klien": "LOCALHOST",
        "Tanggal": "2026-10-28",
        "Seri": "DDCB4",
        "Size": "100000",
        "Sequence": "1",
        "KodeRs": "",
        "KodeTx": "",
        "DbId": "V4YNE",
        "LicenseLimit": "3000-10-28",
        "LicenseLimitDate": "3000-10-28T23:59:00+07:00",
        "MaxClient": "100000",
        "Keterangan": "",
        "Info1": "DDCB4",
        "Info2": "",
        "Info3": "",
    }


def test_client_face_profile_matches_runtime_pair() -> None:
    key, iv = license_codec._profile("client_face")
    assert hashlib.md5(b"3477K3b3rS4mA4N").digest() == key
    assert iv == b"YaRAhM4nY4R4h1M#"


def test_client_fgr_profile_matches_runtime_pair() -> None:
    key, iv = license_codec._profile("client_fgr")
    assert hashlib.md5(b"3477K3b3rS4ma4N").digest() == key
    assert iv == b"YaRahM@nY4R4h1M#"


def test_original_skeleton_has_no_row(tmp_path) -> None:
    info = license_codec.inspect_client_cache(FIXTURES / "original-empty.enc")
    assert info["has_license_row"] is False
    assert info["status"] == "empty_cache"


def test_write_client_cache_roundtrip(tmp_path) -> None:
    out = tmp_path / "licenseface.enc"
    result = license_codec.write_client_cache(server_row(), out)
    written = license_codec.inspect_client_cache(out)
    assert written["fields"] == {**server_row(), "Model": ""}
    assert written["sha256"] == result["sha256"]
    # Client validator reads the FIRST base64 line; file is b64 + CRLF.
    raw = out.read_bytes()
    assert raw.endswith(b"\r\n")
    assert raw.count(b"\r\n") == 1


def test_write_refuses_overwrite_without_flag(tmp_path) -> None:
    out = tmp_path / "licenseface.enc"
    license_codec.write_client_cache(server_row(), out)
    with pytest.raises(license_codec.LicenseError):
        license_codec.write_client_cache(server_row(), out)


def test_resolve_rejects_trial_row(tmp_path) -> None:
    lic = tmp_path / "trial.lic"
    row = server_row()
    row = {**row, "KlienId": "TRIAL"}
    lic.write_bytes(license_codec._encrypt(license_codec._serialize(row)))
    with pytest.raises(license_codec.LicenseError):
        license_codec.fix_client_cache(_client_stub(tmp_path), lic)


def test_resolve_rejects_incomplete_row(tmp_path) -> None:
    lic = tmp_path / "broken.lic"
    row = server_row()
    row = {**row, "DbId": ""}
    lic.write_bytes(license_codec._encrypt(license_codec._serialize(row)))
    with pytest.raises(license_codec.LicenseError):
        license_codec.fix_client_cache(_client_stub(tmp_path), lic)


def _client_stub(tmp_path: Path) -> Path:
    """Fake client install dir: only the marker exe and caches."""
    directory = tmp_path / "client"
    directory.mkdir()
    (directory / license_codec.CLIENT_CACHE_EXE).write_bytes(b"marker")
    (directory / "licensefgr.enc").write_bytes(b"original fgr skeleton")
    (directory / "config.ini").write_bytes(b"cfg")
    return directory


def test_fix_client_cache_backup_and_untouch(tmp_path) -> None:
    client_dir = _client_stub(tmp_path)
    old_cache = client_dir / license_codec.CLIENT_FACE_CACHE
    old_cache.write_bytes((FIXTURES / "original-empty.enc").read_bytes())
    previous_fgr = (client_dir / "licensefgr.enc").read_bytes()
    previous_cfg = (client_dir / "config.ini").read_bytes()

    lic = tmp_path / "server.lic"
    lic.write_bytes(license_codec._encrypt(license_codec._serialize(server_row())))

    result = license_codec.fix_client_cache(client_dir, lic, overwrite=True)
    assert result["backup_path"] is not None
    assert Path(result["backup_path"]).read_bytes() == (FIXTURES / "original-empty.enc").read_bytes()
    assert (client_dir / "licensefgr.enc").read_bytes() == previous_fgr
    assert (client_dir / "config.ini").read_bytes() == previous_cfg

    verification = license_codec.verify_client_fix(result)
    assert verification["ready"] is True

    written = license_codec.inspect_client_cache(client_dir / license_codec.CLIENT_FACE_CACHE)
    assert written["fields"] == {**server_row(), "Model": ""}


def test_fix_refuses_dir_without_client_exe(tmp_path) -> None:
    directory = tmp_path / "notclient"
    directory.mkdir()
    lic = tmp_path / "server.lic"
    lic.write_bytes(license_codec._encrypt(license_codec._serialize(server_row())))
    with pytest.raises(license_codec.LicenseError):
        license_codec.fix_client_cache(directory, lic)


def test_cli_tulis_cache_client(tmp_path, capsys) -> None:
    import cli

    client_dir = _client_stub(tmp_path)
    lic = tmp_path / "server.lic"
    lic.write_bytes(license_codec._encrypt(license_codec._serialize(server_row())))
    exit_code = cli.main([
        "tulis-cache-client",
        "--dari", str(lic),
        "--tujuan", str(client_dir),
        "--overwrite",
    ])
    assert exit_code == 0
    # Cache must now carry the row; run again without overwrite fails cleanly.
    exit_code = cli.main([
        "tulis-cache-client", "--dari", str(lic), "--tujuan", str(client_dir),
    ])
    assert exit_code != 0

