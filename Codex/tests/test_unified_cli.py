"""End-to-end CLI routing with manual IDs and automatic renewal sequence."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


def call(*args):
    result = subprocess.run([sys.executable, '-X', 'utf8', '-m', 'cli', *map(str, args)],
                            cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
    return result.returncode, json.loads(result.stdout or result.stderr)


@pytest.mark.parametrize('product,db,system_field,capacity_field', [
    ('face', 'V4YNE', 'Info1', 'MaxClient'),
    ('schoolpay', '7VJM4', 'SystemId', 'MaxVendor'),
    ('cbe', 'ABCDE', 'Info1', 'MaxClient'),
])
def test_product_generate_inspect_verify_and_renew(tmp_path, product, db, system_field, capacity_field):
    out = tmp_path / f'{product}.lic'
    args = ['--product', product, '--database-id', db, '--system-id', 'DDCB4']
    code, generated = call('generate', *args, '--capacity', '10', '--expires', '2030-12-31', '--out', out)
    assert code == 0 and generated['ok']
    original_client = generated['results'][0]['client_id']
    code, inspected = call('inspect', '--product', product, out)
    fields = inspected['results'][0]['fields']
    assert code == 0 and fields[system_field] == 'DDCB4' and fields[capacity_field] == '10'
    assert call('verify', out, *args, '--for-import')[0] == 0
    assert call('verify', out, '--product', product, '--database-id', '00000', '--system-id', 'DDCB4')[0] == 1
    other = 'schoolpay' if product == 'face' else 'face'
    assert call('inspect', '--product', other, out)[0] == 2
    renewed = tmp_path / f'{product}-renewal.lic'
    code, report = call('generate', *args, '--capacity', '20', '--expires', '2031-12-31',
                        '--previous-license', out, '--out', renewed)
    assert code == 0
    assert report['results'][0]['client_id'] == original_client
    assert report['results'][0]['sequence'] == 2
    assert report['results'][0]['mode'] == 'renewal'


def test_public_cli_is_manual_and_sequence_is_automatic():
    import cli
    parser = cli.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(['detect'])
    with pytest.raises(SystemExit):
        parser.parse_args(['verify', 'file.lic', '--auto'])
    with pytest.raises(SystemExit):
        parser.parse_args(['generate', '--product', 'face', '--database-id', 'ABCDE',
                           '--system-id', '123AB', '--expires', '2030-12-31',
                           '--capacity', '10', '--out', 'file.lic', '--sequence', '10'])


@pytest.mark.parametrize('product,identity,extra,wrong', [
    ('fingerprint', ['--serial', 'SERIAL-TEST'], [], ['--serial', 'OTHER']),
    ('letterstore', ['--database-id', 'ABCDE'], [], ['--database-id', 'ZZZZZ']),
    ('sjs', ['--database-id', 'AB123'],
     ['--registration-token', '97875YgYKBhQIBwgZCQsbCxkPFQ4UAAgJGw4FCBUFCBkLCRsVBBQJGwoZDBUDDQNl',
      '--school-id', 'SCHOOL-EXISTING-001', '--expires', '2030-12-31', '--capacity', '2'],
     ['--database-id', 'ZZZZZ']),
])
def test_extended_products_do_not_require_unrelated_system_id(tmp_path, product, identity, extra, wrong):
    out = tmp_path / (product + '.lic')
    code, result = call('generate', '--product', product, *identity, *extra, '--out', out)
    assert code == 0 and result['ok']
    assert call('inspect', '--product', product, out)[0] == 0
    assert call('verify', '--product', product, out, *identity, '--for-import')[0] == 0
    assert call('verify', '--product', product, out, *wrong)[0] == 1


@pytest.mark.parametrize('product,extra', [
    ('fingerprint', ['--expires', '2030-12-31']),
    ('fingerprint', ['--capacity', '10']),
    ('letterstore', ['--previous-license', 'old.lic']),
    ('letterstore', ['--system-id', 'DDCB4']),
    ('sjs', ['--client-id', 'SHARED-CLIENT']),
])
def test_cli_rejects_flags_that_product_cannot_encode(tmp_path, product, extra):
    out = tmp_path / 'must-not-exist.lic'
    code, result = call('generate', '--product', product, *extra, '--out', out)
    assert code == 2 and result['ok'] is False
    assert 'tidak menggunakan' in result['error']
    assert not out.exists()
