import base64
from datetime import datetime
import json
from pathlib import Path

import pytest

import sjs_codec as codec

TOKEN = "97875YgYKBhQIBwgZCQsbCxkPFQ4UAAgJGw4FCBUFCBkLCRsVBBQJGwoZDBUDDQNl"


def generate(tmp_path, **changes):
    args = dict(database_id="AB123", registration_token=TOKEN,
                school_id="SCHOOL-EXISTING-001", client_name="Sekolah Uji",
                expires="2030-12-31", capacity=2, output_path=tmp_path / "sjs.lic")
    args.update(changes)
    return codec.generate_license(**args)


def test_token_matches_original_encoder_fixture():
    original = json.loads((Path(codec.BASE) / "bukti/sjs/token_oracle.json").read_text(encoding="utf-8-sig"))
    result = codec.inspect_registration_token(original["token"])
    assert original["plain"] == original["decoded_original"]
    assert result["statistics"] == dict(zip(codec.TOKEN_STATISTICS, json.loads(original["plain"])[1:-1]))
    assert result["role"] == "local_registration_statistics"
    assert not result["database_id_present"]
    assert not result["database_binding_proven"]


@pytest.mark.parametrize("token", ["", "ABCDE", "97875not-base64!", "10000AAAA", "97875YWJjZA==", TOKEN + "A"])
def test_rejects_invalid_tokens(token):
    with pytest.raises(codec.LicenseError):
        codec.inspect_registration_token(token)


def test_new_roundtrip_is_product_specific(tmp_path):
    result = generate(tmp_path)
    fields = codec.inspect_license(result["path"])["fields"]
    assert list(fields) == list(codec.COLUMNS)
    assert fields["DatabaseId"] == "AB123"
    assert fields["SchoolId"] == "SCHOOL-EXISTING-001"
    assert fields["MaxAgentConn"] == "2"
    assert "SystemId" not in fields and "Info1" not in fields
    assert result["verification"]["valid"]
    assert not result["activation_proven"]
    assert result["sequence"] == 1


def test_new_school_id_cannot_be_invented(tmp_path):
    with pytest.raises(codec.LicenseError, match="School ID"):
        generate(tmp_path, school_id=None)
    assert not (tmp_path / "sjs.lic").exists()


def test_token_is_not_falsely_bound_to_database(tmp_path):
    first = generate(tmp_path)
    second = generate(tmp_path, database_id="ZX987", output_path=tmp_path / "other.lic")
    assert first["registration_token"]["sha256"] == second["registration_token"]["sha256"]
    assert not codec.verify_license(first["path"], "ZX987", registration_token=TOKEN)["valid"]


def test_renewal_retains_school_and_metadata(tmp_path):
    first = generate(tmp_path, group_id="GROUP-001", group_name="Yayasan",
                     school_short_name="Uji", jenis="Community", services=[["S1", "value"]])
    renewed = generate(tmp_path, school_id=None, client_name="", previous_license_path=first["path"],
                       output_path=tmp_path / "renewal.lic")
    fields = codec.inspect_license(renewed["path"])["fields"]
    assert renewed["sequence"] == 2
    assert renewed["school_id"] == first["school_id"]
    assert fields["SchoolName"] == "Uji" and fields["GroupId"] == "GROUP-001"
    assert fields["Jenis"] == "Community" and json.loads(fields["Services"]) == [["S1", "value"]]


@pytest.mark.parametrize("changes", [{"database_id": "ZZ999"}, {"school_id": "OTHER"}, {"sequence": 1}])
def test_renewal_rejects_changed_identity_or_nonrising_sequence(tmp_path, changes):
    first = generate(tmp_path)
    with pytest.raises(codec.LicenseError):
        generate(tmp_path, previous_license_path=first["path"], output_path=tmp_path / "renewal.lic", **changes)


def test_headerless_payload_accepted(tmp_path):
    result = generate(tmp_path)
    p = Path(result["path"])
    p.write_bytes(b"\r\n".join(p.read_bytes().splitlines()[1:]) + b"\r\n")
    check = codec.verify_license(p, "AB123", registration_token=TOKEN)
    assert check["valid"] and check["importer_accepts_headerless"]


def test_verifier_rejects_expired_even_when_first_import_accepts(tmp_path):
    result = generate(tmp_path)
    check = codec.verify_license(result["path"], "AB123", now=datetime(2031, 1, 1, tzinfo=codec.JAKARTA))
    assert not check["valid"]
    assert any(c["name"] == "expiry" and not c["passed"] for c in check["checks"])


@pytest.mark.parametrize("capacity", [0, -1, True, 2147483648])
def test_capacity_limits(tmp_path, capacity):
    with pytest.raises(codec.LicenseError):
        generate(tmp_path, capacity=capacity)


def test_foreign_table_rejected(tmp_path):
    result = generate(tmp_path)
    p = Path(result["path"])
    xml = codec._serialize(codec.inspect_license(p)["fields"]).replace(b"JibasJsLicense", b"JibasCbeLicense")
    p.write_bytes(base64.b64encode(codec._crypto(xml)))
    with pytest.raises(codec.LicenseError, match="JibasJsLicense"):
        codec.inspect_license(p)


def test_refuses_overwrite_and_opaque_bad_token(tmp_path):
    generate(tmp_path)
    with pytest.raises(codec.LicenseError):
        generate(tmp_path)
    with pytest.raises(codec.LicenseError, match="Registration Token"):
        generate(tmp_path, registration_token="FAKE", output_path=tmp_path / "bad.lic")


def test_services_must_be_list_of_string_lists(tmp_path):
    with pytest.raises(codec.LicenseError, match="Services"):
        generate(tmp_path, services={"invented": True})
