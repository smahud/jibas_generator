"""Regressions for failures reproduced with the original Windows binaries."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

import license_codec as codec


@pytest.mark.parametrize('database_id,system_id', [
    ('V4YNE', 'DDCB4'), ('ABCDE', 'DDCB4'), ('Z9X8W', '123AB')])
def test_import_header_and_ids(tmp_path, database_id, system_id):
    out = tmp_path / 'new.lic'
    result = codec.generate_license(database_id=database_id, system_id=system_id,
                                    expires='2030-12-31', capacity=100, output_path=out)
    assert out.read_bytes().startswith(b'# LISENSI JIBAS SPT FACE\r\n')
    assert result['verification']['valid']
    assert codec.verify_license(out, database_id, system_id, for_import=True)['valid']
    assert not codec.verify_license(out, '00000', system_id, for_import=True)['valid']
    # A readable cache is not a file the original client accepts via its import UI.
    cache = tmp_path / 'licenseface.enc'
    cache.write_bytes(out.read_bytes().split(b'\r\n', 1)[1])
    assert codec.verify_license(cache, database_id, system_id)['valid']
    assert not codec.verify_license(cache, database_id, system_id, for_import=True)['valid']
    assert codec.inspect_license(cache)['file_kind'] == 'cache_or_headerless_payload'


def test_cli_python_entrypoint_and_import_failure(tmp_path):
    tool = Path(__file__).resolve().parents[1]
    fixture = tool / 'tests/fixtures/original-imported.enc'
    result = subprocess.run([sys.executable, '-X', 'utf8', '-m', 'cli', 'inspect', str(fixture)],
                            cwd=tool, capture_output=True, text=True, encoding='utf-8')
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report['results'][0]['has_license_row']
    assert report['results'][0]['client_import_header_present'] is False
    fields = report['results'][0]['fields']
    result = subprocess.run([sys.executable, '-X', 'utf8', '-m', 'cli', 'verify', str(fixture),
                             '--database-id', fields['DbId'], '--system-id', fields['Info1'],
                             '--for-import'], cwd=tool, capture_output=True, text=True,
                            encoding='utf-8')
    assert result.returncode == 1
    assert json.loads(result.stdout)['ok'] is False


def test_explicit_client_id_mode_is_renewal(tmp_path):
    result = codec.generate_license(database_id='ABCDE', system_id='DDCB4',
        client_id='SYNTHETIC-CLIENT', sequence=9, expires='2030-12-31',
        capacity=100, output_path=tmp_path / 'renewal.lic')
    assert result['mode'] == 'renewal'
    with pytest.raises(codec.LicenseError, match='Sequence'):
        codec.generate_license(database_id='ABCDE', system_id='DDCB4',
            client_id='SYNTHETIC-CLIENT', expires='2030-12-31',
            capacity=100, output_path=tmp_path / 'ambiguous.lic')


@pytest.mark.parametrize('field', ['MaxClient', 'Sequence'])
def test_client_cache_int32_overflow_rejected(tmp_path, field):
    # AF7 Convert.ToInt32(Object) rejects this even though Python int accepts it.
    from test_client_cache import server_row
    row = server_row()
    row[field] = '2147483648'
    with pytest.raises(codec.LicenseError, match='Int32'):
        codec.write_client_cache(row, tmp_path / 'licenseface.enc')
