"""Prepare an offline request. No verified issuer API is configured."""
from .validation import validate_ids

ORDER_URL = "https://jibas.id/content/order/order.php"


def prepare_request(database_id: str, system_id: str, client_id: str | None = None) -> dict:
    ids = validate_ids(database_id, system_id, client_id)
    return {
        "schema": "jibas-license-support-request/v1",
        "product": "JIBAS Presensi Wajah",
        "kind": "renewal" if client_id is not None else "new",
        **ids,
        "official_order_url": ORDER_URL,
        "status": "prepared_locally",
        "submitted": False,
        "license_issued": False,
        "activation_proven": False,
        "next_step": "Salin ID ke formulir resmi. JSON ini catatan lokal, bukan file lisensi atau format unggah resmi.",
    }
