"""Build the single-file Windows x64 GUI and record artifact identity."""
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
NAME = 'JIBAS-Generator-Codex.exe'


def main():
    if sys.platform != 'win32' or sys.maxsize <= 2**32:
        raise SystemExit('Build ini memerlukan Python Windows 64-bit.')
    evidence = ROOT / 'bukti' / 'standalone'
    evidence.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='jibas-standalone-build-'))
    args = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
            '--distpath', str(ROOT), '--workpath', str(work),
            str(ROOT / 'JIBAS-Generator-Codex.spec')]
    print('Building ' + NAME, flush=True)
    with (evidence / 'build.log').open('w', encoding='utf-8') as log:
        completed = subprocess.run(args, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    if completed.returncode:
        print((evidence / 'build.log').read_text(encoding='utf-8')[-6000:])
        return completed.returncode
    exe = ROOT / NAME
    manifest = {'file': NAME, 'bytes': exe.stat().st_size,
        'sha256': hashlib.sha256(exe.read_bytes()).hexdigest(),
        'built_utc': datetime.now(timezone.utc).isoformat(), 'architecture': 'Windows x64',
        'onefile': True, 'console': False, 'python': platform.python_version(),
        'packages': {name: version(name) for name in
                     ('pyinstaller', 'pyinstaller-hooks-contrib', 'cryptography')},
        'resources': ['schema.xml', 'schoolpay_schema.xml', 'cbe_schema.xml', 'format_profile.json'],
        'source_hashes': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in
            ('app.py', 'batch_license.py', 'license_codec.py', 'schoolpay_codec.py', 'cbe_codec.py',
             'build_tools/standalone_entry.py', 'build_tools/frozen_smoke.py', 'JIBAS-Generator-Codex.spec')},
    }
    (evidence / 'build_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps({'path': str(exe), 'bytes': manifest['bytes'], 'sha256': manifest['sha256']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
