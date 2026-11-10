#!/usr/bin/env python3
"""
Tests for JIBAS License Tool (OpenCode implementation)
"""
import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import jibas_license_tool as core


class TestJibasLicenseTool:
    """Test core license tool functionality."""

    @pytest.fixture
    def sample_license(self):
        return Path(__file__).parent / "fixtures" / "original-imported.enc"

    def test_inspect_license(self, sample_license):
        result = core.inspect_license(sample_license)
        assert result["has_license_row"] is True
        assert "fields" in result
        assert result["fields"]["DbId"] == "V4YNE"

    def test_verify_license_match(self, sample_license):
        # Fixture has System ID = DDCB4 (Info1)
        result = core.verify_license(sample_license, "V4YNE", "DDCB4")
        assert result["valid"] is True
        assert all(c["passed"] for c in result["checks"])

    def test_verify_license_dbid_mismatch(self, sample_license):
        result = core.verify_license(sample_license, "WRONG", "DDCB4")
        assert result["valid"] is False
        dbid_check = next(c for c in result["checks"] if c["name"] == "database_id")
        assert dbid_check["passed"] is False

    def test_verify_license_sysid_mismatch(self, sample_license):
        result = core.verify_license(sample_license, "V4YNE", "7738F")
        assert result["valid"] is False
        sysid_check = next(c for c in result["checks"] if c["name"] == "system_id")
        assert sysid_check["passed"] is False

    def test_generate_license(self, tmp_path):
        output = tmp_path / "test.lic"
        result = core.generate_license(
            database_id="V4YNE",
            system_id="7738F",
            expires="2027-12-31",
            capacity=100,
            output_path=output,
            client_name="Test School"
        )
        assert result["verification"]["valid"] is True
        assert result["client_id"] is not None
        assert result["sequence"] == 1
        assert output.exists()

    def test_renew_license(self, tmp_path):
        # First generate a license
        prev = tmp_path / "prev.lic"
        core.generate_license(
            database_id="V4YNE",
            system_id="7738F",
            expires="2027-12-31",
            capacity=100,
            output_path=prev,
            client_name="Test School"
        )
        # Then renew it
        new = tmp_path / "new.lic"
        result = core.renew_license(
            database_id="V4YNE",
            system_id="7738F",
            expires="2028-12-31",
            capacity=200,
            output_path=new,
            previous_license_path=prev
        )
        assert result["verification"]["valid"] is True
        assert result["sequence"] == 2
        assert result["mode"] == "renewal"
        assert new.exists()

    def test_legacy_minute_calculation(self):
        # Test cases from original 0x06000667..66B
        from datetime import datetime, timezone, timedelta
        JAKARTA = timezone(timedelta(hours=7))
        
        # 2026-01-31T23:59 -> 1065684959
        dt = datetime(2026, 1, 31, 23, 59, tzinfo=JAKARTA)
        assert core._legacy_minute(dt) == 1065684959
        
        # 2026-02-01T00:00 -> 1065680640 (note: leap year rule)
        dt = datetime(2026, 2, 1, 0, 0, tzinfo=JAKARTA)
        assert core._legacy_minute(dt) == 1065680640

    def test_id_validation(self):
        # Valid Database ID
        assert core._validate_id("V4YNE", "Database ID") == "V4YNE"
        assert core._validate_id("ABCDE", "Database ID") == "ABCDE"
        
        # Invalid Database ID
        with pytest.raises(core.LicenseError):
            core._validate_id("V4YN", "Database ID")  # too short
        with pytest.raises(core.LicenseError):
            core._validate_id("V4YNE!", "Database ID")  # special char
        
        # Valid System ID
        assert core._validate_id("7738F", "System ID", system=True) == "7738F"
        assert core._validate_id("DDCB4", "System ID", system=True) == "DDCB4"
        
        # Invalid System ID
        with pytest.raises(core.LicenseError):
            core._validate_id("7738G", "System ID", system=True)  # not hex
        with pytest.raises(core.LicenseError):
            core._validate_id("7738", "System ID", system=True)  # too short

    def test_client_cache_operations(self, tmp_path, sample_license):
        # Test resolve_client_row
        fields = core.resolve_client_row(sample_license)
        assert "KlienId" in fields
        assert fields["KlienId"] != "TRIAL"
        
        # Test write_client_cache
        output = tmp_path / "licenseface.enc"
        result = core.write_client_cache(fields, output)
        assert result["profile"] == "client_face"
        assert output.exists()
        
        # Test inspect_client_cache
        cache = core.inspect_client_cache(output)
        assert cache["has_license_row"] is True
        assert cache["fields"]["KlienId"] == fields["KlienId"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])