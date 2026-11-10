"""Notebook integration and real Tk worker lifecycle checks, using fake backends."""
from pathlib import Path
import sys
import threading
import time
from functools import partial
from types import SimpleNamespace
import tkinter as tk

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app


@pytest.fixture
def gui():
    window = tk.Tk()
    window.withdraw()
    application = app.LicenseApp(window)
    yield application
    if window.winfo_exists():
        application.close()


def pump(application, predicate, timeout=3):
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        application.window.update()
        time.sleep(0.005)
    assert predicate(), "Tk worker result was not delivered before the deadline"


def values(file="synthetic.lic"):
    return dict(database_id="ABCDE", system_id="123AB", client_id="", client_name="SYNTHETIC",
                capacity="20", expires="2030-12-31", file=file, previous_license="", sequence="")


def test_tabs_have_independent_inputs_and_active_shortcut_target(gui):
    assert [gui.notebook.tab(tab, "text") for tab in gui.notebook.tabs()] == ["Absensi Wajah", "SchoolPay"]
    assert gui.active_panel() is gui.panels["face"]
    gui.panels["face"].inputs["database_id"].set("V4YNE")
    gui.panels["schoolpay"].inputs["database_id"].set("7VJM4")
    gui.notebook.select(gui.panels["schoolpay"])
    assert gui.active_panel() is gui.panels["schoolpay"]
    assert gui.panels["face"].inputs["database_id"].get() == "V4YNE"
    assert gui.panels["schoolpay"].inputs["database_id"].get() == "7VJM4"
    assert gui.panels["face"].product.capacity_label == "Kapasitas wajah"
    assert gui.panels["schoolpay"].product.capacity_label == "Kapasitas vendor"


@pytest.mark.parametrize("key", ["face", "schoolpay"])
def test_dispatch_runs_backend_in_worker_and_applies_result_on_tk_thread(gui, key, monkeypatch):
    panel = gui.panels[key]
    main_thread = threading.get_ident()
    called = []
    result_threads = []
    allow_finish = threading.Event()

    def generate(**kw):
        called.append((threading.get_ident(), kw))
        assert allow_finish.wait(2)
        return {"path": str(kw["output_path"]), "product": key, "verification": {"valid": True}}

    panel._backend = SimpleNamespace(generate_license=generate)
    show_result = panel.show_result

    def observe_result(result):
        result_threads.append(threading.get_ident())
        show_result(result)

    monkeypatch.setattr(panel, "show_result", observe_result)
    for name, value in values().items():
        panel.inputs[name].set(value)
    panel.run_action("generate")
    assert panel.busy
    assert not panel._start_task("other", lambda: None, "")
    pump(gui, lambda: bool(called))
    # Main-thread callbacks remain runnable while the backend is blocked.
    heartbeat = []
    gui.window.after(0, lambda: heartbeat.append(True))
    pump(gui, lambda: bool(heartbeat))
    assert called[0][0] != main_thread
    allow_finish.set()
    pump(gui, lambda: not panel.busy)
    assert result_threads == [main_thread]
    assert called[0][1]["capacity"] == 20
    assert called[0][1]["client_id"] is None
    assert called[0][1]["previous_license_path"] is None
    assert key in panel.output.get("1.0", "end")
    other = gui.panels["schoolpay" if key == "face" else "face"]
    assert other.inputs["file"].get() == ""
    assert other.output.get("1.0", "end").strip() == ""


def test_each_panel_uses_its_detector_and_connection_snapshot(gui, monkeypatch):
    calls, notices = [], []
    secret = "synthetic-db-secret"
    gui.connection = dict(host="example.invalid", port=3434, user="synthetic", password=secret)

    class FakeDbDetector:
        def __init__(self, **kw):
            calls.append(kw)

        def detect(self):
            raise ValueError("Connector included " + secret)

    school = gui.panels["schoolpay"]
    school._detector = SimpleNamespace(DbIdDetector=FakeDbDetector)
    monkeypatch.setattr(app.messagebox, "showerror", lambda *args, **kw: notices.append(args))
    school._detect_db()
    gui.connection["host"] = "changed.invalid"
    pump(gui, lambda: not school.busy)
    assert calls[0]["host"] == "example.invalid"
    assert calls[0]["password"] == secret
    assert secret not in school.output.get("1.0", "end")
    assert notices and secret not in notices[0][1]
    assert not gui.panels["face"].busy


def test_close_while_worker_runs_does_not_schedule_tk_from_worker():
    window = tk.Tk()
    window.withdraw()
    application = app.LicenseApp(window)
    panel = application.panels["schoolpay"]
    started, release, finished = threading.Event(), threading.Event(), threading.Event()

    def operation():
        started.set()
        release.wait(2)
        finished.set()
        return {"value": "finished after close"}

    panel._start_task("inspect", operation, "working")
    assert started.wait(1)
    application.close()
    release.set()
    assert finished.wait(1)
    assert panel._closed
    assert panel._poll_id is None


def test_database_dialog_masks_password_and_updates_memory_only(gui):
    gui.connection["password"] = "synthetic-dialog-secret"
    gui.configure_database()
    dialog = next(child for child in gui.window.winfo_children() if isinstance(child, tk.Toplevel))
    nodes = list(dialog.winfo_children())
    entries, buttons = [], []
    while nodes:
        node = nodes.pop()
        nodes.extend(node.winfo_children())
        if isinstance(node, app.ttk.Entry):
            entries.append(node)
        elif isinstance(node, app.ttk.Button):
            buttons.append(node)
    secret_entry = next(entry for entry in entries if entry.cget("show") == "•")
    assert secret_entry.get() == "synthetic-dialog-secret"
    secret_entry.delete(0, "end")
    secret_entry.insert(0, "changed-synthetic-secret")
    next(button for button in buttons if button.cget("text") == "Gunakan").invoke()
    assert gui.connection["password"] == "changed-synthetic-secret"
    assert not dialog.winfo_exists()


@pytest.mark.parametrize("product,database_id,field", [
    ("face", "V4YNE", "MaxClient"), ("schoolpay", "7VJM4", "MaxVendor")])
def test_real_product_backend_roundtrip_through_gui(gui, tmp_path, product, database_id, field):
    panel = gui.panels[product]
    snapshot = values(str(tmp_path / (product + ".lic")))
    snapshot.update(database_id=database_id, system_id="DDCB4")
    for key, value in snapshot.items():
        panel.inputs[key].set(value)
    panel.run_action("generate")
    pump(gui, lambda: not panel.busy)
    assert Path(panel.inputs["file"].get()).is_file()
    panel.run_action("inspect")
    pump(gui, lambda: not panel.busy)
    import json
    report = json.loads(panel.output.get("1.0", "end"))
    assert report["fields"]["DbId"] == database_id
    assert report["fields"][field] == "20"
    panel.run_action("verify")
    pump(gui, lambda: not panel.busy)
    assert json.loads(panel.output.get("1.0", "end"))["valid"] is True


def test_workers_keep_plain_data_and_close_finalizes_variables_on_main_thread(monkeypatch):
    window = tk.Tk()
    window.withdraw()
    application = app.LicenseApp(window)
    panel = application.panels["schoolpay"]
    launched, finalized = [], []
    main_thread = threading.get_ident()
    original_finalizer = tk.Variable.__del__

    class CapturedThread:
        def __init__(self, **kwargs):
            launched.append(kwargs)

        def start(self):
            pass

    def finalizer(variable):
        finalized.append(threading.get_ident())
        original_finalizer(variable)

    monkeypatch.setattr(app.threading, "Thread", CapturedThread)
    monkeypatch.setattr(tk.Variable, "__del__", finalizer)

    def assert_plain(value):
        assert not isinstance(value, (tk.Misc, tk.Variable))
        if isinstance(value, partial):
            assert value.func.__closure__ is None
            assert_plain(value.args)
            assert_plain(value.keywords)
        elif isinstance(value, dict):
            for item in value.values():
                assert_plain(item)
        elif isinstance(value, (tuple, list)):
            for item in value:
                assert_plain(item)

    try:
        panel.inputs["file"].set("synthetic.lic")
        panel.run_action("inspect")
        panel._set_busy(False)
        panel._detect_db()
        panel._set_busy(False)
        panel._detect_sys()
        assert len(launched) == 3
        for task in launched:
            assert task["target"] is app._run_queued_task
            assert task["target"].__closure__ is None
            assert_plain(task["args"])
        application.close()
        # Each tab owns 9 StringVars, one status StringVar and one BooleanVar.
        assert len(finalized) >= 22
        assert set(finalized) == {main_thread}
    finally:
        application.close()
