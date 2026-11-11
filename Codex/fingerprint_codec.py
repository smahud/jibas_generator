"""Fingerprint JSL license format for Manager 16.5 and Client 14.0/16.10.

Original importers B60/6FF/8C1 accept the generated CM row. Original scanner
validators B61/700/8C2 match Seri exactly. Evidence: bukti/fingerprint/.
This product binds a scanner serial; it has no Database ID, System ID,
Client ID, expiry, capacity, or renewal sequence in the proven format.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET

import license_codec as face

LicenseError = face.LicenseError
BASE = Path(__file__).resolve().parent
TABLE = "JSL"
COLUMNS = (
    "Versi", "Klien", "Tanggal", "Seri", "KodeHw", "KodeRs", "KodeTx",
    "LicType", "Keterangan", "Info1", "Info2", "Info3",
)
IMPORT_MARKER = "LISENSI JIBAS SPT FINGERPRINT"
IMPORT_HEADER = ("# " + IMPORT_MARKER + "\r\n").encode("ascii")
SCOPES = {"both": "CM", "manager": "M", "client": "C"}


def _serial(value) -> str:
    value = str(value or "").strip()
    if (not value or len(value) > 255 or not value.isascii()
            or not value.isprintable()):
        raise LicenseError("Nomor seri scanner wajib berupa 1–255 karakter ASCII yang dapat dicetak.")
    return value


def _scope(value) -> str:
    value = str(value or "both").strip()
    result = SCOPES.get(value.lower(), value.upper())
    if result not in ("CM", "M", "C"):
        raise LicenseError("Cakupan fingerprint harus both/CM, manager/M, atau client/C.")
    return result


def _serialize(fields: dict) -> str:
    try:
        root = ET.fromstring((BASE / "fingerprint_schema.xml").read_text(encoding="ascii"))
    except (OSError, ET.ParseError) as exc:
        raise LicenseError(f"Skema fingerprint tidak dapat dibaca: {exc}") from exc
    row = ET.SubElement(root, TABLE)
    for name in COLUMNS:
        ET.SubElement(row, name).text = str(fields.get(name, ""))
    return ET.tostring(root, encoding="ascii").decode("ascii")


def _load(path):
    source = Path(path)
    try:
        if not source.is_file():
            raise LicenseError("Sumber harus berkas lisensi biasa.")
        with source.open("rb") as stream:
            raw = stream.read(4 * 1024 * 1024 + 1)
    except OSError as exc:
        raise LicenseError(f"Tidak dapat membaca berkas: {exc}") from exc
    xml = face._decrypt(raw, profile="client_fgr")
    if "<!DOCTYPE" in xml.upper() or "<!ENTITY" in xml.upper():
        raise LicenseError("DTD/entity tidak termasuk format lisensi fingerprint.")
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        raise LicenseError(f"XML fingerprint tidak valid: {exc}") from exc
    if root.tag != "NewDataSet":
        raise LicenseError("Root XML fingerprint bukan NewDataSet.")
    schema = root.find("{http://www.w3.org/2001/XMLSchema}schema")
    if schema is None or not any(e.attrib.get("name") == TABLE for e in schema.iter()):
        raise LicenseError("Skema bukan lisensi fingerprint JSL.")
    rows = [{c.tag: c.text or "" for c in row} for row in root.findall(TABLE)]
    return raw, xml, root, rows


def inspect_license(path) -> dict:
    raw, _, _, rows = _load(path)
    text = raw.decode("utf-16") if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else raw.decode("utf-8-sig")
    lines = text.splitlines()
    has_header = bool(lines and IMPORT_MARKER in lines[0])
    return {
        "path": str(Path(path).resolve()),
        "format": "JIBAS Fingerprint JSL / AES-128-CBC / XML DataTable",
        "product": "fingerprint", "sha256": hashlib.sha256(raw).hexdigest(),
        "has_license_row": bool(rows), "fields": rows[0] if rows else {},
        "rows": rows, "row_count": len(rows),
        "status": "license_row" if rows else "empty_cache",
        "file_kind": "import_license" if has_header else "cache_or_headerless_payload",
        "client_import_header_present": has_header,
        "import_header_present": has_header,
        "import_header_required": True,
        "header_requirements": {"manager_16_5": False, "client_14_0": False, "client_16_10": True},
        "identity_kind": "scanner_serial",
    }


def verify_license(path, serial, license_scope=None, *, for_import=False) -> dict:
    serial = _serial(serial)
    expected_scope = _scope(license_scope) if license_scope is not None else None
    inspection = inspect_license(path)
    checks = []

    def check(name, passed, detail):
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    check("license_row", bool(inspection["rows"]), "Baris lisensi fingerprint tersedia.")
    matching = [row for row in inspection["rows"] if row.get("Seri") == serial]
    check("scanner_serial", bool(matching), "Seri harus sama persis, termasuk huruf besar/kecil.")
    if matching:
        check("required_fields", any(all(k in row for k in COLUMNS) for row in matching), "12 kolom JSL lengkap.")
        if expected_scope:
            check("license_scope", any(all(c in row.get("LicType", "") for c in expected_scope) for row in matching),
                  f"Cakupan yang diperlukan: {expected_scope} (C=client, M=manager).")
        else:
            check("license_scope", any("C" in row.get("LicType", "") or "M" in row.get("LicType", "") for row in matching),
                  "LicType memuat cakupan C dan/atau M.")
    if for_import:
        check("client_import_header", inspection["client_import_header_present"],
              "Header LISENSI JIBAS SPT FINGERPRINT diperlukan untuk impor Client 16.10.")
    return {
        "valid": all(c["passed"] for c in checks), "scope": "offline_file_checks",
        "activation_proven": False, "product": "fingerprint", "checks": checks,
        "file_kind": inspection["file_kind"],
        "client_import_header_present": inspection["client_import_header_present"],
        "limitations": [
            "Pemeriksaan offline berdasarkan importer dan validator serial asli; scanner fisik dan alur presensi lengkap tidak dijalankan.",
            "Nomor seri harus diambil dari scanner yang digunakan. Database ID dan System ID bukan pengikat format ini.",
            "Format JSL yang dibuktikan tidak mempunyai tanggal kedaluwarsa, batas kapasitas, atau Sequence.",
            "KodeHw/KodeRs/KodeTx kosong diterima pada replay; makna penerbitnya belum dibuktikan.",
        ],
    }


def generate_license(*, serial, license_scope="both", client_name="", output_path,
                     overwrite=False) -> dict:
    serial, scope = _serial(serial), _scope(license_scope)
    fields = {
        "Versi": "1.0", "Klien": str(client_name or serial),
        "Tanggal": datetime.now(face.JAKARTA).date().isoformat(),
        "Seri": serial, "KodeHw": "", "KodeRs": "", "KodeTx": "",
        "LicType": scope, "Keterangan": "", "Info1": "", "Info2": "", "Info3": "",
    }
    encoded = IMPORT_HEADER + face._encrypt(_serialize(fields), profile="client_fgr")
    output = Path(output_path)
    try:
        with output.open("wb" if overwrite else "xb") as stream:
            stream.write(encoded)
    except FileExistsError as exc:
        raise LicenseError("Berkas keluaran sudah ada. Pilih nama baru atau aktifkan overwrite.") from exc
    except OSError as exc:
        raise LicenseError(f"Tidak dapat menyimpan berkas: {exc}") from exc
    return {
        "path": str(output.resolve()), "product": "fingerprint", "serial": serial,
        "license_scope": scope, "fields": fields, "mode": "new", "file_kind": "import_license",
        "verification": verify_license(output, serial, license_scope=scope, for_import=True),
    }
