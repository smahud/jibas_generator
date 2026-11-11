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


def field_entry(panel, key):
    variable = str(panel.inputs[key])
    return next(widget for widget in widgets(panel)
                if isinstance(widget, app.ttk.Entry) and str(widget.cget("textvariable")) == variable)


def fill_batch_forms(gui):
    for product, database_id in (("face", "V4YNE"), ("schoolpay", "7VJM4"), ("cbe", "ABCDE")):
        snapshot = values(f"unused-{product}.lic")
        snapshot.update(database_id=database_id, system_id="DDCB4")
        for key, value in snapshot.items():
            gui.panels[product].inputs[key].set(value)


def test_three_tabs_keep_database_ids_and_file_controls_independent(gui):
    assert [gui.notebook.tab(tab, "text") for tab in gui.notebook.tabs()] == [
        "Absensi Wajah", "SchoolPay", "CBE Server"]
    for key, database_id in (("face", "V4YNE"), ("schoolpay", "7VJM4"), ("cbe", "ABCDE")):
        panel = gui.panels[key]
        panel.inputs["database_id"].set(database_id)
        gui.notebook.select(panel)
        assert gui.active_panel() is panel
        assert panel.inputs["database_id"].get() == database_id
        assert "sequence" not in panel.inputs
        panel.inputs["file"].set(f"{key}.lic")
        panel.inputs["previous_license"].set(f"{key}-previous.lic")
        panel.overwrite.set(key == "face")
    assert gui.panels["face"].inputs["database_id"].get() == "V4YNE"
    assert gui.panels["schoolpay"].inputs["database_id"].get() == "7VJM4"
    field_entry(gui.panels["cbe"], "database_id").delete(0, "end")
    for key, panel in gui.panels.items():
        assert panel.inputs["file"].get() == f"{key}.lic"
        assert panel.inputs["previous_license"].get() == f"{key}-previous.lic"
        assert panel.overwrite.get() is (key == "face")
    assert gui.panels["cbe"].inputs["database_id"].get() == ""
    assert gui.panels["face"].inputs["database_id"].get() == "V4YNE"
    assert gui.panels["schoolpay"].inputs["database_id"].get() == "7VJM4"
    assert len({str(panel.inputs["database_id"]) for panel in gui.panels.values()}) == 3


@pytest.mark.parametrize("source", ["face", "schoolpay", "cbe"])
def test_shared_fields_update_edit_and_delete_immediately_from_every_tab(gui, source):
    panel = gui.panels[source]
    gui.notebook.select(panel)
    for key in app.SHARED_FIELDS:
        entry = field_entry(panel, key)
        entry.delete(0, "end")
        entry.insert(0, f"{source}-{key}")
        for destination in gui.panels.values():
            assert destination.inputs[key] is gui.shared_inputs[key]
            assert field_entry(destination, key).get() == f"{source}-{key}"
        entry.delete(0, 3)
        entry.insert(0, "edited")
        edited = entry.get()
        assert all(field_entry(destination, key).get() == edited for destination in gui.panels.values())
        entry.delete(0, "end")
        assert all(field_entry(destination, key).get() == "" for destination in gui.panels.values())
        assert not gui.shared_inputs[key].trace_info()


def test_each_save_all_button_is_directly_left_of_individual_save(gui):
    for panel in gui.panels.values():
        batch = panel.save_all_button
        individual = panel.generate_button
        assert batch.cget("text") == "Save All"
        assert batch.master is individual.master
        assert batch.grid_info()["row"] == individual.grid_info()["row"]
        assert batch.grid_info()["column"] + 1 == individual.grid_info()["column"]


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


def test_save_all_validates_missing_third_database_id_before_folder_dialog(gui, tmp_path, monkeypatch):
    fill_batch_forms(gui)
    gui.panels["cbe"].inputs["database_id"].set("")
    errors, dialogs = [], []
    monkeypatch.setattr(app.messagebox, "showerror", lambda title, detail, **kw: errors.append((title, detail)))
    monkeypatch.setattr(app.filedialog, "askdirectory", lambda **kw: dialogs.append(kw) or str(tmp_path))
    assert gui.save_all() is False
    assert dialogs == []
    assert errors and "CBE Server" in " ".join(errors[0])
    assert list(tmp_path.iterdir()) == []
    assert not any(panel.busy for panel in gui.panels.values())


@pytest.mark.parametrize("field,invalid", [("expires", "2030-02-30"), ("capacity", "0"),
                                          ("client_id", "PREVIOUS_CLIENT")])
def test_save_all_rejects_invalid_shared_fields_before_folder_dialog(gui, field, invalid, monkeypatch):
    fill_batch_forms(gui)
    gui.panels["schoolpay"].inputs[field].set(invalid)
    errors, dialogs = [], []
    monkeypatch.setattr(app.messagebox, "showerror", lambda *args, **kw: errors.append(args))
    monkeypatch.setattr(app.filedialog, "askdirectory", lambda **kw: dialogs.append(kw))
    assert gui.save_all() is False
    assert errors and dialogs == []
    if field == "client_id":
        assert "lisensi lama" in str(errors)


def test_save_all_writes_three_real_fixed_files_and_applies_results_on_tk_thread(gui, tmp_path, monkeypatch):
    fill_batch_forms(gui)
    dialogs, result_threads, errors = [], [], []
    main_thread = threading.get_ident()
    monkeypatch.setattr(app.filedialog, "askdirectory", lambda **kw: dialogs.append(kw) or str(tmp_path))
    monkeypatch.setattr(app.messagebox, "showerror", lambda *args, **kw: errors.append(args))
    for panel in gui.panels.values():
        original = panel.show_result

        def show_result(result, original=original):
            result_threads.append(threading.get_ident())
            original(result)

        monkeypatch.setattr(panel, "show_result", show_result)
    gui.panels["schoolpay"].save_all_button.invoke()
    assert gui._batch_busy
    assert all(panel.busy for panel in gui.panels.values())
    pump(gui, lambda: not gui._batch_busy)
    assert len(dialogs) == 1 and not errors
    assert set(path.name for path in tmp_path.iterdir()) == {product.initial_file for product in app.PRODUCTS}
    client_ids = []
    for product in app.PRODUCTS:
        panel = gui.panels[product.key]
        target = tmp_path / product.initial_file
        assert Path(panel.inputs["file"].get()) == target
        result = json.loads(panel.output.get("1.0", "end"))
        assert Path(result["path"]) == target
        assert result["verification"]["valid"] is True
        codec = importlib.import_module(product.codec_module)
        assert codec.verify_license(target, panel.inputs["database_id"].get(), "DDCB4")["valid"] is True
        client_ids.append(codec.inspect_license(target)["fields"]["KlienId"])
        assert "berhasil" in panel.status.get()
        assert not panel.busy
        assert not panel.save_all_button.instate(["disabled"])
        assert int(panel.output.cget("height")) == 6
    assert len(set(client_ids)) == 3
    assert gui.shared_inputs["client_id"].get() == ""
    assert result_threads == [main_thread] * 3


def test_failed_batch_unlocks_every_panel_and_uses_a_plain_snapshot(gui, tmp_path, monkeypatch):
    fill_batch_forms(gui)
    started, release = threading.Event(), threading.Event()
    calls, errors = [], []
    main_thread = threading.get_ident()

    def fail_batch(forms, output_dir, backends=None):
        calls.append((threading.get_ident(), forms, output_dir))
        started.set()
        assert release.wait(2)
        raise ValueError("CBE Server: penyimpanan gagal")

    monkeypatch.setattr(app.batch_license, "generate_all", fail_batch)
    monkeypatch.setattr(app.filedialog, "askdirectory", lambda **kw: str(tmp_path))
    monkeypatch.setattr(app.messagebox, "showerror", lambda *args, **kw: errors.append(args))
    assert gui.save_all() is True
    assert started.wait(1)
    for panel in gui.panels.values():
        assert panel.busy
        assert all(control.instate(["disabled"]) for control in panel._controls)
    assert gui.save_all() is False
    assert gui.panels["face"]._start_task("inspect", lambda: {}, "") is False
    gui.shared_inputs["client_name"].set("changed after snapshot")
    release.set()
    pump(gui, lambda: not gui._batch_busy)
    assert calls[0][0] != main_thread
    assert all(form["values"]["client_name"] == "SYNTHETIC" for form in calls[0][1])
    assert errors and "CBE Server" in str(errors)
    for panel in gui.panels.values():
        assert not panel.busy
        assert all(not control.instate(["disabled"]) for control in panel._controls)
        assert "belum berhasil" in panel.status.get()
        assert "CBE Server" in panel.output.get("1.0", "end")
        assert panel.inputs["file"].get() == f"unused-{panel.product.key}.lic"
    assert list(tmp_path.iterdir()) == []


def test_save_all_refuses_while_an_individual_product_is_busy(gui, monkeypatch):
    fill_batch_forms(gui)
    dialogs = []
    monkeypatch.setattr(app.filedialog, "askdirectory", lambda **kw: dialogs.append(kw))
    gui.panels["schoolpay"]._set_busy(True)
    assert gui.save_all() is False
    assert not gui._batch_busy and dialogs == []
    gui.panels["schoolpay"]._set_busy(False)


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


def test_close_during_batch_leaves_non_daemon_transaction_running_without_tk(tk_master, tmp_path, monkeypatch):
    window = tk.Toplevel(tk_master)
    window.withdraw()
    application = app.LicenseApp(window)
    fill_batch_forms(application)
    started, release, finished = threading.Event(), threading.Event(), threading.Event()
    worker_properties = []

    def finish_batch(forms, output_dir, backends=None):
        worker_properties.append((threading.current_thread().daemon, forms))
        started.set()
        assert release.wait(2)
        finished.set()
        return {"ok": True, "results": {}, "paths": {}}

    monkeypatch.setattr(app.batch_license, "generate_all", finish_batch)
    monkeypatch.setattr(app.filedialog, "askdirectory", lambda **kw: str(tmp_path))
    try:
        assert application.save_all() is True
        assert started.wait(1)
        application.close()
        assert application._batch_poll_id is None
        assert application.shared_inputs == {}
        assert application.panels == {}
        assert worker_properties[0][0] is False
        release.set()
        assert finished.wait(1)
    finally:
        release.set()
        application.close()


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


@pytest.mark.parametrize("mode", ["individual", "batch"])
def test_worker_keeps_plain_data_and_close_finalizes_variables_on_main_thread(monkeypatch, tk_master, mode):
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
    monkeypatch.setattr(app.filedialog, "askdirectory", lambda **kw: "synthetic-output-folder")

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
        if mode == "individual":
            for panel in application.panels.values():
                panel.inputs["file"].set("synthetic.lic")
                panel.run_action("inspect")
            assert len(launched) == 3
        else:
            fill_batch_forms(application)
            assert application.save_all() is True
            assert len(launched) == 1
            assert launched[0]["daemon"] is False
        for task in launched:
            assert task["target"] is app._run_queued_task
            assert task["target"].__closure__ is None
            assert_plain(task["args"])
        application.close()
        # Each panel owns 3 inputs, status, and overwrite; the app owns 5 shared inputs.
        assert len(finalized) >= 3 * 5 + len(app.SHARED_FIELDS)
        assert set(finalized) == {main_thread}
        assert application.shared_inputs == {}
        assert application._batch_poll_id is None
    finally:
        application.close()
