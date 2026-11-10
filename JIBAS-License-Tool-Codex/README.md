# JIBAS License Tool — Codex, 10 November 2026

Perbaikan generator Python berdasarkan pengujian ulang executable asli
Face Server 16.5 dan Face & Fingerprint Client 16.10 di Windows.
Hasil diterbitkan terpisah dari tool dan GUI diagnostik sebelumnya.

**Dua koreksi utama:** file impor client membutuhkan baris pertama
`# LISENSI JIBAS SPT FACE`; System ID mesin ini **DDCB4**, bukan 7738F.
Detector lama menghapus spasi serial disk sebelum hashing.
Rincian algoritme, pembentukan ID, bukti dan batas pengujian ada di
[TEMUAN.md](TEMUAN.md).

## Menjalankan aplikasi

Klik **Jalankan GUI.cmd**. Isi Database ID dan System ID mesin tujuan, tanggal
berakhir, serta kapasitas. Tombol deteksi memakai MySQL lokal dan WMI.
Client ID boleh kosong untuk lisensi baru. Untuk perpanjangan, pilih lisensi
lama agar Client ID tetap sama dan Sequence otomatis naik.

Runtime Python yang sudah ada pada mesin ini didukung launcher. Untuk mesin
lain: Python 3.10+ dengan Tkinter, lalu `python -m pip install -r requirements.txt`.
Launcher memprioritaskan `.venv\Scripts`, runtime lokal sesi, kemudian `py -3`.
Tidak perlu menyalin executable JIBAS untuk memakai generator dengan ID manual.

```bat
cd /d "C:\YIM\JIBAS Generator\JIBAS-License-Tool-Codex"
cli.cmd detect
cli.cmd generate --database-id V4YNE --system-id DDCB4 --expires 2030-12-31 --capacity 100 --out baru.lic
cli.cmd inspect baru.lic
cli.cmd verify baru.lic --auto --for-import
```

Impor `baru.lic` lewat menu lisensi FACE. Jangan mengganti cache `licenseface.enc`
dengan file impor berheader: loader cache membaca Base64 pada baris pertama.
Generator tidak mengimpor atau memasang hasil ke instalasi aktif secara otomatis.

## Perpanjangan

Instalasi yang sudah berlisensi memerlukan Client ID yang sama dan Sequence
lebih tinggi. File baru dengan Client ID acak bukan perpanjangan.

```bat
cli.cmd generate --database-id V4YNE --system-id DDCB4 --previous-license "C:\Program Files\YIM\JIBAS Face Server 16.5\license.enc" --expires 2030-12-31 --capacity 100 --out perpanjangan.lic
```

Tanggal dan kapasitas pada contoh harus disesuaikan dengan tujuan Anda; perintah
tidak mempertahankan nilai lama secara otomatis. Bila hanya mengetahui Client ID,
berikan `--client-id ID --sequence N` dengan N lebih besar dari Sequence terpasang.
Client ID sendiri tidak mengungkap Sequence. File lama boleh cache `.enc` atau
file impor `.lic`. `--overwrite` hanya untuk menimpa berkas keluaran.

## Inspeksi, dekripsi, dan verifikasi

`inspect` mendekripsi file menjadi field XML dan menunjukkan apakah header impor
ada. `verify` memeriksa ID, tanggal, kapasitas dan struktur secara offline;
`--for-import` menambahkan pemeriksaan header client. Tanpa flag itu, cache
internal yang sah masih bisa diperiksa. Hasil bukan konfirmasi aktivasi online.

Fungsi `tulis-cache-client` lama tetap tersedia untuk penggunaan eksplisit,
dengan backup. Perbaikan error impor sekarang dilakukan lewat header file,
sehingga menulis langsung cache tidak diperlukan untuk menyelesaikan error ini.

## Pengujian dan evidence

- 49 pengujian Python lulus di Windows; `python -m pytest tests -q`.
- Server asli: 31/31 skenario importer; 117 kasus predicate runtime sesuai ekspektasi.
- Client asli: header hilang/salah/lowercase ditolak dengan error yang dilaporkan;
  header benar, tiga pasangan ID, dan perpanjangan diuji dengan importer AF9 dan loader AF7.
- Database ID: lima ID pada MariaDB sandbox cocok dengan metode asli;
  bootstrap tanpa routine juga diperiksa. Sandbox dihentikan setelah selesai.
- System ID: metode asli WMI dan enam vector hashing dibandingkan dengan Python.

Bukti sesi baru: `bukti/client_import/`, `bukti/server_matrix/`, `bukti/id_audit/`,
`bukti/inventory_before.json` dan `bukti/inventory_after.json`.
Folder/bukti lama lainnya dan `Analisis.md` adalah arsip historis; klaim 7738F
sebagai ID live, serta klaim cache sama dengan file impor, telah dikoreksi.

Multi-ID importer/runtime menggunakan field lingkungan yang dikendalikan pada
proses terpisah. Ini membuktikan perilaku metode asli pada input tersebut,
bukan pengujian aktivasi GUI penuh atau layanan penerbit pada beberapa komputer.
Tidak ada binary, konfigurasi, cache lisensi, atau routine database aktif yang diubah.
Perbandingan SHA-256 akhir: **seluruh 818 file instalasi identik** sebelum/sesudah
(`bukti/live_integrity.json`).

Repository utama tetap mempertahankan GUI diagnostik dari `main`.
Perbaikan kecil diagnostik folder di Windows disertakan dalam `patches/`,
dan suite root diuji terpisah (71 passed, 1 skipped).
Paket ini berada pada subdirektori `JIBAS-License-Tool-Codex` agar tidak menimpa
hasil agent sebelumnya. Tidak menyertakan binary proprietary atau datadir sandbox.
