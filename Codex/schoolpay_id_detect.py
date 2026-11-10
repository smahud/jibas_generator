"""SchoolPay 10.5 IDs, bound to original methods 0x06000824 / 0x06000945.

SchoolPay uses jbsfina routines, with a different recipe from Face's jbssat.
The shared hardware algorithm is reused only after the original SchoolPay
WMI method and CIL confirmed matching byte/hash behavior.
"""
from __future__ import annotations

import re

from id_detect import DetectError, DbIdDetector as _FaceDbIdDetector
from id_detect import SystemIdDetector, _hex_to_ascii, database_password, _safe_database_error

DB_RECIPE = ((2, 2, 9), (7, 3, 21), (10, 6, 12), (1, 6, 32), (9, 6, 45))


class DbIdDetector(_FaceDbIdDetector):
    """Read existing jbsfina OUT values without original bootstrap writes."""

    def __init__(self, host="127.0.0.1", port=3434, user="root", password=None,
                 database="jbsfina"):
        if not re.fullmatch(r"[A-Za-z0-9_]+", database):
            raise DetectError("Nama database harus huruf, angka, atau underscore.")
        super().__init__(host, port, user, password, database)

    def detect(self):
        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s",
                               (self.database,))
                table_count = cursor.fetchone()
                if not table_count or not table_count[0]:
                    raise DetectError("Database SchoolPay tidak mempunyai tabel; original reader tidak membentuk ID.")
            info = self.verify_procedures(conn)
            if info["missing"]:
                raise DetectError("Prosedur splang SchoolPay hilang: " + ", ".join(info["missing"]))
            variables, pieces = [], []
            with conn.cursor() as cursor:
                for proc, index, position in DB_RECIPE:
                    names = ["@uh" + character for character in "abcdefghi"]
                    cursor.execute(f"CALL `{self.database}`.splang{proc:02d}({', '.join(names)})")
                    while cursor.nextset():
                        pass
                    cursor.execute(f"SELECT {', '.join(names)}")
                    row = cursor.fetchone()
                    if not row or row[index] is None:
                        raise DetectError(f"Keluaran splang{proc:02d} {names[index]} kosong.")
                    decoded = _hex_to_ascii(row[index])
                    if len(decoded) <= position:
                        raise DetectError(f"Payload splang{proc:02d} terlalu pendek.")
                    pieces.append(decoded[position])
                    variables.append({"procedure": f"splang{proc:02d}", "variable": names[index],
                                      "position": position, "character": decoded[position]})
        except DetectError:
            raise
        except Exception as exc:
            raise DetectError("Tidak dapat membaca recipe SchoolPay: " +
                              _safe_database_error(exc, database_password(self.password))) from None
        finally:
            conn.close()
        return "".join(pieces).upper(), {
            "method": "SchoolPay jbsfina recipe (original 0x06000824)",
            "pieces": variables, "connection": f"{self.host}:{self.port}/{self.database}"}
