# Temuan REA dan perbaikan akurasi

Tanggal: 10 November 2026. Dua klaim lama telah dibantah oleh eksekusi metode asli:
ID live yang benar DDCB4, dan file impor client membutuhkan header di luar payload
cache. Kesimpulan di dokumen ini mengungguli README/Analisis/bukti historis paket awal.

## Cakupan direktori

Seluruh `C:\Program Files\YIM` diinventaris rekursif dan dihash SHA-256:

| Direktori | Berkas | Peran terkait lisensi |
|---|---:|---|
| JIBAS Face & Fingerprint Client 16.10 | 555 | FaceFgrClient.exe, licenseface.enc, licensefgr.enc; importer dan loader FACE diuji |
| JIBAS Face & Fingerprint Manager 16.5 | 84 | FaceFingerManager.exe; license.enc memakai skema JSL fingerprint, bukan FACE |
| JIBAS Face Server 16.5 | 73 | FaceServer.exe, license.enc; importer, loader, predicate runtime dan generator ID diuji |
| JIBAS-License-Tool-16.5 | 106 | Generator lama, fixture, bukti/harness; menjadi acuan historis |

Total 818 file termasuk file tersembunyi/.git/cache. Inventaris lengkap ada pada
`bukti/inventory_before.json` dan `inventory_after.json`. Hash seluruh file bukan
klaim semua dependency SDK, TTS, dan native library sudah didekompilasi.

REA mendukung metadata managed pada sesi ini, berbeda dari catatan keterbatasan
agent lama. Metadata SHA/MVID serta managed-members disimpan dalam evidence baru.
Kedua executable target obfuscated/VM; pengujian perilaku memakai refleksi .NET
ke metode asli, tidak mengubah IL/executable. Trace/hook eksplorasi client dipisah
dari matriks final yang berjalan tanpa hook.

| Target | SHA-256 | MVID |
|---|---|---|
| FaceServer.exe | 8a123015b2ee095ceda51ece6d47436e9760c88be8f92fb76ed7c120c923c364 | 9e7e3122-c165-4ca3-3e9c-234edb96bf24 |
| FaceFgrClient.exe | 6f5369df4d854c467d24fb067d8b79c573b35699c7b1ce7f19a310669f1ba546 | 0ec4d2e7-40e6-4d47-2b18-cbedb1259d09 |
| FaceFingerManager.exe | 4f4eed686831b9a6db21a263df3c94f83010bfecb1cf35f7fc7d27ce144db546 | 691ed074-4d5b-457c-c158-7d2227849bf0 |

Manager diperiksa identitasnya melalui REA; cache-nya dapat didekripsi dengan
profil fingerprint lama dan berisi schema JSL 12 kolom tanpa data. Generator
Codex ditujukan ke FACE, bukan format JSL fingerprint/manager.

## Bagaimana file dibuat dan dibaca kembali

Payload FACE berisi XML `NewDataSet` dengan tabel `JibasSptFaceLicense`, 18 kolom.
Sequence bertipe Int32 dan LicenseLimitDate DateTime; kolom lainnya String.

1. Isi DbId dari Database ID; Info1 dari System ID server tujuan.
2. Isi KlienId baru (generator menggunakan UUID), atau pertahankan KlienId lama
   untuk perpanjangan. Sequence baru 1; perpanjangan harus lebih tinggi dari cache.
3. Isi tanggal, kapasitas MaxClient, identitas/nama, dan kolom pelengkap.
4. Serialisasi XML ASCII, gunakan referensi karakter XML untuk teks non-ASCII.
5. Key AES = MD5 byte ASCII password profil; AES-128-CBC dengan IV profil dan
   padding PKCS7. Hasil ciphertext disimpan sebagai Base64 + CRLF.
6. **File impor** diberi baris pertama `# LISENSI JIBAS SPT FACE`.
   **Cache internal** hanya Base64 + CRLF, tanpa header.

Profil yang diuji ada di `format_profile.json`; profil server dan client FACE
sama. Profil fingerprint berbeda kapitalisasi password/IV dan memakai schema
berbeda. Menggunakan profil fingerprint pada payload FACE tidak valid.

Pembacaan balik: lepaskan header/komentar untuk file impor, Base64 decode,
AES-CBC decrypt dengan key/IV yang sama, hapus PKCS7, parse XML, lalu baca kolom.
Implementasi: `_encrypt`, `_decrypt`, `_serialize`, `inspect_license` dalam
`license_codec.py`. Ini rekonstruksi format simetris; bukan private-key signing.
Di jalur yang diuji tidak dibutuhkan tanda tangan asimetris dari generator.
Kesimpulan itu tidak membuktikan seluruh jalur validasi online penerbit.

## Mengapa error client terjadi

Handler UI client `0x06000650` menuju importer `0x06000AF9`. Sebelum dekripsi,
importer mencari literal case-sensitive `LISENSI JIBAS SPT FACE` pada baris
pertama. File generator lama mulai langsung dengan Base64, sehingga dilempar
exception **File terpilih bukan lisensi JIBAS Presensi Wajah**. Nama metode
obfuscated dalam pesan adalah konteks exception, bukan kode lisensi.

Header yang hilang, salah, atau lowercase menghasilkan error yang sama pada
replay asli. Header benar menghilangkan error tersebut. Importer berikutnya
memeriksa Database ID dan aturan perpanjangan. Holder Database ID aktif client
yang benar adalah `0x0400051C`. AF7 merupakan loader/validator cache; menguji
AF7 saja tidak menguji penerimaan file oleh AF9.

`Model=SPTFACE` bukan penyebab penolakan tersebut. File dengan Model ini diterima
setelah header dibenarkan. Generator sekarang menulis header, sementara fungsi
penulis cache tetap tanpa header. `verify --for-import` mendeteksi kekurangan ini.

## Bagaimana verifikasi bekerja

| Tahap | Pemeriksaan yang terbukti | Batas |
|---|---|---|
| Client importer AF9 | Header, XML/crypto, Database ID; Sequence naik dan KlienId sama pada renewal | Info1 salah tetap dapat diimpor |
| Client cache AF7 | Cache dapat dibaca dan field dapat dikonversi, termasuk Int32 | Bukan bukti runtime server aktif |
| Server importer 6CC | Database ID; Sequence naik dan KlienId sama pada renewal | System ID salah tetap dapat diimpor |
| Server loader 6CA dan predicate 913/90D | DbId, Info1/System ID, tanggal, kapasitas, non-TRIAL pada lingkungan uji | Guard jaringan dan keadaan server/database dikendalikan pada proses uji |
| Python verify | Struktur, ID, angka, formula tanggal; header opsional --for-import | Offline; tidak membaca sequence terpasang kecuali saat generate renewal memakai file lama |

Import sukses dan cache berisi baris tidak setara dengan lisensi aktif. Server
menolak System ID salah pada predicate runtime meski importer menerima file.
Client AF9/AF7 juga menerima Info1=00000 dalam kontrol yang diuji.

Formula waktu asli bukan ordinal Gregorian. Sebagai contoh 2028-12-31T23:59
dan 2029-01-01T23:59 menghasilkan minute sama pada metode asli. Python menjaga
kompatibilitas formula lama; uji kedaluwarsa matriks memakai tanggal jauh sesudah
expiry. Jangan menafsirkan `verify` sebagai kalender Gregorian/konfirmasi online.

## Bagaimana Database ID dibentuk

Database ID bukan nilai konfigurasi biasa dan bukan hash System ID. Metode
server `0x06000AC3` mengambil lima karakter dari keluaran routine `jbssat.splangNN`:

| Urutan karakter | Routine | Parameter OUT (0-based) | Posisi ASCII hasil hex decode (0-based) |
|---:|---|---|---:|
| 1 | splang04 | @uhh, indeks 7 | 14 |
| 2 | splang02 | @uhf, indeks 5 | 5 |
| 3 | splang09 | @uhc, indeks 2 | 25 |
| 4 | splang11 | @uhe, indeks 4 | 37 |
| 5 | splang01 | @uhb, indeks 1 | 47 |

Gabungkan lalu uppercase. Pada database aktif hasilnya V + 4 + Y + N + E.

Bootstrap asli: jika tidak ada routine splang, ABF/ABD/AC5 membuat 12 routine,
masing-masing 9 OUT berisi hex dari string acak 64 karakter (ABB/System.Random),
serta ABC menyiapkan struktur pendukung. Lima posisi terpilih menentukan ID.
Jika hanya sebagian routine hilang, jalur asli menolak dengan
`Licensing system has been altered!`. Memanggil AC3 pada database tanpa routine
dapat menulis database; detector Python sengaja menolak routine hilang.

Pembuktian dilakukan pada instance MariaDB kedua port3435 dengan datadir sandbox,
bukan dengan mengganti ID produksi: V4YNE, ABCDE, WRK9T, Z9X8W, a1b2c→A1B2C
cocok antara original AC3 dan Python. Bootstrap kosong menghasilkan 12 routine
dan ID acak LTB28 yang juga cocok. Instance sandbox sudah dihentikan.
Hash routine live port3434 sebelum/sesudah identik.

## Bagaimana System ID dibentuk

Metode asli `0x06000599/59A/59B` mengambil serial PhysicalMedia untuk disk fisik
yang memuat C: dan UUID Win32_ComputerSystemProduct. Serial dan UUID digabung
**tanpa trim/case normalization**, dienkode dengan perilaku ASCII .NET, dihitung
MD5 lowercase hex, diambil indeks **5,17,30,24,3**, lalu uppercase.

Serial mesin ini mempunyai sembilan spasi belakang. Dengan spasi tersebut
metode asli menghasilkan **DDCB4**; trim pada detector lama menghasilkan 7738F.
`id_detect.py` sekarang mempertahankan byte/karakter serial, dan meniru fallback
ASCII per UTF-16 code unit .NET untuk karakter non-ASCII. Enam vector hash
divalidasi terhadap metode asli. Angka DDCB4 di file lama bukan bukti mismatch.

## Pembuktian dan keadaan akhir

- `bukti/server_matrix/matrix_summary.json`: 31 skenario importer dan 117 kasus runtime sesuai ekspektasi; empat pasangan ID termasuk simulasi 7738F.
- `bukti/client_import/matrix_results.json`: 8 skenario/11 percobaan; error exact, header benar, multi-ID, renewal, mismatch, Info1 salah; final tanpa hook.
- `bukti/id_audit/isolated_db_matrix.json`: lima ID dan bootstrap; routine live unchanged.
- `bukti/id_audit/original_hardware_vectors.json`: enam vector hash asli vs Python.
- `tests/`: 49 tes lulus; GUI Tk dibuat/destroy sebagai smoke test; launcher CLI dicoba di path dengan spasi.

Binary/config/cache live tidak ditulis. Layanan JIBAS-Database dan JIBAS-WebService
tetap running. Tidak ada klaim full GUI activation atau panggilan layanan online.
Untuk penggunaan pada instalasi sudah berlisensi, generate renewal dengan
file lama; jangan mengimpor contoh lisensi baru dengan KlienId berbeda.
