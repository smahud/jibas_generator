"""CBE Server 26.5 XML/AES codec, bound to executable SHA-256
a2b77a3fc715d1d8c2b47a29ff65444af0e829c3f2704098ed538c48ce5f140b.

Schema/crypto recovered from original methods 05B8/05B9; date arithmetic
matches original 0E0A including the unchecked Int32 year-minute term.
"""
from __future__ import annotations

from datetime import datetime, time
import hashlib
from pathlib import Path
import uuid
import xml.etree.ElementTree as ET

import license_codec as face

LicenseError = face.LicenseError
BASE = Path(__file__).resolve().parent
TABLE = "JibasCbeLicense"
COLUMNS = (
    "Versi", "KlienId", "Klien", "Tanggal", "Model", "Seri", "Size", "Sequence",
    "KodeRs", "KodeTx", "DbId", "LicenseLimit", "LicenseLimitDate", "MaxClient",
    "Keterangan", "Info1", "Info2", "Info3",
)
IMPORT_MARKER = "LISENSI JIBAS CBE"
IMPORT_HEADER = ("# " + IMPORT_MARKER + "\r\n").encode("ascii")
JAKARTA = face.JAKARTA


def _legacy_minute(value: datetime) -> int:
    year = value.year
    month_days = [31, 29 if year % 4 == 0 else 28, 31, 30, 31, 30,
                  31, 31, 30, 31, 30, 31]
    leap = year // 4
    year_days = leap * 366 + (year - leap) * 365
    year_term = (year_days * 1440 + 2147483648) % 4294967296 - 2147483648
    return year_term + (sum(month_days[:value.month]) + value.day) * 1440 + value.hour * 60 + value.minute


def _serialize(fields: dict) -> str:
    try:
        root = ET.fromstring((BASE / "cbe_schema.xml").read_text(encoding="ascii"))
    except (OSError, ET.ParseError) as exc:
        raise LicenseError(f"Skema CBE tidak dapat dibaca: {exc}") from exc
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
    xml = face._decrypt(raw)
    if "<!DOCTYPE" in xml.upper() or "<!ENTITY" in xml.upper():
        raise LicenseError("DTD/entity tidak termasuk format lisensi CBE.")
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        raise LicenseError(f"XML CBE tidak valid: {exc}") from exc
    if root.tag != "NewDataSet":
        raise LicenseError("Root XML CBE bukan NewDataSet.")
    schema = root.find("{http://www.w3.org/2001/XMLSchema}schema")
    if schema is None or not any(e.attrib.get("name") == TABLE for e in schema.iter()):
        raise LicenseError("Skema bukan lisensi JIBAS CBE Server.")
    rows = root.findall(TABLE)
    if len(rows) > 1:
        raise LicenseError("Diharapkan paling banyak satu baris lisensi CBE.")
    fields = {c.tag: c.text or "" for c in rows[0]} if rows else {}
    return raw, xml, root, fields


def inspect_license(path) -> dict:
    raw, _, _, fields = _load(path)
    text = raw.decode("utf-16") if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else raw.decode("utf-8-sig")
    lines = text.splitlines()
    has_header = bool(lines and IMPORT_MARKER in lines[0])
    return {"path": str(Path(path).resolve()), "format": "JIBAS CBE Server 26.5 / AES-128-CBC / XML DataTable",
            "sha256": hashlib.sha256(raw).hexdigest(), "fields": fields,
            "has_license_row": bool(fields), "status": "license_row" if fields else "empty_cache",
            "file_kind": "import_license" if has_header else "cache_or_payload",
            "client_import_header_present": has_header, "import_header_present": has_header,
            "importer_accepts_headerless": True, "import_header_required": False,
            "product": "cbe"}


def verify_license(path, database_id, system_id, client_id=None, *, for_import=False,
                   now=None, client_count=None) -> dict:
    database_id = face._id(database_id, "Database ID")
    system_id = face._id(system_id, "System ID", system=True)
    inspection = inspect_license(path)
    fields = inspection["fields"]
    checks = []

    def check(name, passed, detail):
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    check("license_row", bool(fields), "Baris lisensi CBE tersedia.")
    if fields:
        check("required_fields", all(k in fields for k in COLUMNS if k != "Model"), "Kolom CBE lengkap.")
        check("database_id", fields.get("DbId") == database_id, f"DbId berkas: {fields.get('DbId', '')}")
        check("system_id", fields.get("Info1") == system_id, f"Info1 berkas: {fields.get('Info1', '')}")
        check("non_trial", fields.get("KlienId", "") not in ("", "TRIAL"), "KlienId terisi dan bukan TRIAL.")
        if client_id:
            check("client_id", fields.get("KlienId") == client_id.strip(), "Client ID sesuai nilai yang diberikan.")
        try:
            expiry = face._datetime(fields["LicenseLimitDate"])
            check("expiry", _legacy_minute(now or datetime.now(JAKARTA)) <= _legacy_minute(expiry),
                  f"LicenseLimitDate: {expiry.isoformat()}")
        except (ValueError, KeyError):
            check("expiry", False, "LicenseLimitDate tidak dapat dibaca.")
        try:
            capacity, sequence = int(fields["MaxClient"]), int(fields["Sequence"])
            check("capacity", 0 <= capacity <= 2147483647, f"MaxClient: {capacity}")
            check("sequence", 0 <= sequence <= 2147483647, f"Sequence: {sequence}")
            if client_count is not None:
                check("client_count", 0 <= client_count <= capacity,
                      f"Koneksi yang diberikan: {client_count}; MaxClient nominal berkas: {capacity}")
        except (ValueError, KeyError):
            check("numeric_fields", False, "MaxClient/Sequence bukan Int32 yang valid.")
    return {"valid": all(c["passed"] for c in checks), "scope": "offline_file_checks",
            "activation_proven": False, "product": "cbe", "checks": checks,
            "file_kind": inspection["file_kind"],
            "client_import_header_present": inspection["client_import_header_present"],
            "importer_accepts_headerless": True,
            "limitations": ["Pemeriksaan offline; bukan konfirmasi aktivasi penerbit.",
                            "Sequence perpanjangan harus dibandingkan dengan lisensi yang terpasang.",
                            "Jumlah koneksi dan jam database tidak dibaca secara otomatis.",
                            "MaxClient adalah nilai nominal berkas; fungsi turunan kapasitas runtime belum dibuktikan pada jalur koneksi.",
                            "Header komentar tidak diwajibkan importer CBE; pemeriksa Python membatasi tabel CBE untuk mencegah salah produk.",
                            "Server runtime dan layanan validasi online tidak dihubungi."]}


def generate_license(*, database_id, system_id, client_id=None, expires, capacity,
                     output_path, client_name="", previous_license_path=None,
                     sequence=None, overwrite=False) -> dict:
    database_id = face._id(database_id, "Database ID")
    system_id = face._id(system_id, "System ID", system=True)
    if not isinstance(capacity, int) or isinstance(capacity, bool) or not 1 <= capacity <= 2147483647:
        raise LicenseError("Kapasitas klien harus antara 1 dan 2147483647.")
    try:
        expiry_date = datetime.strptime(expires, "%Y-%m-%d").date()
    except (ValueError, TypeError) as exc:
        raise LicenseError("Tanggal harus berformat YYYY-MM-DD.") from exc
    created = datetime.now(JAKARTA)
    expiry = datetime.combine(expiry_date, time(23, 59), JAKARTA)
    if expiry_date < created.date():
        raise LicenseError("Tanggal kedaluwarsa sudah lewat.")
    if _legacy_minute(created) > _legacy_minute(expiry):
        raise LicenseError("Tanggal kedaluwarsa tidak valid menurut perhitungan CBE asli; tahun sangat jauh dapat mengalami overflow Int32.")
    client_id = (client_id or "").strip() or None
    renewal = bool(previous_license_path or client_id or sequence is not None)
    previous = {}
    previous_sequence = None
    if previous_license_path:
        previous = inspect_license(previous_license_path)["fields"]
        if not previous or previous.get("KlienId") in (None, "", "TRIAL"):
            raise LicenseError("Lisensi CBE sebelumnya kosong atau TRIAL.")
        if previous.get("DbId") != database_id:
            raise LicenseError("Database ID berbeda dari lisensi sebelumnya.")
        if client_id and previous.get("KlienId") != client_id:
            raise LicenseError("Client ID berbeda dari lisensi sebelumnya.")
        client_id = previous["KlienId"]
        try:
            previous_sequence = int(previous["Sequence"])
        except (ValueError, KeyError) as exc:
            raise LicenseError("Sequence lisensi sebelumnya tidak valid.") from exc
        if sequence is None:
            sequence = previous_sequence + 1
        elif sequence <= previous_sequence:
            raise LicenseError("Sequence perpanjangan harus lebih besar dari sebelumnya.")
    elif client_id and sequence is None:
        raise LicenseError("Pilih lisensi CBE lama agar Sequence perpanjangan dihitung otomatis.")
    if sequence is None:
        sequence = 1
    if not isinstance(sequence, int) or isinstance(sequence, bool) or not 1 <= sequence <= 2147483647:
        raise LicenseError("Sequence harus antara 1 dan 2147483647.")
    client_id = client_id or uuid.uuid4().hex.upper()
    if client_id == "TRIAL" or not client_id.isascii() or not client_id.isprintable():
        raise LicenseError("Client ID harus ASCII tercetak dan bukan TRIAL.")
    fields = {"Versi": "26.5", "KlienId": client_id,
              "Klien": client_name or previous.get("Klien") or database_id,
              "Tanggal": created.date().isoformat(), "Model": "CBE", "Seri": system_id,
              "Size": str(capacity), "Sequence": sequence, "KodeRs": "", "KodeTx": "",
              "DbId": database_id, "LicenseLimit": expires, "LicenseLimitDate": expiry.isoformat(),
              "MaxClient": str(capacity), "Keterangan": "", "Info1": system_id, "Info2": "", "Info3": ""}
    output = Path(output_path)
    raw = IMPORT_HEADER + face._encrypt(_serialize(fields))
    try:
        with output.open("wb" if overwrite else "xb") as stream:
            stream.write(raw)
    except FileExistsError as exc:
        raise LicenseError("Berkas keluaran sudah ada; gunakan overwrite atau nama baru.") from exc
    except OSError as exc:
        raise LicenseError(f"Tidak dapat menyimpan berkas: {exc}") from exc
    return {"path": str(output.resolve()), "client_id": client_id, "sequence": sequence,
            "database_id": database_id, "system_id": system_id, "capacity_unit": "licensed_client",
            "license_max_client": capacity, "runtime_capacity_proven": False,
            "previous_sequence": previous_sequence, "mode": "renewal" if renewal else "new",
            "file_kind": "import_license", "product": "cbe",
            "verification": verify_license(output, database_id, system_id, client_id, for_import=True)}
