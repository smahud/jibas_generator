"""The proven Database ID recipe of JIBAS Face Server 16.5 (original 0x06000AC3).

Database ID bukan salinan konfigurasi: aplikasi membentuknya saat start dari
payload hex yang disimpan di prosedur splang pada skema jbssat:

    DbId = UPPER( hex_decode(@uhh)[14] + hex_decode(@uhf)[5] + hex_decode(@uhc)[25]
                  + hex_decode(@uhe)[37] + hex_decode(@uhb)[47] )

dengan @uhb..@uhi adalah sembilan parameter OUT (@uha..@uhi, indeks 0..8) yang
diisi tiap prosedur splangNN saat di-CALL. Proven by running the ORIGINAL
method 0x06000AC3 against the live installation on this host (see bukti/):
  - kondisi db normal   -> V4YNE
  - kondisi db diubah   -> WRK9T
  - keadaan normal betul -> kembali V4YNE
Both values were reproduced offline by the same formula (DbIdDetector in
id_detect.py matches the original method in all states).
"""
from __future__ import annotations

# (prosedur splangNN, indeks parameter OUT 0..8, posisi karakter pada payload
#  ASCII hasil hex-decode)
RECIPE: tuple[tuple[int, int, int], ...] = (
    (4, 7, 14),   # splang04 @uhh[14]
    (2, 5, 5),    # splang02 @uhf[5]
    (9, 2, 25),   # splang09 @uhc[25]
    (11, 4, 37),  # splang11 @uhe[37]
    (1, 1, 47),   # splang01 @uhb[47]
)


def variable_name(index: int) -> str:
    return "@uh" + "abcdefghi"[index]


def replay(decoded_payloads: dict[tuple[int, int], str]) -> str:
    """Replay the formula from ASCII payloads keyed by (procedure, out_index)."""
    try:
        pieces = [
            decoded_payloads[(proc, out)][position]
            for proc, out, position in RECIPE
        ]
    except KeyError as exc:
        raise ValueError(f"Payload tidak lengkap: {exc}") from exc
    except IndexError as exc:
        raise ValueError("Posisi karakter pada resep melebihi panjang payload.") from exc
    return "".join(pieces).upper()
