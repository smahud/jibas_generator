"""Bounded, read-only diagnostics with privacy-safe reports.

A private temporary copy gives the unchanged codec the same bytes for inspection
and verification. The selected source is only read; no detector or DB is used.
"""
from __future__ import annotations

from datetime import date, datetime
import os
from pathlib import Path
import re
import stat
from tempfile import TemporaryDirectory

import license_codec

MAX_FILE_BYTES = 4 * 1024 * 1024
REDACTED = "[disembunyikan]"
LIMITATIONS = [
    "Hasil ini hanya pemeriksaan berkas lokal, bukan konfirmasi aktivasi penerbit.",
    "Server JIBAS, basis data, dan layanan validasi online tidak dihubungi.",
    "Waktu pemeriksaan menggunakan Asia/Jakarta, bukan waktu basis data.",
    "Jumlah wajah aktif dan urutan perpanjangan terhadap instalasi tidak diperiksa.",
    "Identitas, nama, path, dan teks bebas tidak disertakan dalam laporan.",
]
CHECK_LABELS = {
    "license_row": "Ketersediaan baris lisensi",
    "required_fields": "Kelengkapan kolom",
    "database_id": "Kecocokan Database ID yang diberikan",
    "system_id": "Kecocokan System ID yang diberikan",
    "non_trial": "Status klien pada berkas",
    "client_id": "Kecocokan Client ID yang diberikan",
    "expiry": "Masa berlaku menurut pemeriksaan lokal",
    "capacity": "Format kapasitas",
    "sequence": "Format sequence",
    "numeric_fields": "Format kolom angka",
}
ERROR_MESSAGES = {
    "missing_path": "Pilih berkas yang ingin dibaca terlebih dahulu.",
    "not_found": "Berkas tidak ditemukan. Pilih kembali berkas yang tersedia.",
    "permission": "Berkas tidak dapat dibaca. Periksa izin akses berkas.",
    "not_regular": "Pilih berkas biasa; folder dan perangkat tidak didukung.",
    "too_large": "Ukuran berkas melebihi batas diagnostik 4 MiB.",
    "empty_file": "Berkas kosong. Pilih salinan berkas yang lengkap.",
    "source_changed": "Berkas berubah saat dibaca. Ulangi pemeriksaan.",
    "read_failed": "Berkas tidak dapat dibaca. Periksa lokasi dan izin akses.",
    "format_config": "Profil format lokal tidak dapat dibaca. Periksa kelengkapan repo.",
    "unreadable_format": "Isi berkas tidak dapat dibaca dengan profil format lokal. "
                         "Pastikan berkas lengkap dan jenis berkas sesuai.",
    "unsupported_structure": "Struktur data tidak didukung oleh pemeriksa lokal.",
    "database_id": "Database ID harus berisi 5 huruf atau angka ASCII.",
    "system_id": "System ID harus berisi 5 karakter heksadesimal.",
    "client_id": "Client ID opsional harus berupa teks ASCII tercetak, maksimal 128 karakter.",
    "unexpected": "Pemeriksaan belum dapat diselesaikan. Periksa instalasi "
                  "dan ulangi; detail internal tidak ditampilkan.",
}


class DiagnosticError(ValueError):
    """Stable code and fixed message, with no source data or raw exceptions."""

    def __init__(self, code: str) -> None:
        self.code = code if code in ERROR_MESSAGES else "unexpected"
        super().__init__(ERROR_MESSAGES[self.code])


def _read_source(path: str | Path) -> bytes:
    if not str(path).strip():
        raise DiagnosticError("missing_path")
    try:
        # O_NONBLOCK prevents a FIFO from blocking before fstat rejects it.
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NONBLOCK", 0)
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise DiagnosticError("not_regular")
            if before.st_size > MAX_FILE_BYTES:
                raise DiagnosticError("too_large")
            raw = stream.read(MAX_FILE_BYTES + 1)
            after = os.fstat(stream.fileno())
        if len(raw) > MAX_FILE_BYTES:
            raise DiagnosticError("too_large")
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise DiagnosticError("source_changed")
        if not raw:
            raise DiagnosticError("empty_file")
        return raw
    except FileNotFoundError:
        raise DiagnosticError("not_found") from None
    except PermissionError:
        raise DiagnosticError("permission") from None
    except IsADirectoryError:
        raise DiagnosticError("not_regular") from None
    except OSError:
        raise DiagnosticError("read_failed") from None
    except (ValueError, TypeError) as exc:
        if isinstance(exc, DiagnosticError):
            raise
        raise DiagnosticError("read_failed") from None


def _display_field(name: str, value: str) -> str:
    """Even a known metadata column may contain arbitrary private text."""
    if not value:
        return "(kosong)"
    if name == "Versi" and re.fullmatch(r"[0-9]{1,3}(?:\.[0-9]{1,3}){1,3}", value):
        return value
    if name in ("MaxClient", "Size", "Sequence") and re.fullmatch(r"[0-9]{1,10}", value):
        return value
    try:
        if name in ("Tanggal", "LicenseLimit"):
            return date.fromisoformat(value).isoformat()
        if name == "LicenseLimitDate":
            return datetime.fromisoformat(value).isoformat()
    except ValueError:
        pass
    return REDACTED


def _validate_ids(database_id: str, system_id: str, client_id: str) -> tuple[str, str, str]:
    database_id = database_id.strip().upper()
    system_id = system_id.strip().upper()
    client_id = client_id.strip()
    if not re.fullmatch(r"[A-Z0-9]{5}", database_id):
        raise DiagnosticError("database_id")
    if not re.fullmatch(r"[0-9A-F]{5}", system_id):
        raise DiagnosticError("system_id")
    if client_id and (len(client_id) > 128 or not client_id.isascii() or not client_id.isprintable()):
        raise DiagnosticError("client_id")
    return database_id, system_id, client_id


def inspect_file(path: str | Path) -> dict:
    return _diagnose(path)


def verify_file(path: str | Path, database_id: str, system_id: str, client_id: str = "") -> dict:
    ids = _validate_ids(database_id, system_id, client_id)
    return _diagnose(path, ids)


def _diagnose(path: str | Path, ids: tuple[str, str, str] | None = None) -> dict:
    raw = _read_source(path)
    try:
        with TemporaryDirectory(prefix="jibas-diagnostic-") as directory:
            snapshot = Path(directory) / "input.enc"
            snapshot.write_bytes(raw)
            inspected = license_codec.inspect_license(snapshot)
            verified = license_codec.verify_license(snapshot, *ids) if ids else None
        fields = inspected["fields"]
        checks = [] if verified is None else [
            {"name": item["name"], "passed": item["passed"],
             "detail": CHECK_LABELS.get(item["name"], "Pemeriksaan lokal")}
            for item in verified["checks"]
        ]
        return {
            "status": inspected["status"] if verified is None else
                      ("checks_passed" if verified["valid"] else "checks_failed"),
            "scope": "offline_file_checks",
            "activation_proven": False,
            "format": inspected["format"],
            "sha256": inspected["sha256"],
            "size_bytes": len(raw),
            "has_license_row": inspected["has_license_row"],
            "fields": {name: _display_field(name, fields[name])
                       for name in license_codec.COLUMNS if name in fields},
            "unknown_field_count": len(set(fields) - set(license_codec.COLUMNS)),
            "valid": None if verified is None else verified["valid"],
            "checks": checks,
            "limitations": list(LIMITATIONS),
        }
    except license_codec.LicenseError as exc:
        message = str(exc)
        if message.startswith("Profil format"):
            code = "format_config"
        elif message.startswith("Berkas tidak dapat didekripsi"):
            code = "unreadable_format"
        else:
            code = "unsupported_structure"
        raise DiagnosticError(code) from None
    except OSError:
        raise DiagnosticError("read_failed") from None
    except Exception:
        raise DiagnosticError("unexpected") from None
