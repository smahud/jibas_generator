# Format SchoolPay 10.5 yang dibuktikan

Target `C:\Program Files (x86)\YIM\JIBAS SchoolPay Secure Server 10.5\SPayServer.exe`.
SHA-256 `ca112352f1160ead541ff404354aecb3a83165798e562dea5ca3ef68191cd2f8`,
MVID `3f7d530d-8b12-4c29-229b-d7a7bd599cf1`, .NET Framework 4.8, PE32/x86.
Harness runtime dikompilasi dengan `/platform:x86`; binary target tidak diubah.

## Peta metode dan format

| Tujuan | Token |
|---|---|
| Decoder string / worker | 06000063 / 06000064 |
| Path cache; warm decoder yang aman | 0600074F |
| Cache schema | 06000750 |
| Init pasangan kripto melalui VM | 06000751 |
| Loader cache | 06000756 |
| Importer file yang dipanggil handler UI 06000799 | 06000757 |
| Wrapper VM terkait | 06000758 |
| Kripto init / encrypt-string / decrypt-string | 0600066A / 0600066C / 0600066E |
| Perhitungan menit | 06000704..06000708 |

Host path diarahkan ke sandbox melalui field 0400036F. Pasangan kripto dimuat
0751 ke holder 04000359/0400035A. Sama dengan profil server/FACE yang sudah ada
di format_profile.json: AES-128-CBC, key MD5 byte ASCII password, IV ASCII,
padding PKCS7, XML ASCII → Base64. `format_probe.json` merekam schema dan hasil
dekripsi cache asli (skeleton kosong). `crypto_il.txt` memuat instruksi aslinya.

Cache `license.enc` memakai `NewDataSet/JibasSchoolPayLicense`, schema 19 kolom:
Versi, KlienId, Klien, Tanggal, Model, Seri, Size, Sequence, KodeRs, KodeTx,
DbId, SystemId, LicenseLimit, LicenseLimitDate, MaxVendor, Keterangan,
Info1, Info2, Info3. Sequence bertipe Int32, LicenseLimitDate DateTime,
sisanya String. Loader mengubah MaxVendor menjadi Int32.

**File impor berbeda dari cache:** importer 0757 juga mengakses DataColumn
`ForSchoolPay` pada tabel input. Generator menambahkannya sebagai String ke
schema input dan menulis nilai `1` pada row. Cache hasil importer tetap memakai
schema 19 kolom dan row 18 kolom (Model serta ForSchoolPay tidak disalin).

Pengujian asli menerima nilai ForSchoolPay `0`, `false`, kosong, bahkan row
tanpa elemen ForSchoolPay selama kolomnya dideklarasikan dalam schema.
Karena itu persyaratan yang terbukti adalah **keberadaan DataColumn**, bukan
nilai boolean entitlement. Python `inspect` mengekspos
`for_schoolpay_column_present`; `verify --for-import` memeriksa schema tersebut.

Header `# LISENSI JIBAS SCHOOLPAY` yang dibuat generator adalah komentar
informatif. Headerless maupun komentar `# DIFFERENT PRODUCT` tetap diterima
0757. Jangan menyamakan aturan ini dengan client FACE 16.10 yang mewajibkan
header khusus. Schema FACE ditolak oleh inspector SchoolPay.

## Input dan batas validasi

Database ID SchoolPay berasal dari **jbsfina**, bukan jbssat. Nilai live sesi ini
7VJM4; System ID DDCB4. Deteksi terpisah ada di schoolpay_id_detect.py dan evidence
agen validation. Kapasitas menyatakan **vendor**, bukan jumlah wajah.
System ID disimpan pada kolom `SystemId`, bukan `Info1` seperti FACE.

API schoolpay_codec.py selaras dengan backend FACE: inspect_license,
verify_license, generate_license. Client ID baru dibuat otomatis; perpanjangan
mempertahankan Client ID dan menaikkan Sequence dari berkas lama.

Metode minute asli mempunyai kekhasan loop bulan inklusif dan operasi tahun
Int32 sebelum konversi Int64. schoolpay_codec._legacy_minute mereproduksinya;
oracle 4084, 4085, dan 9999 membuktikan overflow. Tahun 9999 tidak otomatis
menjadi lisensi berjangka sangat lama; generator menolaknya apabila nilai
minute asli berada sebelum waktu saat ini.

Backend memiliki 17 pengujian, termasuk fixture schema asli, import/cache,
schema-only ForSchoolPay, headerless/komentar berbeda, ID berbeda, renewal,
overflow kapasitas/sequence, serta vector tanggal asli. Matriks importer final
agen validation memakai 31 skenario/43 percobaan pada proses terpisah.

`verify` merupakan pemeriksaan offline. Importer menerima SystemId salah dan
tanggal kedaluwarsa dalam kondisi yang diuji; penerimaan file belum membuktikan
runtime aktif. Status updater 09D0, predicate VM 09CD, dan getter VM lain
opaque pada analisis statis. 09CE hanya getter bool 04000523; hasilnya tidak
boleh diklaim sebagai pengujian expiry/kapasitas runtime penuh. Tidak ada
panggilan layanan penerbit online atau aktivasi GUI produksi dalam pembuktian.

## Evidence

- `rea_identity.json`, `rea_members_summary.json`: metadata REA lengkap untuk identitas.
- `SchoolPayFormatProbe.cs`, `format_probe.json`: schema dan pair kripto asli.
- `license_type_il.txt`, `crypto_il.txt`, `minute_il.txt`, `runtime_status_il.txt`: IL.
- `IntSites.cs`, `VmOracle.cs`, `vm_strings.txt`: 1666 string VM dari situs statis.
- `../schoolpay_validation/`: detector dan matriks importer dari agen validation.

Seluruh penulisan harness/cache dilakukan ke sandbox. Berkas konfigurasi,
license.enc, binary, dan database live tidak diubah oleh pekerjaan format ini.
