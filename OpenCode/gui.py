#!/usr/bin/env python3
"""
JIBAS License Tool — GUI (Tkinter)
===================================

A simple desktop GUI for inspecting, verifying, and generating JIBAS licenses.
"""

from __future__ import annotations

import json
import threading
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Dict, List, Optional

import jibas_license_tool as core


class LicenseToolGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("JIBAS License Tool — OpenCode")
        self.root.geometry("1040x740")
        self.root.minsize(760, 600)

        self.current_file: Optional[Path] = None
        self.worker_thread: Optional[threading.Thread] = None
        self.result_queue: List[Dict[str, Any]] = []

        self._build_ui()
        self._check_queue()

    def _build_ui(self):
        # Notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Tab 1: Inspect / Verify
        self.tab_inspect = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_inspect, text="Inspeksi & Verifikasi")
        self._build_inspect_tab()

        # Tab 2: Generate / Renew
        self.tab_generate = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_generate, text="Buat & Perpanjang")
        self._build_generate_tab()

        # Tab 3: SchoolPay
        self.tab_schoolpay = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_schoolpay, text="SchoolPay")
        self._build_schoolpay_tab()

        # Tab 4: CBE Server
        self.tab_cbe = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_cbe, text="CBE Server")
        self._build_cbe_tab()

        # Tab 5: Client Cache Fix
        self.tab_client = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_client, text="Perbaiki Client Cache")
        self._build_client_tab()

        # Status bar
        self.status_var = tk.StringVar(value="Siap")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=8, pady=(0, 8))

    def _build_inspect_tab(self):
        frame = ttk.LabelFrame(self.tab_inspect, text="Berkas Lisensi")
        frame.pack(fill=tk.X, padx=8, pady=8)

        # File selection
        file_frame = ttk.Frame(frame)
        file_frame.pack(fill=tk.X, padx=8, pady=8)

        ttk.Label(file_frame, text="Berkas:").pack(side=tk.LEFT)
        self.inspect_file_var = tk.StringVar()
        self.inspect_file_entry = ttk.Entry(file_frame, textvariable=self.inspect_file_var, width=60)
        self.inspect_file_entry.pack(side=tk.LEFT, padx=4, fill=tk.X, expand=True)
        ttk.Button(file_frame, text="Pilih...", command=self._pick_inspect_file).pack(side=tk.LEFT, padx=4)

        # Profile and Product selection
        profile_frame = ttk.Frame(frame)
        profile_frame.pack(fill=tk.X, padx=8, pady=(0, 8))
        ttk.Label(profile_frame, text="Profil Kripto:").pack(side=tk.LEFT)
        self.inspect_profile_var = tk.StringVar(value="server")
        ttk.Combobox(profile_frame, textvariable=self.inspect_profile_var,
                     values=["server", "client_face", "client_fgr", "schoolpay", "cbe"], width=15, state="readonly").pack(side=tk.LEFT, padx=4)
        ttk.Label(profile_frame, text="Produk:").pack(side=tk.LEFT, padx=(12, 0))
        self.inspect_product_var = tk.StringVar(value="face")
        ttk.Combobox(profile_frame, textvariable=self.inspect_product_var,
                     values=["face", "schoolpay", "cbe"], width=12, state="readonly").pack(side=tk.LEFT, padx=4)

        # Action buttons
        action_frame = ttk.Frame(frame)
        action_frame.pack(fill=tk.X, padx=8, pady=8)
        ttk.Button(action_frame, text="Baca Berkas", command=self._inspect_file).pack(side=tk.LEFT, padx=4)
        ttk.Button(action_frame, text="Verifikasi", command=self._verify_file).pack(side=tk.LEFT, padx=4)

        # Verification IDs
        verify_frame = ttk.LabelFrame(self.tab_inspect, text="ID untuk Verifikasi")
        verify_frame.pack(fill=tk.X, padx=8, pady=8)

        id_grid = ttk.Frame(verify_frame)
        id_grid.pack(fill=tk.X, padx=8, pady=8)

        ttk.Label(id_grid, text="Database ID:").grid(row=0, column=0, sticky=tk.W, padx=4, pady=2)
        self.verify_dbid_var = tk.StringVar()
        ttk.Entry(id_grid, textvariable=self.verify_dbid_var, width=20).grid(row=0, column=1, padx=4, pady=2)

        ttk.Label(id_grid, text="System ID:").grid(row=0, column=2, sticky=tk.W, padx=4, pady=2)
        self.verify_sysid_var = tk.StringVar()
        ttk.Entry(id_grid, textvariable=self.verify_sysid_var, width=20).grid(row=0, column=3, padx=4, pady=2)

        ttk.Label(id_grid, text="Client ID (opsional):").grid(row=1, column=0, sticky=tk.W, padx=4, pady=2)
        self.verify_clientid_var = tk.StringVar()
        ttk.Entry(id_grid, textvariable=self.verify_clientid_var, width=40).grid(row=1, column=1, columnspan=3, sticky=tk.W, padx=4, pady=2)

        ttk.Label(id_grid, text="Jumlah Aktif (opsional):").grid(row=2, column=0, sticky=tk.W, padx=4, pady=2)
        self.verify_facecount_var = tk.StringVar()
        ttk.Entry(id_grid, textvariable=self.verify_facecount_var, width=10).grid(row=2, column=1, padx=4, pady=2, sticky=tk.W)

        # Results area (compact like Codex version)
        result_frame = ttk.LabelFrame(self.tab_inspect, text="Hasil")
        result_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(1, weight=1)

        self.inspect_result_text = tk.Text(
            result_frame, wrap="word", height=10, state="disabled",
            background="white", foreground="#22324b", relief="solid",
            borderwidth=1, font=("Consolas", 9), padx=10, pady=8,
        )
        self.inspect_result_text.grid(row=1, column=0, sticky="nsew", pady=(3, 0), padx=4)
        scrollbar = ttk.Scrollbar(result_frame, orient="vertical", command=self.inspect_result_text.yview)
        scrollbar.grid(row=1, column=1, sticky="ns", pady=(3, 0))
        self.inspect_result_text.configure(yscrollcommand=scrollbar.set)

        # Copy button
        ttk.Button(result_frame, text="Salin JSON", command=self._copy_inspect_result).grid(row=2, column=0, columnspan=2, sticky=tk.E, padx=8, pady=4)

    def _build_generate_tab(self):
        frame = ttk.LabelFrame(self.tab_generate, text="Parameter Lisensi")
        frame.pack(fill=tk.X, padx=8, pady=8)

        grid = ttk.Frame(frame)
        grid.pack(fill=tk.X, padx=8, pady=8)

        # Row 0: Database ID
        ttk.Label(grid, text="Database ID:").grid(row=0, column=0, sticky=tk.W, padx=4, pady=4)
        self.gen_dbid_var = tk.StringVar()
        ttk.Entry(grid, textvariable=self.gen_dbid_var, width=20).grid(row=0, column=1, padx=4, pady=4, sticky=tk.W)

        # Row 1: System ID
        ttk.Label(grid, text="System ID:").grid(row=1, column=0, sticky=tk.W, padx=4, pady=4)
        self.gen_sysid_var = tk.StringVar()
        ttk.Entry(grid, textvariable=self.gen_sysid_var, width=20).grid(row=1, column=1, padx=4, pady=4, sticky=tk.W)

        # Row 2: Product
        ttk.Label(grid, text="Produk:").grid(row=2, column=0, sticky=tk.W, padx=4, pady=4)
        self.gen_product_var = tk.StringVar(value="face")
        ttk.Combobox(grid, textvariable=self.gen_product_var,
                     values=["face", "schoolpay", "cbe"], width=15, state="readonly").grid(row=2, column=1, padx=4, pady=4, sticky=tk.W)

        # Row 3: Client ID (optional)
        ttk.Label(grid, text="Client ID (opsional):").grid(row=3, column=0, sticky=tk.W, padx=4, pady=4)
        self.gen_clientid_var = tk.StringVar()
        ttk.Entry(grid, textvariable=self.gen_clientid_var, width=40).grid(row=3, column=1, padx=4, pady=4, sticky=tk.W)
        ttk.Label(grid, text="(kosongkan untuk lisensi baru, isi untuk perpanjangan)").grid(row=3, column=2, sticky=tk.W, padx=4)

        # Row 4: Client Name
        ttk.Label(grid, text="Nama Klien:").grid(row=4, column=0, sticky=tk.W, padx=4, pady=4)
        self.gen_clientname_var = tk.StringVar()
        ttk.Entry(grid, textvariable=self.gen_clientname_var, width=40).grid(row=4, column=1, padx=4, pady=4, sticky=tk.W)

        # Row 5: Expiry Date
        ttk.Label(grid, text="Tanggal Kedaluwarsa:").grid(row=5, column=0, sticky=tk.W, padx=4, pady=4)
        self.gen_expires_var = tk.StringVar(value="2027-12-31")
        ttk.Entry(grid, textvariable=self.gen_expires_var, width=15).grid(row=5, column=1, padx=4, pady=4, sticky=tk.W)
        ttk.Label(grid, text="(YYYY-MM-DD)").grid(row=5, column=2, sticky=tk.W, padx=4)

        # Row 6: Capacity
        ttk.Label(grid, text="Kapasitas:").grid(row=6, column=0, sticky=tk.W, padx=4, pady=4)
        self.gen_capacity_var = tk.StringVar(value="100")
        ttk.Entry(grid, textvariable=self.gen_capacity_var, width=15).grid(row=6, column=1, padx=4, pady=4, sticky=tk.W)

        # Row 7: Previous license (for renewal)
        ttk.Label(grid, text="Lisensi Sebelumnya:").grid(row=7, column=0, sticky=tk.W, padx=4, pady=4)
        self.gen_prev_license_var = tk.StringVar()
        ttk.Entry(grid, textvariable=self.gen_prev_license_var, width=50).grid(row=7, column=1, padx=4, pady=4, sticky=tk.W)
        ttk.Button(grid, text="Pilih...", command=self._pick_prev_license).grid(row=7, column=2, padx=4, pady=4)

        # Row 8: Output
        ttk.Label(grid, text="File Output:").grid(row=8, column=0, sticky=tk.W, padx=4, pady=4)
        self.gen_output_var = tk.StringVar(value="license.lic")
        ttk.Entry(grid, textvariable=self.gen_output_var, width=50).grid(row=8, column=1, padx=4, pady=4, sticky=tk.W)
        ttk.Button(grid, text="Pilih...", command=self._pick_output).grid(row=8, column=2, padx=4, pady=4)

        self.gen_overwrite_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(grid, text="Timpa jika sudah ada", variable=self.gen_overwrite_var).grid(row=9, column=1, sticky=tk.W, padx=4, pady=4)

        # Action buttons
        action_frame = ttk.Frame(frame)
        action_frame.pack(fill=tk.X, padx=8, pady=8)
        ttk.Button(action_frame, text="Buat Lisensi Baru", command=self._generate_license).pack(side=tk.LEFT, padx=4)
        ttk.Button(action_frame, text="Perpanjang Lisensi", command=self._renew_license).pack(side=tk.LEFT, padx=4)

        # Results (compact like Codex version)
        result_frame = ttk.LabelFrame(self.tab_generate, text="Hasil")
        result_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(1, weight=1)

        self.gen_result_text = tk.Text(
            result_frame, wrap="word", height=10, state="disabled",
            background="white", foreground="#22324b", relief="solid",
            borderwidth=1, font=("Consolas", 9), padx=10, pady=8,
        )
        self.gen_result_text.grid(row=1, column=0, sticky="nsew", pady=(3, 0), padx=4)
        scrollbar = ttk.Scrollbar(result_frame, orient="vertical", command=self.gen_result_text.yview)
        scrollbar.grid(row=1, column=1, sticky="ns", pady=(3, 0))
        self.gen_result_text.configure(yscrollcommand=scrollbar.set)

        ttk.Button(result_frame, text="Salin JSON", command=self._copy_gen_result).grid(row=2, column=0, columnspan=2, sticky=tk.E, padx=8, pady=4)

    def _build_client_tab(self):
        frame = ttk.LabelFrame(self.tab_client, text="Perbaiki Cache FACE (licenseface.enc)")
        frame.pack(fill=tk.X, padx=8, pady=8)

        ttk.Label(frame, text="Perbaikan ini menulis file licenseface.enc ke folder FaceFgrClient 16.10 "
                              "dari lisensi Face Server yang efektif, sehingga menghilangkan pesan 'TRIAL'.").pack(anchor=tk.W, padx=8, pady=8)

        grid = ttk.Frame(frame)
        grid.pack(fill=tk.X, padx=8, pady=8)

        ttk.Label(grid, text="Lisensi Sumber:").grid(row=0, column=0, sticky=tk.W, padx=4, pady=4)
        self.client_source_var = tk.StringVar()
        ttk.Entry(grid, textvariable=self.client_source_var, width=60).grid(row=0, column=1, padx=4, pady=4, sticky=tk.W)
        ttk.Button(grid, text="Pilih...", command=self._pick_client_source).grid(row=0, column=2, padx=4, pady=4)

        ttk.Label(grid, text="Folder Client 16.10:").grid(row=1, column=0, sticky=tk.W, padx=4, pady=4)
        self.client_dir_var = tk.StringVar()
        ttk.Entry(grid, textvariable=self.client_dir_var, width=60).grid(row=1, column=1, padx=4, pady=4, sticky=tk.W)
        ttk.Button(grid, text="Pilih...", command=self._pick_client_dir).grid(row=1, column=2, padx=4, pady=4)

        self.client_overwrite_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(grid, text="Timpa licenseface.enc yang ada (buat cadangan otomatis)", variable=self.client_overwrite_var).grid(row=2, column=1, sticky=tk.W, padx=4, pady=4)

        ttk.Button(grid, text="Terapkan Perbaikan", command=self._fix_client_cache).grid(row=3, column=1, sticky=tk.W, padx=4, pady=8)

        # Results (compact like Codex version)
        result_frame = ttk.LabelFrame(self.tab_client, text="Hasil")
        result_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(1, weight=1)

        self.client_result_text = tk.Text(
            result_frame, wrap="word", height=10, state="disabled",
            background="white", foreground="#22324b", relief="solid",
            borderwidth=1, font=("Consolas", 9), padx=10, pady=8,
        )
        self.client_result_text.grid(row=1, column=0, sticky="nsew", pady=(3, 0), padx=4)
        scrollbar = ttk.Scrollbar(result_frame, orient="vertical", command=self.client_result_text.yview)
        scrollbar.grid(row=1, column=1, sticky="ns", pady=(3, 0))
        self.client_result_text.configure(yscrollcommand=scrollbar.set)

        ttk.Button(result_frame, text="Salin JSON", command=self._copy_client_result).grid(row=2, column=0, columnspan=2, sticky=tk.E, padx=8, pady=4)

    def _pick_inspect_file(self):
        path = filedialog.askopenfilename(
            title="Pilih berkas lisensi",
            filetypes=[("License files", "*.lic *.enc"), ("All files", "*.*")]
        )
        if path:
            self.inspect_file_var.set(path)
            self.current_file = Path(path)

    def _pick_prev_license(self):
        path = filedialog.askopenfilename(
            title="Pilih lisensi sebelumnya",
            filetypes=[("License files", "*.lic *.enc"), ("All files", "*.*")]
        )
        if path:
            self.gen_prev_license_var.set(path)

    def _pick_output(self):
        path = filedialog.asksaveasfilename(
            title="Simpan lisensi sebagai",
            defaultextension=".lic",
            filetypes=[("License files", "*.lic"), ("All files", "*.*")]
        )
        if path:
            self.gen_output_var.set(path)

    def _pick_client_source(self):
        path = filedialog.askopenfilename(
            title="Pilih lisensi sumber (Face Server)",
            filetypes=[("License files", "*.lic *.enc"), ("All files", "*.*")]
        )
        if path:
            self.client_source_var.set(path)

    def _pick_client_dir(self):
        path = filedialog.askdirectory(title="Pilih folder FaceFgrClient 16.10")
        if path:
            self.client_dir_var.set(path)

    def _pick_sp_prev_license(self):
        path = filedialog.askopenfilename(
            title="Pilih lisensi sebelumnya",
            filetypes=[("License files", "*.lic *.enc"), ("All files", "*.*")]
        )
        if path:
            self.sp_prev_license_var.set(path)

    def _pick_sp_output(self):
        path = filedialog.asksaveasfilename(
            title="Simpan lisensi SchoolPay sebagai",
            defaultextension=".lic",
            filetypes=[("License files", "*.lic"), ("All files", "*.*")]
        )
        if path:
            self.sp_output_var.set(path)

    def _pick_cbe_prev_license(self):
        path = filedialog.askopenfilename(
            title="Pilih lisensi sebelumnya",
            filetypes=[("License files", "*.lic *.enc"), ("All files", "*.*")]
        )
        if path:
            self.cbe_prev_license_var.set(path)

    def _pick_cbe_output(self):
        path = filedialog.asksaveasfilename(
            title="Simpan lisensi CBE sebagai",
            defaultextension=".lic",
            filetypes=[("License files", "*.lic"), ("All files", "*.*")]
        )
        if path:
            self.cbe_output_var.set(path)

    def _run_worker(self, func, *args):
        """Run a function in background thread."""
        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showwarning("Sibuk", "Operasi sebelumnya masih berjalan.")
            return
        self.result_queue.clear()
        self.worker_thread = threading.Thread(target=self._worker_wrapper, args=(func, args), daemon=True)
        self.worker_thread.start()
        self.status_var.set("Memproses...")

    def _worker_wrapper(self, func, args):
        try:
            result = func(*args)
            self.result_queue.append({"ok": True, "result": result})
        except Exception as exc:
            self.result_queue.append({"ok": False, "error": str(exc)})

    def _check_queue(self):
        if self.result_queue:
            result = self.result_queue.pop(0)
            self.status_var.set("Siap")
            if result["ok"]:
                self._handle_result(result["result"])
            else:
                messagebox.showerror("Kesalahan", result["error"])
        self.root.after(100, self._check_queue)

    def _inspect_file(self):
        path = self.inspect_file_var.get().strip()
        if not path:
            messagebox.showwarning("Peringatan", "Pilih berkas lisensi terlebih dahulu.")
            return
        profile = self.inspect_profile_var.get()
        product = self.inspect_product_var.get()
        self._run_worker(core.inspect_license, path, profile, product)

    def _verify_file(self):
        path = self.inspect_file_var.get().strip()
        if not path:
            messagebox.showwarning("Peringatan", "Pilih berkas lisensi terlebih dahulu.")
            return
        dbid = self.verify_dbid_var.get().strip()
        sysid = self.verify_sysid_var.get().strip()
        client_id = self.verify_clientid_var.get().strip() or None
        face_count = self.verify_facecount_var.get().strip()
        face_count = int(face_count) if face_count else None
        profile = self.inspect_profile_var.get()
        product = self.inspect_product_var.get()

        if not dbid or not sysid:
            messagebox.showwarning("Peringatan", "Isi Database ID dan System ID.")
            return

        def verify_task():
            return core.verify_license(path, dbid, sysid, client_id, face_count=face_count, profile=profile, product=product)

        self._run_worker(verify_task)

    def _generate_license(self):
        try:
            dbid = self.gen_dbid_var.get().strip()
            sysid = self.gen_sysid_var.get().strip()
            client_id = self.gen_clientid_var.get().strip() or None
            client_name = self.gen_clientname_var.get().strip()
            expires = self.gen_expires_var.get().strip()
            capacity = int(self.gen_capacity_var.get().strip())
            output = self.gen_output_var.get().strip()
            prev_license = self.gen_prev_license_var.get().strip() or None
            overwrite = self.gen_overwrite_var.get()
            product = self.gen_product_var.get()

            if not dbid or not sysid:
                messagebox.showwarning("Peringatan", "Database ID dan System ID wajib diisi.")
                return

            def gen_task():
                return core.generate_license(
                    database_id=dbid,
                    system_id=sysid,
                    client_id=client_id,
                    expires=expires,
                    capacity=capacity,
                    output_path=output,
                    client_name=client_name,
                    previous_license_path=prev_license,
                    overwrite=overwrite,
                    product=product,
                )

            self._run_worker(gen_task)
        except ValueError as exc:
            messagebox.showerror("Kesalahan Input", str(exc))

    def _renew_license(self):
        try:
            dbid = self.gen_dbid_var.get().strip()
            sysid = self.gen_sysid_var.get().strip()
            client_name = self.gen_clientname_var.get().strip()
            expires = self.gen_expires_var.get().strip()
            capacity = int(self.gen_capacity_var.get().strip())
            output = self.gen_output_var.get().strip()
            prev_license = self.gen_prev_license_var.get().strip()
            overwrite = self.gen_overwrite_var.get()
            product = self.gen_product_var.get()

            if not dbid or not sysid:
                messagebox.showwarning("Peringatan", "Database ID dan System ID wajib diisi.")
                return
            if not prev_license:
                messagebox.showwarning("Peringatan", "Lisensi sebelumnya wajib dipilih untuk perpanjangan.")
                return

            def renew_task():
                return core.renew_license(
                    database_id=dbid,
                    system_id=sysid,
                    expires=expires,
                    capacity=capacity,
                    output_path=output,
                    previous_license_path=prev_license,
                    client_name=client_name,
                    overwrite=overwrite,
                    product=product,
                )

            self._run_worker(renew_task)
        except ValueError as exc:
            messagebox.showerror("Kesalahan Input", str(exc))

    def _generate_schoolpay(self):
        try:
            dbid = self.sp_dbid_var.get().strip()
            sysid = self.sp_sysid_var.get().strip()
            client_id = self.sp_clientid_var.get().strip() or None
            client_name = self.sp_clientname_var.get().strip()
            expires = self.sp_expires_var.get().strip()
            capacity = int(self.sp_capacity_var.get().strip())
            output = self.sp_output_var.get().strip()
            prev_license = self.sp_prev_license_var.get().strip() or None
            overwrite = self.sp_overwrite_var.get()

            if not dbid or not sysid:
                messagebox.showwarning("Peringatan", "Database ID dan System ID wajib diisi.")
                return

            def gen_task():
                return core.generate_license(
                    database_id=dbid,
                    system_id=sysid,
                    client_id=client_id,
                    expires=expires,
                    capacity=capacity,
                    output_path=output,
                    client_name=client_name,
                    previous_license_path=prev_license,
                    overwrite=overwrite,
                    product="schoolpay",
                )

            self._run_worker(gen_task)
        except ValueError as exc:
            messagebox.showerror("Kesalahan Input", str(exc))

    def _renew_schoolpay(self):
        try:
            dbid = self.sp_dbid_var.get().strip()
            sysid = self.sp_sysid_var.get().strip()
            client_name = self.sp_clientname_var.get().strip()
            expires = self.sp_expires_var.get().strip()
            capacity = int(self.sp_capacity_var.get().strip())
            output = self.sp_output_var.get().strip()
            prev_license = self.sp_prev_license_var.get().strip()
            overwrite = self.sp_overwrite_var.get()

            if not dbid or not sysid:
                messagebox.showwarning("Peringatan", "Database ID dan System ID wajib diisi.")
                return
            if not prev_license:
                messagebox.showwarning("Peringatan", "Lisensi sebelumnya wajib dipilih untuk perpanjangan.")
                return

            def renew_task():
                return core.renew_license(
                    database_id=dbid,
                    system_id=sysid,
                    expires=expires,
                    capacity=capacity,
                    output_path=output,
                    previous_license_path=prev_license,
                    client_name=client_name,
                    overwrite=overwrite,
                    product="schoolpay",
                )

            self._run_worker(renew_task)
        except ValueError as exc:
            messagebox.showerror("Kesalahan Input", str(exc))

    def _generate_cbe(self):
        try:
            dbid = self.cbe_dbid_var.get().strip()
            sysid = self.cbe_sysid_var.get().strip()
            client_id = self.cbe_clientid_var.get().strip() or None
            client_name = self.cbe_clientname_var.get().strip()
            expires = self.cbe_expires_var.get().strip()
            capacity = int(self.cbe_capacity_var.get().strip())
            output = self.cbe_output_var.get().strip()
            prev_license = self.cbe_prev_license_var.get().strip() or None
            overwrite = self.cbe_overwrite_var.get()

            if not dbid or not sysid:
                messagebox.showwarning("Peringatan", "Database ID dan System ID wajib diisi.")
                return

            def gen_task():
                return core.generate_license(
                    database_id=dbid,
                    system_id=sysid,
                    client_id=client_id,
                    expires=expires,
                    capacity=capacity,
                    output_path=output,
                    client_name=client_name,
                    previous_license_path=prev_license,
                    overwrite=overwrite,
                    product="cbe",
                )

            self._run_worker(gen_task)
        except ValueError as exc:
            messagebox.showerror("Kesalahan Input", str(exc))

    def _renew_cbe(self):
        try:
            dbid = self.cbe_dbid_var.get().strip()
            sysid = self.cbe_sysid_var.get().strip()
            client_name = self.cbe_clientname_var.get().strip()
            expires = self.cbe_expires_var.get().strip()
            capacity = int(self.cbe_capacity_var.get().strip())
            output = self.cbe_output_var.get().strip()
            prev_license = self.cbe_prev_license_var.get().strip()
            overwrite = self.cbe_overwrite_var.get()

            if not dbid or not sysid:
                messagebox.showwarning("Peringatan", "Database ID dan System ID wajib diisi.")
                return
            if not prev_license:
                messagebox.showwarning("Peringatan", "Lisensi sebelumnya wajib dipilih untuk perpanjangan.")
                return

            def renew_task():
                return core.renew_license(
                    database_id=dbid,
                    system_id=sysid,
                    expires=expires,
                    capacity=capacity,
                    output_path=output,
                    previous_license_path=prev_license,
                    client_name=client_name,
                    overwrite=overwrite,
                    product="cbe",
                )

            self._run_worker(renew_task)
        except ValueError as exc:
            messagebox.showerror("Kesalahan Input", str(exc))

    def _fix_client_cache(self):
        source = self.client_source_var.get().strip()
        client_dir = self.client_dir_var.get().strip()
        overwrite = self.client_overwrite_var.get()

        if not source:
            messagebox.showwarning("Peringatan", "Pilih lisensi sumber (Face Server).")
            return
        if not client_dir:
            messagebox.showwarning("Peringatan", "Pilih folder FaceFgrClient 16.10.")
            return

        def fix_task():
            result = core.fix_client_cache(client_dir, source, overwrite=overwrite)
            verification = core.verify_client_fix(result)
            return {"fix": result, "verification": verification}

        self._run_worker(fix_task)

    def _handle_result(self, result: Dict[str, Any]):
        """Route result to appropriate tab."""
        current_tab = self.notebook.index(self.notebook.select())

        if current_tab == 0:  # Inspect/Verify
            self.inspect_result_text.config(state="normal")
            self.inspect_result_text.delete(1.0, tk.END)
            self.inspect_result_text.insert(tk.END, json.dumps(result, ensure_ascii=False, indent=2, default=str))
            self.inspect_result_text.config(state="disabled")
        elif current_tab == 1:  # Generate
            self.gen_result_text.config(state="normal")
            self.gen_result_text.delete(1.0, tk.END)
            self.gen_result_text.insert(tk.END, json.dumps(result, ensure_ascii=False, indent=2, default=str))
            self.gen_result_text.config(state="disabled")
        elif current_tab == 2:  # SchoolPay
            self.sp_result_text.config(state="normal")
            self.sp_result_text.delete(1.0, tk.END)
            self.sp_result_text.insert(tk.END, json.dumps(result, ensure_ascii=False, indent=2, default=str))
            self.sp_result_text.config(state="disabled")
        elif current_tab == 3:  # CBE Server
            self.cbe_result_text.config(state="normal")
            self.cbe_result_text.delete(1.0, tk.END)
            self.cbe_result_text.insert(tk.END, json.dumps(result, ensure_ascii=False, indent=2, default=str))
            self.cbe_result_text.config(state="disabled")
        elif current_tab == 4:  # Client Cache
            self.client_result_text.config(state="normal")
            self.client_result_text.delete(1.0, tk.END)
            self.client_result_text.insert(tk.END, json.dumps(result, ensure_ascii=False, indent=2, default=str))
            self.client_result_text.config(state="disabled")

    def _copy_inspect_result(self):
        text = self.inspect_result_text.get(1.0, tk.END).strip()
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.status_var.set("JSON disalin ke clipboard")

    def _copy_gen_result(self):
        text = self.gen_result_text.get(1.0, tk.END).strip()
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.status_var.set("JSON disalin ke clipboard")

    def _copy_client_result(self):
        self.client_result_text.config(state="normal")
        text = self.client_result_text.get(1.0, tk.END).strip()
        self.client_result_text.config(state="disabled")
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.status_var.set("JSON disalin ke clipboard")

    def _copy_sp_result(self):
        self.sp_result_text.config(state="normal")
        text = self.sp_result_text.get(1.0, tk.END).strip()
        self.sp_result_text.config(state="disabled")
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.status_var.set("JSON disalin ke clipboard")

    def _build_schoolpay_tab(self):
        """Build the SchoolPay license management tab."""
        frame = ttk.LabelFrame(self.tab_schoolpay, text="JIBAS SchoolPay Secure Server 10.5 License Management")
        frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Product info
        info_text = ("JIBAS SchoolPay Secure Server 10.5 License Generator\n"
                     "Table: JibasSchoolPayLicense | Crypto: AES-128-CBC (same as Face Server)\n"
                     "Columns: Versi, KlienId, Klien, Tanggal, Model, Seri, Size, Sequence,\n"
                     "         KodeRs, KodeTx, DbId, SystemId, LicenseLimit, LicenseLimitDate,\n"
                     "         MaxVendor, Keterangan, Info1, Info2, Info3\n"
                     "Key Differences from Face: MaxVendor instead of MaxClient, SystemId column added")
        ttk.Label(frame, text=info_text, justify=tk.LEFT, font=("Consolas", 9)).pack(anchor=tk.W, padx=8, pady=8)

        # Parameters frame
        param_frame = ttk.LabelFrame(frame, text="Parameter Lisensi SchoolPay")
        param_frame.pack(fill=tk.X, padx=8, pady=8)

        grid = ttk.Frame(param_frame)
        grid.pack(fill=tk.X, padx=8, pady=8)

        # Database ID
        ttk.Label(grid, text="Database ID:").grid(row=0, column=0, sticky=tk.W, padx=4, pady=4)
        self.sp_dbid_var = tk.StringVar()
        ttk.Entry(grid, textvariable=self.sp_dbid_var, width=20).grid(row=0, column=1, padx=4, pady=4, sticky=tk.W)

        # System ID
        ttk.Label(grid, text="System ID:").grid(row=1, column=0, sticky=tk.W, padx=4, pady=4)
        self.sp_sysid_var = tk.StringVar()
        ttk.Entry(grid, textvariable=self.sp_sysid_var, width=20).grid(row=1, column=1, padx=4, pady=4, sticky=tk.W)

        # Client ID (optional)
        ttk.Label(grid, text="Client ID (opsional):").grid(row=2, column=0, sticky=tk.W, padx=4, pady=4)
        self.sp_clientid_var = tk.StringVar()
        ttk.Entry(grid, textvariable=self.sp_clientid_var, width=40).grid(row=2, column=1, padx=4, pady=4, sticky=tk.W)
        ttk.Label(grid, text="(kosongkan untuk lisensi baru, isi untuk perpanjangan)").grid(row=2, column=2, sticky=tk.W, padx=4)

        # Client Name
        ttk.Label(grid, text="Nama Klien:").grid(row=3, column=0, sticky=tk.W, padx=4, pady=4)
        self.sp_clientname_var = tk.StringVar()
        ttk.Entry(grid, textvariable=self.sp_clientname_var, width=40).grid(row=3, column=1, padx=4, pady=4, sticky=tk.W)

        # Expiry Date
        ttk.Label(grid, text="Tanggal Kedaluwarsa:").grid(row=4, column=0, sticky=tk.W, padx=4, pady=4)
        self.sp_expires_var = tk.StringVar(value="2027-12-31")
        ttk.Entry(grid, textvariable=self.sp_expires_var, width=15).grid(row=4, column=1, padx=4, pady=4, sticky=tk.W)
        ttk.Label(grid, text="(YYYY-MM-DD)").grid(row=4, column=2, sticky=tk.W, padx=4)

        # Capacity (MaxVendor)
        ttk.Label(grid, text="Max Vendor (Kapasitas):").grid(row=5, column=0, sticky=tk.W, padx=4, pady=4)
        self.sp_capacity_var = tk.StringVar(value="100")
        ttk.Entry(grid, textvariable=self.sp_capacity_var, width=15).grid(row=5, column=1, padx=4, pady=4, sticky=tk.W)

        # Previous license (for renewal)
        ttk.Label(grid, text="Lisensi Sebelumnya:").grid(row=7, column=0, sticky=tk.W, padx=4, pady=4)
        self.sp_prev_license_var = tk.StringVar()
        ttk.Entry(grid, textvariable=self.sp_prev_license_var, width=50).grid(row=7, column=1, padx=4, pady=4, sticky=tk.W)
        ttk.Button(grid, text="Pilih...", command=self._pick_sp_prev_license).grid(row=7, column=2, padx=4, pady=4)

        # Output
        ttk.Label(grid, text="File Output:").grid(row=8, column=0, sticky=tk.W, padx=4, pady=4)
        self.sp_output_var = tk.StringVar(value="schoolpay.lic")
        ttk.Entry(grid, textvariable=self.sp_output_var, width=50).grid(row=8, column=1, padx=4, pady=4, sticky=tk.W)
        ttk.Button(grid, text="Pilih...", command=self._pick_sp_output).grid(row=8, column=2, padx=4, pady=4)

        self.sp_overwrite_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(grid, text="Timpa jika sudah ada", variable=self.sp_overwrite_var).grid(row=9, column=1, sticky=tk.W, padx=4, pady=4)

        # Action buttons
        action_frame = ttk.Frame(param_frame)
        action_frame.pack(fill=tk.X, padx=8, pady=8)
        ttk.Button(action_frame, text="Buat Lisensi SchoolPay Baru", command=self._generate_schoolpay).pack(side=tk.LEFT, padx=4)
        ttk.Button(action_frame, text="Perpanjang Lisensi SchoolPay", command=self._renew_schoolpay).pack(side=tk.LEFT, padx=4)

        # Results
        result_frame = ttk.LabelFrame(self.tab_schoolpay, text="Hasil")
        result_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.sp_result_text = tk.Text(
            result_frame, wrap="word", height=10, state="disabled",
            background="white", foreground="#22324b", relief="solid",
            borderwidth=1, font=("Consolas", 9), padx=10, pady=8,
        )
        self.sp_result_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        scrollbar = ttk.Scrollbar(result_frame, orient="vertical", command=self.sp_result_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.sp_result_text.configure(yscrollcommand=scrollbar.set)

        ttk.Button(result_frame, text="Salin JSON", command=self._copy_sp_result).pack(anchor=tk.E, padx=8, pady=4)

    def _build_cbe_tab(self):
        """Build the CBE Server license management tab."""
        frame = ttk.LabelFrame(self.tab_cbe, text="JIBAS CBE Server 26.5 License Management")
        frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Product info
        info_text = ("JIBAS CBE Server 26.5 License Generator\n"
                     "Table: JibasCbeLicense | Crypto: AES-128-CBC (same as Face Server)\n"
                     "Columns: Versi, KlienId, Klien, Tanggal, Model, Seri, Size, Sequence,\n"
                     "         KodeRs, KodeTx, DbId, LicenseLimit, LicenseLimitDate,\n"
                     "         MaxClient, Keterangan, Info1, Info2, Info3\n"
                     "Key Differences from Face: Same structure, Model=CBE, Versi=26.5")
        ttk.Label(frame, text=info_text, justify=tk.LEFT, font=("Consolas", 9)).pack(anchor=tk.W, padx=8, pady=8)

        # Parameters frame
        param_frame = ttk.LabelFrame(frame, text="Parameter Lisensi CBE Server")
        param_frame.pack(fill=tk.X, padx=8, pady=8)

        grid = ttk.Frame(param_frame)
        grid.pack(fill=tk.X, padx=8, pady=8)

        # Database ID
        ttk.Label(grid, text="Database ID:").grid(row=0, column=0, sticky=tk.W, padx=4, pady=4)
        self.cbe_dbid_var = tk.StringVar()
        ttk.Entry(grid, textvariable=self.cbe_dbid_var, width=20).grid(row=0, column=1, padx=4, pady=4, sticky=tk.W)

        # System ID
        ttk.Label(grid, text="System ID:").grid(row=1, column=0, sticky=tk.W, padx=4, pady=4)
        self.cbe_sysid_var = tk.StringVar()
        ttk.Entry(grid, textvariable=self.cbe_sysid_var, width=20).grid(row=1, column=1, padx=4, pady=4, sticky=tk.W)

        # Client ID (optional)
        ttk.Label(grid, text="Client ID (opsional):").grid(row=2, column=0, sticky=tk.W, padx=4, pady=4)
        self.cbe_clientid_var = tk.StringVar()
        ttk.Entry(grid, textvariable=self.cbe_clientid_var, width=40).grid(row=2, column=1, padx=4, pady=4, sticky=tk.W)
        ttk.Label(grid, text="(kosongkan untuk lisensi baru, isi untuk perpanjangan)").grid(row=2, column=2, sticky=tk.W, padx=4)

        # Client Name
        ttk.Label(grid, text="Nama Klien:").grid(row=3, column=0, sticky=tk.W, padx=4, pady=4)
        self.cbe_clientname_var = tk.StringVar()
        ttk.Entry(grid, textvariable=self.cbe_clientname_var, width=40).grid(row=3, column=1, padx=4, pady=4, sticky=tk.W)

        # Expiry Date
        ttk.Label(grid, text="Tanggal Kedaluwarsa:").grid(row=4, column=0, sticky=tk.W, padx=4, pady=4)
        self.cbe_expires_var = tk.StringVar(value="2027-12-31")
        ttk.Entry(grid, textvariable=self.cbe_expires_var, width=15).grid(row=4, column=1, padx=4, pady=4, sticky=tk.W)
        ttk.Label(grid, text="(YYYY-MM-DD)").grid(row=4, column=2, sticky=tk.W, padx=4)

        # Capacity (MaxClient)
        ttk.Label(grid, text="Max Client (Kapasitas):").grid(row=5, column=0, sticky=tk.W, padx=4, pady=4)
        self.cbe_capacity_var = tk.StringVar(value="100")
        ttk.Entry(grid, textvariable=self.cbe_capacity_var, width=15).grid(row=5, column=1, padx=4, pady=4, sticky=tk.W)

        # Previous license (for renewal)
        ttk.Label(grid, text="Lisensi Sebelumnya:").grid(row=6, column=0, sticky=tk.W, padx=4, pady=4)
        self.cbe_prev_license_var = tk.StringVar()
        ttk.Entry(grid, textvariable=self.cbe_prev_license_var, width=50).grid(row=6, column=1, padx=4, pady=4, sticky=tk.W)
        ttk.Button(grid, text="Pilih...", command=self._pick_cbe_prev_license).grid(row=6, column=2, padx=4, pady=4)

        # Output
        ttk.Label(grid, text="File Output:").grid(row=7, column=0, sticky=tk.W, padx=4, pady=4)
        self.cbe_output_var = tk.StringVar(value="cbe.lic")
        ttk.Entry(grid, textvariable=self.cbe_output_var, width=50).grid(row=7, column=1, padx=4, pady=4, sticky=tk.W)
        ttk.Button(grid, text="Pilih...", command=self._pick_cbe_output).grid(row=7, column=2, padx=4, pady=4)

        self.cbe_overwrite_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(grid, text="Timpa jika sudah ada", variable=self.cbe_overwrite_var).grid(row=8, column=1, sticky=tk.W, padx=4, pady=4)

        # Action buttons
        action_frame = ttk.Frame(param_frame)
        action_frame.pack(fill=tk.X, padx=8, pady=8)
        ttk.Button(action_frame, text="Buat Lisensi CBE Baru", command=self._generate_cbe).pack(side=tk.LEFT, padx=4)
        ttk.Button(action_frame, text="Perpanjang Lisensi CBE", command=self._renew_cbe).pack(side=tk.LEFT, padx=4)

        # Results
        result_frame = ttk.LabelFrame(self.tab_cbe, text="Hasil")
        result_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.cbe_result_text = tk.Text(
            result_frame, wrap="word", height=10, state="disabled",
            background="white", foreground="#22324b", relief="solid",
            borderwidth=1, font=("Consolas", 9), padx=10, pady=8,
        )
        self.cbe_result_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        scrollbar = ttk.Scrollbar(result_frame, orient="vertical", command=self.cbe_result_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.cbe_result_text.configure(yscrollcommand=scrollbar.set)

        ttk.Button(result_frame, text="Salin JSON", command=self._copy_cbe_result).pack(anchor=tk.E, padx=8, pady=4)

    def _copy_cbe_result(self):
        self.cbe_result_text.config(state="normal")
        text = self.cbe_result_text.get(1.0, tk.END).strip()
        self.cbe_result_text.config(state="disabled")
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.status_var.set("JSON disalin ke clipboard")


def main():
    root = tk.Tk()
    app = LicenseToolGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()