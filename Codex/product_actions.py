"""Capability-aware form validation and codec calls, with no Tk dependencies."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re

from product_catalog import PRODUCT_BY_KEY

SCOPES = {'Manager + Client': 'both', 'Manager': 'manager', 'Client': 'client',
          'both': 'both', 'manager': 'manager', 'client': 'client'}


def product_for(key):
    try:
        return PRODUCT_BY_KEY[key]
    except KeyError as exc:
        raise ValueError(f'Produk tidak dikenal: {key}') from exc


def normalize_values(product, values, action='generate'):
    values = dict(values)
    if action == 'inspect':
        if not str(values.get('file') or '').strip():
            raise ValueError('Pilih berkas lisensi terlebih dahulu.')
        return values
    if action not in ('generate', 'verify'):
        raise ValueError('Operasi tidak dikenal.')
    if product.kind == 'fingerprint':
        serial = str(values.get('scanner_serial') or '').strip()
        if not serial:
            raise ValueError('Nomor seri scanner wajib diisi.')
        values['scanner_serial'] = serial
        try:
            values['license_scope'] = SCOPES[values.get('license_scope') or 'Manager + Client']
        except KeyError as exc:
            raise ValueError('Tujuan lisensi Finger tidak valid.') from exc
    else:
        dbid = str(values.get('database_id') or '').strip().upper()
        if not re.fullmatch(r'[A-Z0-9]{5}', dbid):
            raise ValueError('Database ID wajib diisi dengan 5 huruf/angka.')
        values['database_id'] = dbid
    if product.kind == 'standard':
        system = str(values.get('system_id') or '').strip().upper()
        if not re.fullmatch(r'[0-9A-F]{5}', system):
            raise ValueError('System ID wajib diisi dengan 5 karakter heksadesimal.')
        values['system_id'] = system
    if action == 'verify':
        if not str(values.get('file') or '').strip():
            raise ValueError('Pilih berkas lisensi terlebih dahulu.')
        return values
    if product.kind in ('standard', 'sjs'):
        expires = str(values.get('expires') or '').strip()
        if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', expires):
            raise ValueError('Tanggal harus berformat YYYY-MM-DD.')
        try:
            expiry = datetime.strptime(expires, '%Y-%m-%d').date()
        except ValueError as exc:
            raise ValueError('Tanggal tidak valid.') from exc
        if expiry < datetime.now(timezone(timedelta(hours=7))).date():
            raise ValueError('Tanggal kedaluwarsa sudah lewat.')
        values['expires'] = expires
        raw = values.get('capacity', '')
        if isinstance(raw, bool) or not re.fullmatch(r'[0-9]+', str(raw).strip()):
            raise ValueError('Kapasitas harus berupa bilangan bulat positif.')
        capacity = int(raw)
        if not 1 <= capacity <= 2147483647:
            raise ValueError('Kapasitas harus antara 1 dan 2147483647.')
        values['capacity'] = capacity
        previous = str(values.get('previous_license') or '').strip()
        if previous and not Path(previous).is_file():
            raise ValueError('Berkas lisensi lama tidak ditemukan atau bukan berkas.')
        values['previous_license'] = previous
    if product.kind == 'standard':
        client = str(values.get('client_id') or '').strip()
        if client and (client == 'TRIAL' or not client.isascii() or not client.isprintable()):
            raise ValueError('Client ID harus ASCII yang dapat dicetak dan bukan TRIAL.')
        if client and not values['previous_license']:
            raise ValueError('Untuk perpanjangan, pilih berkas lisensi lama agar urutan diperbarui otomatis.')
        values['client_id'] = client
    if product.kind == 'sjs':
        token = str(values.get('registration_token') or '').strip()
        if not token:
            raise ValueError('Registration Token SJS wajib diisi, bukan System ID.')
        school = str(values.get('school_id') or '').strip()
        if not school and not values['previous_license']:
            raise ValueError('School ID wajib untuk lisensi baru SJS; atau pilih lisensi lama untuk perpanjangan.')
        values['registration_token'], values['school_id'] = token, school
    values['client_name'] = str(values.get('client_name') or '').strip()
    return values


def generate_with_backend(backend, product, values, output_path, overwrite=False):
    values = normalize_values(product, values)
    common = dict(output_path=output_path, client_name=values['client_name'], overwrite=overwrite)
    if product.kind == 'fingerprint':
        return backend.generate_license(serial=values['scanner_serial'],
            license_scope=values['license_scope'], **common)
    common['database_id'] = values['database_id']
    if product.kind == 'letterstore':
        return backend.generate_license(**common)
    common.update(expires=values['expires'], capacity=values['capacity'], sequence=None,
        previous_license_path=Path(values['previous_license']) if values['previous_license'] else None)
    if product.kind == 'sjs':
        common.update(registration_token=values['registration_token'], school_id=values['school_id'] or None)
    else:
        common.update(system_id=values['system_id'], client_id=values['client_id'] or None)
    return backend.generate_license(**common)


def verify_with_backend(backend, product, path, values, for_import=False):
    values = normalize_values(product, dict(values, file=str(path)), 'verify')
    if product.kind == 'fingerprint':
        return backend.verify_license(path, serial=values['scanner_serial'],
            license_scope=values['license_scope'], for_import=for_import)
    kwargs = dict(database_id=values['database_id'], for_import=for_import)
    if product.kind == 'standard':
        kwargs.update(system_id=values['system_id'], client_id=(values.get('client_id') or '').strip() or None)
    elif product.kind == 'sjs':
        kwargs.update(registration_token=(values.get('registration_token') or '').strip() or None,
                      school_id=(values.get('school_id') or '').strip() or None)
    return backend.verify_license(path, **kwargs)
