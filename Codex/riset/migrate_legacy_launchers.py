"""Route the older local Codex directory to the single canonical implementation.

This migration writes entry points only. Existing files are backed up once.
It never changes JIBAS installations or the OpenCode implementation.
"""
from pathlib import Path
import shutil


def migrate(canonical=None):
    canonical = Path(canonical or Path(__file__).resolve().parents[1]).resolve()
    if not (canonical / "app.py").is_file() or not (canonical / "cbe_codec.py").is_file():
        raise ValueError("Direktori Codex terpadu belum lengkap.")
    legacy = canonical.parent / "JIBAS-License-Tool-Codex"
    if not legacy.is_dir():
        return {"legacy_exists": False, "changed": []}
    files = {
        "Jalankan GUI.cmd": '@echo off\r\nsetlocal\r\ncall "%~dp0..\\Codex\\Jalankan GUI.cmd"\r\nexit /b %errorlevel%\r\n',
        "cli.cmd": '@echo off\r\nsetlocal\r\ncall "%~dp0..\\Codex\\cli.cmd" %*\r\nexit /b %errorlevel%\r\n',
        "README.md": "# Direktori lama Codex\n\nAplikasi aktif berada di ../Codex/. Launcher dan entry point Python di sini\n"
                     "meneruskan ke aplikasi yang sama: Absensi Wajah, SchoolPay, CBE Server.\n"
                     "Semua ID manual; tidak ada menu koneksi/deteksi atau input Sequence.\n"
                     "Kode dan bukti lama lainnya disimpan sebagai arsip.\n",
    }
    for script in ("app.py", "cli.py"):
        files[script] = (
            '"""Compatibility entry point; the implementation lives in ../Codex/."""\n'
            'from pathlib import Path\nimport runpy\nimport sys\n\n'
            'def main():\n'
            '    canonical = Path(__file__).resolve().parent.parent / "Codex"\n'
            '    sys.path.insert(0, str(canonical))\n'
            f'    return runpy.run_path(str(canonical / "{script}"), run_name="__main__")\n\n'
            'if __name__ == "__main__":\n    main()\n'
        )
    changed = []
    for name, content in files.items():
        target = legacy / name
        raw = content.encode("utf-8")
        if target.is_file() and target.read_bytes() == raw:
            continue
        backup = target.with_name(target.name + ".legacy-backup")
        if target.is_file() and not backup.exists():
            shutil.copy2(target, backup)
        target.write_bytes(raw)
        changed.append(name)
    return {"legacy_exists": True, "changed": changed, "canonical": str(canonical)}


if __name__ == "__main__":
    import json
    print(json.dumps(migrate(), indent=2))
