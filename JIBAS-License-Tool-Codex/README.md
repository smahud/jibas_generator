# JIBAS License Tool — Absensi Wajah dan SchoolPay

Aplikasi Python terpadu dengan dua tab: **Absensi Wajah** dan **SchoolPay**.
Masing-masing tab memakai codec, deteksi ID, input, dan hasil terpisah.
Target yang diteliti: Face Server 16.5, Face & Fingerprint Client 16.10,
dan SchoolPay Secure Server 10.5 di Windows.

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

Pilih tab produk sebelum mengisi data. **Absensi Wajah** memakai kapasitas wajah,
sedangkan **SchoolPay** memakai kapasitas vendor. Tombol **Koneksi Database…**
mengatur host, port, user dan password untuk deteksi; password hanya disimpan
di memori selama aplikasi berjalan. ID manual tidak memerlukan koneksi database.

Pada mesin pengujian, Absensi Wajah mendeteksi **V4YNE/DDCB4**, sedangkan
SchoolPay mendeteksi **7VJM4/DDCB4**. Database ID SchoolPay berasal dari `jbsfina`,
bukan resep Face di `jbssat`; jangan menyalin Database ID antara kedua tab.

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

CLI tetap memakai Face secara default. Untuk SchoolPay, tambahkan
`--product schoolpay` pada perintah `detect`, `generate`, `inspect`, atau `verify`:

```bat
cli.cmd detect --product schoolpay
cli.cmd generate --product schoolpay --database-id 7VJM4 --system-id DDCB4 --expires 2030-12-31 --capacity 10 --out schoolpay-baru.lic
cli.cmd inspect --product schoolpay schoolpay-baru.lic
cli.cmd verify --product schoolpay schoolpay-baru.lic --database-id 7VJM4 --system-id DDCB4 --for-import
```

Deteksi database dari CLI membaca credential dari environment `JIBAS_DB_PASSWORD`.
Generator tidak menyimpan password ke source, lisensi, laporan, atau konfigurasi.
Lihat [SCHOOLPAY.md](SCHOOLPAY.md) untuk format dan hasil pembuktian SchoolPay.

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
`--for-import` memeriksa header client pada Face atau kolom skema ForSchoolPay
pada SchoolPay. Tanpa flag itu, cache internal yang sah masih bisa diperiksa.
Header SchoolPay adalah komentar opsional, berbeda dari client Face.
Hasil bukan konfirmasi aktivasi online.

Fungsi `tulis-cache-client` lama tetap tersedia untuk penggunaan eksplisit,
dengan backup. Perbaikan error impor sekarang dilakukan lewat header file,
sehingga menulis langsung cache tidak diperlukan untuk menyelesaikan error ini.

## Pengujian dan evidence

- **101 tes** suite gabungan lulus: codec, CLI dua produk, detector, dan worker GUI;
  `python -m pytest tests -q` (warning finalizer Tk juga diuji sebagai error).
- SchoolPay asli: 31 skenario / 43 percobaan importer dan cache loader sesuai ekspektasi.
- SchoolPay: 17 tes codec, 5 tes detector, dan 9 vector tanggal oracle asli.
- Server asli: 31/31 skenario importer; 117 kasus predicate runtime sesuai ekspektasi.
- Client asli: header hilang/salah/lowercase ditolak dengan error yang dilaporkan;
  header benar, tiga pasangan ID, dan perpanjangan diuji dengan importer AF9 dan loader AF7.
- Database ID: lima ID pada MariaDB sandbox cocok dengan metode asli;
  bootstrap tanpa routine juga diperiksa. Sandbox dihentikan setelah selesai.
- System ID: metode asli WMI dan enam vector hashing dibandingkan dengan Python.

Bukti sesi baru: `bukti/schoolpay/`, `bukti/schoolpay_validation/`,
`bukti/client_import/`, `bukti/server_matrix/`, `bukti/id_audit/`,
`bukti/inventory_before.json` dan `bukti/inventory_after.json`.
Folder/bukti lama lainnya dan `Analisis.md` adalah arsip historis; klaim 7738F
sebagai ID live, serta klaim cache sama dengan file impor, telah dikoreksi.

Multi-ID importer/runtime menggunakan field lingkungan yang dikendalikan pada
proses terpisah. Ini membuktikan perilaku metode asli pada input tersebut,
bukan pengujian aktivasi GUI penuh atau layanan penerbit pada beberapa komputer.
Tidak ada binary, konfigurasi, cache lisensi, atau routine database aktif yang diubah.
Seluruh 12 file instalasi SchoolPay identik sebelum/sesudah; routine jbsfina
tidak berubah. Lihat `bukti/schoolpay_integrity.json` dan `id_date_oracle.json`.
Perbandingan SHA-256 akhir: **seluruh 818 file instalasi identik** sebelum/sesudah
(`bukti/live_integrity.json`).

Repository utama tetap mempertahankan GUI diagnostik dari `main`.
Perbaikan kecil diagnostik folder di Windows disertakan dalam `patches/`,
dan suite root terbaru diuji terpisah (79 passed, 2 skipped).
Paket ini berada pada subdirektori `JIBAS-License-Tool-Codex` agar tidak menimpa
hasil agent sebelumnya. Tidak menyertakan binary proprietary atau datadir sandbox.
