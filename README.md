# JIBAS License Generator

Satu aplikasi Codex dengan enam tab: **Absensi Wajah**, **Absensi Finger**,
**SchoolPay**, **CBE Server**, **SJS**, dan **LetterStore**.

| Direktori | Isi |
|---|---|
| [Codex](Codex/README.md) | Source Python, standalone EXE, tests, dan bukti REA Codex |
| [OpenCode](OpenCode/README.md) | Implementasi dan arsip OpenCode, terpisah |
| [SharedDocs](SharedDocs/README.md) | Mekanisme, variabel, format, bukti, batas kesimpulan, dan panduan lintas agent |

Root hanya berisi file pendukung. SharedDocs sejajar dengan Codex dan OpenCode.
Direktori hasil Codex aktif adalah **Codex/**; entry point lokal lama dapat
mengarah ke sini sesuai [panduan Codex](Codex/README.md).

## Menjalankan

Buka [Codex/JIBAS-Generator-Codex.exe](Codex/JIBAS-Generator-Codex.exe).
Versi Windows x64 ini satu file dan tidak memerlukan instalasi Python.
[Panduan standalone](Codex/STANDALONE.md) menjelaskan build dan verifikasinya.

Untuk versi source, gunakan **Jalankan GUI.cmd** atau **Jalankan OpenCode.cmd**.
Codex memerlukan Python3.10+ dengan Tkinter:

```bat
python -m pip install -r Codex/requirements.txt
```

## Input tiap produk

| Tab | Identitas | Batas waktu/kapasitas |
|---|---|---|
| Absensi Wajah | Database ID + System ID | Tanggal + wajah |
| Absensi Finger | Nomor seri scanner; tujuan Manager, Client atau keduanya | Tidak memakai keduanya |
| SchoolPay | Database ID + System ID | Tanggal + vendor |
| CBE Server | Database ID + System ID | Tanggal + klien |
| SJS | Database ID + Registration Token; School ID asli untuk baru | Tanggal + agent |
| LetterStore | Database ID | Tidak memakai keduanya |

Semua input manual. System ID/Client ID dibagikan pada Face, SchoolPay, CBE;
nama pada semua tab; tanggal/kapasitas pada tab yang memakainya, termasuk SJS.
Database ID selalu terpisah. Serial scanner, School ID dan token SJS tidak
terhubung ke System ID. Token SJS berisi statistik lokal dan tidak mengungkap
School ID. LetterStore asli hanya menerima satu registrasi.

**Save All**, di kiri **Buat & simpan…**, memvalidasi enam formulir sebelum
memilih folder. Semua hasil dibuat dan diverifikasi di staging; kegagalan tidak
menyisakan keluaran sebagian, dan penggantian file dipulihkan bila gagal.
Pilihan overwrite tetap per tab. File tidak dipasang otomatis ke aplikasi JIBAS.

Tidak ada menu koneksi/deteksi database atau input Sequence. Perpanjangan pada
Face/SchoolPay/CBE/SJS memakai file lama, mempertahankan identitas dan menaikkan
Sequence otomatis. Finger dan LetterStore tidak diberi mekanisme Sequence.
Kotak Hasil tetap enam baris dengan scrollbar.

## Validasi dan batas bukti

Suite mencakup codec enam produk, GUI, field bersama/privat, CLI, Save All dan
rollback. Laporan terbaru di [Codex/TEST_REPORT.md](Codex/TEST_REPORT.md).
Executable diuji sendiri dari folder terisolasi tanpa Python/resource pendamping.
Pemeriksaan layout mencakup enam tab pada ukuran normal dan minimum.

Metode asli Fingerprint Manager16.5/Client14.0/Client16.10 diuji impor, cache,
dan pencocokan serial. LetterStore7.0 diuji beberapa Database ID, cache, flag
registrasi, serta penolakan impor kedua. SJS7.10 diuji importer/renewal dan encoder
token. Penerimaan file lokal tidak membuktikan aktivasi layanan online.
Detail dan langkah reproduksi: [SharedDocs](SharedDocs/README.md).

Jalankan suite dari direktori implementasi masing-masing:

```bat
cd Codex
python -m pytest tests -q -W error::pytest.PytestUnraisableExceptionWarning
```

Binary JIBAS, compiled harness dan datadir eksperimen tidak disertakan dalam
rilis Codex. EXE yang disertakan adalah aplikasi Codex hasil build sendiri.
