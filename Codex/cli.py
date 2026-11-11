"""Manual-ID CLI for the FACE, SchoolPay and CBE license generators."""
from __future__ import annotations

import argparse
from datetime import date
import importlib
import json
from pathlib import Path
import sys

from product_catalog import PRODUCTS as PRODUCT_LIST, PRODUCT_BY_KEY
from product_actions import generate_with_backend, verify_with_backend

PRODUCTS = {item.key: item.codec_module for item in PRODUCT_LIST}


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


def check_product_flags(args):
    """Do not silently discard restrictions that a product cannot encode."""
    product = PRODUCT_BY_KEY[args.product]
    allowed = set(product.input_keys)
    if product.supports_renewal:
        allowed.add('previous_license')
    for key in ('database_id', 'system_id', 'client_id', 'scanner_serial', 'license_scope',
                'registration_token', 'school_id', 'expires', 'capacity', 'previous_license'):
        value = getattr(args, key, None)
        if value not in (None, '') and key not in allowed:
            flag = '--serial' if key == 'scanner_serial' else '--' + key.replace('_', '-')
            raise ValueError(f'{product.label} tidak menggunakan {flag}.')


def build_parser():
    parser = argparse.ArgumentParser(description="Generator enam produk JIBAS; identitas diisi manual sesuai produk.")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("inspect", "verify", "generate"):
        child = commands.add_parser(command)
        child.add_argument("--product", choices=tuple(PRODUCTS), default="face",
                           help="Produk sesuai tab aplikasi; face adalah bawaan.")
        if command in ("inspect", "verify"):
            child.add_argument("file", type=Path, metavar="FILE")
        if command in ("verify", "generate"):
            child.add_argument("--database-id", default="")
            child.add_argument("--system-id", default="")
            child.add_argument("--client-id", default=None)
            child.add_argument("--serial", dest="scanner_serial", default="", help="Nomor seri scanner Fingerprint.")
            child.add_argument("--license-scope", choices=("both", "manager", "client"), default=None)
            child.add_argument("--registration-token", default="", help="Token registrasi SJS asli.")
            child.add_argument("--school-id", default="", help="School ID SJS asli; bukan System ID atau Client ID bersama.")
        if command == "verify":
            child.add_argument("--for-import", action="store_true",
                               help="Periksa syarat file impor produk selain pemeriksaan offline.")
        if command == "generate":
            child.add_argument("--expires", default=None, type=iso_date, metavar="YYYY-MM-DD")
            child.add_argument("--capacity", default=None, type=positive_int,
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
            check_product_flags(args)
            codec = product_codec(args.product)
            if args.command == "inspect":
                result = codec.inspect_license(args.file)
                ok = True
            elif args.command == "verify":
                result = verify_with_backend(codec, PRODUCT_BY_KEY[args.product], args.file,
                    vars(args), for_import=args.for_import)
                ok = result.get("valid") is True
            else:
                result = generate_with_backend(codec, PRODUCT_BY_KEY[args.product],
                    vars(args), args.out, overwrite=args.overwrite)
                ok = result.get("verification", {}).get("valid") is True
            outcomes.append(result)
        print(json.dumps({"ok": ok, "results": outcomes}, ensure_ascii=False, indent=2, default=str))
        return 0 if ok else 1
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
