"""Read existing fixtures only; never create or change a license/cache."""
import hashlib
import json
import os
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import diagnostics
import license_codec

FIXTURES = ROOT / "tests" / "fixtures"


@pytest.mark.parametrize("filename,has_row", [("original-empty.enc", False), ("original-imported.enc", True)])
def test_inspection_preserves_source_and_reports_local_scope(filename, has_row):
    source = FIXTURES / filename
    before, stamp = source.read_bytes(), source.stat().st_mtime_ns
    result = diagnostics.inspect_file(source)
    assert result["has_license_row"] is has_row
    assert result["valid"] is None
    assert result["activation_proven"] is False
    assert result["sha256"] == hashlib.sha256(before).hexdigest()
    assert source.read_bytes() == before
    assert source.stat().st_mtime_ns == stamp


def test_verification_preserves_existing_codec_checks_and_redacts_values():
    source = FIXTURES / "original-imported.enc"
    raw = source.read_bytes()
    fields = license_codec.inspect_license(source)["fields"]
    expected = license_codec.verify_license(source, fields["DbId"], fields["Info1"])
    result = diagnostics.verify_file(source, fields["DbId"], fields["Info1"])
    assert result["valid"] == expected["valid"]
    assert [(c["name"], c["passed"]) for c in result["checks"]] == [
        (c["name"], c["passed"]) for c in expected["checks"]]
    assert result["activation_proven"] is False
    serialized = json.dumps(result)
    for name in ("DbId", "Info1", "KlienId"):
        assert fields[name] not in serialized
    assert str(source) not in serialized
    assert source.read_bytes() == raw


def test_empty_cache_is_readable_but_never_reported_as_active():
    result = diagnostics.verify_file(FIXTURES / "original-empty.enc", "ABCDE", "123AB")
    assert result["valid"] is False
    assert result["status"] == "checks_failed"
    assert result["checks"][0]["passed"] is False


@pytest.mark.parametrize("data,code", [(b"", "empty_file"), (b"not a license", "unreadable_format"),
                                      (b"YWJjZA==", "unreadable_format")])
def test_corrupt_input_has_safe_actionable_error(tmp_path, data, code):
    source = tmp_path / "private-name.enc"
    source.write_bytes(data)
    with pytest.raises(diagnostics.DiagnosticError) as error:
        diagnostics.inspect_file(source)
    assert error.value.code == code
    assert str(source) not in str(error.value)
    assert data == source.read_bytes()


@pytest.mark.parametrize("kind,code", [("missing", "not_found"), ("directory", "not_regular"),
                                      ("oversize", "too_large"), ("empty_path", "missing_path")])
def test_preflight_rejects_invalid_sources(tmp_path, kind, code):
    source = tmp_path / "input"
    if kind == "directory":
        source.mkdir()
    elif kind == "oversize":
        with source.open("wb") as stream:
            stream.truncate(diagnostics.MAX_FILE_BYTES + 1)
    with pytest.raises(diagnostics.DiagnosticError) as error:
        diagnostics.inspect_file("" if kind == "empty_path" else source)
    assert error.value.code == code


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO unavailable on this OS")
def test_fifo_is_rejected_without_blocking(tmp_path):
    source = tmp_path / "pipe"
    os.mkfifo(source)
    with pytest.raises(diagnostics.DiagnosticError) as error:
        diagnostics.inspect_file(source)
    assert error.value.code == "not_regular"


@pytest.mark.parametrize("db,system,client,code", [("", "123AB", "", "database_id"),
    ("ABCDE", "1234G", "", "system_id"), ("ABCDE", "123AB", "x\x00y", "client_id")])
def test_ids_are_validated_before_any_file_read(monkeypatch, db, system, client, code):
    monkeypatch.setattr(diagnostics, "_read_source", lambda _path: pytest.fail("Unexpected read"))
    with pytest.raises(diagnostics.DiagnosticError) as error:
        diagnostics.verify_file("unused", db, system, client)
    assert error.value.code == code


def test_read_only_snapshot_is_identical_and_removed_even_on_failure(monkeypatch):
    source = FIXTURES / "original-imported.enc"
    snapshots = []

    def broken_inspect(path):
        snapshots.append(path)
        assert path != source
        assert path.read_bytes() == source.read_bytes()
        raise RuntimeError("password=SYNTHETIC_SECRET_123")

    monkeypatch.setattr(license_codec, "inspect_license", broken_inspect)
    with pytest.raises(diagnostics.DiagnosticError) as error:
        diagnostics.inspect_file(source)
    assert error.value.code == "unexpected"
    assert "SYNTHETIC_SECRET" not in str(error.value)
    assert snapshots and not snapshots[0].exists()
    assert not snapshots[0].parent.exists()


def test_report_does_not_trust_known_columns_or_unknown_names(monkeypatch):
    secret = "SYNTHETIC_SECRET_123"
    fields = {name: secret for name in license_codec.COLUMNS}
    fields[secret] = secret
    monkeypatch.setattr(license_codec, "inspect_license", lambda _path: {
        "fields": fields, "format": "test", "sha256": "0" * 64,
        "status": "license_row", "has_license_row": True})
    result = diagnostics.inspect_file(FIXTURES / "original-imported.enc")
    assert secret not in json.dumps(result)
    assert result["unknown_field_count"] == 1


def test_permission_errors_do_not_disclose_paths_or_exception_text(monkeypatch):
    def denied(*_args):
        raise PermissionError("SYNTHETIC_PRIVATE_PATH")
    monkeypatch.setattr(diagnostics.os, "open", denied)
    with pytest.raises(diagnostics.DiagnosticError) as error:
        diagnostics.inspect_file("private.enc")
    assert error.value.code == "permission"
    assert "SYNTHETIC" not in str(error.value)
