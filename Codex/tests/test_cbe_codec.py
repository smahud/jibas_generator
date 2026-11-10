"""CBE codec regressions, using original cache/date oracle plus temporary files."""
from datetime import datetime
import json
from pathlib import Path

import pytest

import cbe_codec as codec
import license_codec as face
import schoolpay_codec as schoolpay

ROOT = Path(__file__).resolve().parents[1]


def make(tmp_path, **extra):
    args = dict(database_id="ABCDE", system_id="DDCB4", expires="2030-12-31",
                capacity=100, output_path=tmp_path / "cbe.lic")
    args.update(extra)
    return codec.generate_license(**args)


def test_original_cbe_empty_cache():
    result = codec.inspect_license(ROOT / "tests/fixtures/cbe-empty.enc")
    assert result["status"] == "empty_cache"
    assert not result["has_license_row"]


@pytest.mark.parametrize("db,system", [("ABCDE", "DDCB4"), ("Z9X8W", "123AB"), ("12345", "ABCDE")])
def test_roundtrip_different_ids_and_binding(tmp_path, db, system):
    result = make(tmp_path, database_id=db, system_id=system)
    fields = codec.inspect_license(result["path"])["fields"]
    assert fields["DbId"] == db
    assert fields["Info1"] == system
    assert fields["Versi"] == "26.5"
    assert codec.verify_license(result["path"], db, system)["valid"]
    assert not codec.verify_license(result["path"], "00000", system)["valid"]
    assert not codec.verify_license(result["path"], db, "00000")["valid"]


def test_renewal_automatically_preserves_client_and_increases_sequence(tmp_path):
    first = make(tmp_path)
    second = make(tmp_path, output_path=tmp_path / "renewal.lic", previous_license_path=first["path"])
    assert second["sequence"] == 2
    assert second["client_id"] == first["client_id"]
    assert second["mode"] == "renewal"
    with pytest.raises(codec.LicenseError, match="Sequence"):
        make(tmp_path, output_path=tmp_path / "same.lic", previous_license_path=first["path"], sequence=1)


def test_cross_product_inspection_rejected(tmp_path):
    cbe = make(tmp_path)
    with pytest.raises(face.LicenseError):
        face.inspect_license(cbe["path"])
    with pytest.raises(face.LicenseError):
        schoolpay.inspect_license(cbe["path"])
    output = tmp_path / "face.lic"
    face.generate_license(database_id="ABCDE", system_id="DDCB4", expires="2030-12-31",
                          capacity=100, output_path=output)
    with pytest.raises(codec.LicenseError):
        codec.inspect_license(output)


@pytest.mark.parametrize("capacity", [0, -1, True, 2147483648, "100"])
def test_invalid_capacity_rejected(tmp_path, capacity):
    with pytest.raises(codec.LicenseError):
        make(tmp_path, capacity=capacity)


def test_very_future_expiry_matches_original_overflow_boundary(tmp_path):
    assert codec._legacy_minute(datetime(9999, 12, 31, 23, 59)) == 964677343
    assert codec._legacy_minute(datetime(4084, 1, 1)) == -2146900576
    with pytest.raises(codec.LicenseError, match="overflow"):
        make(tmp_path, expires="9999-12-31")


def test_existing_output_is_not_overwritten(tmp_path):
    make(tmp_path)
    with pytest.raises(codec.LicenseError, match="sudah ada"):
        make(tmp_path)


def test_cbe_importer_does_not_require_comment_header(tmp_path):
    result = make(tmp_path)
    payload = Path(result["path"]).read_bytes().split(b"\r\n", 1)[1]
    for prefix in (b"", b"# ANOTHER COMMENT\r\n", b"# lisensi jibas cbe\r\n"):
        path = tmp_path / "header-variant.lic"
        path.write_bytes(prefix + payload)
        verified = codec.verify_license(path, "ABCDE", "DDCB4", for_import=True)
        assert verified["valid"]
        assert verified["importer_accepts_headerless"]
