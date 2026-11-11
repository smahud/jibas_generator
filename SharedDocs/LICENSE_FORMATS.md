# Format dan variabel umum

## Container crypto keluarga FACE/SchoolPay/CBE

XML ASCII DataTable → PKCS7 → AES128-CBC → Base64+CRLF. Key AES adalah
MD5 dari byte ASCII password profil; IV berasal dari profil. Ini format simetris,
bukan bukti tanda tangan private-key penerbit. Reverse: Base64 decode, decrypt
AES-CBC, hapus PKCS7, parse XML. Implementasi primitif ada pada
`Codex/license_codec.py` (`_profile`, `_encrypt`, `_decrypt`).

Parameter konkret ada pada `Codex/format_profile.json`:

| Variabel | Arti |
|---|---|
| profiles.server.password_b64 /iv_b64 | pasangan yang dibuktikan pada Face Server |
| profiles.client_face | pasangan FACE client, sama dengan server untuk build ini |
| profiles.client_fgr | pasangan fingerprint, berbeda kapitalisasi/karakter; jangan tertukar |
| cipher,padding,key_derivation,plaintext_encoding | metadata algoritme; cocokkan ke kode, bukan hanya label |

`BASE = Path(__file__).resolve().parent` mengikat XML/JSON ke paket source atau
folder ekstraksi PyInstaller. Jangan mengganti ke cwd atau lokasi instalasi JIBAS.

## Kolom keluarga Face/CBE

Tabel Face `JibasSptFaceLicense`, CBE `JibasCbeLicense`, masing-masing18kolom:

| Kolom | Arti/pemakaian terbukti |
|---|---|
| Versi | identitas versi payload, bukan token autentikasi |
| KlienId | identitas renewal; harus sama dengan lisensi lama |
| Klien | nama pelanggan, default jika kosong ditentukan codec |
| Tanggal | tanggal pembuatan string YYYY-MM-DD |
| Model | penanda nominal; bukan gate pada importer CBE yang diuji |
| Seri | diisi System ID oleh generator; jangan disamakan bukti binding runtime |
| Size | nilai kapasitas nominal string |
| Sequence | Int32; baru1, renewal lebih tinggi (generator previous+1) |
| KodeRs,KodeTx | kolom format; tidak dianggap signature penerbit tanpa bukti |
| DbId | Database ID produk/instalasi |
| LicenseLimit | tanggal batas berbentuk string |
| LicenseLimitDate | DateTime; dibandingkan melalui fungsi minute legacy |
| MaxClient | kapasitas nominal; CBE memiliki hasil turunan tambahan yang artinya belum pasti |
| Keterangan | informasi tambahan |
| Info1 | binding System ID pada Face/CBE |
| Info2,Info3 | kolom tambahan, tidak ada arti universal yang boleh diasumsikan |

Importer asli dapat menghilangkan elemen Model ketika menulis cache. Schema
berisi18kolom tidak berarti setiap row cache memiliki18elemen non-null.

SchoolPay: tabel `JibasSchoolPayLicense`, cache19kolom. Ada **SystemId** tersendiri,
**MaxVendor** menggantikan MaxClient. File impor menambah kolom String ForSchoolPay
pada XSD (20kolom); row1 adalah pilihan kanonis generator, tetapi nilai0,false,
kosong, atau tanpa elemen row tetap diterima jika DataColumn ada pada skema.

## Penghitungan waktu

Face memiliki formula minute legacy yang memasukkan hari bulan berjalan secara
tidak lazim. SchoolPay/CBE juga memiliki perkalian komponen tahun dalam Int32
unchecked sebelum menjadi Int64. Jangan mengganti dengan timestamp Gregorian
normal. Kasus31Des2028 dan1Jan2029 bisa menghasilkan minute sama. Tahun4084/9999
memperlihatkan wrap Int32 pada SchoolPay/CBE. Vector metode asli disimpan pada
evidence; helper per codec harus mempertahankan perilaku build aslinya.

## Identitas

System ID keluarga yang diuji: MD5(ASCII.NET(rawSerialDiskC + UUID)), lowercasehex,
ambil indeks0-based5,17,30,24,3 lalu uppercase. Preserve spasi dan case; ASCII.NET
mengganti tiap UTF16codeunit non-ASCII dengan `?`. GUI tidak mendeteksi hardware.

Database ID Face: jbssat splang04/@uhh[14],splang02/@uhf[5],splang09/@uhc[25],
splang11/@uhe[37],splang01/@uhb[47] setelah hexdecodeASCII, gabung uppercase.
SchoolPay: jbsfina splang02/@uhc[9],splang07/@uhd[21],splang10/@uhg[12],
splang01/@uhg[32],splang09/@uhg[45]. Indeks karakter dan OUT sama-sama0-based.
Original reader dapat bootstrap jika semua routine tidak ada; membaca melalui
metode asli tidak selalu read-only. Detector penelitian menolak routine hilang.
