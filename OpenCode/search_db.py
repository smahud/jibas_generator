"""Cari keberadaan Database ID di seluruh basis data JIBAS (mirip util lawas).

Default: mencari lima karakter DbId yang diberikan (contoh V4YNE) di semua
database JIBAS yang dikenal, hanya operasi baca (SELECT). Util ini murni
alat audit, bukan bagian dari pembuatan lisensi.
"""
from __future__ import annotations

import argparse
import sys

KNOWN_DATABASES = [
    "jbsakad", "jbscbe", "jbsclient", "jbsegw", "jbsel", "jbsfina", "jbsjs",
    "jbsletter", "jbsperpus", "jbssat", "jbssdm", "jbssms", "jbstgram",
    "jbsumum", "jbsuser", "jbsvcr",
]


def connect_kwargs() -> dict:
    return {"host": "127.0.0.1", "port": 3434, "user": "root",
            "password": "kebersamaan", "connect_timeout": 5}


def search(database_id: str, databases=None) -> list[dict]:
    import pymysql
    findings = []
    probe = database_id.upper()
    for db in (databases or KNOWN_DATABASES):
        try:
            conn = pymysql.connect(database=db, **connect_kwargs())
        except Exception:
            continue
        try:
            # 1) Isi tabel berisi teks Database ID? (jarang — Database ID asli
            #    bukan data tersimpan; ia dihitung dari payload prosedur splang.
            #    Hasil "Tidak ditemukan" pada tabel adalah perilaku yang benar.)
            with conn.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                tables = [row[0] for row in cursor.fetchall()]
                for table in tables:
                    try:
                        cursor.execute("SELECT * FROM `%s` LIMIT 200" % table)
                        for row in cursor.fetchall():
                            for value in row:
                                if value and probe in str(value).upper():
                                    findings.append({
                                        "database": db, "table": table,
                                        "value": str(value)[:80],
                                    })
                    except Exception:
                        continue
            # 2) Grep literal tubuh prosedur (mis. berkas definisi yang berisi)
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT ROUTINE_NAME, ROUTINE_DEFINITION FROM information_schema.ROUTINES "
                    "WHERE ROUTINE_SCHEMA = %s", (db,))
                for name, body in cursor.fetchall():
                    if body and probe in body.upper():
                        findings.append({
                            "database": db, "table": name,
                            "value": "ROUTINE_DEFINITION mengandung teks ID",
                        })
        finally:
            conn.close()
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Cari teks Database ID di basis data JIBAS.")
    parser.add_argument("id", help="Database ID yang dicari, contoh V4YNE")
    args = parser.parse_args()
    try:
        findings = search(args.id)
    except Exception as exc:
        print("Gagal: %s" % exc, file=sys.stderr)
        return 2
    if findings:
        for item in findings:
            print("%s.%s -> %s" % (item["database"], item["table"], item["value"]))
    else:
        print("Tidak ditemukan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
