"""Letter Store 7.0 JLS codec, verified against the original importer.

Artifact SHA256 1bdf678980b4ad985838a1b9ce2233550b3e00f49cd578b481dd01c5e5690915.
The importer checks Versi 2.0 and Info3 against its current Database ID.
This product has one registration row and no expiry/capacity/renewal sequence.
"""
from __future__ import annotations

import base64
import binascii
from datetime import datetime
import hashlib
from pathlib import Path
import uuid
import xml.etree.ElementTree as ET

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

import license_codec as face

LicenseError = face.LicenseError
JAKARTA = face.JAKARTA
TABLE = "JLS"
COLUMNS = ("Versi", "Klien", "Tanggal", "Seri", "KodeRs", "KodeTx",
           "Keterangan", "Info1", "Info2", "Info3")
IMPORT_MARKER = "LISENSI JIBAS LETTER STORE"
IMPORT_HEADER = ("# " + IMPORT_MARKER + "\r\n").encode("ascii")
# Recovered by original initialization method 0x06000911, not inferred from Face.
_KEY = hashlib.md5(b"3477K3b3rS4mA4N").digest()
_IV = b"YaRAhM4nY4R4h1M#"
_MAX_BYTES = 4 * 1024 * 1024
_XS = "http://www.w3.org/2001/XMLSchema"
_MS = "urn:schemas-microsoft-com:xml-msdata"


def _serialize(fields: dict | None = None) -> str:
    root = ET.Element("NewDataSet")
    schema = ET.SubElement(root, f"{{{_XS}}}schema", {"id": "NewDataSet"})
    dataset = ET.SubElement(schema, f"{{{_XS}}}element", {
        "name": "NewDataSet", f"{{{_MS}}}IsDataSet": "true",
        f"{{{_MS}}}MainDataTable": TABLE, f"{{{_MS}}}UseCurrentLocale": "true"})
    complex_type = ET.SubElement(dataset, f"{{{_XS}}}complexType")
    choice = ET.SubElement(complex_type, f"{{{_XS}}}choice", {"minOccurs": "0", "maxOccurs": "unbounded"})
    table = ET.SubElement(choice, f"{{{_XS}}}element", {"name": TABLE})
    row_type = ET.SubElement(table, f"{{{_XS}}}complexType")
    sequence = ET.SubElement(row_type, f"{{{_XS}}}sequence")
    for column in COLUMNS:
        ET.SubElement(sequence, f"{{{_XS}}}element", {"name": column, "type": "xs:string", "minOccurs": "0"})
    if fields is not None:
        row = ET.SubElement(root, TABLE)
        for column in COLUMNS:
            ET.SubElement(row, column).text = str(fields.get(column, ""))
    return ET.tostring(root, encoding="ascii").decode("ascii")


def _encrypt(xml: str) -> bytes:
    padder = padding.PKCS7(128).padder()
    padded = padder.update(xml.encode("ascii")) + padder.finalize()
    encryptor = Cipher(algorithms.AES(_KEY), modes.CBC(_IV)).encryptor()
    return base64.b64encode(encryptor.update(padded) + encryptor.finalize()) + b"\r\n"


def _decrypt(raw: bytes) -> str:
    if len(raw) > _MAX_BYTES:
        raise LicenseError("Berkas Letter Store terlalu besar.")
    try:
        text = raw.decode("utf-16") if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else raw.decode("utf-8-sig")
        payload = "".join(line.strip() for line in text.splitlines()
                          if line.strip() and not line.strip().startswith("#"))
        encrypted = base64.b64decode(payload, validate=True)
        if not encrypted or len(encrypted) % 16:
            raise ValueError("panjang ciphertext tidak valid")
        decryptor = Cipher(algorithms.AES(_KEY), modes.CBC(_IV)).decryptor()
        padded = decryptor.update(encrypted) + decryptor.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        return (unpadder.update(padded) + unpadder.finalize()).decode("ascii")
    except (ValueError, UnicodeError, binascii.Error) as exc:
        raise LicenseError(f"Berkas Letter Store tidak dapat didekripsi: {exc}") from exc


def _load(path):
    source = Path(path)
    try:
        if not source.is_file():
            raise LicenseError("Sumber harus berkas lisensi biasa.")
        with source.open("rb") as stream:
            raw = stream.read(_MAX_BYTES + 1)
    except OSError as exc:
        raise LicenseError(f"Tidak dapat membaca berkas: {exc}") from exc
    xml = _decrypt(raw)
    if "<!DOCTYPE" in xml.upper() or "<!ENTITY" in xml.upper():
        raise LicenseError("DTD/entity tidak termasuk format lisensi Letter Store.")
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        raise LicenseError(f"XML Letter Store tidak valid: {exc}") from exc
    if root.tag != "NewDataSet":
        raise LicenseError("Root XML Letter Store bukan NewDataSet.")
    schema = root.find(f"{{{_XS}}}schema")
    if schema is None or not any(e.attrib.get("name") == TABLE for e in schema.iter()):
        raise LicenseError("Skema bukan lisensi JIBAS Letter Store (JLS).")
    rows = root.findall(TABLE)
    if len(rows) > 1:
        raise LicenseError("Letter Store hanya menerima satu registrasi lisensi.")
    fields = {element.tag: element.text or "" for element in rows[0]} if rows else {}
    return raw, xml, root, fields


def inspect_license(path) -> dict:
    raw, _, _, fields = _load(path)
    text = raw.decode("utf-16") if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else raw.decode("utf-8-sig")
    has_header = bool(text.splitlines() and text.splitlines()[0].strip().startswith("#"))
    return {"path": str(Path(path).resolve()), "product": "letterstore",
            "format": "JIBAS Letter Store 7.0 / JLS 2.0 / AES-128-CBC / XML DataTable",
            "sha256": hashlib.sha256(raw).hexdigest(), "fields": fields,
            "database_id": fields.get("Info3", ""), "has_license_row": bool(fields),
            "status": "license_row" if fields else "empty_cache",
            "file_kind": "import_license" if has_header else "cache_or_payload",
            "import_header_present": has_header, "client_import_header_present": has_header,
            "import_header_required": False, "importer_accepts_headerless": True}


def verify_license(path, database_id, *, for_import=False) -> dict:
    database_id = face._id(database_id, "Database ID")
    inspection = inspect_license(path)
    fields = inspection["fields"]
    checks = [{"name": "license_row", "passed": bool(fields), "detail": "Satu baris registrasi JLS tersedia."}]
    if fields:
        checks.extend([
            {"name": "required_fields", "passed": all(column in fields for column in COLUMNS),
             "detail": "Sepuluh kolom JLS lengkap."},
            {"name": "version", "passed": fields.get("Versi") == "2.0", "detail": "Versi harus 2.0."},
            {"name": "database_id", "passed": fields.get("Info3") == database_id,
             "detail": f"Info3 berkas: {fields.get('Info3', '')}"},
        ])
    return {"valid": all(check["passed"] for check in checks), "product": "letterstore",
            "scope": "offline_file_checks", "activation_proven": False, "checks": checks,
            "file_kind": inspection["file_kind"], "import_header_required": False,
            "client_import_header_present": inspection["client_import_header_present"],
            "importer_accepts_headerless": True,
            "limitations": ["Pemeriksaan offline; Database ID aktif tidak dibaca dan layanan penerbit tidak dihubungi.",
                            "Importer asli menolak registrasi tambahan ketika tabel lisensi sudah berisi baris.",
                            "Tidak ada tanggal kedaluwarsa, kapasitas, System ID, Client ID, atau Sequence pada skema produk ini."]}


def generate_license(*, database_id, output_path, client_name="", overwrite=False) -> dict:
    database_id = face._id(database_id, "Database ID")
    if not isinstance(client_name, str):
        raise LicenseError("Nama klien harus berupa teks.")
    fields = {column: "" for column in COLUMNS}
    fields.update({"Versi": "2.0", "Klien": client_name.strip(),
                   "Tanggal": datetime.now(JAKARTA).isoformat(timespec="seconds"),
                   "Seri": uuid.uuid4().hex.upper(), "Info3": database_id})
    raw = IMPORT_HEADER + _encrypt(_serialize(fields))
    output = Path(output_path)
    if not str(output_path).strip():
        raise LicenseError("Nama berkas keluaran wajib diisi.")
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("wb" if overwrite else "xb") as stream:
            stream.write(raw)
    except FileExistsError as exc:
        raise LicenseError("Berkas keluaran sudah ada; gunakan overwrite atau nama baru.") from exc
    except OSError as exc:
        raise LicenseError(f"Tidak dapat menyimpan berkas: {exc}") from exc
    return {"path": str(output.resolve()), "database_id": database_id, "product": "letterstore",
            "mode": "new", "file_kind": "import_license",
            "verification": verify_license(output, database_id, for_import=True)}
