"""Tests for id_detect (offline parts) + dbid_recipe replay."""
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOL))

import dbid_recipe  # noqa: E402
import id_detect  # noqa: E402

# Known vectors proven on this host against the original methods.
KNOWN_DISK_SERIAL = "30029941042         "
KNOWN_UUID = "E0813C3C-120B-02FE-5F00-BCAEC5319E78"
KNOWN_SYSTEM_ID = "DDCB4"


def test_dbid_recipe_replay_with_live_pieces():
    """Characters captured live (bukti/splang_decoded.txt, V4YNE state)."""
    payloads = {
        (4, 7): "0" * 14 + "V" + "0" * 10,   # splang04 @uhh[14]
        (2, 5): "1" * 5 + "4",               # splang02 @uhf[5]
        (9, 2): "2" * 25 + "Y",              # splang09 @uhc[25]
        (11, 4): "3" * 37 + "N",             # splang11 @uhe[37]
        (1, 1): "4" * 47 + "E",              # splang01 @uhb[47]
    }
    assert dbid_recipe.replay(payloads) == "V4YNE"


def test_dbid_recipe_wrk9t_state():
    payloads = {
        (4, 7): "0" * 14 + "W" + "0" * 10,
        (2, 5): "1" * 5 + "R",
        (9, 2): "2" * 25 + "K",
        (11, 4): "3" * 37 + "9",
        (1, 1): "4" * 47 + "T",
    }
    assert dbid_recipe.replay(payloads) == "WRK9T"


def test_dbid_recipe_rejects_short_payload():
    with pytest.raises(ValueError):
        dbid_recipe.replay({(4, 7): "W", (2, 5): "R", (9, 2): "K",
                            (11, 4): "9", (1, 1): "T"})


def test_variable_names():
    assert dbid_recipe.variable_name(1) == "@uhb"
    assert dbid_recipe.variable_name(7) == "@uhh"


def test_system_id_known_vector():
    assert id_detect.SystemIdDetector.compute(KNOWN_DISK_SERIAL, KNOWN_UUID) \
        == KNOWN_SYSTEM_ID


def test_system_id_lowercase_digest_used():
    digest = id_detect.SystemIdDetector._md5_hex(
        KNOWN_DISK_SERIAL + KNOWN_UUID)
    assert id_detect.SystemIdDetector.compute(
        KNOWN_DISK_SERIAL, KNOWN_UUID) == "".join(
        digest[i] for i in (5, 17, 30, 24, 3)).upper()


def test_system_id_preserves_wmi_trailing_spaces():
    """Original 599 returns the padding; trimming produced the wrong ID."""
    assert id_detect.SystemIdDetector.compute(
        KNOWN_DISK_SERIAL.rstrip(), KNOWN_UUID) == "7738F"
    assert id_detect.SystemIdDetector.compute(
        KNOWN_DISK_SERIAL, KNOWN_UUID) == "DDCB4"


def test_system_id_dotnet_ascii_fallback():
    import hashlib
    assert id_detect.SystemIdDetector._md5_hex("A\u00e9\U0001f600B") == \
        hashlib.md5(b"A???B").hexdigest()


def test_wmi_output_parsing_preserves_padding(monkeypatch):
    import subprocess
    output = "DISK " + KNOWN_DISK_SERIAL + "\r\nUUID " + KNOWN_UUID + "\r\n"
    monkeypatch.setattr(id_detect.subprocess, "run", lambda *a, **kw:
                        subprocess.CompletedProcess(a, 0, stdout=output, stderr=""))
    result, details = id_detect.SystemIdDetector().detect()
    assert result == "DDCB4"
    assert details["disk_serial_raw"] == KNOWN_DISK_SERIAL


def test_hex_to_ascii():
    assert id_detect._hex_to_ascii("5634" "594E" "45") == "V4YNE"
    with pytest.raises(id_detect.DetectError):
        id_detect._hex_to_ascii("zz")
    with pytest.raises(id_detect.DetectError):
        id_detect._hex_to_ascii("616")      # panjang ganjil


def test_dbid_detector_reports_missing_connection():
    detector = id_detect.DbIdDetector(host="127.0.0.1", port=1)
    with pytest.raises(id_detect.DetectError):
        detector.detect()
