# SchoolPay Secure Server 10.5 — format dan pembuktian

SchoolPay tersedia pada aplikasi Python yang sama melalui tab **SchoolPay**.
Fitur sebelumnya berada pada tab **Absensi Wajah**. Kedua tab memiliki input,
file, hasil, codec dan detector sendiri; mengganti tab tidak menukar nilai ID.

## Cara menggunakan

Jalankan `Jalankan GUI.cmd`, pilih tab SchoolPay, lalu isi Database ID, System ID,
tanggal berakhir dan **kapasitas vendor**. Nama klien opsional. Untuk lisensi
baru, Client ID dan Sequence boleh kosong. Untuk perpanjangan, pilih file lisensi
lama agar Client ID dipertahankan dan Sequence naik otomatis.

Isi ID secara manual dari instalasi SchoolPay tujuan. Menu koneksi database dan
semua tombol deteksi sudah dihapus; aplikasi tidak meminta credential database.

```bat
cli.cmd generate --product schoolpay --database-id 7VJM4 --system-id DDCB4 --expires 2030-12-31 --capacity 10 --out schoolpay.lic
cli.cmd inspect --product schoolpay schoolpay.lic
cli.cmd verify --product schoolpay schoolpay.lic --database-id 7VJM4 --system-id DDCB4 --for-import
```

Untuk perpanjangan, tambahkan `--previous-license FILE_LAMA`. Client ID tetap
dan Sequence naik secara otomatis; tidak ada input Sequence. Contoh di `contoh/SchoolPay-7VJM4-DDCB4-baru.lic`
adalah lisensi baru Sequence 1, kapasitas 10, expiry 2030-12-31, bukan perpanjangan.
Tidak ada hasil yang dipasang ke instalasi aktif secara otomatis.

## Identitas target

Target: `C:\Program Files (x86)\YIM\JIBAS SchoolPay Secure Server 10.5\SPayServer.exe`.
SHA-256: `ca112352f1160ead541ff404354aecb3a83165798e562dea5ca3ef68191cd2f8`.
Executable managed x86; harness oracle dikompilasi/dijalankan sebagai x86.
REA `inspect_managed_artifact` dan `inspect_managed_members` merekam metadata
serta identitas build pada `bukti/schoolpay/rea_identity.json` dan evidence terkait.
Tidak ada patch executable; pengujian refleksi memanggil metode asli dalam proses
terpisah dengan folder cache sandbox, tanpa menjalankan Main/aplikasi pembayaran.

## Perbedaan format dari Face

| Bagian | Absensi Wajah | SchoolPay |
|---|---|---|
| Tabel XML | JibasSptFaceLicense | JibasSchoolPayLicense |
| Cache bawaan | 18 kolom skema | 19 kolom skema |
| System ID | Info1 | SystemId eksplisit |
| Kapasitas | MaxClient (wajah) | MaxVendor (vendor) |
| Database ID | resep jbssat | resep jbsfina |
| File impor | Header FACE wajib untuk client AF9 | Kolom ForSchoolPay di skema input; header komentar opsional |

Kripto SchoolPay sama dengan profil server/FACE yang sudah dibuktikan:
XML ASCII → PKCS7 → AES-128-CBC dengan key MD5(ASCII(password)) dan IV tetap
profil → Base64. Parameter berada pada `format_profile.json`; backend memanggil
primitif crypto bersama tanpa mengubah konstanta global codec Face.

Skema asli `0x06000750` mendefinisikan **cache 19 kolom**, tetapi importer
`0x06000757` juga mengakses **DataColumn ForSchoolPay** dari file masukan.
Generator menambah kolom String itu pada XSD dan menulis nilai `1` pada row,
sehingga file impor memiliki skema **20 kolom**.

Uji negatif memperjelas bahwa keberadaan kolom di XSD yang diperlukan pada jalur
ini. Nilai `0`, `false`, string kosong, bahkan row tanpa elemen ForSchoolPay tetapi
XSD mendeklarasikan kolom tersebut, tetap diterima importer. Karena itu verifier
memeriksa keberadaan kolom di skema tabel SchoolPay; tidak menganggap nilai `1`
sebagai bukti entitlement. Generator tetap memakai nilai kanonis `1`.

Header komentar `# LISENSI JIBAS SCHOOLPAY` ditulis untuk identifikasi manusia.
Importer juga menerima payload tanpa header atau dengan komentar berbeda.
Aturan header client Face tidak diterapkan kepada SchoolPay.
Loader/cache tidak boleh diberi file impor berheader untuk mengganti cache secara
langsung; gunakan jalur impor aplikasi agar aplikasi menulis cache sesuai formatnya.

## Database ID dan System ID

Metode asli `0x06000824` mengambil karakter dari OUT routine di **jbsfina**:

| Urutan | Routine | OUT (indeks 0-based) | Posisi ASCII setelah hex decode (0-based) |
|---:|---|---|---:|
| 1 | splang02 | @uhc (2) | 9 |
| 2 | splang07 | @uhd (3) | 21 |
| 3 | splang10 | @uhg (6) | 12 |
| 4 | splang01 | @uhg (6) | 32 |
| 5 | splang09 | @uhg (6) | 45 |

Gabungkan lalu uppercase. Original dan Python pada mesin ini sama-sama
menghasilkan **7VJM4**, sedangkan Face pada database yang sama instalasinya
menghasilkan **V4YNE** dari skema jbssat. Detector SchoolPay tidak membuat atau
mengubah routine jika tidak lengkap; ia mengembalikan error.

Metode WMI asli SchoolPay `0x06000945` menghasilkan **DDCB4**. Perilakunya cocok
dengan hash hardware Face, termasuk trailing spaces serial disk yang harus
dipertahankan. Karena kesetaraan itu dibuktikan, fungsi WMI/hash dipakai bersama.

## Waktu dan aturan perpanjangan

Sequence dan MaxVendor harus dapat dibaca sebagai Int32; generator membatasi
nilai positif dan mencegah overflow. Perpanjangan menjaga Client ID dan menaikkan
Sequence. DbId yang tidak sesuai ditolak importer asli.

Metode tanggal SchoolPay `0x06000708` memiliki penghitungan bulan non-Gregorian
seperti Face, serta overflow unchecked Int32 pada komponen tahun-menit untuk
tahun sangat jauh. Backend memakai fungsi SchoolPay khusus yang cocok dengan
vector metode asli, termasuk tahun 4084, 4085 dan 9999. Ini mencegah verifikasi
Python menyatakan sah untuk tanggal yang dianggap lewat oleh formula aplikasi.

## Bukti dan batas kesimpulan

`bukti/schoolpay_validation/matrix_summary.json` mencatat **31 skenario / 43
percobaan** sesuai ekspektasi melalui importer resmi `0757` dan cache loader `0756`.
Meliputi tiga pasangan ID, file baru, renewal, Sequence sama/turun, Client ID
berbeda, DbId berbeda, SystemId berbeda, expiry lampau, overflow kapasitas,
payload rusak, variasi header, serta keberadaan/nilai kolom ForSchoolPay.

File diterima importer dan cache dapat dimuat kembali untuk pasangan yang sesuai.
Namun importer juga menerima SystemId salah dan tanggal lampau; keberhasilan
impor tidak membuktikan lisensi aktif. Metode runtime `09D0` masih berada dalam
VM obfuscated dan batas aman terhadap jaringan/database belum terbukti, sehingga
metode itu **tidak dieksekusi**. Tidak ada klaim aktivasi online, pengujian penuh
GUI JIBAS, atau pembuktian transaksi SchoolPay.

Database ID, System ID, dan vector tanggal dicatat di `id_date_oracle.json`.
Hash routine database aktif sebelum/sesudah identik. Hash 12 file instalasi
SchoolPay dibandingkan pada `bukti/schoolpay_integrity.json`.
Screenshot dua tab, ukuran normal/minimum, dan hasil tes worker GUI ada di
`bukti/schoolpay/`. Semua data di screenshot adalah data sintetis.
