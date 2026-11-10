"""Read-only Tkinter diagnostics. Run with python app.py.

Workers only queue plain data. All Tk work, including after() scheduling, runs
on the main thread. The legacy codec and verification rules are unchanged.
"""
from __future__ import annotations

from datetime import datetime
import json
import platform
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, font, ttk

import diagnostics

STATUS_TEXT = {
    "license_row": "Baris lisensi terbaca",
    "empty_cache": "Cache kosong; tidak ada baris lisensi",
    "checks_passed": "Pemeriksaan lokal lulus",
    "checks_failed": "Pemeriksaan lokal belum lulus",
}


def _work(action: str, values: dict[str, str], results: queue.Queue) -> None:
    """No widgets, Tk variables, after(), raw exceptions, or logging here."""
    try:
        result = (diagnostics.inspect_file(values["file"]) if action == "inspect" else
                  diagnostics.verify_file(values["file"], values["database_id"],
                                          values["system_id"], values["client_id"]))
        results.put({"ok": True, "result": result})
    except diagnostics.DiagnosticError as exc:
        results.put({"ok": False, "error": {"code": exc.code, "message": str(exc)}})
    except Exception:
        results.put({"ok": False, "error": {"code": "unexpected", "message": diagnostics.ERROR_MESSAGES["unexpected"]}})


class LicenseApp(ttk.Frame):
    """Keep the historical class name for existing launchers."""

    def __init__(self, window: tk.Tk) -> None:
        super().__init__(window, padding=20)
        self.window = window
        self.busy = False
        self.closed = False
        self.last_result: dict | None = None
        self._poll_id: str | None = None
        self._results: queue.Queue = queue.Queue(maxsize=1)
        self._active_values: dict[str, str] = {}
        self.inputs = {name: tk.StringVar() for name in
                       ("file", "database_id", "system_id", "client_id")}
        self.status = tk.StringVar(value="Siap. Pilih berkas untuk mulai memeriksa.")
        self.summary = tk.StringVar(value="Belum ada pemeriksaan")
        self.metadata = tk.StringVar(value="Ukuran dan sidik SHA-256 akan tampil setelah berkas dibaca.")
        window.title("JIBAS Diagnostics | Pemeriksaan lokal")
        window.geometry("1040x740")
        window.minsize(760, 600)
        self._style()
        self.pack(fill="both", expand=True)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="JIBAS Diagnostics", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="PEMERIKSAAN LOKAL", style="Badge.TLabel").grid(row=0, column=1, sticky="e")
        ttk.Label(header, text="Baca berkas, pahami hasil, dan periksa batasannya.",
                  style="Muted.TLabel").grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))
        self._file_bar()
        self.tabs = ttk.Notebook(self)
        self.tabs.grid(row=2, column=0, sticky="nsew", pady=(16, 12))
        self.overview = self._page("Ringkasan")
        self.inspector = self._page("Inspektor Berkas")
        self.verification = self._page("Diagnostik Lokal")
        self.activity_page = self._page("Aktivitas & Hasil")
        self._overview_page()
        self._inspector_page()
        self._verification_page()
        self._activity_page()
        footer = ttk.Frame(self)
        footer.grid(row=3, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        self.status_label = ttk.Label(footer, textvariable=self.status, style="Muted.TLabel", wraplength=700)
        self.status_label.grid(row=0, column=0, sticky="w", padx=(0, 12))
        self.progress = ttk.Progressbar(footer, mode="indeterminate", length=100)
        self.progress.grid(row=0, column=1, sticky="e")
        for variable in self.inputs.values():
            variable.trace_add("write", self._input_changed)
        window.bind("<Control-o>", lambda _event: self.choose_file())
        window.bind("<Control-Return>", lambda _event: self.run_action("verify"))
        window.bind("<Control-Shift-C>", lambda _event: self.copy_result())
        window.bind("<Configure>", self._resize, add="+")
        window.protocol("WM_DELETE_WINDOW", self.close)
        self._sync_buttons()
        self._log("Aplikasi siap; belum ada sumber data yang dibaca.")
        self.file_entry.focus_set()

    def _style(self) -> None:
        families = set(font.families(self.window))
        family = next((name for name in ("Segoe UI", "DejaVu Sans", "Liberation Sans")
                       if name in families), font.nametofont("TkDefaultFont").actual("family"))
        font.nametofont("TkDefaultFont").configure(family=family, size=10)
        font.nametofont("TkTextFont").configure(family=family, size=10)
        style = ttk.Style(self.window)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        self.window.configure(background="#f3f6fb")
        style.configure(".", font=(family, 10))
        style.configure("TFrame", background="#f3f6fb")
        style.configure("TLabel", background="#f3f6fb", foreground="#182c46")
        style.configure("Title.TLabel", font=(family, 22, "bold"))
        style.configure("Heading.TLabel", font=(family, 14, "bold"))
        style.configure("Muted.TLabel", foreground="#53657b")
        style.configure("Badge.TLabel", foreground="#165a65", background="#dceff0", padding=(12, 6))
        style.configure("TButton", padding=(12, 8))
        style.configure("Accent.TButton", background="#215caa", foreground="#ffffff")
        style.map("Accent.TButton", background=[("disabled", "#b1bdce"), ("active", "#174780")])
        style.configure("TEntry", padding=7)
        style.configure("TNotebook", background="#f3f6fb", borderwidth=0)
        style.configure("TNotebook.Tab", padding=(12, 9))
        style.map("TNotebook.Tab", background=[("selected", "#ffffff")])
        style.configure("Treeview", rowheight=30, background="#ffffff", fieldbackground="#ffffff")
        style.configure("Treeview.Heading", font=(family, 10, "bold"), padding=7)

    def _file_bar(self) -> None:
        bar = ttk.Frame(self)
        bar.grid(row=1, column=0, sticky="ew")
        bar.columnconfigure(0, weight=1)
        ttk.Label(bar, text="Berkas sumber (.lic / .enc)").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 6))
        self.file_entry = ttk.Entry(bar, textvariable=self.inputs["file"])
        self.file_entry.grid(row=1, column=0, sticky="ew", padx=(0, 8))
        self.browse_button = ttk.Button(bar, text="Pilih berkas", command=self.choose_file)
        self.browse_button.grid(row=1, column=1, padx=(0, 8))
        self.inspect_button = ttk.Button(bar, text="Baca berkas", style="Accent.TButton",
                                         command=lambda: self.run_action("inspect"))
        self.inspect_button.grid(row=1, column=2)

    def _page(self, title: str) -> ttk.Frame:
        page = ttk.Frame(self.tabs, padding=18)
        page.columnconfigure(0, weight=1)
        self.tabs.add(page, text=title)
        return page

    def _overview_page(self) -> None:
        ttk.Label(self.overview, text="Diagnostik berkas, tanpa mengubah sumber", style="Heading.TLabel").grid(row=0, column=0, sticky="w")
        self.overview_body = ttk.Label(self.overview, justify="left", wraplength=880, text=(
            "1. Pilih salinan berkas yang sudah tersedia, lalu tekan Baca berkas.\n\n"
            "2. Lihat metadata pada Inspektor Berkas. Identitas dan teks bebas disembunyikan.\n\n"
            "3. Untuk pemeriksaan lokal, isi ID dari sumber resmi pada tab Diagnostik Lokal.\n\n"
            "4. Salin laporan yang sudah disamarkan dari Aktivitas & Hasil."))
        self.overview_body.grid(row=1, column=0, sticky="nw", pady=(18, 20))
        ttk.Separator(self.overview).grid(row=2, column=0, sticky="ew")
        self.overview_note = ttk.Label(self.overview, text=diagnostics.LIMITATIONS[0],
                                       style="Muted.TLabel", wraplength=880)
        self.overview_note.grid(row=3, column=0, sticky="w", pady=(16, 12))
        ttk.Label(self.overview, text=f"Python {sys.version_info.major}.{sys.version_info.minor}  |  "
                  f"Tk {tk.TkVersion}  |  {platform.system()}", style="Muted.TLabel").grid(row=4, column=0, sticky="w")

    def _tree(self, page: ttk.Frame, columns: tuple[str, ...], headings: tuple[str, ...], row: int) -> ttk.Treeview:
        holder = ttk.Frame(page)
        holder.grid(row=row, column=0, sticky="nsew", pady=(12, 0))
        holder.columnconfigure(0, weight=1)
        holder.rowconfigure(0, weight=1)
        page.rowconfigure(row, weight=1)
        tree = ttk.Treeview(holder, columns=columns, show="headings", height=6)
        for column, heading in zip(columns, headings):
            tree.heading(column, text=heading)
            tree.column(column, width=240, minwidth=100, stretch=True)
        tree.grid(row=0, column=0, sticky="nsew")
        vertical = ttk.Scrollbar(holder, orient="vertical", command=tree.yview)
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal = ttk.Scrollbar(holder, orient="horizontal", command=tree.xview)
        horizontal.grid(row=1, column=0, sticky="ew")
        tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        return tree

    def _inspector_page(self) -> None:
        ttk.Label(self.inspector, textvariable=self.summary, style="Heading.TLabel").grid(row=0, column=0, sticky="w")
        self.metadata_label = ttk.Label(self.inspector, textvariable=self.metadata, style="Muted.TLabel", wraplength=880)
        self.metadata_label.grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.fields = self._tree(self.inspector, ("field", "value"), ("Kolom", "Nilai yang dapat ditampilkan"), 2)

    def _verification_page(self) -> None:
        form = ttk.Frame(self.verification)
        form.grid(row=0, column=0, sticky="ew")
        for column in range(3):
            form.columnconfigure(column, weight=1)
        self.id_entries = []
        for column, (key, label) in enumerate((("database_id", "Database ID"), ("system_id", "System ID"),
                                               ("client_id", "Client ID (opsional)"))):
            ttk.Label(form, text=label).grid(row=0, column=column, sticky="w")
            entry = ttk.Entry(form, textvariable=self.inputs[key], width=12)
            entry.grid(row=1, column=column, sticky="ew", padx=(0, 8) if column < 2 else 0, pady=(6, 0))
            self.id_entries.append(entry)
        actions = ttk.Frame(self.verification)
        actions.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        actions.columnconfigure(0, weight=1)
        self.verify_hint = ttk.Label(actions, text="Gunakan ID dari sumber resmi; tidak ada deteksi basis data.",
                                     style="Muted.TLabel", wraplength=600)
        self.verify_hint.grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.verify_button = ttk.Button(actions, text="Periksa lokal", command=lambda: self.run_action("verify"))
        self.verify_button.grid(row=0, column=1, sticky="e")
        self.checks = self._tree(self.verification, ("check", "status"), ("Pemeriksaan", "Status"), 2)
        self.checks.column("check", width=500)
        self.checks.column("status", width=130)
        self.checks.tag_configure("passed", foreground="#17633f")
        self.checks.tag_configure("failed", foreground="#a22b30")
        self.limitations_label = ttk.Label(self.verification, text="\n".join(diagnostics.LIMITATIONS[:4]),
                                            style="Muted.TLabel", wraplength=880, justify="left")
        self.limitations_label.grid(row=3, column=0, sticky="w", pady=(12, 0))

    def _activity_page(self) -> None:
        bar = ttk.Frame(self.activity_page)
        bar.grid(row=0, column=0, sticky="ew")
        bar.columnconfigure(0, weight=1)
        ttk.Label(bar, text="Laporan yang disamarkan", style="Heading.TLabel").grid(row=0, column=0, sticky="w")
        self.copy_button = ttk.Button(bar, text="Salin hasil", command=self.copy_result)
        self.copy_button.grid(row=0, column=1, padx=(8, 0))
        self.activity_page.rowconfigure(1, weight=1)
        self.output = self._text(self.activity_page, 1, 7)
        ttk.Label(self.activity_page, text="Aktivitas sesi", style="Muted.TLabel").grid(row=2, column=0, sticky="w", pady=(12, 0))
        self.activity = self._text(self.activity_page, 3, 3)

    def _text(self, page: ttk.Frame, row: int, height: int) -> tk.Text:
        holder = ttk.Frame(page)
        holder.grid(row=row, column=0, sticky="nsew", pady=(8, 0))
        holder.columnconfigure(0, weight=1)
        holder.rowconfigure(0, weight=1)
        widget = tk.Text(holder, height=height, wrap="word", state="disabled", font="TkTextFont",
                         background="#ffffff", foreground="#182c46", relief="flat", padx=12, pady=10)
        widget.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(holder, orient="vertical", command=widget.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        widget.configure(yscrollcommand=scrollbar.set)
        return widget

    @staticmethod
    def _set_text(widget: tk.Text, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def _log(self, message: str) -> None:
        self.activity.configure(state="normal")
        self.activity.insert("end", f"{datetime.now():%H:%M:%S}  {message}\n")
        if int(self.activity.index("end-1c").split(".")[0]) > 200:
            self.activity.delete("1.0", "2.0")
        self.activity.see("end")
        self.activity.configure(state="disabled")

    def _resize(self, event) -> None:
        if event.widget is self.window:
            width = max(300, event.width - 90)
            for label in (self.overview_body, self.overview_note, self.metadata_label, self.limitations_label):
                label.configure(wraplength=width)
            self.verify_hint.configure(wraplength=max(200, width - 160))
            self.status_label.configure(wraplength=max(250, width - 120))

    def _clear_result(self) -> None:
        self.last_result = None
        self.fields.delete(*self.fields.get_children())
        self.checks.delete(*self.checks.get_children())
        self.summary.set("Belum ada pemeriksaan untuk input ini")
        self.metadata.set("Baca ulang setelah mengubah berkas atau ID.")
        self._set_text(self.output, "")

    def _input_changed(self, *_args) -> None:
        self._clear_result()
        self.status.set("Input berubah. Jalankan pemeriksaan untuk input ini.")
        self._sync_buttons()

    def _sync_buttons(self) -> None:
        has_file = bool(self.inputs["file"].get().strip())
        for widget in (self.file_entry, self.browse_button, *self.id_entries):
            widget.configure(state="disabled" if self.busy else "normal")
        self.inspect_button.configure(state="normal" if has_file and not self.busy else "disabled")
        self.verify_button.configure(state="normal" if has_file and not self.busy else "disabled")
        self.copy_button.configure(state="normal" if self.last_result and not self.busy else "disabled")

    def choose_file(self) -> None:
        if self.busy or self.closed:
            return
        path = filedialog.askopenfilename(parent=self.window, title="Pilih berkas untuk pemeriksaan lokal",
                                         filetypes=[("Berkas lisensi", "*.lic *.enc"), ("Semua berkas", "*.*")])
        if path:
            self.inputs["file"].set(path)
            self._log("Berkas dipilih. Path tidak dicatat dalam log.")

    def run_action(self, action: str) -> None:
        if self.busy or self.closed or action not in ("inspect", "verify"):
            return
        self._active_values = {key: value.get().strip() for key, value in self.inputs.items()}
        self._clear_result()
        self.busy = True
        self._sync_buttons()
        self.status.set("Membaca berkas..." if action == "inspect" else "Menjalankan pemeriksaan lokal...")
        self._log("Pembacaan berkas dimulai." if action == "inspect" else "Pemeriksaan lokal dimulai.")
        self.progress.start(12)
        self.tabs.select(self.inspector if action == "inspect" else self.verification)
        try:
            threading.Thread(target=_work, args=(action, dict(self._active_values), self._results), daemon=True).start()
        except RuntimeError:
            self._results.put({"ok": False, "error": {"code": "unexpected", "message": diagnostics.ERROR_MESSAGES["unexpected"]}})
        self._poll_id = self.window.after(40, self._poll)

    def _poll(self) -> None:
        self._poll_id = None
        if self.closed:
            return
        try:
            outcome = self._results.get_nowait()
        except queue.Empty:
            self._poll_id = self.window.after(40, self._poll)
            return
        self.progress.stop()
        self.busy = False
        current = {key: value.get().strip() for key, value in self.inputs.items()}
        if current != self._active_values:
            self.status.set("Input berubah selama pemeriksaan. Jalankan ulang.")
        else:
            self.last_result = outcome
            self._set_text(self.output, json.dumps(outcome, ensure_ascii=False, indent=2))
            if outcome["ok"]:
                result = outcome["result"]
                self.summary.set(STATUS_TEXT[result["status"]])
                self.metadata.set(f"Ukuran: {result['size_bytes']:,} byte\nSHA-256: {result['sha256']}")
                for key, value in result["fields"].items():
                    self.fields.insert("", "end", values=(key, value))
                for check in result["checks"]:
                    passed = check["passed"]
                    self.checks.insert("", "end", values=(check["detail"], "Lulus" if passed else "Belum lulus"),
                                       tags=("passed" if passed else "failed",))
                self.status.set(self.summary.get() + ". Aktivasi penerbit belum diverifikasi.")
                self._log(self.summary.get() + ".")
            else:
                self.summary.set("Berkas belum dapat diperiksa")
                self.status.set(outcome["error"]["message"])
                self._log("Operasi belum berhasil (" + outcome["error"]["code"] + ").")
                self.tabs.select(self.activity_page)
        self._sync_buttons()

    def copy_result(self) -> None:
        if self.busy or self.closed or self.last_result is None:
            return
        try:
            self.window.clipboard_clear()
            self.window.clipboard_append(json.dumps(self.last_result, ensure_ascii=False, indent=2))
            self.status.set("Laporan yang disamarkan disalin ke clipboard.")
        except tk.TclError:
            self.status.set("Clipboard tidak tersedia. Pilih dan salin teks pada tab hasil.")

    def close(self) -> None:
        self.closed = True
        if self._poll_id is not None:
            self.window.after_cancel(self._poll_id)
            self._poll_id = None
        self.progress.stop()
        self.window.destroy()


def main() -> None:
    window = tk.Tk()
    LicenseApp(window)
    window.mainloop()


if __name__ == "__main__":
    main()
