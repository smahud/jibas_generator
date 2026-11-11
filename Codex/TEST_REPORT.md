# Pengujian aplikasi terpadu — Windows, 11 November 2026

Pembaruan field bersama/Save All: **153 passed,1 skipped** (10.95 detik),
warning finalizer Tk sebagai error. Termasuk25tes GUI dan21tes batch. Database ID
tetap terpisah, semua field yang diminta terhubung, dan keluaran batch dipulihkan
bila gagal. Layout enam scene lolos. Lihat SHARED_SAVE_ALL.md.

Standalone: JIBAS-Generator-Codex.exe (Windows x64) lulus
pemeriksaan terisolasi dengan hanya satu EXE dan tanpa environment Python.
Ketiga produk diuji melalui panel Tk asli: buat, baca, verifikasi, mismatch
System ID, perpanjangan dan verifikasi ulang. Resource/Tcl/Tk/native crypto
berasal dari bundle internal. Lihat STANDALONE.md dan bukti/standalone.

Versi manual terbaru: **120 passed in 8.56s**, dengan warning finalizer Tk
dianggap error. Ketiga produk diuji melalui GUI dan CLI; 12 tes GUI memeriksa
ketiadaan kontrol koneksi/deteksi/Sequence, renewal otomatis, dan hasil6baris.
CBE: 14 tes codec serta oracle34skenario/46percobaan (semua sesuai).
Seluruh13file instalasi CBE tetap identik. Lihat MANUAL_UPDATE.md dan CBE.md.

Bagian di bawah adalah catatan pengujian Face/SchoolPay sebelumnya.

Python 3.12.14, cryptography 50.0.2, PyMySQL 1.2.4, pytest 9.2.0.

```text
python -X utf8 -m pytest tests -q -W error::pytest.PytestUnraisableExceptionWarning
101 passed in 6.82s
```

Suite mencakup regresi Face sebelumnya, diagnostik, codec SchoolPay (17 tes),
detector SchoolPay (5), CLI kedua produk (2), serta GUI/worker (9).
CLI dijalankan melalui subprocess di path dengan spasi; routing generate,
inspect, verify, mismatch produk, dan renewal kedua produk diuji end-to-end.

GUI diuji memakai Tk nyata: nama tab, state terpisah, backend/detector tepat,
worker data biasa, heartbeat, pencegahan klik ganda, masking password, dan close
saat worker berjalan. Satu masalah finalizer Tk lintas thread yang muncul pada
suite gabungan telah diperbaiki dengan worker top-level tanpa closure widget
serta pelepasan referensi variabel Tk di main thread. Regresi mengamati finalizer
dan semua jenis worker; timeout tes tidak dinaikkan.

Tampilan dua tab diperiksa pada 880x710 dan 760x650, tanpa widget terpotong.
Ukuran awal menyesuaikan tinggi layar. Screenshot di bukti/schoolpay memakai
data sintetis dan hanya region client jendela QA. Pillow diperlukan hanya untuk
skrip screenshot opsional, bukan dependency runtime generator.

## Oracle executable asli

| Pengujian | Hasil | Evidence |
|---|---|---|
| SchoolPay importer0757 + loader0756 |31 skenario /43 percobaan sesuai | bukti/schoolpay_validation/matrix_summary.json |
| SchoolPay ID dan tanggal | live7VJM4/DDCB4;9 vector tanggal cocok | bukti/schoolpay_validation/id_date_oracle.json |
| Integritas instalasi SchoolPay | seluruh12 file identik | bukti/schoolpay_integrity.json |
| Face Server importer (sesi sebelumnya) |31/31 sesuai | bukti/server_matrix/matrix_summary.json |
| Face Server predicate runtime (sebelumnya) |117 kasus sesuai | JSON per skenario server_matrix |
| Face client importer+cache (sebelumnya) |8 skenario/11 percobaan sesuai | bukti/client_import/matrix_results.json |
| Face ID (sebelumnya) |5 Database ID + bootstrap cocok | bukti/id_audit/isolated_db_matrix.json |

Semua oracle memakai metode executable yang tidak dipatch. Multi-ID importer
menggunakan field identitas lingkungan terkontrol dalam proses terpisah.
Database/routine/config/cache produksi tidak dimodifikasi. SchoolPay menjalankan
0757 dan0756, tetapi runtime VM09D0 tidak dieksekusi karena guard jaringan/SQL
belum dipastikan. Importer menerima SystemId salah dan tanggal lampau, sehingga
hasil ini tidak membuktikan aktivasi runtime, online, atau transaksi pembayaran.

Suite diagnostik repository root dipisahkan dari suite tool standalone melalui
pytest.ini. Pengujian root release: **79 passed,2 skipped** (8.35 detik).
Paket hasil salinan release juga lulus **101 tes** dengan warning finalizer
Tk dianggap error (8.76 detik). Kode lama di root dipertahankan; launcher utama sekarang
membuka aplikasi terpadu di subdirektori Codex.
