"""Run with python -m license_support; all output is local JSON."""
import argparse
import json
from pathlib import Path
import sys

from .analysis import inspect_envelope
from .issuance import prepare_request


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Diagnostik envelope dan penyiapan permintaan lisensi resmi JIBAS.")
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect-envelope")
    inspect.add_argument("file")
    request = commands.add_parser("prepare-request")
    request.add_argument("--database-id", required=True)
    request.add_argument("--system-id", required=True)
    request.add_argument("--client-id")
    request.add_argument("--out", type=Path, help="JSON lokal baru; tidak menimpa berkas yang sudah ada.")
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect-envelope":
            result = inspect_envelope(args.file)
        else:
            result = prepare_request(args.database_id, args.system_id, args.client_id)
            if args.out is not None:
                if args.out.suffix.lower() != ".json":
                    raise ValueError("Gunakan ekstensi .json; keluaran ini bukan file lisensi .lic/.enc.")
                with args.out.open("x", encoding="utf-8", newline="\n") as stream:
                    stream.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({"ok": True, "result": result}, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError) as exc:
        # OS messages can contain private paths. Return a useful class instead.
        message = str(exc) if isinstance(exc, ValueError) else f"Operasi berkas gagal ({type(exc).__name__})."
        print(json.dumps({"ok": False, "error": message}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
