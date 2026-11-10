# Panduan Agent — Audit Diagnostik Read-only

## Mulai dari kondisi saat ini

Baca `README.md`, `AUDIT_REPORT.md`, `GUI_REVIEW.md`, dan `TEST_REPORT.md`.
Baseline audit: branch `main`, commit
`edb62b9052d235ef7c3f5bff82580613dcb98cb1`, working tree awal bersih.

Repository ini memuat aplikasi Python dan arsip riset historis, bukan salinan
lengkap instalasi JIBAS. Klaim runtime dalam arsip bukan hasil pengujian sesi
ini. Jangan mengasumsikan kondisi mesin, layanan, atau database dari catatan lama.

## Batas pekerjaan

- Kerjakan hanya GUI, pembacaan berkas, pelaporan, penanganan error, dan
  diagnostik offline yang tidak mengubah sumber.
- Jangan mengembangkan pembuatan/modifikasi lisensi, penulisan cache,
  penghindaran trial, aktivasi, entitlement, atau penerimaan importer target.
- Jangan mengubah kriptografi, expiry, kapasitas, sequence, atau pemeriksaan
  entitlement pada codec. Jika ada masalah di sana, laporkan tanpa memperbaikinya.
- Jangan mengubah binary, database, stored procedure, konfigurasi, atau folder
  instalasi JIBAS. Jangan memakai credential historis untuk akses sistem.
- Jangan menjalankan harness C# atau mengimpor dump SQL sebagai bagian dari
  pengujian diagnostik. Sebagian harness dan dump mempunyai efek mutasi.
- Jangan menghapus/membuat ulang fixture dan arsip `bukti/`, `contoh/`, `riset/`,
  atau `db/` tanpa kebutuhan dan otorisasi yang jelas.
- Jangan menyalin key, credential, identitas mesin, atau data lisensi mentah
  ke output/log/dokumentasi baru. Laporkan kategori dan lokasi temuan saja.

## Peta kode yang relevan

`app.py` → `diagnostics.py` → fungsi baca/periksa pada `license_codec.py`.
`cli.py` memakai facade diagnostik untuk `inspect`/`verify`.

`diagnostics.py` membuka sumber read-only, membatasi input 4 MiB, kemudian
memproses salinan sementara privat yang dibersihkan. Snapshot yang sama dipakai
untuk inspeksi dan verifikasi. Penyamaran adalah allowlist metadata, bukan
pencarian kata password saja. Hasil selalu menyatakan `activation_proven: false`.

Thread GUI: ambil input pada main thread, jalankan worker tanpa panggilan Tk,
ambil hasil lewat antrean yang dipoll dengan `after()` pada main thread.
Pertahankan invalidasi hasil saat input berubah dan penutupan aman saat worker
masih berjalan. Jangan tambahkan framework atau abstraksi tanpa kebutuhan.

CLI historis masih memiliki fungsi lain dan tidak seluruhnya read-only. Jangan
menganggap dokumentasi diagnostik ini sebagai izin menjalankan semua command.

## Pengujian yang sesuai ruang lingkup

```sh
python -m pytest -q tests/test_diagnostics.py tests/test_cli_diagnostics.py tests/test_gui.py
python -m pytest -q tests/test_provenance_compat.py::test_read_original_importer_cache_fixture tests/test_provenance_compat.py::test_original_importer_cache_is_capacity_parseable tests/test_provenance_compat.py::test_read_original_empty_cache_fixture
python -m compileall -q app.py cli.py diagnostics.py id_detect.py dbid_recipe.py search_db.py license_codec.py tests
python -m pip check
```

Tes GUI membutuhkan desktop/display dan akan skip bila tidak tersedia. Selalu
laporkan jumlah pass/fail/skip sebenarnya. Jangan mengklaim Windows atau target
proprietary telah diuji jika hanya menggunakan Tk di Linux.

Jangan menjalankan seluruh `pytest tests` untuk audit read-only: ada tes lama
yang membuat lisensi dan menulis cache. Jangan menambah tes untuk meningkatkan
jalur tersebut. Periksa diff dan hash file yang dilindungi sebelum commit.

## Dokumentasi dan laporan

Perbarui laporan yang relevan jika perilaku berubah. Catat temuan, alasan
perubahan, perintah uji, hasil, dan keterbatasan. Gunakan `MANIFEST.json` untuk
inventaris saat ini. `bukti/manifest_sha256.json` adalah bukti historis; jangan
memutakhirkannya agar tampak mewakili source baru.

Tidak ada instruksi deployment atau akses produksi dalam panduan ini.
