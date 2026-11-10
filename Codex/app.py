"""Manual-input desktop app for FACE, SchoolPay, and CBE license workflows.

Tk operations stay on the main thread. Each tab owns its inputs, backend,
background task queue, and results, so switching tabs does not mix products.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import partial
import importlib
import json
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
    capacity_label: str
    initial_file: str


PRODUCTS = (
    Product("face", "Absensi Wajah", "Face Server 16.5 / Client FACE 16.10",
            "license_codec", "Kapasitas wajah", "absensi-wajah.lic"),
    Product("schoolpay", "SchoolPay", "SchoolPay Secure Server 10.5",
            "schoolpay_codec", "Kapasitas vendor", "schoolpay.lic"),
    Product("cbe", "CBE Server", "CBE Server 26.5",
            "cbe_codec", "Kapasitas klien", "cbe-server.lic"),
)


def _run_queued_task(events, kind, operation):
    """Worker entry point: never retain widgets, variables, or their owner."""
    try:
        result = operation()
    except Exception as exc:
        detail = str(exc)
        events.put(("error", kind, detail))
    else:
        events.put(("result", kind, result))


def _run_product_action(module_name, backend, action, values, overwrite):
    module = backend if backend is not None else importlib.import_module(module_name)
    return run_backend_action(module, action, values, overwrite=overwrite)


def run_backend_action(backend, action: str, values: dict, *, overwrite=False) -> dict:
    """Execute a snapshot of a form without reading or writing Tk objects."""
    if action == "inspect":
        if not values["file"]:
            raise ValueError("Pilih berkas lisensi terlebih dahulu.")
        return backend.inspect_license(Path(values["file"]))
    if action not in ("verify", "generate"):
        raise ValueError("Operasi tidak dikenal.")
    if not values["database_id"] or not values["system_id"]:
        raise ValueError("Isi Database ID dan System ID mesin tujuan secara manual.")
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
    if values["client_id"] and not values["previous_license"]:
        raise ValueError("Untuk perpanjangan, pilih berkas lisensi lama agar urutan diperbarui otomatis.")
    if not values["file"]:
        raise ValueError("Pilih lokasi keluaran terlebih dahulu.")
    return backend.generate_license(
        database_id=values["database_id"], system_id=values["system_id"],
        client_id=values["client_id"] or None, expires=values["expires"],
        capacity=capacity, output_path=values["file"], client_name=values["client_name"],
        previous_license_path=Path(values["previous_license"]) if values["previous_license"] else None,
        sequence=None, overwrite=overwrite)


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
    def __init__(self, parent, product: Product, *, backend=None):
        super().__init__(parent, padding=12)
        self.window = self.winfo_toplevel()
        self.product = product
        self._backend = backend
        self._events = queue.Queue()
        self._closed = False
        self.busy = False
        self._controls = []
        self.columnconfigure(1, weight=1)
        self.columnconfigure(3, weight=1)
        # Surplus window height stays below the form; results remain six lines.
        self.rowconfigure(12, weight=1)
        self.inputs = {key: tk.StringVar(self) for key in (
            "database_id", "system_id", "client_id", "client_name", "capacity",
            "file", "previous_license")}
        self.inputs["expires"] = tk.StringVar(self, value=(date.today() + timedelta(days=365)).isoformat())
        self.overwrite = tk.BooleanVar(self, value=False)
        self.status = tk.StringVar(self, value=f"Siap — {product.label}. Isi ID mesin tujuan secara manual.")

        ttk.Label(self, text=product.label, style="Title.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
        ttk.Label(self, text=product.subtitle, style="Hint.TLabel").grid(
            row=0, column=2, columnspan=2, sticky="e")
        self._field(1, 0, "Database ID", "database_id", "Database ID dari instalasi produk yang dipilih")
        self._field(1, 2, "System ID", "system_id", "Isi System ID mesin tujuan secara manual")
        self._field(2, 0, "Client ID", "client_id", "Kosongkan untuk lisensi baru; pertahankan untuk perpanjangan")
        self._field(2, 2, "Nama klien", "client_name", "Opsional")
        self._field(3, 0, "Berlaku sampai", "expires", "Format YYYY-MM-DD")
        capacity_hint = ("Maksimum koneksi CBE Client bersamaan" if product.key == "cbe"
                         else "Bilangan bulat lebih dari nol")
        self._field(3, 2, product.capacity_label, "capacity", capacity_hint)
        ttk.Label(self, text="Perpanjangan: pilih lisensi lama; Client ID dipertahankan, urutan naik otomatis.",
                  style="Hint.TLabel").grid(row=4, column=0, columnspan=4, sticky="w", pady=(4, 5))
        self._browse_row(5, "Lisensi lama", "previous_license", previous=True)
        ttk.Separator(self).grid(row=6, column=0, columnspan=4, sticky="ew", pady=7)
        self._browse_row(7, "Berkas lisensi", "file", previous=False)

        output_frame = ttk.Frame(self)
        output_frame.grid(row=8, column=0, columnspan=4, sticky="ew", pady=5)
        output_frame.columnconfigure(0, weight=1)
        ttk.Label(output_frame, text="Hasil", style="Hint.TLabel").grid(row=0, column=0, sticky="w")
        self.output = tk.Text(output_frame, wrap="word", height=6, state="disabled",
                              background="white", foreground="#22324b", relief="solid",
                              borderwidth=1, font=("Consolas", 9), padx=10, pady=8)
        self.output.grid(row=1, column=0, sticky="ew", pady=(3, 0))
        scrollbar = ttk.Scrollbar(output_frame, orient="vertical", command=self.output.yview)
        scrollbar.grid(row=1, column=1, sticky="ns", pady=(3, 0))
        self.output.configure(yscrollcommand=scrollbar.set)

        actions = ttk.Frame(self)
        actions.grid(row=9, column=0, columnspan=4, sticky="ew", pady=(3, 0))
        actions.columnconfigure(2, weight=1)
        self._button(actions, "Baca isi", lambda: self.run_action("inspect")).grid(row=0, column=0, padx=(0, 6))
        self._button(actions, "Periksa", lambda: self.run_action("verify")).grid(row=0, column=1)
        overwrite_box = ttk.Checkbutton(actions, text="Timpa berkas keluaran", variable=self.overwrite)
        overwrite_box.grid(row=0, column=2, sticky="w", padx=8)
        self._controls.append(overwrite_box)
        self._button(actions, "Buat & simpan…", lambda: self.run_action("generate"),
                     style="Accent.TButton").grid(row=0, column=3)
        self.progress = ttk.Progressbar(self, mode="indeterminate")
        self.progress.grid(row=10, column=0, columnspan=4, sticky="ew", pady=(7, 0))
        ttk.Label(self, textvariable=self.status, style="Hint.TLabel", wraplength=790).grid(
            row=11, column=0, columnspan=4, sticky="w", pady=(5, 0))
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
            self.status.set("Lisensi lama dipilih; Client ID dan urutan diperbarui otomatis saat pembuatan."
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

    def _start_task(self, kind, operation, status):
        if self.busy or self._closed:
            return False
        self._set_busy(True)
        self.status.set(status)

        threading.Thread(target=_run_queued_task,
            args=(self._events, kind, operation), daemon=True,
            name=f"jibas-{self.product.key}-{kind}").start()
        return True

    def _load_backend(self):
        return self._backend if self._backend is not None else importlib.import_module(self.product.codec_module)

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


class LicenseApp(ttk.Frame):
    def __init__(self, window, *, backends=None):
        super().__init__(window)
        self.window = window
        self._closed = False
        window.title("JIBAS — Generator Lisensi")
        screen_width, screen_height = window.winfo_screenwidth(), window.winfo_screenheight()
        width = min(880, max(1, screen_width - 40))
        height = min(650, max(1, screen_height - 80))
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height - 40) // 2)
        window.geometry(f"{width}x{height}+{x}+{y}")
        window.minsize(min(760, width), min(560, height))
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
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)
        self.panels = {}
        for product in PRODUCTS:
            panel = LicensePanel(self.notebook, product, backend=(backends or {}).get(product.key))
            self.panels[product.key] = panel
            self.notebook.add(panel, text=product.label)
        window.bind("<Control-o>", lambda event: self.active_panel().choose_file())
        window.protocol("WM_DELETE_WINDOW", self.close)

    def active_panel(self):
        return self.nametowidget(self.notebook.select())

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


def main():
    window = tk.Tk()
    LicenseApp(window)
    window.mainloop()


if __name__ == "__main__":
    main()
