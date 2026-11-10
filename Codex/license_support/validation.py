"""Local input checks, not an implementation of issuer allocation rules."""
import re


def validate_ids(database_id: str, system_id: str, client_id: str | None = None) -> dict:
    # Match the five-character IDs observed in these two builds. Keep the user
    # supplied case explicit; do not silently change a request's identity.
    for label, value in (("Database ID", database_id), ("System ID", system_id)):
        if not re.fullmatch(r"[A-Z0-9]{5}", value):
            raise ValueError(f"{label} harus 5 huruf ASCII kapital/angka dari aplikasi tujuan.")
    if client_id is not None:
        # Client ID is opaque. In particular, the historic tool's UUID choice
        # is not proof that the vendor allocates UUIDs.
        if not client_id or len(client_id) > 256 or any(not c.isprintable() for c in client_id):
            raise ValueError("Client ID harus teks tercetak 1–256 karakter; salin dari lisensi resmi.")
        if client_id != client_id.strip():
            raise ValueError("Client ID mengandung spasi di awal/akhir; periksa kembali sumbernya.")
    return {"database_id": database_id, "system_id": system_id, "client_id": client_id}
