# Audit ulang Database ID dan System ID

Tanggal: 2026-11-10. Target asli `FaceServer.exe` 16.5.0.0, SHA-256
`8a123015b2ee095ceda51ece6d47436e9760c88be8f92fb76ed7c120c923c364`,
MVID `9e7e3122-c165-4ca3-3e9c-234edb96bf24`.

## Koreksi penting terhadap README dan bukti lama

**System ID mesin ini adalah DDCB4.** Metode asli `0x06000599` mengembalikan
serial fisik WMI `30029941042         ` (20 karakter, termasuk 9 spasi).
Metode `0x0600059B` menggabungkannya langsung dengan UUID
`E0813C3C-120B-02FE-5F00-BCAEC5319E78`, memanggil MD5 ASCII `0x06000849`,
mengambil indeks hex `[5,17,30,24,3]`, kemudian mengubah hasil menjadi huruf besar.

Tidak ada operasi Trim pada jalur tersebut. Penghapusan spasi dalam
`SystemIdDetector.read_wmi()` lama menghasilkan **7738F**, berbeda dari
keluaran asli. Kode Codex mempertahankan spasi dan mereplikasi fallback ASCII
.NET untuk karakter non-ASCII (termasuk pasangan surrogate). Enam vektor
hash dibandingkan dengan metode asli dan seluruhnya cocok. Karena itu klaim
lama bahwa DDCB4 salah dan 7738F benar harus dibatalkan. Bukti yang mengisi
field System ID runtime dengan 7738F hanya membuktikan perilaku untuk
nilai yang disuntikkan; bukan pembacaan hardware asli.

Rujukan: `original_hardware_vectors.json`, `original_systemid.txt`,
`599_il.txt`, `59b_il.txt`, `849_il.txt`.

## Bagaimana Database ID dibentuk

Metode asli `0x06000AC3` memakai `USE jbssat`, mengecek bahwa skema memiliki
tabel, lalu memeriksa routine melalui `0x06000ABF`. Jika semua 12 routine
splang tidak ada, ia membuatnya melalui `0x06000ABD` / `0x06000AC5` dan
menjalankan initializer tambahan `0x06000ABC`. Generator `0x06000ABB` memakai
`System.Random` untuk menyusun payload 64 karakter. Payload ini diubah menjadi
teks hex dan disimpan pada sembilan parameter OUT routine, `uha` sampai `uhi`.
Jika hanya sebagian routine hilang, ia melempar
`Licensing system has been altered!`.

Setelah routine tersedia, resep lima karakternya adalah:

| Routine | OUT (indeks 0..8) | Indeks karakter setelah hex-decode |
|---|---|---|
| splang04 | uhh (7) | 14 |
| splang02 | uhf (5) | 5 |
| splang09 | uhc (2) | 25 |
| splang11 | uhe (4) | 37 |
| splang01 | uhb (1) | 47 |

Gabungkan urutan tabel dan uppercase. Ini identitas yang persisten dalam
routine database, bukan turunan System ID, nama sekolah, atau isi lisensi.
Menghapus/reinisialisasi routine bisa membuat Database ID baru.
Detector Python sengaja hanya membaca routine yang sudah ada; ia melaporkan
kesalahan jika routine hilang dan tidak meniru cabang bootstrap yang menulis DB.

## Pembuktian lintas ID tanpa mengubah database live

MariaDB kedua dijalankan sementara pada `127.0.0.1:3435`, dengan datadir
baru `mysql_sandbox` di direktori audit. Tidak dibuat Windows service.
Metode AC3 asli pada skema awal membentuk 12 routine dan ID acak `LTB28`;
detector Python membaca nilai yang sama. Selanjutnya routine fixture hanya di
sandbox diatur untuk lima kasus:

| Fixture | Metode AC3 asli | Python |
|---|---|---|
| V4YNE | V4YNE | V4YNE |
| ABCDE | ABCDE | ABCDE |
| WRK9T | WRK9T | WRK9T |
| Z9X8W | Z9X8W | Z9X8W |
| a1b2c | A1B2C | A1B2C |

Hash definisi semua routine `jbssat` live port3434 sebelum dan setelah
eksperimen identik. Pembacaan live akhir: **V4YNE / DDCB4**. Sandbox sudah
dihentikan dengan `mysqladmin shutdown`; MySQL live tetap berjalan.

Rujukan: `isolated_db_matrix.json`, `audit_ids.py`, `IdOracle.cs`.
Fixture membuktikan pemilihan karakter lintas ID, bukan jaminan bahwa setiap
routine arbitrer atau database rusak akan diperlakukan sama oleh detector.

## Sumber bukti dan reproduksi

REA managed inspection tersedia pada sesi ini: identitas biner serta metadata
metode dipastikan tanpa mengeksekusi target dalam `rea_server_identity.json`,
`rea_id_members_summary.json`, dan `rea_id_methods.json`. Token hanya bermakna
untuk SHA/MVID di atas. Dump IL memakai reflection-only reader lama `riset/il.ps1`.
Observasi runtime memakai harness C# proses terpisah, memanggil metode asli,
tanpa menjalankan Main/UI dan tanpa memodifikasi biner.

Kompilasi oracle dengan .NET Framework csc (path penuh), referensi
`System.Web.Extensions.dll`, lalu jalankan `IdOracle.exe` untuk pembacaan
hardware. Mode `IdOracle.exe db PORT` membaca password dari env
`ID_AUDIT_MYSQL_PASSWORD`. Mode DB memanggil AC3 asli yang dapat bootstrap;
gunakan sandbox untuk skema yang routine-nya belum lengkap.

`audit_ids.py` memerlukan MariaDB sandbox baru di port3435. Skrip tersebut
mereset hanya skema jbssat instance sandbox itu; semua operasi koneksi live
port3434 di skrip adalah SELECT. Datadir dan executable hasil kompilasi
merupakan artefak lokal; kode sumber serta JSON cukup untuk repositori.

Regresi: `python -m pytest tests/test_id_detect.py -q` -> **11 passed**.
