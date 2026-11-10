"""Create a release manifest or copy only reviewable source/evidence files."""
from pathlib import Path
from datetime import date
import hashlib
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]


def release_files():
    for directory, dirs, files in __import__('os').walk(ROOT):
        dirs[:] = sorted(d for d in dirs if d not in {
            '.git', '__pycache__', '.pytest_cache', '.venv', 'mysql_sandbox', 'sandbox'
        } and not d.startswith(('sandbox_', 'verify_')))
        for name in sorted(files):
            if name == 'PUBLISH_RESULT.json' or Path(name).suffix.lower() in {'.exe', '.dll', '.zip', '.pyc'}:
                continue
            yield Path(directory) / name


def manifest():
    rows = []
    for path in release_files():
        if path.name == 'MANIFEST.json':
            continue
        data = path.read_bytes()
        rows.append({'path': path.relative_to(ROOT).as_posix(), 'bytes': len(data),
                     'sha256': hashlib.sha256(data).hexdigest()})
    result = {'release': 'Codex', 'date': date.today().isoformat(),
              'scope': 'source + evidence; MANIFEST.json excluded from its own hashes',
              'excluded': ['compiled executables', 'proprietary DLLs', 'sandbox datadir',
                           'temporary sandbox caches', 'Python caches', 'Git metadata'],
              'files': rows}
    (ROOT / 'MANIFEST.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    result = manifest()
    if len(sys.argv) > 1:
        destination = Path(sys.argv[1])
        destination.mkdir(parents=True, exist_ok=True)
        for path in release_files():
            target = destination / path.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
    print(json.dumps({'release_files': len(result['files']),
                      'bytes': sum(row['bytes'] for row in result['files'])}))
