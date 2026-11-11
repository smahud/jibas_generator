# Build on Windows x64: python -m build_standalone
from pathlib import Path

root = Path(SPECPATH)
resources = ['schema.xml', 'schoolpay_schema.xml', 'cbe_schema.xml', 'format_profile.json',
             'fingerprint_schema.xml', 'sjs_schema.xml', 'sjs_format.json']
a = Analysis(
    [str(root / 'build_tools' / 'standalone_entry.py')],
    pathex=[str(root)], binaries=[], datas=[(str(root / name), '.') for name in resources],
    hiddenimports=['license_codec', 'schoolpay_codec', 'cbe_codec',
                   'fingerprint_codec', 'letterstore_codec', 'sjs_codec'],
    hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['pymysql', 'id_detect', 'schoolpay_id_detect', 'pytest', 'PIL'],
    noarchive=False, optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name='JIBAS-Generator-Codex', debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=False, disable_windowed_traceback=False,
    argv_emulation=False, target_arch=None, codesign_identity=None, entitlements_file=None,
)
