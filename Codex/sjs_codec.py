"""SJS 7.10 offline format; see SharedDocs/products/sjs.md for evidence/limits.

Registration tokens describe database statistics, not a machine binding. A School
ID identifies a remote school and must be supplied or retained from an old file.
"""
from __future__ import annotations

import base64
import binascii
from datetime import datetime, time
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import license_codec as face

LicenseError = face.LicenseError
BASE = Path(__file__).resolve().parent
JAKARTA = face.JAKARTA
TABLE = "JibasJsLicense"
COLUMNS = ("Versi", "SchoolId", "SchoolFullName", "SchoolName", "GroupId", "GroupName",
           "DatabaseId", "MaxAgentConn", "Jenis", "LimitDate", "Sequence", "Services")
IMPORT_MARKER = "LISENSI JIBAS JENDELA SEKOLAH"
IMPORT_HEADER = ("# " + IMPORT_MARKER + "\r\n").encode("ascii")
TOKEN_STATISTICS = ("students", "employees", "departments", "classes", "subjects",
                    "exam_grades", "final_grades", "accounts", "journals",
                    "student_days", "exam_grade_days", "final_grade_days", "journal_days")
LIMITATIONS = [
    "Pemeriksaan dan file lokal; aktivasi/penerimaan layanan Jendela Sekolah belum dibuktikan.",
    "School ID harus berasal dari registrasi sekolah; aplikasi ini tidak mengalokasikan identitas sekolah online.",
    "Registration Token memuat statistik database, tidak memuat Database ID dan tidak menjadi kolom lisensi.",
    "Kesesuaian token dengan database yang diberikan tidak dapat dibuktikan tanpa sumber database.",
    "Group, Jenis, Services dan jumlah koneksi tidak mengonfirmasi hak layanan penerbit.",
    "Jam database, konfigurasi, database dan layanan online tidak dibaca atau diubah.",
    "Python memeriksa expiry pada setiap file; importer asli melewati expiry pada impor pertama.",
]


def inspect_registration_token(registration_token) -> dict:
    token = str(registration_token or "").strip()
    if len(token) > 16384 or not re.fullmatch(r"[0-9]{5}[A-Za-z0-9+/]+={0,2}", token):
        raise LicenseError("Registration Token SJS harus berisi prefiks 5 angka dan payload Base64.")
    seed = int(token[:5]) - 17
    if not 91000 <= seed < 99800:
        raise LicenseError("Prefiks Registration Token tidak sesuai SJS 7.10.")
    try:
        encoded = base64.b64decode(token[5:], validate=True).decode("utf-8")
        key = str(seed)
        plain = "".join(chr(ord(c) ^ ord(key[i % len(key)])) for i, c in enumerate(encoded))
        values = json.loads(plain)
        if (not isinstance(values, list) or len(values) != 15 or
                any(type(v) is not int or not -2147483648 <= v <= 2147483647 for v in values) or
                not 100 <= values[0] < 999 or not 100 <= values[-1] < 999 or
                any(v < 0 for v in values[1:10])):
            raise ValueError("struktur statistik tidak sesuai")
    except (ValueError, UnicodeError, binascii.Error) as exc:
        raise LicenseError(f"Registration Token SJS tidak dapat dibaca: {exc}") from exc
    return {"format": "SJS 7.10 / decimal prefix + Base64 / repeating decimal XOR",
            "valid": True, "sha256": hashlib.sha256(token.encode("ascii")).hexdigest(),
            "statistics": dict(zip(TOKEN_STATISTICS, values[1:-1])),
            "database_id_present": False, "database_binding_proven": False,
            "issuer_authentication_proven": False, "role": "local_registration_statistics"}


def _crypto(data, *, decrypt=False):
    try:
        profile = json.loads((BASE / "sjs_format.json").read_text(encoding="ascii"))
        key = hashlib.md5(base64.b64decode(profile["password_b64"], validate=True)).digest()
        iv = base64.b64decode(profile["iv_b64"], validate=True)
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        if decrypt:
            context = cipher.decryptor()
            padded = context.update(data) + context.finalize()
            unpad = padding.PKCS7(128).unpadder()
            return unpad.update(padded) + unpad.finalize()
        pad = padding.PKCS7(128).padder()
        padded = pad.update(data) + pad.finalize()
        context = cipher.encryptor()
        return context.update(padded) + context.finalize()
    except (OSError, ValueError, KeyError) as exc:
        raise LicenseError(f"Format kriptografi SJS tidak valid: {exc}") from exc


def _serialize(fields):
    root = ET.fromstring((BASE / "sjs_schema.xml").read_text(encoding="ascii"))
    row = ET.SubElement(root, TABLE)
    for name in COLUMNS:
        ET.SubElement(row, name).text = str(fields.get(name, ""))
    return ET.tostring(root, encoding="ascii")


def inspect_license(path) -> dict:
    source = Path(path)
    try:
        if not source.is_file():
            raise LicenseError("Sumber harus berkas lisensi biasa.")
        with source.open("rb") as stream:
            raw = stream.read(4 * 1024 * 1024 + 1)
        if len(raw) > 4 * 1024 * 1024:
            raise LicenseError("Berkas SJS terlalu besar.")
        text = raw.decode("utf-16") if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else raw.decode("utf-8-sig")
        payload = "".join(x.strip() for x in text.splitlines() if x.strip() and not x.strip().startswith("#"))
        ciphertext = base64.b64decode(payload, validate=True)
        xml = _crypto(ciphertext, decrypt=True).decode("ascii")
        if "<!DOCTYPE" in xml.upper() or "<!ENTITY" in xml.upper():
            raise LicenseError("DTD/entity tidak termasuk format SJS.")
        root = ET.fromstring(xml)
    except (OSError, ValueError, UnicodeError, ET.ParseError) as exc:
        raise LicenseError(f"Lisensi SJS tidak dapat dibaca: {exc}") from exc
    schema = root.find("{http://www.w3.org/2001/XMLSchema}schema")
    if root.tag != "NewDataSet" or schema is None or not any(e.attrib.get("name") == TABLE for e in schema.iter()):
        raise LicenseError("Berkas bukan tabel lisensi JIBAS SJS (JibasJsLicense).")
    rows = root.findall(TABLE)
    if len(rows) > 1:
        raise LicenseError("Diharapkan paling banyak satu baris lisensi SJS.")
    fields = {c.tag: c.text or "" for c in rows[0]} if rows else {}
    header = any(x.strip().startswith("#") for x in text.splitlines())
    return {"path": str(source.resolve()), "sha256": hashlib.sha256(raw).hexdigest(),
            "format": "JIBAS SJS 7.10 / AES-128-CBC / XML DataTable", "product": "sjs",
            "fields": fields, "has_license_row": bool(fields),
            "status": "license_row" if fields else "empty_cache",
            "file_kind": "import_license" if header else "cache_or_payload",
            "import_header_present": header, "client_import_header_present": header,
            "importer_accepts_headerless": True, "import_header_required": False}


def verify_license(path, database_id, registration_token=None, client_id=None, *, school_id=None,
                   for_import=False, now=None, client_count=None) -> dict:
    database_id = face._id(database_id, "Database ID")
    inspection = inspect_license(path)
    fields = inspection["fields"]
    checks = []
    def check(name, passed, detail):
        checks.append({"name": name, "passed": bool(passed), "detail": detail})
    check("license_row", bool(fields), "Baris lisensi SJS tersedia.")
    token_info = None
    if registration_token is not None:
        try:
            token_info = inspect_registration_token(registration_token)
            check("registration_token_format", True, "Statistik token SJS dapat dibaca; bukan bukti binding database.")
        except LicenseError as exc:
            check("registration_token_format", False, str(exc))
    if fields:
        check("required_fields", all(k in fields for k in COLUMNS), "Kolom SJS lengkap.")
        check("database_id", fields.get("DatabaseId") == database_id, "DatabaseId sesuai input.")
        expected_school = school_id or client_id
        check("school_id_present", bool(fields.get("SchoolId")), "SchoolId tersedia; alokasi penerbit tidak diverifikasi.")
        if expected_school:
            check("school_id", fields.get("SchoolId") == expected_school.strip(), "SchoolId sesuai input.")
        try:
            expiry = face._datetime(fields["LimitDate"])
            check("expiry", face._datetime((now or datetime.now(JAKARTA)).isoformat()) <= expiry, f"LimitDate: {expiry.isoformat()}")
        except (ValueError, KeyError):
            check("expiry", False, "LimitDate tidak dapat dibaca.")
        try:
            capacity, sequence = int(fields["MaxAgentConn"]), int(fields["Sequence"])
            check("capacity", 1 <= capacity <= 2147483647, f"MaxAgentConn: {capacity}")
            check("sequence", 1 <= sequence <= 2147483647, f"Sequence: {sequence}")
            if client_count is not None:
                check("client_count", 0 <= client_count <= capacity, "Jumlah koneksi sesuai kapasitas nominal.")
            services = json.loads(fields["Services"])
            check("services", isinstance(services, list) and all(isinstance(v, list) and all(isinstance(s, str) for s in v) for v in services), "Services berupa JSON daftar string bertingkat.")
        except (ValueError, KeyError):
            check("numeric_or_services_fields", False, "MaxAgentConn, Sequence, atau Services tidak valid.")
    return {"valid": all(c["passed"] for c in checks), "scope": "offline_file_checks", "product": "sjs",
            "activation_proven": False, "checks": checks, "registration_token": token_info,
            "file_kind": inspection["file_kind"], "importer_accepts_headerless": True,
            "client_import_header_present": inspection["client_import_header_present"],
            "limitations": list(LIMITATIONS)}


def generate_license(*, database_id, registration_token, expires, capacity, output_path,
                     school_id=None, client_id=None, client_name="", previous_license_path=None,
                     sequence=None, overwrite=False, group_id=None, group_name=None,
                     school_short_name=None, services=None, jenis=None) -> dict:
    database_id = face._id(database_id, "Database ID")
    token_info = inspect_registration_token(registration_token)
    if type(capacity) is not int or not 1 <= capacity <= 2147483647:
        raise LicenseError("Max Agent Connection harus antara 1 dan 2147483647.")
    try:
        expiry_date = datetime.strptime(expires, "%Y-%m-%d").date()
    except (ValueError, TypeError) as exc:
        raise LicenseError("Tanggal harus berformat YYYY-MM-DD.") from exc
    if expiry_date < datetime.now(JAKARTA).date():
        raise LicenseError("Tanggal kedaluwarsa sudah lewat.")
    if school_id and client_id and school_id != client_id:
        raise LicenseError("School ID dan Client ID alias berbeda.")
    school_id = str(school_id or client_id or "").strip()
    previous = {}
    previous_sequence = None
    if previous_license_path:
        previous = inspect_license(previous_license_path)["fields"]
        if not previous or not previous.get("SchoolId"):
            raise LicenseError("Lisensi SJS sebelumnya kosong atau SchoolId tidak tersedia.")
        if previous.get("DatabaseId") != database_id:
            raise LicenseError("Database ID berbeda dari lisensi sebelumnya.")
        if school_id and previous["SchoolId"] != school_id:
            raise LicenseError("School ID berbeda dari lisensi sebelumnya.")
        school_id = previous["SchoolId"]
        try:
            previous_sequence = int(previous["Sequence"])
        except (ValueError, KeyError) as exc:
            raise LicenseError("Sequence lama tidak valid.") from exc
        sequence = previous_sequence + 1 if sequence is None else sequence
        if type(sequence) is not int or sequence <= previous_sequence:
            raise LicenseError("Sequence perpanjangan harus meningkat.")
    elif sequence is not None and sequence != 1:
        raise LicenseError("Lisensi SJS lama diperlukan untuk perpanjangan.")
    if not school_id or len(school_id) > 255 or not school_id.isprintable():
        raise LicenseError("School ID dari registrasi sekolah wajib diisi; ID sekolah online tidak dibuat otomatis.")
    sequence = 1 if sequence is None else sequence
    if type(sequence) is not int or not 1 <= sequence <= 2147483647:
        raise LicenseError("Sequence di luar rentang Int32.")
    if services is None:
        services = previous.get("Services", "[]")
    if not isinstance(services, str):
        services = json.dumps(services, ensure_ascii=True, separators=(",", ":"))
    try:
        parsed_services = json.loads(services)
        if not isinstance(parsed_services, list) or any(not isinstance(v, list) or any(not isinstance(s, str) for s in v) for v in parsed_services):
            raise ValueError("diperlukan daftar bertingkat berisi string")
    except (ValueError, TypeError) as exc:
        raise LicenseError(f"Services SJS tidak valid: {exc}") from exc
    name = client_name or previous.get("SchoolFullName", "")
    fields = {"Versi": previous.get("Versi", "7.10"), "SchoolId": school_id,
              "SchoolFullName": name, "SchoolName": school_short_name if school_short_name is not None else previous.get("SchoolName", name),
              "GroupId": group_id if group_id is not None else previous.get("GroupId", ""),
              "GroupName": group_name if group_name is not None else previous.get("GroupName", ""),
              "DatabaseId": database_id, "MaxAgentConn": str(capacity),
              "Jenis": jenis if jenis is not None else previous.get("Jenis", ""),
              "LimitDate": datetime.combine(expiry_date, time(23, 59, 59), JAKARTA).isoformat(),
              "Sequence": str(sequence), "Services": services}
    output = Path(output_path)
    raw = IMPORT_HEADER + base64.b64encode(_crypto(_serialize(fields))) + b"\r\n"
    try:
        with output.open("wb" if overwrite else "xb") as stream:
            stream.write(raw)
    except OSError as exc:
        raise LicenseError(f"Tidak dapat menyimpan lisensi SJS: {exc}") from exc
    return {"path": str(output.resolve()), "product": "sjs", "database_id": database_id,
            "school_id": school_id, "client_id": school_id, "client_id_role": "school_id",
            "sequence": sequence, "previous_sequence": previous_sequence,
            "mode": "renewal" if previous else "new", "file_kind": "import_license",
            "capacity_unit": "agent_connection", "license_max_client": capacity,
            "registration_token": token_info, "activation_proven": False,
            "runtime_capacity_proven": False,
            "verification": verify_license(output, database_id, registration_token, school_id=school_id, for_import=True)}
