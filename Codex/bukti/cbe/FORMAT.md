# CBE Server 26.5 — format yang dipastikan

Executable `CbeServer.exe`, SHA-256
`a2b77a3fc715d1d8c2b47a29ff65444af0e829c3f2704098ed538c48ce5f140b`,
MVID `5831bc0d-d22e-4a13-67b9-f22eab4b24a8`, managed x64 .NET Framework4.8.
REA identity dan focused member inspection tersedia dalam JSON pada folder ini.
Inspeksi seluruh member sempat melewati representation budget64MiB; inspeksi
dua declaring type lisensi/crypto kemudian lengkap dalam scope yang dipilih.

## Method map

| Keperluan | Token |
|---|---|
| VM string wrapper / worker | 0600005C /0600005D |
| Path license.enc | 060005B7, direktori runtime040005D2 |
| Schema cache | 060005B8, DataTable holder040002DE |
| Crypto initialization | 060005B9, password/IV040005A5/040005A6 |
| Cache loader | 060005BE |
| Kapasitas turunan | 060005BF |
| Importer yang dipanggil handler UI | 060005C0 |
| Handler UI impor | 06000BB6 |
| Arithmetika tanggal DateTime→minute | 06000E0A |

Harness FormatProbe hanya mengisi direktori sandbox, menghangatkan path getter,
menjalankan crypto init dan schema builder. Tidak memakai Main, init aplikasi
05BA, database, transaksi, atau jaringan. Init05BA sengaja dihindari karena
memanggil fungsi tambahan DD2. Cache asli dibaca saja untuk dekripsi.

## XML dan crypto

DataTable bernama **JibasCbeLicense**, 18kolom: Versi,KlienId,Klien,Tanggal,
Model,Seri,Size,Sequence,KodeRs,KodeTx,DbId,LicenseLimit,LicenseLimitDate,
MaxClient,Keterangan,Info1,Info2,Info3. Sequence Int32,LicenseLimitDate DateTime,
sisanya String. Cache instalasi adalah skeleton tanpa row. Profil AES cocok
dengan FACE/server: key=MD5(ASCII(password profil)), IV ASCII tetap, AES128CBC,
PKCS7, XML ASCII, Base64+CRLF. Profil sumber tetap di format_profile.json.

Input ID disimpan pada DbId dan Info1; Seri juga diisi System ID. Generator
menghasilkan Versi26.5,ModelCBE. Cipher primitif dipakai bersama dengan Face,
tetapi schema/konstanta tabel CBE terpisah sehingga produk tidak tertukar.

Kandidat payload18kolom sudah diterima oleh official importer05C0 dan dapat
dimuat oleh loader05BE di sandbox. Hasil matriks final serta variasi header
dan perpanjangan berada di ../cbe_validation/. Keberhasilan importer bukan
bukti aktivasi runtime/online.

Header komentar CBE tidak diwajibkan: payload tanpa header, komentar arbitrary,
dan komentar lowercase diterima05C0. Importer asli juga menerima file Face
dengan tabel JibasSptFaceLicense yang memiliki kolom kompatibel. Dengan demikian
tidak ada bukti discriminator produk pada jalur ini. Inspector Python sengaja
meminta schemaCBE untuk mencegah salah produk pada aplikasi terpadu; pembatasan
ini tidak disamakan dengan rejection dari aplikasi asli.

## Kapasitas dan waktu

Literal UI asli `Maksimum koneksi CBE Client` dan `Jumlah koneksi client secara
bersamaan dalam satu waktu` menunjukkan maksud nominal field MaxClient.
Loader menyimpan nilai nominal pada040003FD dan hasil5BF pada040003FE.
Original5BF bukan identitas: input100 menghasilkan250; input di bawah100
menghasilkan40. Consumer040003FE tidak ditemukan sebagai read langsung CIL
dan berada di VM. Karena fungsi turunan itu belum ditelusuri sampai gate
koneksi runtime, hasilnya tidak dilabeli jumlah koneksi aktual. Generator/API
mempertahankan nilai nominal MaxClient yang diminta; runtime_capacity_proven
tetapfalse. Nilai oracle tersimpan pada ../cbe_validation/.

Metode tanggal0E0A dibuktikan memakai overflow uncheckedInt32 pada komponen
tahun-menit, sama dengan SchoolPay. Backend CBE memiliki helper sendiri yang
cocok dengan vector oracle, termasuk4084 dan9999. Tanggal9999-12-31 menghasilkan
minute964677343 sehingga tidak diterima generator sebagai expiry masa depan
menurut arithmetika asli. Formula Gregorian normal tidak menggantikannya.

Sequence tetap internal: baru1; perpanjangan file lama mempertahankan KlienId
dan naik satu. Jika hanya Client ID diberikan tanpa file lama, backend tidak
mengarang Sequence terpasang. Antarmuka manual meminta file lama untuk renewal.

## Pengujian dan batas

Final original importer/loader matrix: **34 skenario /46 percobaan**, semua
hasil sesuai ekspektasi (29diterima,17ditolak). Tiga pasangan ID hasilgenerator
terbaru diterima oleh05C0 dan05BE. Variasi header dan Model tidak menjadi gate;
wrongInfo1/Seri dan expiry lampau juga diterima importer, sehingga runtime
activation tetap tidak terbukti. Lihat ../cbe_validation/matrix_summary.json.

`tests/test_cbe_codec.py`: **14 tes lulus**, original empty fixture, tiga ID, binding mismatch,
renewal otomatis, salah produk, angka tidak valid, overflow tanggal, overwrite.
Semua hasil generator diuji offline, sedangkan oracle asli menggunakan proses
terpisah dan direktori sandbox. Tidak ada binary,config,cache lisensi,atau
database instalasi aktif yang diubah. Report matriks ../cbe_validation/ menjadi
otoritas untuk acceptance, bukan test roundtrip Python sendiri.
