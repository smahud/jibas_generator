"""Real Tk tests; require a display. No target software or database is used."""
from pathlib import Path
import queue
import sys
import threading
import time
import tkinter as tk

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app
import diagnostics

SOURCE = ROOT / "tests" / "fixtures" / "original-imported.enc"


class ThreadGuard:
    """Catch any Tcl/Tk access from a worker, including Variable.get/set."""
    def __init__(self, interpreter):
        self.interpreter = interpreter
        self.owner = threading.get_ident()
        self.violations = []

    def __getattr__(self, name):
        attribute = getattr(self.interpreter, name)
        if not callable(attribute):
            return attribute

        def checked(*args, **kwargs):
            if threading.get_ident() != self.owner:
                self.violations.append(name)
                raise AssertionError("Tk called outside main thread")
            return attribute(*args, **kwargs)
        return checked


@pytest.fixture
def gui():
    try:
        root = tk.Tk()
    except tk.TclError as error:
        pytest.skip(f"Display unavailable: {error}")
    guard = ThreadGuard(root.tk)
    root.tk = guard
    callbacks = []
    root.report_callback_exception = lambda *error: callbacks.append(error)
    ui = app.LicenseApp(root)
    root.update()
    yield root, ui
    if not ui.closed:
        ui.close()
    assert not callbacks, callbacks
    assert not guard.violations


def finish(root, ui):
    deadline = time.monotonic() + 5
    while ui.busy and time.monotonic() < deadline:
        root.update()
        time.sleep(0.005)
    assert not ui.busy, "Diagnostic worker did not finish"
    root.update()


def test_read_existing_fixture_populates_structured_view(gui):
    root, ui = gui
    ui.inputs["file"].set(str(SOURCE))
    ui.run_action("inspect")
    assert ui.busy and ui.inspect_button.instate(["disabled"])
    finish(root, ui)
    assert ui.last_result["ok"] is True
    assert len(ui.fields.get_children()) == 17
    assert ui.copy_button.instate(["!disabled"])
    ui.copy_result()
    assert "offline_file_checks" in root.clipboard_get()
    assert str(SOURCE) not in root.clipboard_get()


def test_error_is_visible_and_previous_result_cannot_be_copied(gui):
    root, ui = gui
    ui.inputs["file"].set(str(SOURCE))
    ui.run_action("inspect")
    finish(root, ui)
    ui.inputs["file"].set("/private/SYNTHETIC_SECRET.enc")
    assert ui.last_result is None
    assert not ui.fields.get_children()
    assert ui.copy_button.instate(["disabled"])
    ui.run_action("inspect")
    finish(root, ui)
    assert ui.last_result["error"]["code"] == "not_found"
    assert "SYNTHETIC" not in ui.output.get("1.0", "end")
    assert "SYNTHETIC" not in ui.activity.get("1.0", "end")
    assert ui.tabs.select() == str(ui.activity_page)


def test_verification_shows_per_check_status_and_clears_stale_ids(gui):
    root, ui = gui
    for key, value in (("file", str(SOURCE)), ("database_id", "ABCDE"), ("system_id", "123AB")):
        ui.inputs[key].set(value)
    ui.run_action("verify")
    finish(root, ui)
    assert ui.last_result["result"]["valid"] is False
    assert ui.checks.get_children()
    statuses = [ui.checks.item(row)["values"][1] for row in ui.checks.get_children()]
    assert "Belum lulus" in statuses
    ui.inputs["system_id"].set("FFFFF")
    assert ui.last_result is None
    assert not ui.checks.get_children()


def test_slow_worker_keeps_events_live_and_rejects_duplicate_clicks(gui, monkeypatch):
    root, ui = gui
    started, release = threading.Event(), threading.Event()
    calls = []
    original = diagnostics.inspect_file

    def slow(path):
        calls.append(path)
        started.set()
        assert release.wait(timeout=3)
        return original(path)

    monkeypatch.setattr(diagnostics, "inspect_file", slow)
    ui.inputs["file"].set(str(SOURCE))
    ui.run_action("inspect")
    try:
        assert started.wait(timeout=1)
        ui.run_action("inspect")
        heartbeats = []
        root.after(0, lambda: heartbeats.append(True))
        root.update()
        assert heartbeats and ui.busy
        assert len(calls) == 1
        assert ui.file_entry.instate(["disabled"])
    finally:
        release.set()
    finish(root, ui)
    assert ui.last_result["ok"] is True


def test_close_during_work_does_not_call_destroyed_tk(gui, monkeypatch):
    root, ui = gui
    release, done = threading.Event(), threading.Event()

    def slow(_path):
        try:
            release.wait(timeout=3)
            raise RuntimeError("SYNTHETIC_SECRET")
        finally:
            done.set()

    monkeypatch.setattr(diagnostics, "inspect_file", slow)
    ui.inputs["file"].set(str(SOURCE))
    ui.run_action("inspect")
    ui.close()
    assert ui._poll_id is None
    release.set()
    assert done.wait(timeout=1)


def test_file_dialog_selection_and_cancel(gui, monkeypatch):
    _root, ui = gui
    monkeypatch.setattr(app.filedialog, "askopenfilename", lambda **_kwargs: str(SOURCE))
    ui.choose_file()
    assert ui.inputs["file"].get() == str(SOURCE)
    monkeypatch.setattr(app.filedialog, "askopenfilename", lambda **_kwargs: "")
    ui.choose_file()
    assert ui.inputs["file"].get() == str(SOURCE)


@pytest.mark.parametrize("width,height", [(760, 600), (1040, 740), (1400, 900)])
def test_resize_keeps_actions_and_active_pages_inside_window(gui, width, height):
    root, ui = gui
    root.geometry(f"{width}x{height}")
    root.update()
    for page in (ui.overview, ui.inspector, ui.verification, ui.activity_page):
        ui.tabs.select(page)
        root.update()
        widgets = [ui.file_entry, ui.browse_button, ui.inspect_button, ui.status_label, page]
        if page == ui.verification:
            widgets += [ui.verify_button, ui.checks, ui.limitations_label, *ui.id_entries]
        if page == ui.activity_page:
            widgets += [ui.output, ui.copy_button, ui.activity]
        for widget in widgets:
            x = widget.winfo_rootx() - root.winfo_rootx()
            y = widget.winfo_rooty() - root.winfo_rooty()
            assert 0 <= x < width
            assert 0 <= y < height
            assert x + widget.winfo_width() <= width
            assert y + widget.winfo_height() <= height


def test_worker_unexpected_error_is_safe_without_a_display(monkeypatch):
    def broken(_path):
        raise RuntimeError("password=SYNTHETIC_SECRET")
    monkeypatch.setattr(diagnostics, "inspect_file", broken)
    results = queue.Queue()
    app._work("inspect", {"file": "unused"}, results)
    result = results.get_nowait()
    assert result["error"]["code"] == "unexpected"
    assert "SYNTHETIC" not in str(result)
