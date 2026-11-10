"""CLI regression checks restricted to existing files and read-only commands."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import cli
import license_codec

SOURCE = ROOT / "tests" / "fixtures" / "original-imported.enc"


def test_python_module_entrypoint_runs_inspection():
    result = subprocess.run([sys.executable, "-m", "cli", "inspect", str(SOURCE)], cwd=ROOT,
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["results"][0]["status"] == "license_row"
    assert report["results"][0]["activation_proven"] is False


@pytest.mark.parametrize("db,system", [("ABCDE", "123AB"), ("", "")])
def test_verification_failure_has_json_and_exit_status(capsys, db, system):
    args = ["verify", str(SOURCE), "--database-id", db, "--system-id", system]
    code = cli.main(args)
    captured = capsys.readouterr()
    report = json.loads(captured.out or captured.err)
    assert code == (1 if db else 2)
    assert report["ok"] is False
    assert str(SOURCE) not in (captured.out + captured.err)


def test_matching_fixture_verification_returns_original_validity(capsys):
    fields = license_codec.inspect_license(SOURCE)["fields"]
    expected = license_codec.verify_license(SOURCE, fields["DbId"], fields["Info1"])
    code = cli.main(["verify", str(SOURCE), "--database-id", fields["DbId"], "--system-id", fields["Info1"]])
    report = json.loads(capsys.readouterr().out)
    assert report["ok"] == expected["valid"]
    assert code == (0 if expected["valid"] else 1)
    assert fields["KlienId"] not in json.dumps(report)


def test_missing_file_has_redacted_error(capsys):
    assert cli.main(["inspect", "/private/SYNTHETIC_SECRET.enc"]) == 2
    captured = capsys.readouterr()
    report = json.loads(captured.err)
    assert report["error_code"] == "not_found"
    assert "SYNTHETIC" not in captured.err
