"""SchoolPay codec regressions; schema fixture comes from the original target."""
from pathlib import Path
import pytest

import schoolpay_codec as codec
import license_codec as face


def make(tmp_path, database_id="7VJM4", system_id="DDCB4", **kwargs):
    return codec.generate_license(database_id=database_id, system_id=system_id,
        expires="2030-12-31", capacity=10, output_path=tmp_path / "schoolpay.lic", **kwargs)


def test_original_empty_schoolpay_cache():
    cache = Path(__file__).parent / "fixtures/schoolpay-empty.enc"
    result = codec.inspect_license(cache)
    assert not result["has_license_row"]
    assert result["status"] == "empty_cache"
    assert result["product"] == "schoolpay"


@pytest.mark.parametrize("database_id,system_id", [("7VJM4", "DDCB4"), ("ABCDE", "123AB")])
def test_generate_schoolpay_columns_and_ids(tmp_path, database_id, system_id):
    result = make(tmp_path, database_id, system_id)
    assert result["verification"]["valid"]
    fields = codec.inspect_license(result["path"])["fields"]
    assert fields["SystemId"] == system_id
    assert fields["DbId"] == database_id
    assert fields["MaxVendor"] == "10"
    assert "MaxClient" not in fields
    assert fields["Versi"] == "10.5"
    assert not codec.verify_license(result["path"], "ZZZZZ", system_id)["valid"]
    assert not codec.verify_license(result["path"], database_id, "00000")["valid"]


def test_face_payload_is_not_schoolpay(tmp_path):
    p = tmp_path / "face.lic"
    face.generate_license(database_id="V4YNE", system_id="DDCB4", expires="2030-12-31",
                          capacity=10, output_path=p)
    with pytest.raises(codec.LicenseError, match="bukan lisensi JIBAS SchoolPay"):
        codec.inspect_license(p)


def test_schoolpay_renewal_keeps_client_and_increments_sequence(tmp_path):
    first = make(tmp_path)
    renewed = codec.generate_license(database_id="7VJM4", system_id="DDCB4", expires="2031-12-31",
        capacity=20, output_path=tmp_path / "renew.lic", previous_license_path=first["path"])
    assert renewed["sequence"] == 2
    assert renewed["client_id"] == first["client_id"]
    assert renewed["mode"] == "renewal"
    with pytest.raises(codec.LicenseError, match="Sequence"):
        codec.generate_license(database_id="7VJM4", system_id="DDCB4", expires="2031-12-31",
            capacity=20, output_path=tmp_path / "same.lic", previous_license_path=first["path"], sequence=1)


@pytest.mark.parametrize("field,value", [("capacity", 2147483648), ("sequence", 2147483648)])
def test_schoolpay_rejects_overflow(tmp_path, field, value):
    args = dict(database_id="7VJM4", system_id="DDCB4", expires="2030-12-31", capacity=10,
                output_path=tmp_path / "invalid.lic")
    args[field] = value
    with pytest.raises(codec.LicenseError):
        codec.generate_license(**args)


def test_client_id_alone_cannot_choose_renewal_sequence(tmp_path):
    with pytest.raises(codec.LicenseError, match="Sequence"):
        make(tmp_path, client_id="CLIENT")


def test_schoolpay_import_needs_feature_column_but_not_comment_header(tmp_path):
    result = make(tmp_path)
    path = Path(result["path"])
    fields = codec.inspect_license(path)["fields"]
    assert fields["ForSchoolPay"] == "1"
    headerless = tmp_path / "headerless.lic"
    headerless.write_bytes(path.read_bytes().split(b"\r\n", 1)[1])
    verified = codec.verify_license(headerless, "7VJM4", "DDCB4", for_import=True)
    assert verified["valid"]
    assert not verified["client_import_header_present"]
    assert verified["file_kind"] == "import_license"
    wrong_comment = tmp_path / "comment.lic"
    wrong_comment.write_bytes(b"# DIFFERENT PRODUCT\r\n" + headerless.read_bytes())
    assert codec.verify_license(wrong_comment, "7VJM4", "DDCB4", for_import=True)["valid"]
    cache = tmp_path / "license.enc"
    cache.write_bytes(face._encrypt(codec._serialize(fields, for_import=False)))
    assert codec.verify_license(cache, "7VJM4", "DDCB4")["valid"]
    assert not codec.verify_license(cache, "7VJM4", "DDCB4", for_import=True)["valid"]


@pytest.mark.parametrize("flag", ["0", "false", ""])
def test_schoolpay_feature_column_value_not_an_entitlement_gate(tmp_path, flag):
    result = make(tmp_path)
    fields = codec.inspect_license(result["path"])["fields"]
    fields["ForSchoolPay"] = flag
    p = tmp_path / "wrongflag.lic"
    p.write_bytes(face._encrypt(codec._serialize(fields)))
    assert codec.verify_license(p, "7VJM4", "DDCB4", for_import=True)["valid"]


def test_import_column_in_schema_is_sufficient_without_row_value(tmp_path):
    import xml.etree.ElementTree as ET
    result = make(tmp_path)
    fields = codec.inspect_license(result["path"])["fields"]
    root = ET.fromstring(codec._serialize(fields))
    row = root.find(codec.TABLE)
    row.remove(row.find("ForSchoolPay"))
    path = tmp_path / "schema-only-flag.lic"
    path.write_bytes(face._encrypt(ET.tostring(root, encoding="ascii").decode("ascii")))
    info = codec.inspect_license(path)
    assert "ForSchoolPay" not in info["fields"]
    assert info["for_schoolpay_column_present"]
    assert codec.verify_license(path, "7VJM4", "DDCB4", for_import=True)["valid"]


@pytest.mark.parametrize("stamp,expected", [
    ("9999-12-31T23:59:00", 964677343),
    ("4084-01-01T00:00:00", -2146900576),
    ("4085-01-01T00:00:00", -2146374976),
])
def test_schoolpay_minute_int32_wrap_matches_original_oracle(stamp, expected):
    from datetime import datetime
    assert codec._legacy_minute(datetime.fromisoformat(stamp)) == expected


def test_very_future_expiry_with_wrapped_original_time_rejected(tmp_path):
    with pytest.raises(codec.LicenseError, match="kedaluwarsa"):
        codec.generate_license(database_id="7VJM4", system_id="DDCB4", expires="9999-12-31",
                               capacity=10, output_path=tmp_path / "year9999.lic")
