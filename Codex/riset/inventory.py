"""Read-only inventory/hash of every file below the installed YIM directory."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import sys


def inventory(root):
    rows = []
    for path in sorted(root.rglob('*')):
        if not path.is_file():
            continue
        try:
            digest = hashlib.sha256()
            with path.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(chunk)
            rows.append({'path': str(path.relative_to(root)),
                         'size': path.stat().st_size, 'sha256': digest.hexdigest()})
        except OSError as exc:
            rows.append({'path': str(path.relative_to(root)), 'error': str(exc)})
    return {'root': str(root), 'files': rows,
            'counts_by_directory': dict(Counter(row['path'].split('\\')[0] for row in rows)),
            'scope': 'all files recursively, read-only; hashes do not prove semantic analysis of all dependencies'}


if __name__ == '__main__':
    result = inventory(Path(sys.argv[1]))
    Path(sys.argv[2]).write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'files': len(result['files']), 'counts': result['counts_by_directory']}))
