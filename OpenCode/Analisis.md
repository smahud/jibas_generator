# Status Analisis — Diagnostik Read-only JIBAS

Dokumen ini menggantikan panduan operasional riset lama yang memuat data mesin,
credential, serta prosedur mutasi lisensi/cache. Perubahan dilakukan untuk
menyesuaikan dokumentasi aktif dengan ruang lingkup diagnostik. Arsip riset dan
fixture tetap utuh; versi dokumentasi terdahulu tetap ada dalam riwayat Git.

## Fakta yang dapat diperiksa pada checkout

- `app.py` adalah GUI Tkinter read-only dengan empat tab. Tidak memanggil deteksi
  database/hardware, pembuatan lisensi, atau penulisan cache.
- `diagnostics.py` membatasi input, memproses snapshot sementara, dan menyamarkan
  laporan. Semua pembaruan widget berlangsung pada main thread GUI.
- `cli.py` menyediakan `inspect` dan `verify` melalui facade yang sama. CLI masih
  memuat command historis lain; command tersebut di luar audit aktif.
- `license_codec.py` memuat fungsi baca/periksa dan fungsi mutasi historis.
  Seluruh berkas codec dibiarkan tidak berubah; hasil verifikasi offline tidak
  membuktikan penerimaan importer atau aktivasi penerbit.
- `id_detect.py` mempunyai pembacaan WMI dan pemanggilan stored procedure;
  `search_db.py` melakukan pencarian lintas skema. Keduanya tidak dijalankan.
- Tidak ada binary target proprietary di checkout ini.

## Bukti historis dan batas penggunaannya

| Arsip | Peran | Batas |
|---|---|---|
| `bukti/import_results/`, `bukti/e2e/` | Catatan hasil sesi runtime terdahulu | Tidak dieksekusi ulang atau dianggap konfirmasi kondisi live saat ini |
| `bukti/detector_provenance.json`, `bukti/variable_audit.json` | Provenance dan pencatatan pemetaan historis | Dapat mengandung identitas/data sensitif; jangan salin nilainya ke laporan baru |
| `bukti/client16/` | Hasil ekstraksi string dan lokasi panggilan | Bukan seluruh source/binary target; ketiadaan string tidak meniadakan jalur lain |
| `bukti/manifest_sha256.json` | Hash snapshot terdahulu | Bukan checksum rilis source setelah audit |
| `tests/fixtures/`, `contoh/` | Berkas yang sudah tersedia | Keberhasilan pembacaan bukan bukti keaslian/entitlement |
| `riset/` | Harness C# historis | Tidak dijalankan; sebagian berpotensi menulis atau mengakses instalasi |
| `db/` | Dump SQL historis | Memuat data akun dan restore destruktif; tidak diimpor |

## Error “File terpilih bukan lisensi JIBAS Presensi Wajah”

Pencarian literal pesan dan dua nama obfuscated pada laporan pengguna tidak
menemukan kecocokan di checkout. Arsip string klien memuat filter pemilihan
berkas berlabel presensi wajah, tetapi tidak cukup untuk memetakan exception
tersebut ke metode tertentu.

Fixture yang tersedia dapat dibaca oleh codec lokal. Tidak tersedia berkas
pemicu yang terkonfirmasi, versi lengkap binary pemicu, atau log lengkap proses
asli. Karena itu root cause pada target masih **belum terkonfirmasi**. Dugaan
ketidakcocokan jenis/struktur berkas tetap hipotesis, bukan kesimpulan.

Perbaikan sesi ini menangani masalah diagnostik yang terbukti: pembacaan sinkron
pada GUI lama, pesan error mentah, tampilan JSON saja, CLI tanpa entry point,
dan hasil yang perlu dibersihkan ketika input berubah. Tidak ada klaim bahwa
perubahan ini memperbaiki penolakan oleh aplikasi target.

Rincian reproduksi aman, severity, dan temuan lanjutan:
[AUDIT_REPORT.md](AUDIT_REPORT.md). Bukti uji saat ini:
[TEST_REPORT.md](TEST_REPORT.md).
