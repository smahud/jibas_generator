"""Tests for the OpenCode license codec engine.

Run with: python -m pytest tests -q  (fixture-free, offline).
"""
import sys
from datetime import datetime
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOL))

import license_codec  # noqa: E402


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    path = tmp_path_factory.mktemp("lic") / "basic.enc"
    result = license_codec.generate_license(
        database_id="V4YNE", system_id="7738F", expires="2027-12-31",
        capacity=1000, output_path=str(path), client_name="UJI")
    return result, path


def test_roundtrip_inspect(generated):
    _, path = generated
    fields = license_codec.inspect_license(path)["fields"]
    assert fields["Versi"] == "16.5"
    assert fields["Klien"] == "UJI"
    assert fields["Model"] == "SPTFACE"
    assert fields["Seri"] == "7738F"
    assert fields["Size"] == "1000"
    assert fields["Sequence"] == "1"
    assert fields["DbId"] == "V4YNE"
    assert fields["MaxClient"] == "1000"
    assert fields["Info1"] == "7738F"
    assert fields["LicenseLimit"] == "2027-12-31"
    assert sorted(fields) == sorted(license_codec.COLUMNS)


def test_verify_accepts_matching_ids(generated):
    _, path = generated
    report = license_codec.verify_license(path, "V4YNE", "7738F")
    assert report["valid"] is True


def test_verify_rejects_different_dbid(generated):
    _, path = generated
    report = license_codec.verify_license(path, "WRK9T", "7738F")
    assert report["valid"] is False


def test_verify_rejects_wrong_info1(generated):
    _, path = generated
    report = license_codec.verify_license(path, "V4YNE", "DDCB4")
    assert report["valid"] is False


def test_generate_rejects_bad_ids(tmp_path):
    with pytest.raises(license_codec.LicenseError):
        license_codec.generate_license(
            database_id="V4YN", system_id="7738F", expires="2027-12-31",
            capacity=10, output_path=str(tmp_path / "x.enc"))
    with pytest.raises(license_codec.LicenseError):
        license_codec.generate_license(
            database_id="V4YNE", system_id="1234G", expires="2027-12-31",
            capacity=10, output_path=str(tmp_path / "x.enc"))


def test_generate_refuses_existing_without_overwrite(generated):
    _, path = generated
    with pytest.raises(license_codec.LicenseError):
        license_codec.generate_license(
            database_id="V4YNE", system_id="7738F", expires="2027-12-31",
            capacity=1000, output_path=str(path))
    again = license_codec.generate_license(
        database_id="V4YNE", system_id="7738F", expires="2027-12-31",
        capacity=1000, output_path=str(path), overwrite=True)
    assert again["verification"]["valid"] is True


def test_past_date_rejected(tmp_path):
    with pytest.raises(license_codec.LicenseError):
        license_codec.generate_license(
            database_id="V4YNE", system_id="7738F", expires="2020-01-01",
            capacity=10, output_path=str(tmp_path / "x.enc"))


def test_renewal_requires_rising_sequence_and_keeps_client(generated):
    _, path = generated
    with pytest.raises(license_codec.LicenseError):
        license_codec.generate_license(
            database_id="V4YNE", system_id="7738F", expires="2028-06-30",
            capacity=2000, output_path=str(path) + ".renewal",
            previous_license_path=str(path), sequence=1)
    previous_client = license_codec.inspect_license(path)["fields"]["KlienId"]
    renewal = license_codec.generate_license(
        database_id="V4YNE", system_id="7738F", expires="2028-06-30",
        capacity=2000, output_path=str(path) + ".renewal",
        previous_license_path=str(path))
    assert renewal["sequence"] == 2
    assert renewal["previous_sequence"] == 1
    assert renewal["client_id"] == previous_client
    assert renewal["mode"] == "renewal"
    assert license_codec.verify_license(
        str(path) + ".renewal", "V4YNE", "7738F", previous_client)["valid"] is True


def test_legacy_minute_matches_original_semantics():
    """Original arithmetic incl. its `year % 4` month rule (compat quirk)."""
    value = license_codec._legacy_minute(datetime(2026, 11, 10, 12, 0))
    leap = 2026 // 4
    month_days = [31, 28 if 2026 % 4 else 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    days = leap * 366 + (2026 - leap) * 365 + sum(month_days[:11]) + 10
    assert value == (days * 1440) + (12 * 60)
    # 2100 is NOT a Gregorian leap year, but the original treats it as one.
    # The running month's days are included, then the current day is added.
    days_2100 = (2100 // 4) * 366 + (2100 - 2100 // 4) * 365 + 31 + 29 + 31 + 1
    assert license_codec._legacy_minute(datetime(2100, 3, 1, 0, 0)) == days_2100 * 1440
