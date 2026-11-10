"""One Windows desktop app for the FACE and SchoolPay license workflows.

Tk operations stay on the main thread. Each tab owns its inputs, backend,
background task queue, and results, so switching tabs does not mix products.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import partial
import importlib
import json
import os
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


@dataclass(frozen=True)
class Product:
    key: str
    label: str
    subtitle: str
    codec_module: str
    detector_module: str
    capacity_label: str
    initial_file: str


PRODUCTS = (
    Product("face", "Absensi Wajah", "Face Server 16.5 / Client FACE 16.10",
            "license_codec", "id_detect", "Kapasitas wajah", "absensi-wajah.lic"),
    Product("schoolpay", "SchoolPay", "SchoolPay Secure Server 10.5",
            "schoolpay_codec", "schoolpay_id_detect", "Kapasitas vendor", "schoolpay.lic"),
)


def _run_queued_task(events, kind, operation, secrets):
    """Worker entry point: never retain widgets, variables, or their owner."""
    try:
        result = operation()
    except Exception as exc:
        detail = str(exc)
        for secret in secrets:
            if secret:
                detail = detail.replace(secret, "[disembunyikan]")
        events.put(("error", kind, detail))
    else:
        events.put(("result", kind, result))


def _run_product_action(module_name, backend, action, values, overwrite):
    module = backend if backend is not None else importlib.import_module(module_name)
    return run_backend_action(module, action, values, overwrite=overwrite)


def _run_detector(module_name, detector, kind, connection):
    module = detector if detector is not None else importlib.import_module(module_name)
    instance = module.DbIdDetector(**connection) if kind == "database_id" else module.SystemIdDetector()
    return instance.detect()


def run_backend_action(backend, action: str, values: dict, *, overwrite=False) -> dict:
    """Execute a snapshot of a form without reading or writing Tk objects."""
    if action == "inspect":
        if not values["file"]:
            raise ValueError("Pilih berkas lisensi terlebih dahulu.")
        return backend.inspect_license(Path(values["file"]))
    if action not in ("verify", "generate"):
        raise ValueError("Operasi tidak dikenal.")
    if not values["database_id"] or not values["system_id"]:
        raise ValueError("Database ID dan System ID harus diisi atau dideteksi dari mesin tujuan.")
    if action == "verify":
        if not values["file"]:
            raise ValueError("Pilih berkas lisensi terlebih dahulu.")
        return backend.verify_license(
            Path(values["file"]), values["database_id"], values["system_id"],
            client_id=values["client_id"] or None)
    datetime.strptime(values["expires"], "%Y-%m-%d")
    try:
        capacity = int(values["capacity"])
    except ValueError as exc:
        raise ValueError("Kapasitas harus berupa bilangan bulat lebih dari nol.") from exc
    if not 1 <= capacity <= 2_147_483_647:
        raise ValueError("Kapasitas harus antara 1 dan 2147483647.")
    try:
        sequence = int(values["sequence"]) if values["sequence"] else None
    except ValueError as exc:
        raise ValueError("Sequence harus berupa bilangan bulat.") from exc
    if sequence is not None and not 1 <= sequence <= 2_147_483_647:
        raise ValueError("Sequence harus antara 1 dan 2147483647.")
    if not values["file"]:
        raise ValueError("Pilih lokasi keluaran terlebih dahulu.")
    return backend.generate_license(
        database_id=values["database_id"], system_id=values["system_id"],
        client_id=values["client_id"] or None, expires=values["expires"],
        capacity=capacity, output_path=values["file"], client_name=values["client_name"],
        previous_license_path=Path(values["previous_license"]) if values["previous_license"] else None,
        sequence=sequence, overwrite=overwrite)


class _Tooltip:
    def __init__(self, widget, text):
        self.widget, self.text, self.tip = widget, text, None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _show(self, _event=None):
        if self.tip is not None:
            return
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{self.widget.winfo_rootx() + 10}+"
                             f"{self.widget.winfo_rooty() + self.widget.winfo_height() + 4}")
        tk.Label(self.tip, text=self.text, justify="left", background="#fffbe6",
                 foreground="#183153", relief="solid", borderwidth=1,
                 font=("Segoe UI", 8), padx=7, pady=3).pack()

    def _hide(self, _event=None):
        if self.tip is not None:
            self.tip.destroy()
            self.tip = None


class LicensePanel(ttk.Frame):
    """A separate form and task queue for one product."""
    def __init__(self, parent, product: Product, *, backend=None, detector=None, connection_supplier=None):
        super().__init__(parent, padding=12)
        self.window = self.winfo_toplevel()
        self.product = product
        self._backend, self._detector = backend, detector
        self._connection_supplier = connection_supplier or (lambda: {})
        self._events = queue.Queue()
        self._closed = False
        self.busy = False
        self._controls = []
        self.columnconfigure(1, weight=1)
        self.columnconfigure(3, weight=1)
        self.rowconfigure(9, weight=1)
        self.inputs = {key: tk.StringVar(self) for key in (
            "database_id", "system_id", "client_id", "client_name", "capacity",
            "file", "previous_license", "sequence")}
        self.inputs["expires"] = tk.StringVar(self, value=(date.today() + timedelta(days=365)).isoformat())
        self.overwrite = tk.BooleanVar(self, value=False)
        self.status = tk.StringVar(self, value=f"Siap — {product.label}. Isi ID mesin tujuan atau gunakan deteksi.")

        ttk.Label(self, text=product.label, style="Title.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
        ttk.Label(self, text=product.subtitle, style="Hint.TLabel").grid(
            row=0, column=2, columnspan=2, sticky="e")
        self._field(1, 0, "Database ID", "database_id", "Database ID dari instalasi produk yang dipilih")
        self._field(1, 2, "System ID", "system_id", "System ID mesin tujuan; gunakan detector produk ini")
        self._field(2, 0, "Client ID", "client_id", "Kosongkan untuk lisensi baru; pertahankan untuk perpanjangan")
        self._field(2, 2, "Nama klien", "client_name", "Opsional")
        self._field(3, 0, "Berlaku sampai", "expires", "Format YYYY-MM-DD")
        self._field(3, 2, product.capacity_label, "capacity", "Bilangan bulat lebih dari nol")
        self._field(4, 0, "Sequence", "sequence", "Baru: 1; otomatis naik jika memilih lisensi lama")
        ttk.Label(self, text="Perpanjangan: pilih lisensi lama agar Client ID tetap sama.",
                  style="Hint.TLabel").grid(row=4, column=2, columnspan=2, sticky="w")

        detect_row = ttk.Frame(self)
        detect_row.grid(row=5, column=0, columnspan=4, sticky="w", pady=(6, 4))
        self._button(detect_row, "Deteksi Database ID", self._detect_db).grid(row=0, column=0, padx=(0, 6))
        self._button(detect_row, "Deteksi System ID", self._detect_sys).grid(row=0, column=1)
        self._browse_row(6, "Lisensi lama", "previous_license", previous=True)
        ttk.Separator(self).grid(row=7, column=0, columnspan=4, sticky="ew", pady=7)
        self._browse_row(8, "Berkas lisensi", "file", previous=False)

        output_frame = ttk.Frame(self)
        output_frame.grid(row=9, column=0, columnspan=4, sticky="nsew", pady=5)
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(1, weight=1)
        ttk.Label(output_frame, text="Hasil", style="Hint.TLabel").grid(row=0, column=0, sticky="w")
        self.output = tk.Text(output_frame, wrap="word", height=10, state="disabled",
                              background="white", foreground="#22324b", relief="solid",
                              borderwidth=1, font=("Consolas", 9), padx=10, pady=8)
        self.output.grid(row=1, column=0, sticky="nsew", pady=(3, 0))
        scrollbar = ttk.Scrollbar(output_frame, orient="vertical", command=self.output.yview)
        scrollbar.grid(row=1, column=1, sticky="ns", pady=(3, 0))
        self.output.configure(yscrollcommand=scrollbar.set)

        actions = ttk.Frame(self)
        actions.grid(row=10, column=0, columnspan=4, sticky="ew", pady=(3, 0))
        actions.columnconfigure(2, weight=1)
        self._button(actions, "Baca isi", lambda: self.run_action("inspect")).grid(row=0, column=0, padx=(0, 6))
        self._button(actions, "Periksa", lambda: self.run_action("verify")).grid(row=0, column=1)
        overwrite_box = ttk.Checkbutton(actions, text="Timpa berkas keluaran", variable=self.overwrite)
        overwrite_box.grid(row=0, column=2, sticky="w", padx=8)
        self._controls.append(overwrite_box)
        self._button(actions, "Buat & simpan…", lambda: self.run_action("generate"),
                     style="Accent.TButton").grid(row=0, column=3)
        self.progress = ttk.Progressbar(self, mode="indeterminate")
        self.progress.grid(row=11, column=0, columnspan=4, sticky="ew", pady=(7, 0))
        ttk.Label(self, textvariable=self.status, style="Hint.TLabel", wraplength=790).grid(
            row=12, column=0, columnspan=4, sticky="w", pady=(5, 0))
        self._poll_id = self.after(50, self._poll_events)

    def _button(self, parent, text, command, **kw):
        widget = ttk.Button(parent, text=text, command=command, **kw)
        self._controls.append(widget)
        return widget

    def _field(self, row, column, label, key, hint):
        ttk.Label(self, text=label, width=16, anchor="w").grid(row=row, column=column, sticky="w", pady=3)
        entry = ttk.Entry(self, textvariable=self.inputs[key])
        entry.grid(row=row, column=column + 1, sticky="ew", padx=(0, 12), pady=3)
        self._controls.append(entry)
        _Tooltip(entry, hint)

    def _browse_row(self, row, label, key, *, previous):
        ttk.Label(self, text=label, width=16, anchor="w").grid(row=row, column=0, sticky="w", pady=3)
        entry = ttk.Entry(self, textvariable=self.inputs[key])
        entry.grid(row=row, column=1, columnspan=2, sticky="ew", padx=(0, 8), pady=3)
        self._controls.append(entry)
        self._button(self, "Pilih…", lambda: self.choose_file(previous=previous)).grid(row=row, column=3, sticky="w")

    def choose_file(self, previous=False):
        if self.busy:
            return
        path = filedialog.askopenfilename(parent=self.window,
            title=f"{self.product.label} — pilih lisensi {'lama' if previous else 'yang akan dibaca'}",
            filetypes=[("Berkas lisensi", "*.lic *.enc"), ("Semua berkas", "*.*")])
        if path:
            self.inputs["previous_license" if previous else "file"].set(path)
            self.status.set("Lisensi lama dipilih; Client ID dan Sequence diambil saat pembuatan."
                            if previous else "Berkas dipilih. Klik Baca isi atau Periksa.")

    def show_result(self, result):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", json.dumps(result, ensure_ascii=False, indent=2, default=str))
        self.output.configure(state="disabled")

    def _set_busy(self, busy):
        self.busy = busy
        for widget in self._controls:
            widget.state(["disabled"] if busy else ["!disabled"])
        if busy:
            self.progress.start(12)
        else:
            self.progress.stop()

    def _start_task(self, kind, operation, status, *, secrets=()):
        if self.busy or self._closed:
            return False
        self._set_busy(True)
        self.status.set(status)

        threading.Thread(target=_run_queued_task,
            args=(self._events, kind, operation, tuple(secrets)), daemon=True,
            name=f"jibas-{self.product.key}-{kind}").start()
        return True

    def _load_backend(self):
        return self._backend if self._backend is not None else importlib.import_module(self.product.codec_module)

    def _load_detector(self):
        return self._detector if self._detector is not None else importlib.import_module(self.product.detector_module)

    def _detect_db(self):
        # Read settings on the Tk thread; the worker only sees ordinary data.
        connection = dict(self._connection_supplier())
        operation = partial(_run_detector, self.product.detector_module, self._detector,
                            "database_id", connection)
        self._start_task("database_id", operation,
                         f"Mendeteksi Database ID {self.product.label}…",
                         secrets=(connection.get("password"),))

    def _detect_sys(self):
        operation = partial(_run_detector, self.product.detector_module, self._detector,
                            "system_id", {})
        self._start_task("system_id", operation,
                         f"Mendeteksi System ID {self.product.label}…")

    def run_action(self, action):
        if self.busy:
            return
        values = {key: variable.get().strip() for key, variable in self.inputs.items()}
        if action == "generate" and not values["file"]:
            destination = filedialog.asksaveasfilename(parent=self.window,
                title=f"Simpan lisensi {self.product.label}", initialfile=self.product.initial_file,
                defaultextension=".lic", filetypes=[("Lisensi impor", "*.lic"), ("Semua berkas", "*.*")])
            if not destination:
                return
            values["file"] = destination
        overwrite = self.overwrite.get()
        operation = partial(_run_product_action, self.product.codec_module, self._backend,
                            action, values, overwrite)
        self._start_task(action, operation,
                         f"Memproses {self.product.label}…")

    def _poll_events(self):
        if self._closed:
            return
        try:
            while True:
                state, kind, payload = self._events.get_nowait()
                self._set_busy(False)
                if state == "error":
                    self.status.set("Operasi belum berhasil. Lihat rincian hasil.")
                    self.show_result({"error": payload})
                    messagebox.showerror(self.product.label, payload, parent=self.window)
                elif kind in ("database_id", "system_id"):
                    value, info = payload
                    self.inputs[kind].set(value)
                    self.show_result(info)
                    self.status.set(f"{'Database ID' if kind == 'database_id' else 'System ID'}: {value}")
                else:
                    self.show_result(payload)
                    if kind == "generate":
                        self.inputs["file"].set(str(payload.get("path", "")))
                        valid = payload.get("verification", {}).get("valid")
                        self.status.set("File lisensi dibuat; pemeriksaan offline berhasil."
                                        if valid is True else "File dibuat. Periksa rincian sebelum diimpor.")
                    elif kind == "verify":
                        self.status.set("Pemeriksaan offline berhasil; aktivasi aplikasi belum dibuktikan."
                                        if payload.get("valid") is True else "Pemeriksaan belum lulus. Lihat hasil.")
                    else:
                        self.status.set("Isi berkas berhasil dibaca. Periksa field dan status pada hasil.")
        except queue.Empty:
            pass
        self._poll_id = self.after(50, self._poll_events)

    def close(self):
        self._closed = True
        if self._poll_id is not None:
            self.after_cancel(self._poll_id)
            self._poll_id = None
        self.progress.stop()

    def release_tk_references(self):
        """Release owned Variables on Tk's thread, after widgets are destroyed.

        Worker functions keep ordinary data only. Clearing these final owners
        prevents later cyclic GC in an unrelated worker from finalizing Tcl
        variables belonging to a window that has already closed.
        """
        self.inputs.clear()
        self.status = None
        self.overwrite = None
        self._controls.clear()
        self.output = None
        self.progress = None
        self._connection_supplier = None


class LicenseApp(ttk.Frame):
    def __init__(self, window, *, backends=None, detectors=None):
        super().__init__(window)
        self.window = window
        self._closed = False
        window.title("JIBAS — Generator Lisensi")
        screen_width, screen_height = window.winfo_screenwidth(), window.winfo_screenheight()
        width = min(880, max(1, screen_width - 40))
        height = min(710, max(1, screen_height - 80))
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height - 40) // 2)
        window.geometry(f"{width}x{height}+{x}+{y}")
        window.minsize(min(760, width), min(650, height))
        window.configure(background="#f4f6fa")
        style = ttk.Style(window)
        style.theme_use("clam")
        style.configure("TFrame", background="#f4f6fa")
        style.configure("TLabel", background="#f4f6fa", font=("Segoe UI", 9))
        style.configure("Title.TLabel", font=("Segoe UI", 15, "bold"), foreground="#183153")
        style.configure("Hint.TLabel", foreground="#637085", font=("Segoe UI", 8))
        style.configure("TEntry", padding=4, font=("Segoe UI", 9))
        style.configure("TButton", padding=(8, 5), font=("Segoe UI", 9))
        style.configure("TNotebook.Tab", padding=(18, 8), font=("Segoe UI", 10))
        style.configure("Accent.TButton", foreground="white", background="#2463b4")
        style.map("Accent.TButton", background=[("active", "#194e91")])
        self.pack(fill="both", expand=True)
        self.connection = {
            "host": os.environ.get("JIBAS_DB_HOST", "127.0.0.1"),
            "port": os.environ.get("JIBAS_DB_PORT", "3434"),
            "user": os.environ.get("JIBAS_DB_USER", "root"),
            "password": os.environ.get("JIBAS_DB_PASSWORD"),
        }
        try:
            self.connection["port"] = int(self.connection["port"])
        except ValueError:
            self.connection["port"] = 3434
        toolbar = ttk.Frame(self, padding=(12, 8))
        toolbar.pack(fill="x")
        ttk.Label(toolbar, text="Satu aplikasi untuk lisensi JIBAS", style="Hint.TLabel").pack(side="left")
        ttk.Button(toolbar, text="Koneksi Database…", command=self.configure_database).pack(side="right")
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)
        self.panels = {}
        for product in PRODUCTS:
            panel = LicensePanel(self.notebook, product,
                backend=(backends or {}).get(product.key), detector=(detectors or {}).get(product.key),
                connection_supplier=lambda: dict(self.connection))
            self.panels[product.key] = panel
            self.notebook.add(panel, text=product.label)
        window.bind("<Control-o>", lambda event: self.active_panel().choose_file())
        window.protocol("WM_DELETE_WINDOW", self.close)

    def active_panel(self):
        return self.nametowidget(self.notebook.select())

    def configure_database(self):
        dialog = tk.Toplevel(self.window)
        dialog.title("Koneksi Database")
        dialog.transient(self.window)
        dialog.resizable(False, False)
        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill="both", expand=True)
        values = {key: tk.StringVar(dialog, value="" if value is None else str(value))
                  for key, value in self.connection.items()}
        for row, (key, label) in enumerate((("host", "Host"), ("port", "Port"),
                                            ("user", "User"), ("password", "Password"))):
            ttk.Label(frame, text=label, width=13).grid(row=row, column=0, sticky="w", pady=4)
            entry = ttk.Entry(frame, textvariable=values[key], width=34,
                              show="•" if key == "password" else "")
            entry.grid(row=row, column=1, sticky="ew", pady=4)
        ttk.Label(frame, text="Dipakai untuk deteksi ID kedua tab. Hanya disimpan selama aplikasi terbuka.",
                  style="Hint.TLabel", wraplength=390).grid(row=4, column=0, columnspan=2, sticky="w", pady=(9, 12))

        def save():
            host, user = values["host"].get().strip(), values["user"].get().strip()
            try:
                port = int(values["port"].get())
                if not 1 <= port <= 65535 or not host or not user:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Koneksi Database", "Isi host/user dan port antara 1–65535.", parent=dialog)
                return
            self.connection = {"host": host, "port": port, "user": user,
                               "password": values["password"].get()}
            dialog.destroy()

        actions = ttk.Frame(frame)
        actions.grid(row=5, column=0, columnspan=2, sticky="e")
        ttk.Button(actions, text="Batal", command=dialog.destroy).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Gunakan", command=save).pack(side="left")
        dialog.bind("<Return>", lambda event: save())
        dialog.bind("<Escape>", lambda event: dialog.destroy())
        dialog.grab_set()
        dialog.focus_set()

    def close(self):
        if self._closed:
            return
        self._closed = True
        for panel in self.panels.values():
            panel.close()
        self.window.destroy()
        for panel in self.panels.values():
            panel.release_tk_references()
        self.panels.clear()
        self.notebook = None
        self.connection.clear()


def main():
    window = tk.Tk()
    LicenseApp(window)
    window.mainloop()


if __name__ == "__main__":
    main()
