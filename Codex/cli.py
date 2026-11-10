"""Manual-ID CLI for the FACE, SchoolPay and CBE license generators."""
from __future__ import annotations

import argparse
from datetime import date
import importlib
import json
from pathlib import Path
import sys

PRODUCTS = {"face": "license_codec", "schoolpay": "schoolpay_codec", "cbe": "cbe_codec"}


def product_codec(product="face"):
    return importlib.import_module(PRODUCTS[product])


def positive_int(value):
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Kapasitas harus berupa bilangan bulat.") from exc
    if not 1 <= number <= 2147483647:
        raise argparse.ArgumentTypeError("Kapasitas harus antara 1 dan 2147483647.")
    return number


def iso_date(value):
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Tanggal harus berformat YYYY-MM-DD.") from exc
    if parsed.isoformat() != value:
        raise argparse.ArgumentTypeError("Tanggal harus berformat YYYY-MM-DD.")
    return value


def build_parser():
    parser = argparse.ArgumentParser(description="Lisensi Absensi Wajah, SchoolPay dan CBE Server; ID diisi manual.")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("inspect", "verify", "generate"):
        child = commands.add_parser(command)
        child.add_argument("--product", choices=tuple(PRODUCTS), default="face",
                           help="face (bawaan), schoolpay, atau cbe.")
        if command in ("inspect", "verify"):
            child.add_argument("file", type=Path, metavar="FILE")
        if command in ("verify", "generate"):
            child.add_argument("--database-id", required=True)
            child.add_argument("--system-id", required=True)
            child.add_argument("--client-id", default=None)
        if command == "verify":
            child.add_argument("--for-import", action="store_true",
                               help="Periksa syarat file impor produk selain pemeriksaan offline.")
        if command == "generate":
            child.add_argument("--expires", required=True, type=iso_date, metavar="YYYY-MM-DD")
            child.add_argument("--capacity", required=True, type=positive_int,
                               help="Wajah (face), vendor (schoolpay), koneksi klien (cbe).")
            child.add_argument("--client-name", default="")
            child.add_argument("--previous-license", type=Path, default=None,
                               help="File lama untuk perpanjangan; Sequence dihitung otomatis.")
            child.add_argument("--out", required=True, type=Path, metavar="FILE")
            child.add_argument("--overwrite", action="store_true")

    cache = commands.add_parser("tulis-cache-client", help="Utilitas cache FACE historis dengan backup.")
    cache.add_argument("--dari", type=Path, default=None, metavar="FILE")
    cache.add_argument("--tujuan", type=Path, default=None, metavar="DIR")
    cache.add_argument("--overwrite", action="store_true")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    outcomes = []
    try:
        if args.command == "tulis-cache-client":
            codec = product_codec("face")
            result = codec.fix_client_cache(args.tujuan or codec.DEFAULT_CLIENT_DIR,
                args.dari or codec.DEFAULT_CLIENT_SOURCE, overwrite=args.overwrite)
            outcomes.append(result)
            verification = codec.verify_client_fix(result)
            outcomes.append(verification)
            ok = verification.get("ready") is True
        else:
            codec = product_codec(args.product)
            if args.command == "inspect":
                result = codec.inspect_license(args.file)
                ok = True
            elif args.command == "verify":
                result = codec.verify_license(args.file, args.database_id.strip(), args.system_id.strip(),
                    client_id=(args.client_id or "").strip() or None, for_import=args.for_import)
                ok = result.get("valid") is True
            else:
                client_id = (args.client_id or "").strip() or None
                if client_id and not args.previous_license:
                    raise ValueError("Untuk perpanjangan, pilih file lisensi lama agar Sequence dihitung otomatis.")
                result = codec.generate_license(database_id=args.database_id.strip(),
                    system_id=args.system_id.strip(), client_id=client_id, expires=args.expires,
                    capacity=args.capacity, output_path=args.out, client_name=args.client_name.strip(),
                    previous_license_path=args.previous_license, sequence=None, overwrite=args.overwrite)
                ok = result.get("verification", {}).get("valid") is True
            outcomes.append(result)
        print(json.dumps({"ok": ok, "results": outcomes}, ensure_ascii=False, indent=2, default=str))
        return 0 if ok else 1
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
