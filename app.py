"""Windows desktop interface for the JIBAS Face Server 16.5 license tool.

Same layout as the proven 16.5-era tool, extended with automatic
Database ID / System ID detection (jbssat splang recipe + WMI) and an
overwrite switch. Runs the same engine as cli.py (license_codec, id_detect).
Launch with "Jalankan GUI.cmd".

Compact variant: identical features, tighter geometry (two field columns,
row-height trimmed, tooltips carry the formerly inline hints).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
import json
from pathlib import Path
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import id_detect
import license_codec


class _Tooltip:
    """Show extra hint text near a widget while it is hovered."""

    def __init__(self, widget: tk.Widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self.tip: tk.Toplevel | None = None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _show(self, _event=None) -> None:
        if self.tip is not None:
            return
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        tk.Label(self.tip, text=self.text, justify="left",
                 background="#fffbe6", foreground="#183153", relief="solid",
                 borderwidth=1, font=("Segoe UI", 8), padx=7, pady=3).pack()

    def _hide(self, _event=None) -> None:
        if self.tip is not None:
            self.tip.destroy()
            self.tip = None


class LicenseApp(ttk.Frame):
    def __init__(self, window: tk.Tk) -> None:
        super().__init__(window, padding=12)
        self.window = window
        window.title("JIBAS Face Server 16.5 — Perangkat Lisensi (OpenCode)")
        window.geometry("760x600")
        window.minsize(660, 540)
        window.configure(background="#f4f6fa")
        self.pack(fill="both", expand=True)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(3, weight=1)
        self.inputs = {
            key: tk.StringVar() for key in
            ("database_id", "system_id", "client_id", "client_name", "capacity",
             "file", "previous_license", "sequence")
        }
        self.inputs["expires"] = tk.StringVar(
            value=(date.today() + timedelta(days=365)).isoformat()
        )
        self.overwrite = tk.BooleanVar(value=False)
        self.status = tk.StringVar(
            value="Siap. Tombol deteksi mengisi Database ID dari MySQL jbssat "
                  "dan System ID dari WMI, persis seperti aplikasi asli.")
        style = ttk.Style(window)
        style.theme_use("clam")
        style.configure("TFrame", background="#f4f6fa")
        style.configure("TLabel", background="#f4f6fa", font=("Segoe UI", 9))
        style.configure("Title.TLabel", font=("Segoe UI", 15, "bold"), foreground="#183153")
        style.configure("Hint.TLabel", foreground="#637085", font=("Segoe UI", 8))
        style.configure("TEntry", padding=4, font=("Segoe UI", 9))
        style.configure("TButton", padding=(8, 4), font=("Segoe UI", 9))
        style.configure("Accent.TButton", foreground="white", background="#2463b4")
        style.map("Accent.TButton", background=[("active", "#194e91")])
        ttk.Label(self, text="Perangkat Lisensi", style="Title.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w"
        )
        ttk.Label(self, text="JIBAS Face Server 16.5", style="Hint.TLabel").grid(
            row=0, column=2, columnspan=2, sticky="e"
        )
        self._field(1, 0, "Database ID", "database_id", "Contoh: V4YNE")
        self._field(1, 2, "System ID", "system_id", "Contoh: 7738F (bukan DDCB4)")
        self._field(2, 0, "Client ID", "client_id", "Opsional; untuk perpanjangan")
        self._field(2, 2, "Nama klien", "client_name", "Opsional")
        self._field(3, 0, "Berlaku sampai", "expires", "Format YYYY-MM-DD")
        self._field(3, 2, "Kapasitas wajah", "capacity", "Bilangan bulat > 0")
        self._field(4, 0, "Sequence", "sequence", "Opsional; otomatis naik untuk perpanjangan")
        ttk.Label(self, text="(mengosongkan = 1)", style="Hint.TLabel").grid(
            row=4, column=2, columnspan=2, sticky="w", padx=(8, 0)
        )
        detect_row = ttk.Frame(self)
        detect_row.grid(row=5, column=0, columnspan=4, sticky="w", pady=(4, 2))
        db_button = ttk.Button(detect_row, text="Deteksi Database ID",
                               command=self._detect_db)
        db_button.grid(row=0, column=0, padx=(0, 6))
        sys_button = ttk.Button(detect_row, text="Deteksi System ID",
                                command=self._detect_sys)
        sys_button.grid(row=0, column=1, padx=(0, 6))
        ttk.Label(detect_row, text="Resep splang asli (0x06000AC3) + WMI (0x0600059B).",
                  style="Hint.TLabel").grid(row=0, column=2, sticky="w")
        _Tooltip(db_button, "Deteksi Database ID dari MySQL jbssat "
                            "memakai resep prosedur splang asli (0x06000AC3); "
                            "hasil mengisi kolom Database ID.")
        _Tooltip(sys_button, "Deteksi System ID dari WMI (0x0600059B): "
                             "serial fisik disk + UUID, persis prosedur asli.")
        self._browse_row(6, "Lisensi lama", "previous_license",
                         "Pilih untuk perpanjangan…", previous=True,
                         hint="Berkas lisensi sebelumnya untuk perpanjangan; "
                              "Client ID dan Sequence otomatis diambil dari "
                              "berkas ini.")
        ttk.Separator(self).grid(row=7, column=0, columnspan=4, sticky="ew", pady=(6, 6))
        self._browse_row(8, "Berkas lisensi", "file",
                         "Pilih…", previous=False,
                         hint="Berkas yang dibaca/diperiksa; berisi juga "
                              "lokasi simpan hasil Buat & simpan.")
        output_frame = ttk.Frame(self)
        output_frame.grid(row=9, column=0, columnspan=4, sticky="nsew", pady=(4, 4))
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(1, weight=1)
        ttk.Label(output_frame, text="Hasil", style="Hint.TLabel").grid(
            row=0, column=0, sticky="w")
        self.output = tk.Text(
            output_frame, wrap="word", height=6, state="disabled",
            background="white", foreground="#22324b", relief="solid",
            borderwidth=1, font=("Consolas", 9), padx=10, pady=8,
        )
        self.output.grid(row=1, column=0, sticky="nsew", pady=(3, 0))
        scrollbar = ttk.Scrollbar(output_frame, orient="vertical", command=self.output.yview)
        scrollbar.grid(row=1, column=1, sticky="ns", pady=(3, 0))
        self.output.configure(yscrollcommand=scrollbar.set)
        actions = ttk.Frame(self)
        actions.grid(row=10, column=0, columnspan=4, sticky="ew")
        actions.columnconfigure(2, weight=1)
        ttk.Button(actions, text="Baca isi", command=lambda: self.run_action("inspect")).grid(
            row=0, column=0, padx=(0, 6)
        )
        ttk.Button(actions, text="Periksa", command=lambda: self.run_action("verify")).grid(
            row=0, column=1
        )
        ttk.Checkbutton(actions, text="Timpa berkas keluaran",
                        variable=self.overwrite).grid(row=0, column=2, sticky="w", padx=(6, 6))
        ttk.Button(actions, text="Buat & simpan…", style="Accent.TButton",
                   command=lambda: self.run_action("generate")).grid(row=0, column=3)
        ttk.Label(self, textvariable=self.status, style="Hint.TLabel",
                  wraplength=720).grid(row=11, column=0, columnspan=4, sticky="w", pady=(8, 0))
        self.rowconfigure(9, weight=1)
        window.bind("<Control-o>", lambda event: self.choose_file())

    def _field(self, row: int, column: int, label: str, key: str, hint: str) -> None:
        ttk.Label(self, text=label, width=13, anchor="w").grid(
            row=row, column=column, sticky="w", pady=2
        )
        entry = ttk.Entry(self, textvariable=self.inputs[key])
        entry.grid(row=row, column=column + 1, sticky="ew", padx=(0, 10), pady=2)
        _Tooltip(entry, hint)

    def _browse_row(self, row: int, label: str, key: str, button_text: str,
                    previous: bool, hint: str = "") -> None:
        ttk.Label(self, text=label, width=13, anchor="w").grid(
            row=row, column=0, sticky="w", pady=2
        )
        entry = ttk.Entry(self, textvariable=self.inputs[key])
        entry.grid(row=row, column=1, columnspan=2, sticky="ew", padx=(0, 6), pady=2)
        if hint:
            _Tooltip(entry, hint)
        ttk.Button(self, text=button_text,
                   command=lambda: self.choose_file(previous=previous)).grid(
            row=row, column=3, sticky="w"
        )

    def choose_file(self, previous: bool = False) -> None:
        path = filedialog.askopenfilename(
            parent=self.window,
            title="Pilih lisensi sebelumnya" if previous else "Pilih berkas lisensi",
            filetypes=[("Berkas lisensi", "*.lic *.enc"),
                       ("Lisensi impor", "*.lic"), ("Cache lisensi", "*.enc"),
                       ("Semua berkas", "*.*")],
        )
        if path:
            self.inputs["previous_license" if previous else "file"].set(path)
            self.status.set(
                "Lisensi sebelumnya dipilih; Client ID dan Sequence diambil dari berkas ini."
                if previous else "Berkas dipilih. Klik Baca isi atau Periksa.")

    def show_result(self, result: dict) -> None:
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert(
            "1.0", json.dumps(result, ensure_ascii=False, indent=2, default=str))
        self.output.configure(state="disabled")

    # ---------- detection ----------
    def _detect_db(self) -> None:
        def work():
            try:
                dbid, info = id_detect.DbIdDetector().detect()
                self.window.after(0, self._apply_db, dbid, info)
            except id_detect.DetectError as exc:
                self.window.after(0, messagebox.showwarning,
                                  "Deteksi Database ID", str(exc))
        threading.Thread(target=work, daemon=True).start()
        self.status.set("Membaca prosedur splang jbssat…")

    def _apply_db(self, dbid, info):
        self.inputs["database_id"].set(dbid)
        pieces = ", ".join("%s[%d]=%s" % (p["variable"], p["position"], p["character"])
                           for p in info["pieces"])
        self.status.set("Database ID: %s (%s)" % (dbid, pieces))
        self.show_result(info)

    def _detect_sys(self) -> None:
        def work():
            try:
                sysid, info = id_detect.SystemIdDetector().detect()
                self.window.after(0, self._apply_sys, sysid, info)
            except id_detect.DetectError as exc:
                self.window.after(0, messagebox.showwarning,
                                  "Deteksi System ID", str(exc))
        threading.Thread(target=work, daemon=True).start()
        self.status.set("Membaca WMI (serial fisik disk + UUID)…")

    def _apply_sys(self, sysid, info):
        self.inputs["system_id"].set(sysid)
        self.status.set("System ID: %s — disk %s, UUID %s"
                        % (sysid, info["disk_serial_raw"], info["csproduct_uuid"]))
        self.show_result(info)

    # ---------- actions ----------
    def run_action(self, action: str) -> None:
        values = {key: variable.get().strip() for key, variable in self.inputs.items()}
        try:
            if action in ("verify", "generate"):
                if not values["database_id"] or not values["system_id"]:
                    raise ValueError("Database ID dan System ID harus diisi "
                                     "(atau pakai tombol deteksi).")
            if action in ("inspect", "verify"):
                if not values["file"]:
                    raise ValueError("Pilih berkas lisensi terlebih dahulu.")
            sequence = None
            capacity = None
            if action == "generate":
                datetime.strptime(values["expires"], "%Y-%m-%d")
                try:
                    capacity = int(values["capacity"])
                except ValueError as exc:
                    raise ValueError("Kapasitas harus berupa bilangan bulat lebih dari nol.") from exc
                if capacity < 1:
                    raise ValueError("Kapasitas harus lebih dari nol.")
                if values["sequence"]:
                    try:
                        sequence = int(values["sequence"])
                    except ValueError as exc:
                        raise ValueError("Sequence harus berupa bilangan bulat.") from exc
                    if not 1 <= sequence <= 2_147_483_647:
                        raise ValueError("Sequence harus antara 1 dan 2147483647.")
            if action == "inspect":
                result = license_codec.inspect_license(Path(values["file"]))
                self.status.set("Isi berkas berhasil dibaca. Lihat hasil pemeriksaan untuk status validitas.")
            elif action == "verify":
                result = license_codec.verify_license(
                    Path(values["file"]), values["database_id"], values["system_id"],
                    client_id=values["client_id"] or None,
                )
                self.status.set(
                    "Pemeriksaan berkas offline berhasil; aktivasi server belum dibuktikan."
                    if result.get("valid") is True
                    else "Pemeriksaan berkas gagal atau belum lengkap. Lihat rincian hasil.")
            else:
                destination = values["file"] or filedialog.asksaveasfilename(
                    parent=self.window, title="Simpan lisensi baru",
                    initialfile="license-baru.lic", defaultextension=".lic",
                    filetypes=[("Lisensi impor", "*.lic"), ("Cache lisensi", "*.enc"),
                               ("Semua berkas", "*.*")],
                )
                if not destination:
                    return
                if Path(destination).exists() and not self.overwrite.get():
                    raise ValueError("Berkas keluaran sudah ada. Pilih nama berkas baru "
                                     "atau centang Timpa berkas keluaran.")
                result = license_codec.generate_license(
                    database_id=values["database_id"], system_id=values["system_id"],
                    client_id=values["client_id"] or None, expires=values["expires"],
                    capacity=capacity, output_path=destination,
                    client_name=values["client_name"],
                    previous_license_path=(Path(values["previous_license"])
                                           if values["previous_license"] else None),
                    sequence=sequence,
                    overwrite=self.overwrite.get(),
                )
                self.inputs["file"].set(str(result.get("path", destination)))
                verification = result.get("verification", {})
                self.status.set(
                    "Berkas dibuat; pemeriksaan offline berhasil. Aktivasi server belum dibuktikan."
                    if verification.get("valid") is True
                    else "Berkas dibuat. Periksa rincian status verifikasi sebelum digunakan.")
            self.show_result(result)
        except (license_codec.LicenseError, ValueError, TypeError, OSError) as exc:
            self.status.set("Operasi belum berhasil.")
            self.show_result({"error": str(exc)})
            messagebox.showerror("Operasi belum berhasil", str(exc), parent=self.window)


def main() -> None:
    window = tk.Tk()
    LicenseApp(window)
    window.mainloop()


if __name__ == "__main__":
    main()
