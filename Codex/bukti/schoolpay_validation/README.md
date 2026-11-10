# Pembuktian SchoolPay Secure Server 10.5

Target SHA-256 `ca112352f1160ead541ff404354aecb3a83165798e562dea5ca3ef68191cd2f8`,
MVID `3f7d530d-8b12-4c29-229b-d7a7bd599cf1`. REA identity tersimpan pada
`rea_identity.json`; token berikut hanya berlaku pada build ini.

## ID dan waktu

Original reader `0x06000824` membaca **jbsfina**, berbeda dari Face yang membaca
jbssat. Recipe (routine, indeks OUT, posisi hasil ASCII hex-decode), semuanya
0-based: `(2,2,9), (7,3,21), (10,6,12), (1,6,32), (9,6,45)`.
Karakter digabung dan uppercase. Reader asli dan Python memberikan **7VJM4**
pada database live. Kedua set hash 12 routine sebelum/sesudah identik.
Reader asli hanya dipanggil setelah memastikan semua routine tersedia;
detector Python tidak menjalankan bootstrap jika routine hilang.

Original hardware `0x06000943/944/945` menghasilkan **DDCB4**. Algoritme sama
dengan Face: serial PhysicalMedia disk C: mentah (termasuk sembilan spasi),
UUID ComputerSystemProduct, ASCII .NET, MD5 lowercase hex[5,17,30,24,3], uppercase.
Implementasi `schoolpay_id_detect.py` berbagi helper hardware yang sudah diuji,
tetapi memiliki recipe/database sendiri. Password dibaca eksplisit atau dari
environment JIBAS_DB_PASSWORD, tanpa disimpan oleh GUI.

`id_date_oracle.json` merekam original ID, detail karakter, raw hardware,
routine hashes, dan sembilan vector original date `0x06000708`.
Vector tahun4084,4085,9999 membuktikan signed Int32 overflow pada komponen tahun.
Codec SchoolPay memakai helper terpisah yang meniru arithmetic ini. Formula
Face lama hanya menjadi pembanding; tidak dijadikan oracle untuk tahun jauh.

## Importer resmi dan cache

UI file dialog handler `0x06000799` memanggil **`0x06000757`**. Metode0758
merupakan wrapper VM lain, bukan entry point UI yang dipakai matriks ini.
Host folder `0x0400036F` diarahkan ke sandbox; warm074F, initcrypto0751,
schema0750 dipanggil sebelum importer. CurrentDb holder052D dan System0524
diisi lingkungan kontrol. Tidak menjalankan Main, UI, SQL/network pada matriks.

Input impor membutuhkan **DataColumn `ForSchoolPay` pada schema XML** di samping
19 kolom cache. Nilai1,0,false,kosong, dan nullable/schema-only semuanya diterima.
Generator memilih nilai1 sebagai keluaran kanonik. Nilai tersebut tidak
dibuktikan sebagai gate entitlement. Cache hasil importer tidak menyimpan
ForSchoolPay dan tidak menyalin Model ke row. Loader asli `0x06000756` berhasil
membaca setiap cache yang berasal dari impor sukses.

Header `# LISENSI JIBAS SCHOOLPAY` bersifat komentar opsional: headerless dan
komentar produk lain juga diterima. Ini berbeda dengan importer client FACE.
Missing ForSchoolPay memicu exception setelah beberapa holder in-memory
sudah diperbarui; file cache belum dibuat. Karena itu penolakan format ini
tidak boleh dinyatakan atomik. Pengujian berlangsung pada proses terpisah.

## Matriks final

`run_import_matrix.py` mengompilasi harness x86 dan menghasilkan input melalui
codec Python terbaru. `matrix_summary.json`: **31 skenario / 43 percobaan**,
seluruh hasil sesuai ekspektasi. Detail tiap percobaan berada di JSON perlabel
dan `matrix_results.json`.

- Tiga pasangan ID: 7VJM4/DDCB4, ABCDE/ABCDE, 12345/12345.
- Fresh dan Sequence naik diterima; Sequence sama/turun dan Client ID berubah
  ditolak melalui exception spesifik asli.
- Database ID berbeda ditolak. System ID berbeda tetap diterima importer/cache.
- Payload rusak, kolom ForSchoolPay hilang, MaxVendor di luar Int32 ditolak.
- Lisensi yang tanggalnya sudah lewat masih diterima importer.
- Header opsional, flag0/false/kosong/schema-only diterima.

**Batas:** importer/cache success tidak membuktikan runtime/aktivasi online.
Updater runtime09D0 berupa VM opaque; guard SQL/online yang aman belum dapat
dibuktikan secara statis, sehingga metode itu tidak dieksekusi. Matriks ini
tidak mengklaim expiry/capacity/SystemId telah diterima oleh runtime penuh.

## Menjalankan ulang

Compile `SchoolPayIdProbe.cs` dengan .NET Framework csc x86 dan reference
System.Web.Extensions.dll; untuk audit ID set credential hanya dalam environment,
lalu `python -X utf8 -m bukti.schoolpay_validation.audit_schoolpay_ids`.
Jalankan matriks melalui `python -X utf8 -m bukti.schoolpay_validation.run_import_matrix`.
Runner membuat sandbox unik di TEMP dan tidak memasang cache ke direktori target.
Executable hasil kompilasi dan folder sandbox bukan bagian paket Git.
