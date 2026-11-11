"""Check the exact one-file executable outside its source/build directory."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = ROOT / 'JIBAS-Generator-Codex.exe'
    isolated = Path(tempfile.mkdtemp(prefix='jibas-standalone-only-'))
    executable = isolated / source.name
    shutil.copy2(source, executable)
    initial = sorted(p.name for p in isolated.iterdir())
    assert initial == [source.name]
    env = {key: value for key, value in os.environ.items()
           if not key.upper().startswith('PYTHON') and key.upper() not in
           {'VIRTUAL_ENV', 'TCL_LIBRARY', 'TK_LIBRARY'}}
    windows = Path(env.get('SystemRoot', r'C:\Windows'))
    env['PATH'] = str(windows / 'System32') + os.pathsep + str(windows)
    env['PYTHONNOUSERSITE'] = '1'
    output = isolated / 'self-check.json'
    process = subprocess.run([str(executable), '--self-check', str(output)],
        cwd=isolated, env=env, capture_output=True, timeout=90,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    report = json.loads(output.read_text(encoding='utf-8')) if output.exists() else {}
    result = {'ok': process.returncode == 0 and report.get('ok') is True,
        'exit_code': process.returncode, 'isolated_directory': str(isolated),
        'initial_files': initial, 'python_environment_removed': True,
        'path_restricted_to_windows': env['PATH'],
        'artifact_sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
        'report': report}
    evidence = ROOT / 'bukti' / 'standalone'
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / 'verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'ok': result['ok'], 'exit_code': process.returncode,
        'products': [case['product'] for case in report.get('cases', [])],
        'report': str(evidence / 'verification.json'), 'error': report.get('error')}))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
