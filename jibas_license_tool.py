#!/usr/bin/env python3
"""
JIBAS License Tool — OpenCode Implementation
=============================================

A Python tool for generating, verifying, and managing JIBAS Face Server 16.5
and JIBAS Face & Fingerprint Client 16.10 licenses.

Based on reverse-engineering analysis of:
- FaceServer.exe (SHA-256: 8a123015b2ee095ceda51ece6d47436e9760c88be8f92fb76ed7c120c923c364)
- FaceFgrClient.exe (SHA-256: 6f5369df4d854c467d24fb067d8b79c573b35699c7b1ce7f19a310669f1ba546)

License Format:
- Encrypted XML DataTable (AES-128-CBC, PKCS#7 padding)
- Key: MD5(ASCII(password)) where password derived from executable constants
- IV: Constant from executable constants
- File extension: .lic (import) or .enc (cache)

Required IDs for License Generation:
1. Database ID (DbId) - 5 alphanumeric chars (e.g., V4YNE)
   * Computed from jbssat database via 12 splang procedures (method 0x06000AC3)

2. System ID (Info1/Seri) - 5 hex chars (e.g., 7738F)
   * Computed from: MD5(disk_serial_C: + ComputerSystemProduct.UUID)
   * Hex chars at positions [5,17,30,24,3] (zero-based), uppercased

3. Client ID (KlienId) - Optional, for renewals only
   * 32-char hex UUID (e.g., 3515DE1C38554ABFA6595A327D57DA53)
   * Generated automatically for new licenses
   * Must be preserved for renewals

Verification Rules:
1. DbId must match installation Database ID
2. Info1 must match System ID (machine binding)
3. KlienId must not be empty or "TRIAL"
4. LicenseLimitDate must not be expired (using legacy minute calculation)
5. Sequence must be > 0
6. MaxClient must be > 0
7. For renewals: Sequence must be > previous Sequence, same KlienId, same DbId
"""

from __future__ import annotations

import argparse
import base64
import binascii
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
import os
import sys
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

# =============================================================================
# CONSTANTS
# =============================================================================

BASE = Path(__file__).resolve().parent

# Face/Fingerprint constants
TABLE_FACE = "JibasSptFaceLicense"
COLUMNS_FACE = (
    "Versi", "KlienId", "Klien", "Tanggal", "Model", "Seri", "Size",
    "Sequence", "KodeRs", "KodeTx", "DbId", "LicenseLimit",
    "LicenseLimitDate", "MaxClient", "Keterangan", "Info1", "Info2", "Info3",
)

# SchoolPay constants
TABLE_SCHOOLPAY = "JibasSchoolPayLicense"
COLUMNS_SCHOOLPAY = (
    "Versi", "KlienId", "Klien", "Tanggal", "Model", "Seri", "Size",
    "Sequence", "KodeRs", "KodeTx", "DbId", "SystemId",
    "LicenseLimit", "LicenseLimitDate", "MaxVendor", "Keterangan", "Info1", "Info2", "Info3",
)

# CBE Server constants
TABLE_CBE = "JibasCbeLicense"
COLUMNS_CBE = (
    "Versi", "KlienId", "Klien", "Tanggal", "Model", "Seri", "Size",
    "Sequence", "KodeRs", "KodeTx", "DbId", "LicenseLimit",
    "LicenseLimitDate", "MaxClient", "Keterangan", "Info1", "Info2", "Info3",
)

# Default to Face for backward compatibility
TABLE = TABLE_FACE
COLUMNS = COLUMNS_FACE

JAKARTA = timezone(timedelta(hours=7))
ET.register_namespace("xs", "http://www.w3.org/2001/XMLSchema")
ET.register_namespace("msdata", "urn:schemas-microsoft-com:xml-msdata")

# Crypto profiles (from format_profile.json)
# server: FaceServer.exe license.enc
# client_face: FaceFgrClient 16.10 licenseface.enc (FACE cache)
# client_fgr: FaceFgrClient 16.10 licensefgr.enc (FGR cache)
# schoolpay: JIBAS SchoolPay Secure Server 10.5 license.enc
# cbe: JIBAS CBE Server 26.5 license.enc (same crypto as server)


# =============================================================================
# EXCEPTIONS
# =============================================================================

class LicenseError(ValueError):
    """License operation error."""
    pass


class DetectError(ValueError):
    """ID detection error."""
    pass


# =============================================================================
# CORE CRYPTOGRAPHY
# =============================================================================

def _load_format_profile() -> dict:
    """Load format profile from JSON file."""
    profile_path = BASE / "format_profile.json"
    try:
        return json.loads(profile_path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError, KeyError) as exc:
        raise LicenseError(f"Profil format tidak dapat dibaca: {exc}") from exc


def _profile(name: str = "server") -> tuple[bytes, bytes]:
    """Return (aes_key, iv) for a named profile."""
    profile = _load_format_profile()
    if name == "server" and name not in profile.get("profiles", {}):
        return _legacy_profile(profile)
    pair = profile["profiles"][name]
    password = base64.b64decode(pair["password_b64"], validate=True)
    iv = base64.b64decode(pair["iv_b64"], validate=True)
    if len(iv) != 16:
        raise ValueError("IV bukan 16 byte")
    return hashlib.md5(password).digest(), iv


def _legacy_profile(profile: dict) -> tuple[bytes, bytes]:
    """Flat pre-client encoding of format_profile.json (back-compat)."""
    password = base64.b64decode(profile["password_b64"], validate=True)
    iv = base64.b64decode(profile["iv_b64"], validate=True)
    if len(iv) != 16:
        raise ValueError("IV bukan 16 byte")
    return hashlib.md5(password).digest(), iv


def _decrypt(data: bytes, profile: str = "server") -> str:
    """Decrypt license file."""
    if len(data) > 4 * 1024 * 1024:
        raise LicenseError("Berkas terlalu besar untuk format lisensi ini.")
    try:
        text = (data.decode("utf-16") if data.startswith((b"\xff\xfe", b"\xfe\xff"))
                else data.decode("utf-8-sig"))
        text = "".join(
            line.strip() for line in text.splitlines()
            if line.strip() and not line.strip().startswith("#")
        )
        ciphertext = base64.b64decode(text, validate=True)
        if not ciphertext or len(ciphertext) % 16:
            raise ValueError("panjang ciphertext tidak valid")
        key, iv = _profile(profile)
        decryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
        padded = decryptor.update(ciphertext) + decryptor.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        plaintext = unpadder.update(padded) + unpadder.finalize()
        return plaintext.decode("ascii")
    except (UnicodeError, binascii.Error, ValueError) as exc:
        raise LicenseError(f"Berkas tidak dapat didekripsi: {exc}") from exc


def _encrypt(xml: str, profile: str = "server") -> bytes:
    """Encrypt XML to license format."""
    key, iv = _profile(profile)
    try:
        plaintext = xml.encode("ascii")
    except UnicodeError as exc:
        raise LicenseError("XML harus menggunakan ASCII atau referensi karakter XML.") from exc
    padder = padding.PKCS7(128).padder()
    padded = padder.update(plaintext) + padder.finalize()
    encryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    ciphertext = encryptor.update(padded) + encryptor.finalize()
    return base64.b64encode(ciphertext) + b"\r\n"


# =============================================================================
# XML HANDLING
# =============================================================================

def _get_table_columns_schema(product: str = "face"):
    """Get table name, columns, and schema file for a product."""
    if product == "schoolpay":
        return TABLE_SCHOOLPAY, COLUMNS_SCHOOLPAY, BASE / "schema_schoolpay.xml"
    elif product == "cbe":
        return TABLE_CBE, COLUMNS_CBE, BASE / "schema_cbe.xml"
    return TABLE_FACE, COLUMNS_FACE, BASE / "schema.xml"


def _parse_xml(xml: str, product: str = "face"):
    """Parse license XML and extract fields."""
    if "<!DOCTYPE" in xml.upper() or "<!ENTITY" in xml.upper():
        raise LicenseError("Deklarasi DTD/entity tidak termasuk format lisensi.")
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        raise LicenseError(f"XML lisensi tidak valid: {exc}") from exc
    if root.tag != "NewDataSet":
        raise LicenseError("Root XML bukan NewDataSet.")
    table_name, _, _ = _get_table_columns_schema(product)
    rows = root.findall(table_name)
    if len(rows) > 1:
        raise LicenseError("Diharapkan paling banyak satu baris lisensi.")
    fields = {child.tag: child.text or "" for child in rows[0]} if rows else {}
    return root, fields


def _serialize(fields: dict, product: str = "face") -> str:
    """Serialize fields to license XML."""
    _, columns, schema_file = _get_table_columns_schema(product)
    table_name, _, _ = _get_table_columns_schema(product)
    try:
        root = ET.fromstring(schema_file.read_text(encoding="ascii"))
    except (OSError, ET.ParseError) as exc:
        raise LicenseError(f"Skema lisensi tidak tersedia: {exc}") from exc
    for existing in list(root.findall(table_name)):
        root.remove(existing)
    row = ET.SubElement(root, table_name)
    for name in columns:
        ET.SubElement(row, name).text = str(fields.get(name, ""))
    return ET.tostring(root, encoding="ascii", xml_declaration=False).decode("ascii")


# =============================================================================
# VALIDATION HELPERS
# =============================================================================

def _validate_id(value: str, label: str, system: bool = False) -> str:
    """Validate Database ID or System ID format."""
    value = str(value or "").strip().upper()
    pattern = r"[0-9A-F]{5}" if system else r"[A-Z0-9]{5}"
    if not value or not __import__('re').fullmatch(pattern, value):
        kind = "heksadesimal" if system else "huruf/angka"
        raise LicenseError(f"{label} harus 5 karakter {kind}.")
    return value


def _parse_datetime(value: str) -> datetime:
    """Parse ISO datetime string to Jakarta timezone."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return (parsed.replace(tzinfo=JAKARTA) if parsed.tzinfo is None
            else parsed.astimezone(JAKARTA))


def _legacy_minute(value: datetime) -> int:
    """
    Exact arithmetic of original time calculation (method 0x06000667..66B).
    Includes the original month rule (leap year = year % 4 == 0).
    """
    year = value.year
    month_days = [31, 29 if year % 4 == 0 else 28, 31, 30, 31, 30,
                  31, 31, 30, 31, 30, 31]
    leap = year // 4
    days = leap * 366 + (year - leap) * 365
    days += sum(month_days[:value.month]) + value.day
    return days * 1440 + value.hour * 60 + value.minute


# =============================================================================
# PUBLIC API: INSPECTION & VERIFICATION
# =============================================================================

def inspect_license(path: str | Path, profile: str = "server", product: str = "face") -> Dict[str, Any]:
    """Read and decrypt license file, return metadata and fields."""
    path = Path(path)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise LicenseError(f"Tidak dapat membaca berkas: {exc}") from exc
    xml = _decrypt(raw, profile=profile)
    _, fields = _parse_xml(xml, product=product)
    format_name = "JIBAS SchoolPay Secure Server 10.5" if product == "schoolpay" else "JIBAS Face Server 16.5"
    return {
        "path": str(path.resolve()),
        "format": f"{format_name} / AES-128-CBC / XML DataTable",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "has_license_row": bool(fields),
        "fields": fields,
        "status": "license_row" if fields else "empty_cache",
    }


def verify_license(
    path: str | Path,
    database_id: str,
    system_id: str,
    client_id: Optional[str] = None,
    *,
    face_count: Optional[int] = None,
    now: Optional[datetime] = None,
    profile: str = "server",
    product: str = "face"
) -> Dict[str, Any]:
    """
    Verify license against installation IDs.

    Returns dict with:
    - valid: bool (all checks passed)
    - scope: "offline_file_checks"
    - activation_proven: False (never contacts server)
    - checks: list of individual check results
    - limitations: list of verification limitations
    """
    database_id = _validate_id(database_id, "Database ID")
    system_id = _validate_id(system_id, "System ID", system=True)
    fields = inspect_license(path, profile=profile, product=product)["fields"]
    checks: List[Dict[str, Any]] = []

    def add_check(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": passed, "detail": detail})

    add_check("license_row", bool(fields),
              "Baris lisensi tersedia." if fields else "Cache tidak berisi baris lisensi; ini bukan lisensi aktif.")
    if fields:
        _, columns, _ = _get_table_columns_schema(product)
        add_check("required_fields", all(name in fields for name in columns if name != "Model"),
                  f"{len(columns)} kolom yang dibaca importer; Model boleh tidak ditulis cache asli.")
        add_check("database_id", fields.get("DbId") == database_id,
                  f"DbId berkas: {fields.get('DbId', '')}")
        add_check("system_id", fields.get("Info1") == system_id,
                  f"Info1 berkas: {fields.get('Info1', '')}")
        add_check("non_trial", fields.get("KlienId", "") not in ("", "TRIAL"),
                  "KlienId harus terisi dan bukan TRIAL.")
        if client_id:
            add_check("client_id", fields.get("KlienId") == client_id.strip(),
                      f"KlienId berkas: {fields.get('KlienId', '')}")
        try:
            expiry = _parse_datetime(fields["LicenseLimitDate"])
            current = now or datetime.now(JAKARTA)
            add_check("expiry", _legacy_minute(current) <= _legacy_minute(expiry),
                      f"LicenseLimitDate: {expiry.isoformat()}")
        except (ValueError, KeyError):
            add_check("expiry", False, "LicenseLimitDate tidak dapat dibaca.")
        try:
            capacity_field = "MaxVendor" if product == "schoolpay" else "MaxClient"
            capacity = int(fields[capacity_field])
            sequence = int(fields["Sequence"])
            add_check("capacity", 0 <= capacity <= 2147483647, f"{capacity_field}: {capacity}")
            add_check("sequence", 0 <= sequence <= 2147483647, f"Sequence: {sequence}")
            if face_count is not None:
                add_check("face_count", 0 <= face_count <= capacity,
                          f"Wajah aktif: {face_count}; kapasitas: {capacity}")
        except (ValueError, KeyError):
            add_check("numeric_fields", False, f"{capacity_field}/Sequence bukan Int32 yang valid.")

    return {
        "valid": all(item["passed"] for item in checks),
        "scope": "offline_file_checks",
        "activation_proven": False,
        "checks": checks,
        "limitations": [
            "Status server berjalan dan koneksi basis data tidak diperiksa.",
            "Jam pemeriksaan memakai Asia/Jakarta; aplikasi asli mengambil waktu basis data.",
            "Jumlah wajah aktif tidak diperiksa." if face_count is None else
            "Jumlah wajah aktif menggunakan nilai yang diberikan.",
            "Tidak menghubungi layanan validasi online; hasil bukan konfirmasi penerbit.",
            "Urutan perpanjangan perlu dibandingkan dengan lisensi yang sedang terpasang.",
        ],
    }


# =============================================================================
# PUBLIC API: LICENSE GENERATION
# =============================================================================

def generate_license(
    *,
    database_id: str,
    system_id: str,
    client_id: Optional[str] = None,
    expires: str,
    capacity: int,
    output_path: str | Path,
    client_name: str = "",
    previous_license_path: Optional[str | Path] = None,
    sequence: Optional[int] = None,
    overwrite: bool = False,
    profile: str = "server",
    product: str = "face"
) -> Dict[str, Any]:
    """
    Generate a new license file.

    Args:
        database_id: 5-char alphanumeric Database ID (e.g., V4YNE)
        system_id: 5-char hex System ID (e.g., 7738F)
        client_id: Optional Client ID for renewals (32-char hex)
        expires: Expiry date YYYY-MM-DD
        capacity: Max faces/vendors (1..2147483647)
        output_path: Output .lic file path
        client_name: Optional client name
        previous_license_path: Previous license for renewal
        sequence: Explicit sequence number (for renewal without previous file)
        overwrite: Overwrite existing output file
        product: "face" (Face/Fingerprint) or "schoolpay" (SchoolPay)

    Returns:
        Dict with path, client_id, sequence, verification result
    """
    database_id = _validate_id(database_id, "Database ID")
    system_id = _validate_id(system_id, "System ID", system=True)

    # Validate capacity
    if not isinstance(capacity, int) or isinstance(capacity, bool):
        raise LicenseError("Kapasitas harus bilangan bulat.")
    if not 1 <= capacity <= 2147483647:
        raise LicenseError("Kapasitas harus antara 1 dan 2147483647.")

    # Validate expiry date
    try:
        expiry_date = date.fromisoformat(expires)
        if expiry_date.isoformat() != expires:
            raise ValueError("Tanggal harus YYYY-MM-DD.")
        if expiry_date < datetime.now(JAKARTA).date():
            raise ValueError("Tanggal kedaluwarsa sudah lewat.")
    except (ValueError, TypeError) as exc:
        raise LicenseError(str(exc)) from exc

    client_id = (client_id or "").strip() or None
    previous = None
    previous_sequence = None
    is_renewal = bool(previous_license_path or client_id or (sequence is not None))

    if previous_license_path:
        previous = inspect_license(previous_license_path, profile=profile, product=product)["fields"]
        if not previous:
            raise LicenseError("Lisensi sebelumnya tidak berisi baris lisensi.")
        if previous.get("DbId") != database_id:
            raise LicenseError(
                "Database ID berbeda dari lisensi sebelumnya "
                f"(berkas: {previous.get('DbId', '')}).")
        if client_id and previous.get("KlienId") != client_id:
            raise LicenseError(
                "Client ID berbeda dari lisensi sebelumnya "
                f"(berkas: {previous.get('KlienId', '')}).")
        client_id = previous.get("KlienId")
        if not client_id or client_id == "TRIAL":
            raise LicenseError("Lisensi sebelumnya bukan lisensi klien yang dapat diperpanjang.")
        try:
            previous_sequence = int(previous["Sequence"])
        except (ValueError, KeyError) as exc:
            raise LicenseError("Sequence lisensi sebelumnya tidak valid.") from exc
        if sequence is None:
            sequence = previous_sequence + 1
        elif sequence <= previous_sequence:
            raise LicenseError("Sequence perpanjangan harus lebih besar dari sebelumnya.")
    elif client_id and sequence is None:
        raise LicenseError(
            "Perpanjangan membutuhkan berkas lisensi sebelumnya atau Sequence yang "
            "lebih besar dari Sequence terpasang. Client ID saja tidak mengungkap nilai itu.")

    if sequence is None:
        sequence = 1
    if not isinstance(sequence, int) or isinstance(sequence, bool) or not 1 <= sequence <= 2147483647:
        raise LicenseError("Sequence harus antara 1 dan 2147483647.")

    if client_id is None:
        client_id = uuid.uuid4().hex.upper()
    if client_id == "TRIAL" or not client_id.isascii() or not client_id.isprintable():
        raise LicenseError("Client ID harus ASCII yang dapat dicetak dan bukan TRIAL.")

    created = datetime.now(JAKARTA)
    expiry = datetime.combine(expiry_date, time(23, 59), JAKARTA)
    if _legacy_minute(created) > _legacy_minute(expiry):
        raise LicenseError("Tanggal ini sudah lewat menurut perhitungan waktu aplikasi asli.")

    # Product-specific fields
    if product == "schoolpay":
        fields = {
            "Versi": "10.5", "KlienId": client_id,
            "Klien": client_name or (previous or {}).get("Klien") or database_id,
            "Tanggal": created.date().isoformat(), "Model": "SCHOOLPAY",
            "Seri": system_id, "Size": str(capacity), "Sequence": str(sequence),
            "KodeRs": "", "KodeTx": "", "DbId": database_id,
            "SystemId": system_id,  # SchoolPay has separate SystemId column
            "LicenseLimit": expires, "LicenseLimitDate": expiry.isoformat(),
            "MaxVendor": str(capacity), "Keterangan": "",
            "Info1": system_id, "Info2": "", "Info3": "",
        }
    elif product == "cbe":
        fields = {
            "Versi": "26.5", "KlienId": client_id,
            "Klien": client_name or (previous or {}).get("Klien") or database_id,
            "Tanggal": created.date().isoformat(), "Model": "CBE",
            "Seri": system_id, "Size": str(capacity), "Sequence": str(sequence),
            "KodeRs": "", "KodeTx": "", "DbId": database_id,
            "LicenseLimit": expires, "LicenseLimitDate": expiry.isoformat(),
            "MaxClient": str(capacity), "Keterangan": "",
            "Info1": system_id, "Info2": "", "Info3": "",
        }
    else:
        fields = {
            "Versi": "16.5", "KlienId": client_id,
            "Klien": client_name or (previous or {}).get("Klien") or database_id,
            "Tanggal": created.date().isoformat(), "Model": "SPTFACE",
            "Seri": system_id, "Size": str(capacity), "Sequence": str(sequence),
            "KodeRs": "", "KodeTx": "", "DbId": database_id,
            "LicenseLimit": expires, "LicenseLimitDate": expiry.isoformat(),
            "MaxClient": str(capacity), "Keterangan": "",
            "Info1": system_id, "Info2": "", "Info3": "",
        }

    output = Path(output_path)
    encoded = _encrypt(_serialize(fields, product=product), profile=profile)
    try:
        if overwrite:
            with output.open("wb") as stream:
                stream.write(encoded)
        else:
            with output.open("xb") as stream:
                stream.write(encoded)
    except FileExistsError as exc:
        raise LicenseError("Berkas keluaran sudah ada. Pilih nama baru atau aktifkan overwrite.") from exc
    except OSError as exc:
        raise LicenseError(f"Tidak dapat menyimpan berkas: {exc}") from exc

    verification = verify_license(output, database_id, system_id, client_id, profile=profile, product=product)
    return {
        "path": str(output.resolve()),
        "client_id": client_id,
        "sequence": sequence,
        "database_id": database_id,
        "system_id": system_id,
        "previous_sequence": previous_sequence,
        "mode": "renewal" if previous_license_path or (previous_sequence is not None) else "new",
        "verification": verification,
    }


def renew_license(
    *,
    database_id: str,
    system_id: str,
    expires: str,
    capacity: int,
    output_path: str | Path,
    previous_license_path: str | Path,
    client_name: str = "",
    sequence: Optional[int] = None,
    overwrite: bool = False,
    profile: str = "server",
    product: str = "face"
) -> Dict[str, Any]:
    """
    Convenience function for license renewal.
    """
    return generate_license(
        database_id=database_id,
        system_id=system_id,
        expires=expires,
        capacity=capacity,
        output_path=output_path,
        client_name=client_name,
        previous_license_path=previous_license_path,
        sequence=sequence,
        overwrite=overwrite,
        profile=profile,
        product=product,
    )


# =============================================================================
# CLIENT 16.10 FACE CACHE SUPPORT
# =============================================================================

DEFAULT_CLIENT_DIR = Path(r"C:\Program Files\YIM\JIBAS Face & Fingerprint Client 16.10")
DEFAULT_CLIENT_SOURCE = Path(r"C:\Program Files\YIM\JIBAS Face Server 16.5\license.enc")
CLIENT_FACE_CACHE = "licenseface.enc"
CLIENT_CACHE_EXE = "FaceFgrClient.exe"


def inspect_client_cache(path: str | Path) -> dict:
    """Read client FACE cache (licenseface.enc) with client profile."""
    return inspect_license(path, profile="client_face")


def _normalize_cache_fields(fields: dict) -> dict:
    """Map a row to the full 18-column schema, filling absent columns with empty string."""
    return {name: str(fields.get(name, "")) for name in COLUMNS}


def validate_client_fields(fields: dict) -> None:
    """Accept row only if columns consumed by client validator are properly filled."""
    if not isinstance(fields, dict) or not fields:
        raise LicenseError("Baris cache klien kosong.")
    required = ("Versi", "KlienId", "Klien", "Tanggal", "Seri", "Size",
                "Sequence", "DbId", "LicenseLimit", "LicenseLimitDate",
                "MaxClient", "Info1")
    missing = [name for name in required if not str(fields.get(name, ""))]
    if missing:
        raise LicenseError("Baris sumber tidak lengkap; kolom kosong: "
                           + ", ".join(missing))
    if fields["KlienId"] == "TRIAL":
        raise LicenseError("Baris sumber masih lisensi TRIAL (KlienId=TRIAL); "
                           "cache klien tidak akan menonaktifkan pesan uji coba.")
    try:
        _parse_datetime(fields["LicenseLimitDate"])
        int(fields["MaxClient"])
        int(fields["Sequence"])
    except (ValueError, KeyError) as exc:
        raise LicenseError("Baris sumber punya LicenseLimitDate/MaxClient/"
                           "Sequence yang tidak dapat dibaca aplikasi.") from exc


def resolve_client_row(source_path: str | Path) -> dict:
    """Load one license row suitable for client cache from .lic/.enc."""
    fields = inspect_license(source_path, profile="server")["fields"]
    validate_client_fields(fields)
    return {name: fields[name] for name in COLUMNS if name in fields}


def write_client_cache(fields: dict, output_path: str | Path, overwrite: bool = False) -> dict:
    """Write one licenseface.enc for FaceFgrClient 16.10."""
    validate_client_fields(fields)
    output = Path(output_path)
    ordered = _normalize_cache_fields(fields)
    encoded = _encrypt(_serialize(ordered), profile="client_face")
    try:
        if overwrite:
            with output.open("wb") as stream:
                stream.write(encoded)
        else:
            with output.open("xb") as stream:
                stream.write(encoded)
    except FileExistsError as exc:
        raise LicenseError("Berkas keluaran sudah ada. Gunakan timpa dengan "
                           "cadangan otomatis.") from exc
    except OSError as exc:
        raise LicenseError(f"Tidak dapat menyimpan berkas: {exc}") from exc
    written = inspect_client_cache(output)
    if written["fields"] != ordered:
        raise LicenseError("Verifikasi cache yang baru ditulis tidak cocok.")
    return {
        "path": str(output.resolve()),
        "sha256": written["sha256"],
        "fields": ordered,
        "profile": "client_face",
    }


def fix_client_cache(
    client_dir: str | Path,
    source: str | Path,
    *,
    overwrite: bool = False,
    make_backup: bool = True
) -> dict:
    """
    Apply TRIAL fix for client 16.10: write licenseface.enc from `source`.

    Safety:
      - `client_dir` must contain FaceFgrClient.exe (marker check).
      - Existing licenseface.enc never lost: with --overwrite it's moved to
        licenseface.enc.bak-<stamp>; without --overwrite call fails.
      - licensefgr.enc and config.ini never touched.
      - Written bytes re-read and compared column-by-column before returning.
    """
    directory = Path(client_dir)
    if not directory.is_dir():
        raise LicenseError(f"Direktori klien tidak ada: {directory}")
    if not (directory / CLIENT_CACHE_EXE).is_file():
        raise LicenseError("Direktori yang dipilih bukan folder aplikasi "
                           f"klien 16.10 (tidak menemukan {CLIENT_CACHE_EXE}).")
    fields = resolve_client_row(source)
    target = directory / CLIENT_FACE_CACHE
    backup_path = None
    if target.exists():
        if not overwrite:
            raise LicenseError(f"{CLIENT_FACE_CACHE} sudah ada. Gunakan timpa "
                               "(--overwrite) agar dibuat cadangan otomatis "
                               "sebelum ditulis ulang.")
        if make_backup:
            stamp = datetime.now(JAKARTA).strftime("%Y%m%dT%H%M%S")
            backup_path = target.with_name(f"{target.name}.bak-{stamp}")
            try:
                target.replace(backup_path)
            except OSError as exc:
                raise LicenseError(f"Tidak dapat membuat cadangan: {exc}") from exc
    try:
        result = write_client_cache(fields, target, overwrite=True)
    except LicenseError:
        if backup_path is not None and backup_path.exists():
            backup_path.replace(target)  # restore original
        raise
    existing_fgr = directory / "licensefgr.enc"
    existing_cfg = directory / "config.ini"
    return {
        "client_dir": str(directory.resolve()),
        "cache_path": result["path"],
        "sha256": result["sha256"],
        "fields": _normalize_cache_fields(fields),
        "backup_path": str(backup_path) if backup_path else None,
        "untouched": {
            "licensefgr.enc": bool(existing_fgr.is_file()),
            "config.ini": bool(existing_cfg.is_file()),
        },
        "source": str(Path(source).resolve()),
    }


def verify_client_fix(fix_result: dict) -> dict:
    """Re-read client cache from fix_client_cache and ensure it's ready."""
    try:
        cache = inspect_client_cache(fix_result["cache_path"])
    except (LicenseError, KeyError, OSError) as exc:
        raise LicenseError(f"Cache klien tidak dapat dibaca ulang: {exc}") from exc
    checks = []

    def check(name, passed, detail):
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    fields = cache["fields"]
    check("license_row", bool(fields), "Baris lisensi terbaca dari cache klien.")
    if fields:
        try:
            validate_client_fields(fields)
            check("consumer_columns", True,
                  "Kolom yang dikonsumsi validator klien lengkap dan dapat dibaca.")
        except LicenseError as exc:
            check("consumer_columns", False, str(exc))
        check("row_copy", _normalize_cache_fields(fields) == _normalize_cache_fields(fix_result.get("fields", {})),
              "Baris cache sama dengan baris sumber lisensi efektif.")
    return {
        "valid": all(item["passed"] for item in checks),
        "ready": all(item["passed"] for item in checks),
        "checks": checks,
    }


# =============================================================================
# DATABASE ID / SYSTEM ID DETECTION
# =============================================================================

DB_RECIPE = [
    # (procedure, output_parameter_index, substring_position)
    (4, 7, 14),
    (2, 5, 5),
    (9, 2, 25),
    (11, 4, 37),
    (1, 1, 47),
]
SPLANG_PROCEDURES = [f"splang{i:02d}" for i in range(1, 13)]


def _hex_to_ascii(hex_text: str) -> str:
    text = (hex_text or "").strip()
    if len(text) % 2 != 0 or not __import__('re').fullmatch(r"[0-9A-Fa-f]{4,}", text or ""):
        raise DetectError("Nilai hex variabel splang tidak valid.")
    try:
        return binascii.unhexlify(text).decode("ascii")
    except (binascii.Error, UnicodeError) as exc:
        raise DetectError(f"Payload splang bukan teks ASCII heksadesimal: {exc}") from exc


class DbIdDetector:
    """Reads the Database ID exactly like original method 0x06000AC3."""

    def __init__(self, host="127.0.0.1", port=3434, user="root", password="kebersamaan",
                 database="jbssat"):
        self.host, self.port, self.user, self.password = host, port, user, password
        self.database = database

    def _connect(self):
        try:
            import pymysql
        except ImportError as exc:
            raise DetectError(
                "Modul pymysql tidak tersedia. Install dengan: python -m pip install pymysql") from exc
        try:
            return pymysql.connect(host=self.host, port=self.port, user=self.user,
                                   password=self.password, database=self.database,
                                   charset="utf8mb4", connect_timeout=10)
        except Exception as exc:
            raise DetectError(f"Tidak dapat terhubung MySQL {self.host}:{self.port}: {exc}") from exc

    def verify_procedures(self, conn) -> dict:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT specific_name FROM information_schema.ROUTINES "
            "WHERE routine_schema = %s AND routine_type = 'PROCEDURE'",
            (self.database,))
        existing = {row[0] for row in cursor.fetchall()}
        missing = [name for name in SPLANG_PROCEDURES if name not in existing]
        return {"present": sorted(existing), "missing": missing}

    def detect(self) -> tuple[str, dict]:
        conn = self._connect()
        try:
            cursor = conn.cursor()
            info = self.verify_procedures(conn)
            if info["missing"]:
                raise DetectError(
                    "Prosedur splang hilang: " + ", ".join(info["missing"]))
            pieces = []
            variables = []
            for proc, index, position in DB_RECIPE:
                var = "@uh" + "abcdefghi"[index]
                names = [f"@uh{c}" for c in "abcdefghi"]
                cursor.execute(
                    f"CALL `{self.database}`.splang{proc:02d}({', '.join(names)})")
                cursor.execute(f"SELECT {', '.join(names)}")
                row = cursor.fetchone()
                if not row or row[index] is None:
                    raise DetectError(f"Nilai keluaran {var} splang{proc:02d} kosong.")
                decoded = _hex_to_ascii(row[index])
                if position >= len(decoded):
                    raise DetectError(
                        f"Posisi {position} di luar payload splang{proc:02d} {var}.")
                character = decoded[position]
                pieces.append(character)
                variables.append({
                    "procedure": f"splang{proc:02d}", "variable": var,
                    "position": position, "character": character,
                })
        finally:
            conn.close()
        db_id = "".join(pieces).upper()
        return db_id, {"method": "jbssat splang procedure recipe (original 0x06000AC3)",
                       "pieces": variables, "connection": f"{self.host}:{self.port}/{self.database}"}


class SystemIdDetector:
    """Reads the System ID like original 0x06000599 + 0x0600059A + 0x0600059B."""

    WMI_DISK_QUERY = "select * from Win32_DiskDrive where InterfaceType='SCSI' or InterfaceType='IDE'"

    def __init__(self, disk_serial=None, cs_uuid=None):
        self._disk_serial, self._cs_uuid = disk_serial, cs_uuid

    def read_wmi(self) -> tuple[str, str]:
        script = r"""
$ErrorActionPreference = 'SilentlyContinue'
$drives = Get-WmiObject -Query "select * from Win32_DiskDrive where InterfaceType='SCSI' or InterfaceType='IDE'"
$media = @(Get-WmiObject -Query "SELECT Tag, SerialNumber FROM Win32_PhysicalMedia")
$csp = @(Get-WmiObject -Query 'SELECT UUID FROM Win32_ComputerSystemProduct')
foreach ($drive in $drives) {
  $devId = $drive.DeviceID
  $parts = @(Get-WmiObject -Query ("ASSOCIATORS OF {Win32_DiskDrive.DeviceID='" + $devId + "'} WHERE AssocClass = Win32_DiskDriveToDiskPartition"))
  foreach ($part in $parts) {
    $logicals = @(Get-WmiObject -Query ("ASSOCIATORS OF {Win32_DiskPartition.DeviceID='" + $part.DeviceID + "'} WHERE AssocClass = Win32_LogicalDiskToPartition"))
    foreach ($logical in $logicals) {
      if ($logical.DeviceID -eq 'C:') {
        $match = @($media | Where-Object { ('' + $_.Tag) -eq $devId })
        if ($match.Count -gt 0) {
          $raw = '' + $match[0].SerialNumber
          while ($raw.Length -gt 0 -and $raw[$raw.Length-1] -eq ' ') { $raw = $raw.Substring(0, $raw.Length - 1) }
          Write-Output ('DISK ' + $raw)
          if ($csp.Count -gt 0) { Write-Output ('UUID ' + ('' + $csp[0].UUID)) }
          exit 0
        }
      }
    }
  }
}
Write-Output 'DISK NOT FOUND'
exit 0
"""
        try:
            import subprocess
            completed = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True, text=True, timeout=60, encoding="utf-8", errors="replace")
        except OSError as exc:
            raise DetectError(f"PowerShell tidak dapat dijalankan: {exc}") from exc
        disk, cs_uuid = "", ""
        for line in (completed.stdout or "").splitlines():
            if line.startswith("DISK "):
                disk = line[5:]
            elif line.startswith("UUID "):
                cs_uuid = line[5:]
        if not disk or disk == "NOT FOUND":
            raise DetectError("Serial fisik disk C: tidak ditemukan lewat WMI.")
        return disk, cs_uuid

    @staticmethod
    def _md5_hex(ascii_input: str) -> str:
        return hashlib.md5(ascii_input.encode("ascii")).hexdigest().lower()

    @classmethod
    def compute(cls, disk_serial: str, cs_uuid: str) -> str:
        digest = cls._md5_hex((disk_serial or "") + (cs_uuid or ""))
        return "".join(digest[i] for i in (5, 17, 30, 24, 3)).upper()

    def detect(self) -> tuple[str, dict]:
        if self._disk_serial is None or self._cs_uuid is None:
            disk, cs_uuid = self.read_wmi()
        else:
            disk, cs_uuid = self._disk_serial, self._cs_uuid
        try:
            system_id = self.compute(disk, cs_uuid)
        except UnicodeError as exc:
            raise DetectError(f"Nilai hardware mengandung karakter non-ASCII: {exc}") from exc
        return system_id, {
            "disk_serial_raw": disk, "csproduct_uuid": cs_uuid,
            "algorithm": "MD5(disk_serial + csproduct_uuid) hex[5,17,30,24,3].upper()",
        }


# =============================================================================
# CLI
# =============================================================================

def _positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Kapasitas harus berupa bilangan bulat.") from exc
    if number < 1:
        raise argparse.ArgumentTypeError("Kapasitas harus lebih dari nol.")
    return number


def _positive_int32(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Sequence harus berupa bilangan bulat.") from exc
    if not 1 <= number <= 2_147_483_647:
        raise argparse.ArgumentTypeError("Sequence harus antara 1 dan 2147483647.")
    return number


def _iso_date(value: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Tanggal harus berformat YYYY-MM-DD.") from exc
    if parsed.isoformat() != value:
        raise argparse.ArgumentTypeError("Tanggal harus berformat YYYY-MM-DD.")
    return value


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="JIBAS Face Server 16.5 / Face & Fingerprint Client 16.10 License Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Detect Database ID and System ID
  python jibas_license_tool.py detect

  # Generate new license
  python jibas_license_tool.py generate --database-id V4YNE --system-id 7738F \\
      --expires 2027-12-31 --capacity 100 --output license.lic

  # Generate with custom client name
  python jibas_license_tool.py generate --database-id V4YNE --system-id 7738F \\
      --expires 2027-12-31 --capacity 100 --client-name "My School" \\
      --output license.lic

  # Renew license (requires previous license file)
  python jibas_license_tool.py renew --database-id V4YNE --system-id 7738F \\
      --expires 2028-12-31 --capacity 200 \\
      --previous-license license.lic --output license_renewal.lic

  # Verify license
  python jibas_license_tool.py verify --file license.lic --database-id V4YNE --system-id 7738F

  # Inspect license contents
  python jibas_license_tool.py inspect --file license.lic

  # Fix client 16.10 TRIAL (write licenseface.enc from server license)
  python jibas_license_tool.py fix-client-cache --overwrite

  # Fix client cache with custom source and target
  python jibas_license_tool.py fix-client-cache --dari license.lic --tujuan "C:\\Program Files\\YIM\\JIBAS Face & Fingerprint Client 16.10" --overwrite
        """
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Inspect command
    inspect = subparsers.add_parser("inspect", help="Read license file contents")
    inspect.add_argument("file", type=Path, metavar="FILE")
    inspect.add_argument("--profile", choices=["server", "client_face", "client_fgr", "schoolpay", "cbe"], default="server",
                         help="Crypto profile to use for decryption")
    inspect.add_argument("--product", choices=["face", "schoolpay", "cbe"], default="face",
                         help="Product type: face (Face/Fingerprint), schoolpay (SchoolPay), or cbe (CBE Server)")

    # Verify command
    verify = subparsers.add_parser("verify", help="Verify license against installation IDs")
    verify.add_argument("file", type=Path, metavar="FILE")
    verify.add_argument("--database-id", required=True, help="Database ID (5 alphanumeric)")
    verify.add_argument("--system-id", required=True, help="System ID (5 hex)")
    verify.add_argument("--client-id", help="Client ID for verification (optional)")
    verify.add_argument("--count", type=_positive_int, help="Active face/vendor count (optional)")
    verify.add_argument("--profile", choices=["server", "client_face", "client_fgr", "schoolpay", "cbe"], default="server",
                        help="Crypto profile to use for decryption")
    verify.add_argument("--product", choices=["face", "schoolpay", "cbe"], default="face",
                        help="Product type: face (Face/Fingerprint), schoolpay (SchoolPay), or cbe (CBE Server)")

    # Generate command
    generate = subparsers.add_parser("generate", help="Generate new license file")
    generate.add_argument("--database-id", required=True, help="Database ID (5 alphanumeric, e.g., V4YNE)")
    generate.add_argument("--system-id", required=True, help="System ID (5 hex, e.g., 7738F)")
    generate.add_argument("--client-id", help="Client ID for renewal (optional, 32-char hex)")
    generate.add_argument("--expires", required=True, type=_iso_date, help="Expiry date YYYY-MM-DD")
    generate.add_argument("--capacity", required=True, type=_positive_int, help="Max faces/vendors (1..2147483647)")
    generate.add_argument("--client-name", default="", help="Client name (optional)")
    generate.add_argument("--output", required=True, type=Path, help="Output .lic file path")
    generate.add_argument("--overwrite", action="store_true", help="Overwrite existing output file")
    generate.add_argument("--product", choices=["face", "schoolpay", "cbe"], default="face",
                          help="Product type: face (Face/Fingerprint), schoolpay (SchoolPay), or cbe (CBE Server)")

    # Renew command
    renew = subparsers.add_parser("renew", help="Renew license (requires previous license file)")
    renew.add_argument("--database-id", required=True, help="Database ID (5 alphanumeric)")
    renew.add_argument("--system-id", required=True, help="System ID (5 hex) - can differ from previous")
    renew.add_argument("--expires", required=True, type=_iso_date, help="New expiry date YYYY-MM-DD")
    renew.add_argument("--capacity", required=True, type=_positive_int, help="New max faces/vendors")
    renew.add_argument("--previous-license", required=True, type=Path, help="Previous license file (.lic/.enc)")
    renew.add_argument("--client-name", default="", help="Client name (optional, defaults to previous)")
    renew.add_argument("--output", required=True, type=Path, help="Output .lic file path")
    renew.add_argument("--overwrite", action="store_true", help="Overwrite existing output file")
    renew.add_argument("--product", choices=["face", "schoolpay", "cbe"], default="face",
                       help="Product type: face (Face/Fingerprint), schoolpay (SchoolPay), or cbe (CBE Server)")

    # Fix client cache command
    client = subparsers.add_parser(
        "fix-client-cache",
        help="Fix TRIAL on FaceFgrClient 16.10: write licenseface.enc from effective Face Server license"
    )
    client.add_argument("--dari", type=Path, default=None, metavar="FILE",
                        help="Effective license (.lic/.enc); default: Face Server 16.5 license.enc")
    client.add_argument("--tujuan", type=Path, default=None, metavar="DIR",
                        help="FaceFgrClient 16.10 folder; default: installed client 16.10 folder")
    client.add_argument("--overwrite", action="store_true",
                        help="Overwrite existing licenseface.enc (auto backup to licenseface.enc.bak-<stamp>)")

    return parser


def _print_result(result: Dict[str, Any], command: str) -> int:
    """Print result as JSON and return exit code."""
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    if command == "verify":
        return 0 if result.get("valid") is True else 1
    verification = result.get("verification") if command in ("generate", "renew") else None
    if isinstance(verification, dict) and verification.get("valid") is False:
        return 1
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "inspect":
            result = inspect_license(args.file, profile=args.profile, product=args.product)
            print(json.dumps({"ok": True, "results": [result]}, ensure_ascii=False, indent=2, default=str))
            return 0

        elif args.command == "verify":
            database_id = args.database_id.strip()
            system_id = args.system_id.strip()
            client_id = (args.client_id or "").strip() or None
            result = verify_license(
                args.file, database_id, system_id, client_id,
                face_count=args.count, profile=args.profile, product=args.product
            )
            output = {"ok": result.get("valid") is True, "results": [result]}
            print(json.dumps(output, ensure_ascii=False, indent=2, default=str))
            return 0 if result.get("valid") is True else 1

        elif args.command == "generate":
            result = generate_license(
                database_id=args.database_id.strip(),
                system_id=args.system_id.strip(),
                client_id=(args.client_id or "").strip() or None,
                expires=args.expires,
                capacity=args.capacity,
                output_path=args.output,
                client_name=args.client_name.strip(),
                overwrite=args.overwrite,
                product=args.product,
            )
            return _print_result(result, "generate")

        elif args.command == "renew":
            result = renew_license(
                database_id=args.database_id.strip(),
                system_id=args.system_id.strip(),
                expires=args.expires,
                capacity=args.capacity,
                output_path=args.output,
                previous_license_path=args.previous_license,
                client_name=args.client_name.strip(),
                sequence=args.sequence,
                overwrite=args.overwrite,
                product=args.product,
            )
            return _print_result(result, "renew")

        elif args.command == "fix-client-cache":
            source = args.dari or DEFAULT_CLIENT_SOURCE
            client_dir = args.tujuan or DEFAULT_CLIENT_DIR
            result = fix_client_cache(client_dir, source, overwrite=args.overwrite)
            verification = verify_client_fix(result)
            output = {"ok": verification.get("ready") is True, "results": [result, verification]}
            print(json.dumps(output, ensure_ascii=False, indent=2, default=str))
            return 0 if verification.get("ready") is True else 1

        else:
            parser.error(f"Perintah tidak dikenal: {args.command}")
            return 2

    except LicenseError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    except DetectError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"Kesalahan tak terduga: {exc}"}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())