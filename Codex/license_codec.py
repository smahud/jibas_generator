"""JIBAS Face Server 16.5 license codec — Codex accuracy revision.

Format facts (proven against FaceServer.exe SHA-256
8a123015b2ee095ceda51ece6d47436e9760c88be8f92fb76ed7c120c923c364):

  cache = base64(AES-128-CBC(ascii(XML), MD5(ascii(password)), ascii(iv))) + CRLF
  import file = '# LISENSI JIBAS SPT FACE' + CRLF + cache
  XML  = DataTable NewDataSet with one JibasSptFaceLicense row, 18 columns.

The importer (method 0x060006CC) reads the first row, compares DbId with the
current Database ID, enforces rising Sequence and equal KlienId for renewals,
and copies DataRows into the encrypted license.enc cache. No signature check
exists in that import path (verified in prior static + original-importer tests,
documented in bukti/).
"""
from __future__ import annotations

import base64
import binascii
from datetime import datetime, time, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import uuid
import xml.etree.ElementTree as ET

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

BASE = Path(__file__).resolve().parent
TABLE = "JibasSptFaceLicense"
IMPORT_MARKER = "LISENSI JIBAS SPT FACE"
IMPORT_HEADER = ("# " + IMPORT_MARKER + "\r\n").encode("ascii")
COLUMNS = (
    "Versi", "KlienId", "Klien", "Tanggal", "Model", "Seri", "Size",
    "Sequence", "KodeRs", "KodeTx", "DbId", "LicenseLimit",
    "LicenseLimitDate", "MaxClient", "Keterangan", "Info1", "Info2", "Info3",
)
JAKARTA = timezone(timedelta(hours=7))
ET.register_namespace("xs", "http://www.w3.org/2001/XMLSchema")
ET.register_namespace("msdata", "urn:schemas-microsoft-com:xml-msdata")


class LicenseError(ValueError):
    pass


def _profile(name: str = "server") -> tuple[bytes, bytes]:
    """Return (aes_key, iv) for a named profile from format_profile.json.

    "server"       : FaceServer.exe init 0x060006C5 (license.enc).
    "client_face"  : FaceFgrClient 16.10 FACE cache pair (proved at runtime:
                     dynamic pre-init 0x06000AF2 fills holders 0x04000375/76).
    "client_fgr"   : FaceFgrClient 16.10 FGR cache pair (dynamic pre-init
                     0x060008BC fills holders 0x04000366/67).
    """
    try:
        profile = json.loads((BASE / "format_profile.json").read_text(encoding="utf-8-sig"))
        if name == "server" and name not in profile.get("profiles", {}):
            return _legacy_profile(profile)
        pair = profile["profiles"][name]
        password = base64.b64decode(pair["password_b64"], validate=True)
        iv = base64.b64decode(pair["iv_b64"], validate=True)
        if len(iv) != 16:
            raise ValueError("IV bukan 16 byte")
        return hashlib.md5(password).digest(), iv
    except (OSError, ValueError, KeyError) as exc:
        raise LicenseError(f"Profil format tidak dapat dibaca: {exc}") from exc


def _legacy_profile(profile: dict) -> tuple[bytes, bytes]:
    """Flat pre-client encoding of format_profile.json (back-compat)."""
    password = base64.b64decode(profile["password_b64"], validate=True)
    iv = base64.b64decode(profile["iv_b64"], validate=True)
    if len(iv) != 16:
        raise ValueError("IV bukan 16 byte")
    return hashlib.md5(password).digest(), iv


def _decrypt(data: bytes, profile: str = "server") -> str:
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


def _parse_xml(xml: str):
    if "<!DOCTYPE" in xml.upper() or "<!ENTITY" in xml.upper():
        raise LicenseError("Deklarasi DTD/entity tidak termasuk format lisensi.")
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        raise LicenseError(f"XML lisensi tidak valid: {exc}") from exc
    if root.tag != "NewDataSet":
        raise LicenseError("Root XML bukan NewDataSet.")
    rows = root.findall(TABLE)
    if not rows and root.find(
            ".//{http://www.w3.org/2001/XMLSchema}element[@name='" + TABLE + "']") is None:
        raise LicenseError("Berkas bukan lisensi Absensi Wajah (tabel JibasSptFaceLicense tidak ditemukan).")
    if len(rows) > 1:
        raise LicenseError("Diharapkan paling banyak satu baris lisensi.")
    fields = {child.tag: child.text or "" for child in rows[0]} if rows else {}
    return root, fields


def _load(path, profile: str = "server"):
    try:
        source = Path(path)
        if not source.is_file():
            raise LicenseError("Sumber harus berkas lisensi biasa.")
        with source.open("rb") as stream:
            raw = stream.read(4 * 1024 * 1024 + 1)
    except OSError as exc:
        raise LicenseError(f"Tidak dapat membaca berkas: {exc}") from exc
    xml = _decrypt(raw, profile=profile)
    root, fields = _parse_xml(xml)
    return raw, xml, root, fields


def inspect_license(path) -> dict:
    raw, _, _, fields = _load(path)
    text = (raw.decode("utf-16") if raw.startswith((b"\xff\xfe", b"\xfe\xff"))
            else raw.decode("utf-8-sig"))
    first_line = text.splitlines()[0] if text.splitlines() else ""
    has_header = IMPORT_MARKER in first_line
    return {
        "path": str(Path(path).resolve()),
        "format": "JIBAS Face Server 16.5 / AES-128-CBC / XML DataTable",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "has_license_row": bool(fields),
        "fields": fields,
        "status": "license_row" if fields else "empty_cache",
        "file_kind": "import_license" if has_header else "cache_or_headerless_payload",
        "client_import_header_present": has_header,
    }


def _id(value, label, system=False):
    value = str(value or "").strip().upper()
    pattern = r"[0-9A-F]{5}" if system else r"[A-Z0-9]{5}"
    if not re.fullmatch(pattern, value):
        kind = "heksadesimal" if system else "huruf/angka"
        raise LicenseError(f"{label} harus 5 karakter {kind}.")
    return value


def _datetime(value: str):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return (parsed.replace(tzinfo=JAKARTA) if parsed.tzinfo is None
            else parsed.astimezone(JAKARTA))


def _legacy_minute(value: datetime) -> int:
    """Original 0x06000667..66B arithmetic, including its month leap rule."""
    year = value.year
    month_days = [31, 29 if year % 4 == 0 else 28, 31, 30, 31, 30,
                  31, 31, 30, 31, 30, 31]
    leap = year // 4
    days = leap * 366 + (year - leap) * 365
    days += sum(month_days[:value.month]) + value.day
    return days * 1440 + value.hour * 60 + value.minute


def verify_license(path, database_id, system_id, client_id=None,
                   *, face_count=None, now=None, for_import=False) -> dict:
    database_id = _id(database_id, "Database ID")
    system_id = _id(system_id, "System ID", system=True)
    inspection = inspect_license(path)
    fields = inspection["fields"]
    checks = []

    def check(name, passed, detail):
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    check("license_row", bool(fields), "Baris lisensi tersedia." if fields else
          "Cache tidak berisi baris lisensi; ini bukan lisensi aktif.")
    if for_import:
        check("client_import_header", inspection["client_import_header_present"],
              "Baris pertama wajib memuat LISENSI JIBAS SPT FACE untuk menu impor client 16.10.")
    if fields:
        check("required_fields", all(name in fields for name in COLUMNS if name != "Model"),
              "17 kolom yang dibaca importer; Model boleh tidak ditulis cache asli.")
        check("database_id", fields.get("DbId") == database_id,
              f"DbId berkas: {fields.get('DbId', '')}")
        check("system_id", fields.get("Info1") == system_id,
              f"Info1 berkas: {fields.get('Info1', '')}")
        check("non_trial", fields.get("KlienId", "") not in ("", "TRIAL"),
              "KlienId harus terisi dan bukan TRIAL.")
        if client_id:
            check("client_id", fields.get("KlienId") == client_id.strip(),
                  f"KlienId berkas: {fields.get('KlienId', '')}")
        try:
            expiry = _datetime(fields["LicenseLimitDate"])
            current = now or datetime.now(JAKARTA)
            # Original compares DateTime components with DB-server local components.
            check("expiry", _legacy_minute(current) <= _legacy_minute(expiry),
                  f"LicenseLimitDate: {expiry.isoformat()}")
        except (ValueError, KeyError):
            check("expiry", False, "LicenseLimitDate tidak dapat dibaca.")
        try:
            capacity = int(fields["MaxClient"])
            sequence = int(fields["Sequence"])
            check("capacity", 0 <= capacity <= 2147483647, f"MaxClient: {capacity}")
            check("sequence", 0 <= sequence <= 2147483647, f"Sequence: {sequence}")
            if face_count is not None:
                check("face_count", 0 <= face_count <= capacity,
                      f"Wajah aktif: {face_count}; kapasitas: {capacity}")
        except (ValueError, KeyError):
            check("numeric_fields", False, "MaxClient/Sequence bukan Int32 yang valid.")
    return {
        "valid": all(item["passed"] for item in checks),
        "scope": "offline_file_checks",
        "activation_proven": False,
        "file_kind": inspection["file_kind"],
        "client_import_header_present": inspection["client_import_header_present"],
        "checks": checks,
        "limitations": [
            "Status server berjalan dan koneksi basis data tidak diperiksa.",
            "Jam pemeriksaan memakai Asia/Jakarta; aplikasi asli mengambil waktu basis data.",
            "Jumlah wajah aktif tidak diperiksa." if face_count is None else
            "Jumlah wajah aktif menggunakan nilai yang diberikan.",
            "Tidak menghubungi layanan validasi online; hasil bukan konfirmasi penerbit.",
            "Urutan perpanjangan perlu dibandingkan dengan lisensi yang sedang terpasang.",
            "Cache tanpa header tidak dapat diimpor lewat menu client 16.10."
            if not inspection["client_import_header_present"] else
            "Header impor sesuai; penerimaan tetap bergantung pada ID dan aturan perpanjangan aplikasi.",
        ],
    }


def _serialize(fields: dict) -> str:
    try:
        root = ET.fromstring((BASE / "schema.xml").read_text(encoding="ascii"))
    except (OSError, ET.ParseError) as exc:
        raise LicenseError(f"Skema lisensi tidak tersedia: {exc}") from exc
    for existing in list(root.findall(TABLE)):
        root.remove(existing)
    row = ET.SubElement(root, TABLE)
    for name in COLUMNS:
        ET.SubElement(row, name).text = str(fields.get(name, ""))
    return ET.tostring(root, encoding="ascii", xml_declaration=False).decode("ascii")


def generate_license(*, database_id, system_id, client_id=None, expires,
                     capacity, output_path, client_name="",
                     previous_license_path=None, sequence=None,
                     overwrite=False) -> dict:
    database_id = _id(database_id, "Database ID")
    system_id = _id(system_id, "System ID", system=True)
    try:
        if not isinstance(capacity, int) or isinstance(capacity, bool):
            raise ValueError("Kapasitas harus bilangan bulat.")
        if not 1 <= capacity <= 2147483647:
            raise ValueError("Kapasitas harus antara 1 dan 2147483647.")
        expiry_date = datetime.strptime(expires, "%Y-%m-%d").date()
        if expiry_date < datetime.now(JAKARTA).date():
            raise LicenseError("Tanggal kedaluwarsa sudah lewat.")
    except (ValueError, TypeError) as exc:
        raise LicenseError("Tanggal harus berformat YYYY-MM-DD.") from exc
    client_id = (client_id or "").strip() or None
    previous = None
    previous_sequence = None
    is_renewal = bool(previous_license_path or client_id or (sequence is not None))
    if previous_license_path:
        previous = inspect_license(previous_license_path)["fields"]
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
    fields = {
        "Versi": "16.5", "KlienId": client_id,
        "Klien": client_name or (previous or {}).get("Klien") or database_id,
        "Tanggal": created.date().isoformat(), "Model": "SPTFACE",
        "Seri": system_id, "Size": str(capacity), "Sequence": sequence,
        "KodeRs": "", "KodeTx": "", "DbId": database_id,
        "LicenseLimit": expires, "LicenseLimitDate": expiry.isoformat(),
        "MaxClient": str(capacity), "Keterangan": "",
        "Info1": system_id, "Info2": "", "Info3": "",
    }
    output = Path(output_path)
    # Client AF9 inspects the FIRST line before decrypting the remaining payload.
    # Server 6CC ignores comment lines; the same import file works for both.
    # Keep _encrypt headerless: cache loaders read the first line as ciphertext.
    encoded = IMPORT_HEADER + _encrypt(_serialize(fields))
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
    verification = verify_license(output, database_id, system_id, client_id, for_import=True)
    return {"path": str(output.resolve()), "client_id": client_id,
            "sequence": sequence, "database_id": database_id,
            "system_id": system_id,
            "file_kind": "import_license",
            "previous_sequence": previous_sequence,
            "mode": "renewal" if is_renewal else "new",
            "verification": verification}


# --------------------------------------------------------------------------
# Client 16.10 face cache (licenseface.enc) support.
#
# Akar masalah (dibuktikan saat runtime, FaceFgrClient.exe SHA-256
# 6f5369df…, salinan sandbox): validator 0x06000AF7 mendekripsi
# %FOLDER-KLIEN%\licenseface.enc dengan profil "client_face" (holder
# 0x04000375/76 yang diisi pre-init dinamis 0x06000AF2), membaca BARIS
# base64 pertama saaja lewat StreamReader.ReadLine + DataTable.ReadXml:
#   rows == 0  -> FALSE -> holder mode global 0x040004C7..D1 tetap pada
#              nilai default cctor ("TRIAL" di semua kolom);
#   rows >= 1  -> kolom baris pertama disalin ke holder -> TRUE.
# Saat mode "TRIAL", handler simpan (0x0600051E / VM -121135179) menolak
# dengan "Tidak dapat menyimpan presensi wajah karena …". Skeleton asli
# selalu kosong, jadi pesan uji coba selalu muncul. Menulis satu baris yang
# disalin dari lisensi efektif Face Server membuka penyimpanan.
# licensefgr.enc (skema "JSL", profil "client_fgr") divalidasi terpisah dan
# sah pada kondisi baris nol; tool ini tidak menyentuhnya.
# --------------------------------------------------------------------------

DEFAULT_CLIENT_DIR = Path(r"C:\Program Files\YIM\JIBAS Face & Fingerprint Client 16.10")
DEFAULT_CLIENT_SOURCE = Path(r"C:\Program Files\YIM\JIBAS Face Server 16.5\license.enc")
CLIENT_FACE_CACHE = "licenseface.enc"
CLIENT_CACHE_EXE = "FaceFgrClient.exe"


def verify_client_fix(fix_result: dict) -> dict:
    """Baca ulang cache klien hasil fix_client_cache dan pastikan layak.

    `ready` hanya True bila baris lisensi terbaca kembali dari cache dan
    memenuhi semua syarat yang dikonsumsi validator klien (baris >= 1).
    """
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


def inspect_client_cache(path) -> dict:
    """Baca cache FACE FaceFgrClient 16.10 dengan profil kliennya."""
    raw, _, _, fields = _load(path, profile="client_face")
    return {
        "path": str(Path(path).resolve()),
        "format": "JIBAS Face & Fingerprint Client 16.10 / licenseface.enc",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "has_license_row": bool(fields),
        "fields": fields,
        "status": "license_row" if fields else "empty_cache",
    }


def _normalize_cache_fields(fields: dict) -> dict:
    """Map a row to the full 18-column schema, filling absent columns with ""."""
    return {name: str(fields.get(name, "")) for name in COLUMNS}


def validate_client_fields(fields: dict) -> None:
    """Terima baris hanya bila kolom yang dikonsumsi validator terisi sewajarnya."""
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
        _datetime(fields["LicenseLimitDate"])
        for name in ("MaxClient", "Sequence"):
            value = int(fields[name])
            if not -2147483648 <= value <= 2147483647:
                raise ValueError(f"{name} di luar rentang Int32")
    except (ValueError, KeyError) as exc:
        raise LicenseError("Baris sumber punya LicenseLimitDate/MaxClient/"
                           "Sequence yang tidak dapat dibaca sebagai DateTime/Int32 aplikasi.") from exc


def resolve_client_row(source_path) -> dict:
    """Muat satu baris lisensi yang layak dipakai cache klien dari .lic/.enc.

    Kolom yang dikonsumsi validator klien: Versi, KlienId (bukan TRIAL),
    Klien, Tanggal, Seri, Size, Sequence, DbId, LicenseLimit,
    LicenseLimitDate (datetime ISO), MaxClient, Info1. Kolom yang tidak ada
    fatal, supaya baris cacat tidak pernah sampai ke disk.
    """
    fields = inspect_license(source_path)["fields"]
    validate_client_fields(fields)
    return {name: fields[name] for name in COLUMNS if name in fields}


def write_client_cache(fields: dict, output_path, overwrite: bool = False) -> dict:
    """Tulis satu baris licenseface.enc untuk FaceFgrClient 16.10.

    Validator klien membaca baris base64 PERTAMA berkas, jadi berkasnya
    tepat base64(AES-128-CBC(...)) + CRLF, sama seperti cache server.
    """
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


def fix_client_cache(client_dir, source, *, overwrite: bool = False,
                     make_backup: bool = True) -> dict:
    """Terapkan perbaikan TRIAL klien 16.10: tulis licenseface.enc dari `source`.

    Perilaku pengamanan:
      - `client_dir` wajib berisi FaceFgrClient.exe (cek penanda).
      - licenseface.enc yang sudah ada tidak pernah luruh: dengan --overwrite
        berkas itu dipindah ke licenseface.enc.bak-<stamp>; tanpa --overwrite
        panggilan gagal.
      - licensefgr.enc dan config.ini tidak pernah disentuh.
      - byte hasil ditulis dibaca ulang dan dibandingkan kolom demi kolom
        sebelum hasil dikembalikan.
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
            stamp = datetime.now(JAKARTA).strftime("%Y%m%dT%H%M%S%f")
            backup_path = target.with_name(f"{target.name}.bak-{stamp}")
            try:
                target.replace(backup_path)
            except OSError as exc:
                raise LicenseError(f"Tidak dapat membuat cadangan: {exc}") from exc
    try:
        result = write_client_cache(fields, target, overwrite=True)
    except LicenseError:
        if backup_path is not None and backup_path.exists():
            backup_path.replace(target)  # kembalikan berkas asli
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
