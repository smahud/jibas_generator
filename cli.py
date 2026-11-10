"""Command-line interface for the JIBAS Face Server 16.5 license tool (OpenCode rebuild).

Commands:
  default    Detection readout of Database ID and System ID
  inspect    Read the contents of a license file
  verify     Check the license against the installation ID (can be detected automatically)
  generate   Create a new license file or an extension
  tulis-cache-client  Fix the client 16.10 trial notice: write licenseface.enc
                      from the effective Face Server license row.
"""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import sys

import id_detect
import license_codec


def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Kapasitas harus berupa bilangan bulat.") from exc
    if number < 1:
        raise argparse.ArgumentTypeError("Kapasitas harus lebih dari nol.")
    return number


def positive_int32(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Sequence harus berupa bilangan bulat.") from exc
    if not 1 <= number <= 2_147_483_647:
        raise argparse.ArgumentTypeError("Sequence harus antara 1 dan 2147483647.")
    return number


def iso_date(value: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Tanggal harus berformat YYYY-MM-DD.") from exc
    if parsed.isoformat() != value:
        raise argparse.ArgumentTypeError("Tanggal harus berformat YYYY-MM-DD.")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Baca, periksa, buat, dan deteksi ID "
                    "berkas lisensi JIBAS Face Server 16.5."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    detect = commands.add_parser("detect", help="Deteksi Database ID dan System ID asli.")
    detect.add_argument("--no-system", action="store_true", help="Lewati deteksi hardware WMI.")

    inspect = commands.add_parser("inspect", help="Baca isi berkas lisensi.")
    inspect.add_argument("file", type=Path, metavar="FILE")

    verify = commands.add_parser("verify", help="Periksa lisensi terhadap ID instalasi.")
    verify.add_argument("file", type=Path, metavar="FILE")
    verify.add_argument("--database-id", default=None)
    verify.add_argument("--system-id", default=None)
    verify.add_argument("--client-id", default=None)
    verify.add_argument("--auto", action="store_true",
                        help="Deteksi ID asli dari MySQL/WMI bila argumen ID tidak diberikan.")

    generate = commands.add_parser("generate", help="Buat berkas lisensi baru/muridkan perpanjangan.")
    generate.add_argument("--database-id", required=True)
    generate.add_argument("--system-id", required=True)
    generate.add_argument("--client-id", default=None)
    generate.add_argument("--expires", required=True, type=iso_date, metavar="YYYY-MM-DD")
    generate.add_argument("--capacity", required=True, type=positive_int, metavar="N")
    generate.add_argument("--client-name", default="")
    generate.add_argument("--previous-license", type=Path, default=None, metavar="FILE",
                          help="Lisensi sebelumnya untuk perpanjangan.")
    generate.add_argument("--sequence", type=positive_int32, default=None, metavar="N",
                          help="Sequence eksplisit; harus lebih besar dari lisensi sebelumnya.")
    generate.add_argument("--out", required=True, type=Path, metavar="FILE")
    generate.add_argument("--overwrite", action="store_true")

    client = commands.add_parser(
        "tulis-cache-client",
        help="Perbaiki TRIAL FaceFgrClient 16.10: tulis licenseface.enc "
             "dari baris lisensi efektif Face Server.")
    client.add_argument("--dari", type=Path, default=None, metavar="FILE",
                        help="Lisensi efektif (.lic/.enc); bawaan: "
                             "license.enc Face Server 16.5 terpasang.")
    client.add_argument("--tujuan", type=Path, default=None, metavar="DIR",
                        help="Folder FaceFgrClient 16.10; bawaan: folder "
                             "instalasi klien 16.10.")
    client.add_argument("--overwrite", action="store_true",
                        help="Timpa licenseface.enc yang ada (cadangan "
                             "licenseface.enc.bak-<stempel> dibuat otomatis).")
    return parser


def run_detect(args, outcomes: list) -> dict:
    result: dict = {"dbid_detector": "jbssat splang recipe (original 0x06000AC3)"}
    try:
        dbid, info = id_detect.DbIdDetector().detect()
        result["database_id"] = dbid
        result["database_id_detail"] = info
    except id_detect.DetectError as exc:
        result["database_id_error"] = str(exc)
    if not args.no_system:
        try:
            sysid, info = id_detect.SystemIdDetector().detect()
            result["system_id"] = sysid
            result["system_id_detail"] = info
        except id_detect.DetectError as exc:
            result["system_id_error"] = str(exc)
    outcomes.append(result)
    return result


def run_generate(args, outcomes: list) -> dict:
    result = license_codec.generate_license(
        database_id=args.database_id.strip(),
        system_id=args.system_id.strip(),
        client_id=(args.client_id or "").strip() or None,
        expires=args.expires,
        capacity=args.capacity,
        output_path=args.out,
        client_name=args.client_name.strip(),
        previous_license_path=args.previous_license,
        sequence=args.sequence,
        overwrite=args.overwrite,
    )
    outcomes.append(result)
    verification = result.get("verification")
    if isinstance(verification, dict) and verification.get("valid") is False:
        raise SystemExit(1)
    return result


def run_fix_client_cache(args, outcomes: list) -> dict:
    source = args.dari or license_codec.DEFAULT_CLIENT_SOURCE
    client_dir = args.tujuan or license_codec.DEFAULT_CLIENT_DIR
    result = license_codec.fix_client_cache(
        client_dir, source, overwrite=args.overwrite)
    outcomes.append(result)
    verification = license_codec.verify_client_fix(result)
    outcomes.append(verification)
    if verification.get("ready") is not True:
        raise SystemExit(1)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    outcomes = []
    try:
        if args.command == "detect":
            run_detect(args, outcomes)
        elif args.command == "inspect":
            outcomes.append(license_codec.inspect_license(args.file))
        elif args.command == "verify":
            database_id = (args.database_id or "").strip()
            system_id = (args.system_id or "").strip()
            auto_used = False
            if args.auto:
                if not database_id:
                    database_id = id_detect.DbIdDetector().detect()[0]
                    auto_used = True
                if not system_id:
                    system_id = id_detect.SystemIdDetector().detect()[0]
                    auto_used = True
            if not database_id or not system_id:
                raise SystemExit(2)
            verify_result = license_codec.verify_license(
                args.file, database_id, system_id,
                client_id=(args.client_id or "").strip() or None)
            outcomes.append(verify_result)
            if auto_used:
                outcomes.append({"auto_detection": True})
            is_valid = verify_result.get("valid") is True
            print(json.dumps({"ok": is_valid, "results": outcomes},
                             ensure_ascii=False, indent=2, default=str))
            return 0 if is_valid else 1
        else:
            if args.command == "tulis-cache-client":
                run_fix_client_cache(args, outcomes)
            else:
                run_generate(args, outcomes)
        print(json.dumps({"ok": True, "results": outcomes},
                         ensure_ascii=False, indent=2, default=str))
        return 0
    except SystemExit as exc:  # propagated statuses from helpers
        if isinstance(exc.code, str):
            raise
        return 1 if exc.code is None else exc.code
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False),
              file=sys.stderr)
        return 2
