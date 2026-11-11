import xml.etree.ElementTree as ET

import pytest

import fingerprint_codec as codec
import license_codec as face


@pytest.mark.parametrize("scope,expected", [("both", "CM"), ("manager", "M"), ("client", "C"), ("CM", "CM")])
def test_generation_binds_exact_scanner_serial(tmp_path, scope, expected):
    target = tmp_path / "fingerprint.lic"
    result = codec.generate_license(serial="{01234567-89AB-CDEF}", license_scope=scope,
                                    client_name="Sekolah & École", output_path=target)
    inspection = codec.inspect_license(target)
    assert target.read_bytes().startswith(codec.IMPORT_HEADER)
    assert inspection["fields"]["LicType"] == expected
    assert inspection["fields"]["Klien"] == "Sekolah & École"
    assert set(inspection["fields"]) == set(codec.COLUMNS)
    assert result["verification"]["valid"]
    assert not codec.verify_license(target, "{01234567-89ab-cdef}")["valid"]
    assert not codec.verify_license(target, "ANOTHER")["valid"]


def test_scope_is_checked_when_requested(tmp_path):
    target = tmp_path / "client.lic"
    codec.generate_license(serial="SCANNER-1", license_scope="client", output_path=target)
    assert codec.verify_license(target, "SCANNER-1", license_scope="client")["valid"]
    assert not codec.verify_license(target, "SCANNER-1", license_scope="manager")["valid"]
    assert not codec.verify_license(target, "SCANNER-1", license_scope="both")["valid"]


def test_header_is_required_for_common_import_but_not_cache(tmp_path):
    target = tmp_path / "fingerprint.lic"
    codec.generate_license(serial="SCANNER-2", output_path=target)
    target.write_bytes(target.read_bytes()[len(codec.IMPORT_HEADER):])
    assert codec.verify_license(target, "SCANNER-2")["valid"]
    assert not codec.verify_license(target, "SCANNER-2", for_import=True)["valid"]
    assert codec.inspect_license(target)["header_requirements"] == {
        "manager_16_5": False, "client_14_0": False, "client_16_10": True}


def test_empty_cache_and_multiple_scanners_are_inspectable(tmp_path):
    root = ET.fromstring((codec.BASE / "fingerprint_schema.xml").read_text())
    target = tmp_path / "cache.enc"
    target.write_bytes(face._encrypt(ET.tostring(root, encoding="ascii").decode(), "client_fgr"))
    assert codec.inspect_license(target)["status"] == "empty_cache"
    assert not codec.verify_license(target, "SCANNER-3")["valid"]
    for serial in ["SCANNER-3", "SCANNER-4"]:
        row = ET.SubElement(root, codec.TABLE)
        for name in codec.COLUMNS:
            ET.SubElement(row, name).text = {"Seri": serial, "LicType": "CM"}.get(name, "")
    target.write_bytes(face._encrypt(ET.tostring(root, encoding="ascii").decode(), "client_fgr"))
    assert codec.inspect_license(target)["row_count"] == 2
    assert codec.verify_license(target, "SCANNER-4")["valid"]


def test_wrong_product_and_broken_payload_are_rejected(tmp_path):
    target = tmp_path / "bad.lic"
    target.write_bytes(face._encrypt("<NewDataSet><JibasSptFaceLicense /></NewDataSet>", "client_fgr"))
    with pytest.raises(codec.LicenseError, match="Skema"):
        codec.inspect_license(target)
    target.write_bytes(b"invalid base64!")
    with pytest.raises(codec.LicenseError, match="dekripsi"):
        codec.inspect_license(target)


@pytest.mark.parametrize("serial", ["", "   ", "a\nb", "é", "x" * 256])
def test_invalid_serial_never_writes_output(tmp_path, serial):
    target = tmp_path / "invalid.lic"
    with pytest.raises(codec.LicenseError, match="seri"):
        codec.generate_license(serial=serial, output_path=target)
    assert not target.exists()


def test_bad_scope_and_existing_file_are_not_overwritten(tmp_path):
    target = tmp_path / "existing.lic"
    with pytest.raises(codec.LicenseError, match="Cakupan"):
        codec.generate_license(serial="S", license_scope="expired", output_path=target)
    target.write_bytes(b"existing contents")
    with pytest.raises(codec.LicenseError, match="sudah ada"):
        codec.generate_license(serial="S", output_path=target)
    assert target.read_bytes() == b"existing contents"
    assert codec.generate_license(serial="S", output_path=target, overwrite=True)["verification"]["valid"]


def test_format_has_no_unproven_face_identifiers_or_limits(tmp_path):
    target = tmp_path / "fingerprint.lic"
    result = codec.generate_license(serial="SCANNER-5", output_path=target)
    assert not {"DbId", "KlienId", "Sequence", "MaxClient", "LicenseLimitDate"}.intersection(result["fields"])
    assert result["fields"]["KodeHw"] == result["fields"]["KodeRs"] == result["fields"]["KodeTx"] == ""
