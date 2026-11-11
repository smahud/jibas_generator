"""Isolated six-product packaged-app check; no installed JIBAS or DB access."""
import hashlib
import importlib
import json
from pathlib import Path
import sys
import time
import traceback

# Synthetic statistics copied from bukti/sjs/smoke_fixture.json; the fixture
# file is not bundled and this token is not an online school registration.
SJS_FIXTURE = {
    'database_id': 'AB123',
    'registration_token': '97875YgYKBhQIBwgZCQsbCxkPFQ4UAAgJGw4FCBUFCBkLCRsVBBQJGwoZDBUDDQNl',
    'school_id': 'SCHOOL-EXISTING-001',
}
PRODUCT_KEYS = ('face', 'fingerprint', 'schoolpay', 'cbe', 'sjs', 'letterstore')


def run(output_dir):
    import tkinter as tk
    import app
    from product_actions import verify_with_backend

    assert getattr(sys, 'frozen', False), 'Run this check using the packaged executable.'
    output_dir = Path(output_dir).resolve()
    bundle = Path(sys._MEIPASS).resolve()
    errors = []
    original_error = app.messagebox.showerror
    original_picker = app.filedialog.askdirectory
    app.messagebox.showerror = lambda *args, **kwargs: errors.append(str(args))
    root = tk.Tk()
    root.withdraw()
    application = app.LicenseApp(root)
    report = {
        'frozen': True, 'executable': sys.executable,
        'executable_sha256': hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
        'bundle': str(bundle), 'sys_path': sys.path,
        'tabs': [application.notebook.tab(t, 'text') for t in application.notebook.tabs()],
        'cases': [], 'sjs_fixture_kind': 'synthetic statistics; no online registration',
    }

    def action(panel, name):
        panel.run_action(name)
        deadline = time.monotonic() + 25
        while panel.busy and time.monotonic() < deadline:
            root.update()
            time.sleep(0.01)
        assert not panel.busy, f'{panel.product.key}: {name} timed out'
        assert not errors, errors
        return json.loads(panel.output.get('1.0', 'end'))

    def set_inputs(panel, values):
        for field, value in values.items():
            assert field in panel.inputs, (panel.product.key, field)
            panel.inputs[field].set(value)

    def check_file(panel, path):
        backend = importlib.import_module(panel.product.codec_module)
        assert Path(backend.__file__).resolve().is_relative_to(bundle)
        verified = verify_with_backend(backend, panel.product, path, panel.snapshot(), for_import=True)
        assert verified['valid'], (panel.product.key, verified)
        return backend

    try:
        assert tuple(product.key for product in app.PRODUCTS) == PRODUCT_KEYS
        assert report['tabs'] == [product.label for product in app.PRODUCTS]
        assert len(application.panels) == 6
        assert not hasattr(application, 'connection')
        database_ids = {'face': 'V4YNE', 'schoolpay': '7VJM4', 'cbe': 'ABCDE',
                        'sjs': SJS_FIXTURE['database_id'], 'letterstore': 'LS123'}
        database_panels = {key: panel for key, panel in application.panels.items()
                           if 'database_id' in panel.inputs}
        assert set(database_panels) == set(database_ids) and len(database_panels) == 5
        for key, value in database_ids.items():
            database_panels[key].inputs['database_id'].set(value)
        shared_values = {'system_id': 'DDCB4', 'client_id': 'SHARED-QA',
                         'client_name': 'Shared QA', 'expires': '2030-12-31', 'capacity': '100'}
        shared_owners = {}
        for field, value in shared_values.items():
            owners = [panel for panel in application.panels.values() if field in panel.inputs]
            assert owners, field
            assert all(panel.inputs[field] is application.shared_inputs[field] for panel in owners)
            owners[0].inputs[field].set(value)
            assert all(panel.inputs[field].get() == value for panel in owners)
            owners[-1].inputs[field].set('')
            assert all(panel.inputs[field].get() == '' for panel in owners)
            owners[0].inputs[field].set(value)
            shared_owners[field] = [panel.product.key for panel in owners]
        assert {key: panel.inputs['database_id'].get() for key, panel in database_panels.items()} == database_ids
        assert len({str(panel.inputs['database_id']) for panel in database_panels.values()}) == 5
        report['shared_fields_verified'] = list(app.SHARED_FIELDS)
        report['shared_field_owners'] = shared_owners
        report['database_ids_independent'] = True
        report['database_id_panel_count'] = 5
        report['resources'] = {}
        for name in ('schema.xml', 'schoolpay_schema.xml', 'cbe_schema.xml', 'fingerprint_schema.xml',
                     'sjs_schema.xml', 'sjs_format.json', 'format_profile.json'):
            path = bundle / name
            assert path.is_file(), name
            report['resources'][name] = hashlib.sha256(path.read_bytes()).hexdigest()
        report['tcl_library'] = root.tk.eval('info library')
        report['tk_library'] = root.tk.eval('set tk_library')
        assert Path(report['tcl_library']).resolve().is_relative_to(bundle)
        assert Path(report['tk_library']).resolve().is_relative_to(bundle)

        for product in app.PRODUCTS:
            key, panel = product.key, application.panels[product.key]
            application.notebook.select(panel)
            assert 'sequence' not in panel.inputs
            assert ('previous_license' in panel.inputs) is product.supports_renewal
            source = output_dir / f'{key}-new.lic'
            values = {'file': str(source), 'client_name': 'Standalone QA'}
            if 'database_id' in panel.inputs:
                values['database_id'] = database_ids[key]
            if product.kind == 'standard':
                values.update(system_id='DDCB4', client_id='', capacity='100',
                              expires='2030-12-31', previous_license='')
            elif product.kind == 'fingerprint':
                values.update(scanner_serial='SCANNER-QA-001', license_scope='Manager + Client')
            elif product.kind == 'sjs':
                values.update(registration_token=SJS_FIXTURE['registration_token'],
                              school_id=SJS_FIXTURE['school_id'], capacity='100',
                              expires='2030-12-31', previous_license='')
            set_inputs(panel, values)
            generated = action(panel, 'generate')
            assert generated['verification']['valid']
            if product.supports_renewal:
                assert generated['sequence'] == 1
            else:
                assert 'sequence' not in generated
            inspected = action(panel, 'inspect')
            fields = inspected['fields']
            if product.kind == 'fingerprint':
                assert fields['Seri'] == values['scanner_serial'] and fields['LicType'] == 'CM'
            elif product.kind == 'letterstore':
                assert fields['Info3'] == database_ids[key] and fields['Versi'] == '2.0'
            elif product.kind == 'sjs':
                assert fields['DatabaseId'] == database_ids[key]
                assert fields['SchoolId'] == SJS_FIXTURE['school_id'] and fields['MaxAgentConn'] == '100'
            else:
                assert fields['DbId'] == database_ids[key]
                assert fields['SystemId' if key == 'schoolpay' else 'Info1'] == 'DDCB4'
                assert fields['MaxVendor' if key == 'schoolpay' else 'MaxClient'] == '100'
            assert action(panel, 'verify')['valid']
            wrong_checks = {}
            identity_field = 'scanner_serial' if product.kind == 'fingerprint' else 'database_id'
            original_identity = panel.inputs[identity_field].get()
            panel.inputs[identity_field].set('SCANNER-WRONG' if product.kind == 'fingerprint' else 'ZZ999')
            assert action(panel, 'verify')['valid'] is False
            panel.inputs[identity_field].set(original_identity)
            wrong_checks['wrong_scanner_rejected' if product.kind == 'fingerprint' else 'wrong_database_rejected'] = True
            if 'system_id' in panel.inputs:
                panel.inputs['system_id'].set('123AB')
                assert action(panel, 'verify')['valid'] is False
                panel.inputs['system_id'].set('DDCB4')
                wrong_checks['wrong_system_rejected'] = True
            backend = check_file(panel, source)
            second = output_dir / f'{key}-{"renewal" if product.supports_renewal else "regenerated"}.lic'
            panel.inputs['file'].set(str(second))
            if product.supports_renewal:
                panel.inputs['previous_license'].set(str(source))
                panel.inputs['expires'].set('2031-12-31')
            repeated = action(panel, 'generate')
            assert repeated['verification']['valid']
            assert action(panel, 'verify')['valid']
            check_file(panel, second)
            case = {'product': key, 'generated': True, 'inspected': True, 'verified': True,
                    'module': backend.__file__, **wrong_checks}
            if product.supports_renewal:
                assert repeated['sequence'] == 2 and repeated['client_id'] == generated['client_id']
                case.update(renewal_sequence=2, client_id_preserved=True)
            else:
                assert 'sequence' not in repeated and 'previous_license' not in panel.inputs
                case['regenerated_without_renewal'] = True
            report['cases'].append(case)

        destination = output_dir / 'save-all-new'
        destination.mkdir()
        picker_calls = []

        def pick_folder(**kwargs):
            picker_calls.append(str(destination))
            return str(destination)

        app.filedialog.askdirectory = pick_folder
        for panel in application.panels.values():
            if 'previous_license' in panel.inputs:
                panel.inputs['previous_license'].set('')
        shared = application.shared_inputs
        for field, value in {'client_id': '', 'client_name': 'Save All QA', 'expires': '2032-12-31',
                             'capacity': '100', 'system_id': 'DDCB4'}.items():
            shared[field].set(value)
        application.panels['letterstore'].inputs['database_id'].set('')
        assert application.save_all() is False
        assert not picker_calls and not list(destination.iterdir()) and errors
        errors.clear()
        application.panels['letterstore'].inputs['database_id'].set(database_ids['letterstore'])

        def save_all():
            assert application.save_all() is True
            assert all(panel.busy for panel in application.panels.values())
            deadline = time.monotonic() + 25
            while application._batch_busy and time.monotonic() < deadline:
                root.update()
                time.sleep(0.01)
            assert not application._batch_busy and not errors, errors
            assert all(not panel.busy for panel in application.panels.values())

        save_all()
        batch_clients = {}
        for key, panel in application.panels.items():
            result = json.loads(panel.output.get('1.0', 'end'))
            target = destination / panel.product.initial_file
            assert target.is_file() and Path(result['path']) == target
            assert result['verification']['valid']
            check_file(panel, target)
            if panel.product.supports_renewal:
                assert result['sequence'] == 1
                batch_clients[key] = result['client_id']
                panel.inputs['previous_license'].set(str(target))
            else:
                assert 'sequence' not in result
        assert len(batch_clients) == 4
        assert len(list(destination.glob('*.lic'))) == 6
        destination = output_dir / 'save-all-renewal'
        destination.mkdir()
        shared['expires'].set('2033-12-31')
        save_all()
        renewed, regenerated = [], []
        for key, panel in application.panels.items():
            result = json.loads(panel.output.get('1.0', 'end'))
            assert result['verification']['valid']
            target = destination / panel.product.initial_file
            assert target.is_file() and Path(result['path']) == target
            check_file(panel, target)
            if panel.product.supports_renewal:
                assert result['sequence'] == 2 and result['client_id'] == batch_clients[key]
                renewed.append(key)
            else:
                assert 'sequence' not in result
                regenerated.append(key)
        assert len(list(destination.glob('*.lic'))) == 6 and len(picker_calls) == 2
        assert len(renewed) == 4 and set(regenerated) == {'fingerprint', 'letterstore'}
        report['save_all'] = {'preflight_before_picker': True, 'new_files': 6,
                              'renewed_files': 4, 'regenerated_files': 2,
                              'second_folder_files': 6, 'renewed_products': renewed,
                              'regenerated_products': regenerated, 'client_ids_preserved': True,
                              'all_panels_unlocked': True}
        rust = importlib.import_module('cryptography.hazmat.bindings._rust')
        assert Path(rust.__file__).resolve().is_relative_to(bundle)
        report['cryptography_native'] = rust.__file__
        report['ok'] = True
        report['activation_proven'] = False
        return report
    finally:
        application.close()
        app.messagebox.showerror = original_error
        app.filedialog.askdirectory = original_picker


def main(report_path):
    path = Path(report_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        report = run(path.parent)
    except Exception:
        report = {'ok': False, 'error': traceback.format_exc(), 'frozen': getattr(sys, 'frozen', False)}
    path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    return 0 if report['ok'] else 1
