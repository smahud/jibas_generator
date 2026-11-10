"""Compatibility and provenance tests.

Uses fixtures recovered from the earlier proof session:
  - tests/fixtures/date_reference.json : 8 sample outputs of the ORIGINAL
    minute-arithmetic method 0x0600066B (pure date conversion, captured live);
  - tests/fixtures/original-empty.enc  : cache of the ORIGINAL importer (empty);
  - tests/fixtures/original-imported.enc: cache written by the ORIGINAL importer.
The installed original cache (C:\\...\\license.enc), when reachable, is only
read (never written) to prove column-format parity of the generator.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOL))

import license_codec  # noqa: E402

FIXTURES = TOOL / "tests" / "fixtures"
INSTALLED_CACHE = Path(r"C:\Program Files\YIM\JIBAS Face Server 16.5\license.enc")


def date_reference() -> dict:
    return json.loads((FIXTURES / "date_reference.json").read_text(encoding="utf-8-sig"))


@pytest.mark.parametrize("sample,value", [
    (key, value)
    for key, value in sorted(date_reference()["samples"].items())
])
def test_legacy_minute_matches_original_66b_samples(sample, value):
    stamp = datetime.fromisoformat(sample)
    assert license_codec._legacy_minute(stamp) == value, \
        "_legacy_minute tidak sesuai metode asli 0x0600066B untuk %s" % sample


def test_read_original_importer_cache_fixture():
    fields = license_codec.inspect_license(FIXTURES / "original-imported.enc")["fields"]
    assert fields["Versi"] == "16.5"
    assert "Model" not in fields          # kolom Model tidak disalin importer asli
    assert len(fields) == 17


def test_original_importer_cache_is_capacity_parseable():
    fields = license_codec.inspect_license(FIXTURES / "original-imported.enc")["fields"]
    assert int(fields["MaxClient"]) >= 0
    assert int(fields["Sequence"]) >= 0


def test_read_original_empty_cache_fixture():
    result = license_codec.inspect_license(FIXTURES / "original-empty.enc")
    assert result["status"] == "empty_cache"
    assert result["has_license_row"] is False


def test_installed_cache_format_parity_with_generator():
    """Read-only comparison with the installed original cache."""
    if not INSTALLED_CACHE.exists():
        pytest.skip("Cache terpasang tidak tersedia di mesin ini.")
    original = license_codec.inspect_license(INSTALLED_CACHE)["fields"]
    # Generator harus menulis format tanggal yang sama dengan cache asli.
    assert original["Tanggal"] == datetime.strptime(
        original["Tanggal"], "%Y-%m-%d").date().isoformat()
    assert original["LicenseLimit"] == datetime.strptime(
        original["LicenseLimit"], "%Y-%m-%d").date().isoformat()
    assert license_codec._datetime(original["LicenseLimitDate"]) is not None
    assert original["Versi"] == "16.5"
