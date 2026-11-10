"""Manual-only notebook routing and Tk worker lifecycle, without live installs."""
from functools import partial
import importlib
import json
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace
import tkinter as tk

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app


@pytest.fixture(scope="module")
def tk_master():
    # A real application uses one Tcl/Tk interpreter per process. Repeated Tk()
    # creation has process-global native Tk state; isolate forms in Toplevels.
    master = tk.Tk()
    master.withdraw()
    yield master
    master.destroy()


@pytest.fixture
def gui(tk_master):
    window = tk.Toplevel(tk_master)
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
                capacity="20", expires="2030-12-31", file=file, previous_license="")


def widgets(root):
    yield root
    for child in root.winfo_children():
        yield from widgets(child)


def test_three_tabs_have_independent_manual_inputs(gui):
    assert [gui.notebook.tab(tab, "text") for tab in gui.notebook.tabs()] == [
        "Absensi Wajah", "SchoolPay", "CBE Server"]
    for key, database_id in (("face", "V4YNE"), ("schoolpay", "7VJM4"), ("cbe", "ABCDE")):
        panel = gui.panels[key]
        panel.inputs["database_id"].set(database_id)
        gui.notebook.select(panel)
        assert gui.active_panel() is panel
        assert panel.inputs["database_id"].get() == database_id
        assert "sequence" not in panel.inputs
    assert gui.panels["face"].inputs["database_id"].get() == "V4YNE"
    assert gui.panels["schoolpay"].inputs["database_id"].get() == "7VJM4"


def test_database_settings_and_detection_controls_are_removed(gui):
    texts = []
    for widget in widgets(gui):
        if "text" in widget.keys():
            texts.append(str(widget.cget("text")))
    assert "Koneksi Database…" not in texts
    assert "Deteksi Database ID" not in texts
    assert "Deteksi System ID" not in texts
    assert "Sequence" not in texts
    assert not hasattr(gui, "connection")
    assert not hasattr(gui, "configure_database")
    for panel in gui.panels.values():
        assert not hasattr(panel, "_detect_db")
        assert not hasattr(panel, "_detect_sys")
        assert "database_id" in panel.inputs and "system_id" in panel.inputs


def test_results_stay_six_lines_when_window_height_grows(gui):
    gui.window.deiconify()
    gui.window.geometry("880x650+0+0")
    gui.window.update()
    panel = gui.panels["face"]
    first_height = panel.output.winfo_height()
    assert int(panel.output.cget("height")) == 6
    gui.window.geometry("880x730+0+0")
    gui.window.update()
    assert panel.output.winfo_height() == first_height
    assert str(panel.output.cget("wrap")) == "word"
    gui.window.withdraw()


@pytest.mark.parametrize("key", ["face", "schoolpay", "cbe"])
def test_dispatch_runs_backend_in_worker_and_applies_result_on_tk_thread(gui, key, monkeypatch):
    panel = gui.panels[key]
    main_thread = threading.get_ident()
    called, result_threads = [], []
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
    heartbeat = []
    gui.window.after(0, lambda: heartbeat.append(True))
    pump(gui, lambda: bool(heartbeat))
    assert called[0][0] != main_thread
    allow_finish.set()
    pump(gui, lambda: not panel.busy)
    assert result_threads == [main_thread]
    assert called[0][1]["capacity"] == 20
    assert called[0][1]["client_id"] is None
    assert called[0][1]["sequence"] is None
    assert called[0][1]["previous_license_path"] is None
    assert key in panel.output.get("1.0", "end")
    for other_key, other in gui.panels.items():
        if other_key != key:
            assert other.inputs["file"].get() == ""
            assert other.output.get("1.0", "end").strip() == ""


def test_renewal_client_id_without_previous_file_explains_automatic_sequence():
    snapshot = values()
    snapshot["client_id"] = "PREVIOUS_CLIENT"
    with pytest.raises(ValueError, match="lisensi lama"):
        app.run_backend_action(SimpleNamespace(), "generate", snapshot)


def test_close_while_worker_runs_does_not_schedule_tk_from_worker(tk_master):
    window = tk.Toplevel(tk_master)
    window.withdraw()
    application = app.LicenseApp(window)
    panel = application.panels["cbe"]
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
    assert panel._closed and panel._poll_id is None


@pytest.mark.parametrize("product,database_id", [
    ("face", "V4YNE"), ("schoolpay", "7VJM4"), ("cbe", "ABCDE")])
def test_real_backend_new_and_renewal_sequences_are_automatic(gui, tmp_path, product, database_id):
    codec_name = next(item.codec_module for item in app.PRODUCTS if item.key == product)
    codec = importlib.import_module(codec_name)
    panel = gui.panels[product]
    first = tmp_path / f"{product}.lic"
    snapshot = values(str(first))
    snapshot.update(database_id=database_id, system_id="DDCB4")
    for key, value in snapshot.items():
        panel.inputs[key].set(value)
    panel.run_action("generate")
    pump(gui, lambda: not panel.busy)
    assert first.is_file()
    first_fields = codec.inspect_license(first)["fields"]
    assert first_fields["Sequence"] == "1"
    panel.run_action("verify")
    pump(gui, lambda: not panel.busy)
    assert json.loads(panel.output.get("1.0", "end"))["valid"] is True
    renewed = tmp_path / f"{product}-renewal.lic"
    panel.inputs["previous_license"].set(str(first))
    panel.inputs["file"].set(str(renewed))
    panel.run_action("generate")
    pump(gui, lambda: not panel.busy)
    renewed_fields = codec.inspect_license(renewed)["fields"]
    assert renewed_fields["Sequence"] == "2"
    assert renewed_fields["KlienId"] == first_fields["KlienId"]
    assert "sequence" not in panel.inputs


def test_worker_keeps_plain_data_and_close_finalizes_variables_on_main_thread(monkeypatch, tk_master):
    window = tk.Toplevel(tk_master)
    window.withdraw()
    application = app.LicenseApp(window)
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
        for panel in application.panels.values():
            panel.inputs["file"].set("synthetic.lic")
            panel.run_action("inspect")
        assert len(launched) == 3
        for task in launched:
            assert task["target"] is app._run_queued_task
            assert task["target"].__closure__ is None
            assert_plain(task["args"])
        application.close()
        # Each of three panels owns 8 input StringVars, status, and BooleanVar.
        assert len(finalized) >= 30
        assert set(finalized) == {main_thread}
    finally:
        application.close()
