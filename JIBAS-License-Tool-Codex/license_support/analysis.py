"""Inspect the import envelope without decrypting, changing or trusting it."""
import base64
import binascii
import hashlib
import os
from pathlib import Path
import stat

MAX_BYTES = 4 * 1024 * 1024
FACE_MARKER = b"LISENSI JIBAS SPT FACE"


def inspect_envelope(path: str | Path) -> dict:
    source = Path(path)
    if not source.is_file():
        raise ValueError("Sumber harus berkas biasa yang sudah tersedia.")
    with source.open("rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("Sumber harus berkas biasa.")
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("Berkas melebihi batas diagnostik 4 MiB.")
    # StreamReader.ReadLine uses CR/LF, not Python bytes.splitlines' wider set.
    lines = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n").split(b"\n")
    first = lines[0]
    marker = FACE_MARKER in first
    payload_lines = lines[1:] if marker else lines
    payload = b"".join(line.strip() for line in payload_lines if line.strip() and not line.lstrip().startswith(b"#"))
    decoded = None
    try:
        if payload:
            decoded = base64.b64decode(payload, validate=True)
    except (ValueError, binascii.Error):
        pass
    plausible = decoded is not None and len(decoded) > 0 and len(decoded) % 16 == 0
    return {
        "schema": "jibas-license-envelope-report/v1",
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "face_marker_on_first_line": marker,
        "payload_base64_block_length_plausible": plausible,
        "classification": "face_import_candidate" if marker else "unidentified_or_cache",
        "activation_proven": False,
        "issuer_authenticity_proven": False,
        "explanation": (
            "Marker impor ditemukan; struktur terenkripsi, identitas, dan penerimaan aplikasi belum diperiksa."
            if marker else
            "Marker FACE tidak ditemukan pada baris pertama; ini konsisten dengan error impor, tetapi berkas dapat berupa cache internal."
        ),
        "limits": [
            "Pemeriksaan byte lokal; bukan emulator importer .NET.",
            "Tidak mendekripsi payload atau memvalidasi Database ID/System ID/Client ID.",
            "Panjang Base64/kelipatan blok bukan bukti ciphertext atau lisensi sah.",
        ],
    }
