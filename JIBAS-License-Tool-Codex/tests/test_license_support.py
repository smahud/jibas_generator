import base64
import json

import pytest

from license_support.__main__ import main
from license_support.analysis import inspect_envelope
from license_support.issuance import prepare_request


@pytest.mark.parametrize("db,system", [("ABCDE", "DDCB4"), ("V4YNE", "123AB"), ("Z9X8W", "123AB")])
def test_distinct_requests_preserve_ids_without_claiming_issuance(db, system):
    result = prepare_request(db, system)
    assert (result["database_id"], result["system_id"]) == (db, system)
    assert result["kind"] == "new"
    assert not any(result[k] for k in ("submitted", "license_issued", "activation_proven"))


def test_renewal_preserves_opaque_vendor_client_id():
    result = prepare_request("V4YNE", "DDCB4", "issuer.client-123")
    assert result["client_id"] == "issuer.client-123"
    assert result["kind"] == "renewal"


@pytest.mark.parametrize("db,system,client", [("v4yne", "DDCB4", None), ("Ｖ4YNE", "DDCB4", None), ("V4YNE", "DDCB4\n", None), ("V4YNE", "DDCB4", "abc\n123"), ("V4YNE", "DDCB4", "")])
def test_invalid_input(db, system, client):
    with pytest.raises(ValueError):
        prepare_request(db, system, client)


def test_envelope_distinguishes_header_from_cache_without_rewriting(tmp_path):
    payload = base64.b64encode(b"synthetic-block!")
    path = tmp_path / "input.lic"
    for marker, expected in [(b"# LISENSI JIBAS SPT FACE\r\n", True), (b"# lisensi jibas spt face\n", False), (b"", False)]:
        original = marker + payload + b"\r\n"
        path.write_bytes(original)
        result = inspect_envelope(path)
        assert result["face_marker_on_first_line"] is expected
        assert result["payload_base64_block_length_plausible"]
        assert not result["activation_proven"]
        assert not result["issuer_authenticity_proven"]
        assert path.read_bytes() == original


def test_bad_payload_and_limit(tmp_path, monkeypatch):
    path = tmp_path / "input.lic"
    path.write_bytes(b"LISENSI JIBAS SPT FACE\ninvalid payload!")
    assert not inspect_envelope(path)["payload_base64_block_length_plausible"]
    monkeypatch.setattr("license_support.analysis.MAX_BYTES", 8)
    with pytest.raises(ValueError, match="4 MiB"):
        inspect_envelope(path)
    with pytest.raises(ValueError, match="berkas biasa"):
        inspect_envelope(tmp_path)


def test_cli_never_overwrites_or_labels_request_as_license(tmp_path, capsys):
    path = tmp_path / "request.json"
    argv = ["prepare-request", "--database-id", "V4YNE", "--system-id", "DDCB4", "--out", str(path)]
    assert main(argv) == 0
    original = path.read_bytes()
    assert not json.loads(original)["license_issued"]
    assert main(argv) == 2
    assert path.read_bytes() == original
    assert main(argv[:-1] + [str(tmp_path / "license.lic")]) == 2
    assert not (tmp_path / "license.lic").exists()
    assert "FileExistsError" in capsys.readouterr().err
