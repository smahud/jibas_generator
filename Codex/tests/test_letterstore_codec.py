import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

import letterstore_codec as ls
from license_codec import LicenseError


@pytest.mark.parametrize("database_id", ["ABCDE", "12XYZ", "9Z8Y7"])
def test_database_only_roundtrip(tmp_path, database_id):
    path = tmp_path / "school.lic"
    result = ls.generate_license(database_id=database_id.lower(), output_path=path,
                                 client_name="Sekolah & <Uji> 雪")
    assert result["verification"]["valid"]
    inspection = ls.inspect_license(path)
    assert inspection["database_id"] == database_id
    assert tuple(inspection["fields"]) == ls.COLUMNS
    assert inspection["fields"]["Klien"] == "Sekolah & <Uji> 雪"
    assert inspection["fields"]["Versi"] == "2.0"
    assert not ls.verify_license(path, "QWERT")["valid"]


def test_original_importer_evidence_and_fixture_identity():
    evidence = Path(__file__).parents[1] / "bukti" / "letterstore"
    results = json.loads((evidence / "original_import_results.json").read_text(encoding="utf-8-sig"))
    assert results["artifact_sha256"] == "1bdf678980b4ad985838a1b9ce2233550b3e00f49cd578b481dd01c5e5690915"
    assert len(results["attempts"]) == 7
    for attempt in results["attempts"]:
        fixture = evidence / "fixtures" / attempt["input_name"]
        assert hashlib.sha256(fixture.read_bytes()).hexdigest() == attempt["input_sha256"]
        assert ls.verify_license(fixture, attempt["database_id"])["valid"] == attempt["accepted"]
        if attempt["accepted"]:
            assert attempt["registered_flag"] and attempt["cache_loader_returned"]
            assert attempt["reloaded_registered_flag"]
            assert not attempt["wrong_runtime_id_registered_flag"]
            assert not attempt["duplicate_accepted"]
            assert attempt["duplicate_exception"] == "Exception: Kode lisensi sudah dimasukkan!"


def test_header_optional_and_empty_cache(tmp_path):
    file = tmp_path / "license.lic"
    ls.generate_license(database_id="ABCDE", output_path=file)
    file.write_bytes(file.read_bytes().split(b"\r\n", 1)[1])
    assert ls.verify_license(file, "ABCDE", for_import=True)["valid"]
    assert not ls.inspect_license(file)["import_header_present"]
    file.write_bytes(ls._encrypt(ls._serialize()))
    assert ls.inspect_license(file)["status"] == "empty_cache"
    assert not ls.verify_license(file, "ABCDE")["valid"]


def test_wrong_product_and_multiple_registration_rejected(tmp_path):
    path = tmp_path / "bad.lic"
    path.write_bytes(ls._encrypt(ls._serialize({column: "" for column in ls.COLUMNS}).replace("JLS", "JibasCbeLicense")))
    with pytest.raises(LicenseError, match="Skema bukan"):
        ls.inspect_license(path)
    root = ET.fromstring(ls._serialize({column: "" for column in ls.COLUMNS}))
    ET.SubElement(root, ls.TABLE)
    path.write_bytes(ls._encrypt(ET.tostring(root, encoding="ascii").decode("ascii")))
    with pytest.raises(LicenseError, match="satu registrasi"):
        ls.inspect_license(path)


@pytest.mark.parametrize("database_id", ["", "ABCD", "ABCDEF", "AB-C1", "AB雪12"])
def test_bad_database_id_rejected(tmp_path, database_id):
    with pytest.raises(LicenseError, match="5 karakter"):
        ls.generate_license(database_id=database_id, output_path=tmp_path / "bad.lic")


def test_corruption_and_existing_output(tmp_path):
    path = tmp_path / "school.lic"
    ls.generate_license(database_id="ABCDE", output_path=path)
    original = path.read_bytes()
    with pytest.raises(LicenseError, match="sudah ada"):
        ls.generate_license(database_id="QWERT", output_path=path)
    assert path.read_bytes() == original
    ls.generate_license(database_id="QWERT", output_path=path, overwrite=True)
    assert ls.verify_license(path, "QWERT")["valid"]
    path.write_bytes(b"invalid")
    with pytest.raises(LicenseError, match="dekripsi"):
        ls.inspect_license(path)
