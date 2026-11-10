# Laporan Pengujian — 2026-11-10

## Environment dan kondisi awal

- Repository: `smahud/jibas_generator`, branch `main`.
- Baseline: `edb62b9052d235ef7c3f5bff82580613dcb98cb1`; working tree awal bersih.
- Linux x86_64, Python 3.12.14, Tk 9.0, cryptography 50.0.0.
- Environment uji terpisah: pytest 9.2.0, PyMySQL 1.2.4; dependency runtime
  diakses dari runtime Python yang sudah tersedia. Tidak menambahkan dependency
  runtime ke repository.
- Display awal tidak tersedia. Paket pytest/PyMySQL awalnya belum tersedia;
  keduanya dipasang ke venv uji. Xvfb tidak tersedia dan APT tidak dapat
  memperbarui indeks sistem sebagai user biasa. GUI akhirnya diuji memakai
  Xorg 1.21.1.16 dengan driver dummy yang sudah terpasang.
- Xorg dan klien tes berjalan dalam satu proses tree sandbox, memakai display
  TCP lokal sementara. Percobaan socket Unix ditolak sandbox; percobaan klien
  pada sandbox terpisah tidak dapat mengakses server. Ini batas environment,
  bukan kegagalan aplikasi. Server temporer untuk tes/screenshot dihentikan
  setelah dipakai.
- Tidak ada binary proprietary, Windows desktop, database produksi, atau
  instalasi JIBAS yang dipakai. Tidak ada harness C# dijalankan.

## Baseline sebelum edit

| Pemeriksaan | Hasil |
|---|---|
| Branch/commit/status | Dicatat; main, baseline di atas, bersih |
| Inventaris recursive | 61 file tracked; root 16, tests 7, contoh 2, bukti 25, riset 10, db 1 |
| Koleksi suite historis | 39 tes terkoleksi; bukan klaim 39 tes dijalankan |
| Tiga tes baca fixture historis | 3 passed |
| Pembacaan fixture dan sampel tersedia | Berhasil; byte sumber sama sebelum/sesudah |
| Pencarian pesan bug target dan nama obfuscated | Tidak ditemukan pada source/arsip baseline |
| `python cli.py inspect tests/fixtures/original-empty.enc` | Exit 0 tanpa output, mereproduksi main guard yang hilang |
| Startup GUI baseline | Jendela 760 × 600 berhasil dibuat; screenshot `report/gui/before.png` |

Koleksi awal memuat warning plugin pytest dari environment runtime bersama,
bukan kegagalan tes aplikasi. Pengujian final memakai
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` untuk menghindari plugin di luar proyek.

## Perintah dan hasil akhir

Perintah berikut dijalankan menggunakan Python dari venv uji. Untuk tes GUI,
`DISPLAY` menunjuk Xorg temporer yang aktif dalam sandbox yang sama.

```sh
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_diagnostics.py tests/test_cli_diagnostics.py tests/test_gui.py tests/test_provenance_compat.py::test_read_original_importer_cache_fixture tests/test_provenance_compat.py::test_original_importer_cache_is_capacity_parseable tests/test_provenance_compat.py::test_read_original_empty_cache_fixture
python -m compileall -q app.py cli.py diagnostics.py id_detect.py dbid_recipe.py search_db.py license_codec.py tests
python -m pip check
python -m cli inspect tests/fixtures/original-empty.enc
python -m cli verify tests/fixtures/original-empty.enc --database-id ABCDE --system-id 123AB
git diff --check
```

| Pemeriksaan | Hasil |
|---|---|
| `tests/test_diagnostics.py` | 18 passed |
| `tests/test_cli_diagnostics.py` | 5 passed |
| `tests/test_gui.py` | 10 passed, menggunakan interpreter Tk nyata |
| Tiga tes baca fixture historis | 3 passed |
| Total suite terpilih | **36 passed, 0 failed, 0 skipped** |
| Compile/syntax semua Python dan tes | Lulus |
| Import modul terkait | Lulus pada environment uji |
| pip dependency check | Tidak ada dependency rusak |
| CLI inspect cache kosong | JSON stdout, `ok: true`, `empty_cache`, `valid: null`, exit 0 |
| CLI verify cache kosong dengan ID sintetis | JSON stdout, `ok: false`, `checks_failed`, exit 1; hasil yang diharapkan |
| CLI input/error invalid | Exit 2, JSON error tanpa path/nilai exception privat |
| Whitespace diff | Lulus |
| Integritas source/arsip yang dilindungi | Hash terhadap baseline sama; lihat kelompok file pada `AUDIT_REPORT.md` |

Perintah CLI dengan ID di atas memakai nilai sintetis, bukan identitas instalasi.
Exit 1 yang diharapkan pada cache kosong tidak dihitung sebagai tes gagal.

## Invariant yang diuji

- Fixture berbaris dan kosong dibaca dengan status yang benar; input tidak
  berubah byte/mtime selama diagnostik.
- Check boolean dan `valid` pada fixture berbaris sama dengan codec historis;
  `activation_proven` tetap false. Tidak mengubah aturan entitlement.
- Input kosong, rusak, terpotong, hilang, folder, FIFO, berukuran lebih dari
  batas, izin baca gagal, dan format ID salah menghasilkan pesan yang aman.
- Nilai private pada kolom dikenal maupun nama kolom tak dikenal tidak bocor.
  Exception sintetis berisi marker rahasia tidak diteruskan ke laporan.
- Snapshot sama dengan byte sumber dan direktori sementara dibersihkan saat
  pemrosesan gagal.
- CLI dapat dijalankan sebagai module Python; exit status dan JSON sesuai.
- GUI dapat dibuat, menampilkan metadata/per-check result dan error, serta
  menyalin laporan tersamarkan ke clipboard nyata.
- Input berubah membersihkan hasil lama; error tidak meninggalkan tabel sukses.
- Worker lambat tetap mengizinkan heartbeat event Tk. Klik kedua diabaikan.
- Penutupan saat worker aktif tidak mengakses widget yang sudah dihancurkan.
- Guard pada interpreter Tcl/Tk tidak menemukan akses dari worker, termasuk
  akses variabel dan penjadwalan callback.
- Geometri seluruh tab/kontrol utama diperiksa pada 760 × 600, 1040 × 740,
  dan 1400 × 900. Screenshot Linux diperiksa pada ukuran awal dan minimum.
- Pemilihan/cancel berkas diuji lewat mock return dialog; bukan klaim
  pengujian dialog native Windows.

## Tidak dijalankan atau belum dapat dibuktikan

| Pemeriksaan | Status/alasan |
|---|---|
| Suite historis penuh | Sengaja tidak dijalankan; sebagian tes membuat lisensi/cache atau menguji jalur pembatasan |
| Metode tanggal, resep ID, dan jalur mutasi historis | Bukan tujuan pengujian audit ini; source/tes dipertahankan |
| Deteksi MySQL/WMI, pencarian database | Tidak dijalankan; tidak memakai credential lama untuk akses instalasi |
| Harness C#, importer/runtime target | Tidak dijalankan; binary target tidak tersedia dan sebagian harness berefek mutasi |
| Error target persis dari tugas | Belum direproduksi: berkas pemicu dan binary pemicu tidak tersedia |
| Windows `.cmd`, Tk 8.6, DPI tinggi | Ditinjau statis; runtime tersebut tidak tersedia dalam environment ini |
| Dialog native Windows, shortcut manual, screen reader | Belum diuji |
| Pemeriksaan seluruh kemungkinan data pribadi pada dump/arsip | Bukan sertifikasi sanitasi; scan kategori menemukan residual sensitif |
| Database/layanan produksi dan aktivasi penerbit | Tidak diakses/dibuktikan; di luar scope |

## Status akhir

**Lulus untuk scope diagnostik lokal yang diuji.** Ada keterbatasan historis dan
validasi platform/target yang tetap terbuka. Tidak mengklaim seluruh suite lama
lulus atau penolakan importer sudah diperbaiki. Screenshot disimpan bersama
`GUI_REVIEW.md`; temuan dan alasan perubahan ada di `AUDIT_REPORT.md`.
