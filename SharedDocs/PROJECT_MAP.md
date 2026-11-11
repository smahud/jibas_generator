# Status dan peta project

## Direktori dan entry point

- `Codex/`: aplikasi utama Codex, codec per produk, unit/integration tests, contoh,
  harness dan evidence. `app.py` adalah GUI; `cli.py` adalah CLI manual.
- `OpenCode/`: implementasi lain; jangan menimpa kode atau menganggap detailnya
  identik dengan Codex. Jalankan suite dari direktori implementasi masing-masing.
- `SharedDocs/`: dokumentasi bersama, sejajar dengan dua direktori kode.
- Root Git: README, launcher dan konfigurasi pendukung; tidak ada produk `.py`.
- Checkout Git pada mesin analisis: `C:\YIM\JIBAS Generator\JIBAS-License-Tool-Codex-Publish`.
- Source kerja lokal Codex: `C:\YIM\JIBAS Generator\Codex`. Sinkronkan hanya setelah
  pengujian, menggunakan `python -m riset.build_release <checkout>\Codex`.
- Direktori lokal lama `JIBAS-License-Tool-Codex` berisi entry point kompatibilitas
  menuju `Codex`; jangan mengedit versi arsip sebagai implementasi aktif.

## Yang sudah dibuktikan sebelum penambahan produk terbaru

| Produk | Bukti metode asli | Batas |
|---|---|---|
| Face Server16.5 |31skenario importer +117kasus predikat runtime | lingkungan runtime dikendalikan; bukan aktivasi GUI/online |
| Face/Fingerprint Client16.10, jalur FACE |8skenario/11percobaan importer+loader | bukan semua workflow presensi |
| SchoolPay10.5 |31skenario/43percobaan importer+loader;9vector tanggal | VM runtime09D0 tidak dijalankan |
| CBE26.5 |34skenario/46percobaan importer+loader;8vector tanggal | gate runtime/online dan arti quota sekunder belum terbukti |

| Produk baru | Bukti metode asli | Batas |
|---|---|---|
| Fingerprint Manager16.5 / Client14.0 / Client16.10 | impor CM, cache reload, cocok/salah serial; cakupan dan marker | bukan seluruh alur perangkat/presensi |
| LetterStore7.0 | 3 Database ID, headerless, cache, flag registrasi, penolakan impor kedua | bukan layanan penerbit/online |
| SJS7.10 | 11 kontrol importer/renewal; encoder token asli | School ID remote harus tersedia; koneksi layanan belum diuji |

Ketiganya memiliki halaman sendiri dengan hash/MVID, token metode dan batas
reproduksi. Jangan mengisi ketidakpastian dengan asumsi format Face.

## Koreksi historis yang jangan diulang

1. System ID mesin uji adalah **DDCB4**, bukan7738F. Detector lama membuang
   sembilan spasi belakang serial disk. Hash asli memakai serial mentah.
2. Cache FACE tanpa header bukan file yang diterima menu impor clientAF9.
   Client itu membutuhkan `LISENSI JIBAS SPT FACE` pada baris pertama.
3. SchoolPay tidak membutuhkan header itu. Kolom skema `ForSchoolPay` yang
   diperlukan; nilainya bukan gate boolean pada importer yang diuji.
4. CBE tidak membutuhkan header/ForCbe; importer asli bahkan menerima tabel Face
   yang kolomnya kompatibel. Inspector Codex tetap membatasi tabel per produk.
5. Database ID berbeda menurut produk/skema DB. Face V4YNE dan SchoolPay7VJM4
   pada mesin uji bukan nilai yang boleh di-hardcode untuk mesin lain.
6. Client ID tidak mengungkap Sequence. Renewal mengambil file lama, menjaga
   Client ID dan menaikkan Sequence. GUI/CLI publik tidak meminta Sequence manual.
7. Semua field tidak otomatis cocok lintas produk. System ID bukan Registration
   Token; LetterStore/SJS tidak boleh dipaksa memakai validator System ID Face.
