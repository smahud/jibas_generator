"""Isolated packaged-app verification; never accesses installed JIBAS or a DB."""
import hashlib
import importlib
import json
from pathlib import Path
import sys
import time
import traceback


def run(output_dir):
    import tkinter as tk
    import app

    assert getattr(sys, 'frozen', False), 'Run this check using the packaged executable.'
    bundle = Path(sys._MEIPASS).resolve()
    errors = []
    original_error = app.messagebox.showerror
    app.messagebox.showerror = lambda *args, **kwargs: errors.append(str(args))
    root = tk.Tk()
    root.withdraw()
    application = app.LicenseApp(root)
    report = {
        'frozen': True, 'executable': sys.executable,
        'executable_sha256': hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
        'bundle': str(bundle), 'sys_path': sys.path,
        'tabs': [application.notebook.tab(t, 'text') for t in application.notebook.tabs()],
        'cases': [],
    }

    def action(panel, name):
        panel.run_action(name)
        deadline = time.monotonic() + 25
        while panel.busy and time.monotonic() < deadline:
            root.update()
            time.sleep(0.01)
        assert not panel.busy, f'{name} timed out'
        assert not errors, errors
        return json.loads(panel.output.get('1.0', 'end'))

    try:
        assert report['tabs'] == ['Absensi Wajah', 'SchoolPay', 'CBE Server']
        assert not hasattr(application, 'connection')
        report['resources'] = {}
        for name in ('schema.xml', 'schoolpay_schema.xml', 'cbe_schema.xml', 'format_profile.json'):
            path = bundle / name
            assert path.is_file(), name
            report['resources'][name] = hashlib.sha256(path.read_bytes()).hexdigest()
        report['tcl_library'] = root.tk.eval('info library')
        report['tk_library'] = root.tk.eval('set tk_library')
        assert Path(report['tcl_library']).resolve().is_relative_to(bundle)
        assert Path(report['tk_library']).resolve().is_relative_to(bundle)
        for key, db, system_field, capacity_field in (
            ('face', 'V4YNE', 'Info1', 'MaxClient'),
            ('schoolpay', '7VJM4', 'SystemId', 'MaxVendor'),
            ('cbe', 'ABCDE', 'Info1', 'MaxClient'),
        ):
            panel = application.panels[key]
            application.notebook.select(panel)
            assert 'sequence' not in panel.inputs
            source = output_dir / f'{key}-new.lic'
            values = dict(database_id=db, system_id='DDCB4', client_id='', client_name='Standalone QA',
                          capacity='100', expires='2030-12-31', file=str(source), previous_license='')
            for field, value in values.items():
                panel.inputs[field].set(value)
            generated = action(panel, 'generate')
            assert generated['sequence'] == 1 and generated['verification']['valid']
            inspected = action(panel, 'inspect')
            assert inspected['fields']['DbId'] == db
            assert inspected['fields'][system_field] == 'DDCB4'
            assert inspected['fields'][capacity_field] == '100'
            assert action(panel, 'verify')['valid']
            panel.inputs['system_id'].set('123AB')
            assert action(panel, 'verify')['valid'] is False
            panel.inputs['system_id'].set('DDCB4')
            panel.inputs['previous_license'].set(str(source))
            panel.inputs['file'].set(str(output_dir / f'{key}-renewal.lic'))
            panel.inputs['expires'].set('2031-12-31')
            renewed = action(panel, 'generate')
            assert renewed['sequence'] == 2 and renewed['client_id'] == generated['client_id']
            assert action(panel, 'verify')['valid']
            module = importlib.import_module(panel.product.codec_module)
            assert Path(module.__file__).resolve().is_relative_to(bundle)
            report['cases'].append({'product': key, 'generated': True, 'inspected': True,
                'verified': True, 'wrong_system_rejected': True, 'renewal_sequence': 2,
                'client_id_preserved': True, 'module': module.__file__})
        rust = importlib.import_module('cryptography.hazmat.bindings._rust')
        assert Path(rust.__file__).resolve().is_relative_to(bundle)
        report['cryptography_native'] = rust.__file__
        report['ok'] = True
        report['activation_proven'] = False
        return report
    finally:
        application.close()
        app.messagebox.showerror = original_error


def main(report_path):
    path = Path(report_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        report = run(path.parent)
    except Exception:
        report = {'ok': False, 'error': traceback.format_exc(), 'frozen': getattr(sys, 'frozen', False)}
    path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    return 0 if report['ok'] else 1
