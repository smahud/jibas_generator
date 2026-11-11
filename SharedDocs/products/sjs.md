# JIBAS SJS 7.10

Status 2026-11-11: format lisensi dan importer lokal sudah direproduksi. Registrasi/aktivasi server Jendela Sekolah belum diuji dan tidak diklaim berhasil. Aplikasi Generator memerlukan **Database ID + Registration Token**; SJS tidak menggunakan System ID. **School ID yang sudah terdaftar** diperlukan untuk lisensi baru. File lama dapat memasok School ID untuk perpanjangan.

## Identitas build dan bukti

| Item | Nilai |
|---|---|
| Target | `C:\Program Files (x86)\YIM\JIBAS SJS - Sinkronisasi Jendela Sekolah 7.10\JsSync.exe` |
| Assembly | `JsSync`, `7.10.0.0`, .NET Framework 4.8 |
| SHA-256 | `6078efda305e292dabc2bd371c78f870fade17eff98f0c141e5aa565cb25c838` |
| MVID | `8bab9291-3e99-4322-07e1-cc628baabb12` |
| REA inventory | `ev_9cdb090b6a52a9623b586e57e53bec41305930e76341d4e0e3842f46c25337cc` |
| REA metadata | `ev_d2e69805a8a7c7b7923d363680176fd6380479a942658ce5f52aa30671ad35d0` |
| REA focused members | `ev_ce9c1a84cd429124a7c84027ce994c7839562e7693433d0748c9f8045bbdece9` |

Koordinat metadata di bawah hanya berlaku untuk SHA/MVID ini. Inventaris menyeluruh anggota awal mencapai batas representasi REA, lalu diperbaiki dengan pemilihan empat tipe relevan; hasil fokus berstatus complete untuk pilihan itu: 46 metode, 15 field, 861 call edge dan 92 field access. Ini bukan dekompilasi semua kode VM maupun bukti eksekusi seluruh aplikasi.

Bukti: [ringkasan REA](../../Codex/bukti/sjs/rea_summaries.json), [IL fokus beserta string hasil decoder](../../Codex/bukti/sjs/focused_il.txt), [skema/format hasil metode asli](../../Codex/bukti/sjs/format.json), [matriks oracle asli](../../Codex/bukti/sjs/oracle_matrix.json), [fixture token dari encoder asli](../../Codex/bukti/sjs/token_oracle.json).

## Registration Token

UI asli menyebut Database ID dan Registration Token sebagai data untuk registrasi Jendela Sekolah. Tombol token `0x06000928` memanggil `0x0600103E`; metode itu membaca statistik DB lalu mengemasnya secara lokal. Tidak ada penerbitan token online pada jalur tersebut.

Token berbentuk **lima angka desimal + Base64**. Prefix = seed + 17; seed dipilih melalui `0x06000FFF` dari rentang 91000 sampai 99799. Payload = Base64(UTF-8(JSON yang setiap karakternya di-XOR dengan karakter angka seed berulang)). Pasangan encoder/decoder `0x06000FFC`/`0x06000FFE` mendukung format ini. `0x06000FF9` menginisialisasi offset 17 pada field `0x04000786`. Encoding ini bukan tanda tangan penerbit.

JSON berisi 15 bilangan Int32:

| Posisi | Makna dari `0x0600103E` |
|---|---|
| 0, 14 | Sentinel acak 100..998 |
| 1..5 | Jumlah siswa, pegawai, departemen, kelas, pelajaran |
| 6..9 | Jumlah nilaiujian, nap, rekakun, jurnal |
| 10..13 | Selisih hari sejak ts terakhir siswa, nilaiujian, nap, jurnal; -1 bila data tidak ada |

Token **tidak memuat Database ID, School ID, System ID, expiry, kapasitas atau data lisensi**. Karena itu token valid yang sama dapat dipasangkan dengan input Database ID berbeda pada pemeriksaan format offline; kecocokannya dengan DB tidak terbukti. Token tidak disimpan sebagai kolom lisensi dan importer asli tidak membacanya. Generator memvalidasi struktur dan memperlihatkan statistik, tanpa membuat token pengganti atau mengklaim token sebagai binding lisensi.

Fixture token dalam bukti dibuat dari statistik sintetis melalui encoder asli yang murni, lalu diperiksa decoder asli dan implementasi Python. Fixture tersebut bukan token DB pengguna atau token registrasi yang diterbitkan secara online.

## Bentuk lisensi dan variabel

`0x06000EB3` membuat DataTable `JibasJsLicense` di bawah `NewDataSet` dengan skema XSD dan tepat 12 kolom. Semua bertipe string kecuali LimitDate (`DateTime`) dan Sequence (`Int32`).

| Kolom | Input / aturan Generator |
|---|---|
| Versi | `7.10` untuk baru; dipertahankan saat renewal. Importer lokal tidak memvalidasi versi. |
| SchoolId | `school_id`; alias API `client_id` berarti School ID. Wajib manual untuk baru; tidak dialokasikan acak. |
| SchoolFullName | `client_name`; dipertahankan dari file lama jika kosong. |
| SchoolName | `school_short_name`; untuk baru memakai nama penuh bila tidak diberikan. |
| GroupId, GroupName | Parameter opsional; dipertahankan saat renewal. Default baru kosong terbukti diterima importer lokal. |
| DatabaseId | `database_id`, 5 karakter huruf/angka; dibandingkan importer dan pemeriksaan runtime lokal. |
| MaxAgentConn | `capacity`, bilangan positif Int32. Disimpan sebagai string lalu dikonversi ke Int32 oleh aplikasi. |
| Jenis | Metadata opsional, dipertahankan saat renewal; default baru kosong diterima importer lokal. Makna hak server belum diketahui. |
| LimitDate | `expires` (`YYYY-MM-DD`), akhir hari 23:59:59 WIB. |
| Sequence | Baru 1; perpanjangan otomatis file lama + 1. |
| Services | JSON list dari list string (`List<List<string>>`), default baru `[]`; dipertahankan saat renewal. Makna elemen/hak fitur belum diketahui. |

SchoolId dipakai sebagai `JsUserRequest.SchoolId` dalam registrasi remote (`0x06001353`). School ID lokal acak tidak akan membuktikan adanya sekolah tersebut di server. Generator sengaja memerlukan School ID yang sudah diketahui. Nama, group dan Services kosong hanya telah dibuktikan dapat diimpor lokal; kesesuaian metadata penerbit tetap belum diketahui.

MaxAgentConn mengisi field kapasitas `0x040007E3` dan kapasitas efektif awal `0x040007E4`. `0x06001064` memberi label 1 = Community Single Speed, 2 = Extra Double Speed, 3 = Extra Triple Speed, 4 = Extra Quad Speed; nilai lain tampil `-`. Kapasitas dipakai pada loop koneksi dan dibawa dalam permintaan registrasi server. Pengujian file tidak membuktikan jumlah koneksi aktif atau kapasitas yang diizinkan server.

## Kriptografi dan impor

`0x06000EB4` menginisialisasi pasangan format di field `0x040003C8`/`0x040003C9`. Profil terpisah ada di [sjs_format.json](../../Codex/sjs_format.json), skema di [sjs_schema.xml](../../Codex/sjs_schema.xml). Pasangan ini adalah konstanta format binary, bukan kredensial login.

`0x06001081` membuat key MD5(ASCII(password)), IV ASCII 16 byte, Rijndael/AES CBC dengan PKCS7. `0x06001083` menghasilkan Base64 dari enkripsi ASCII XML; `0x06001085` mendekripsinya. File impor dapat mengandung komentar `#`; header khusus tidak diwajibkan. Generator menambah `# LISENSI JIBAS JENDELA SEKOLAH` sebagai label yang dapat dibaca. Cache `license.enc` adalah satu baris Base64 dengan CRLF tanpa header.

Importer `0x06000EBA`:

1. Menggabungkan baris nonkosong yang bukan komentar, mendekripsi, lalu `ReadXml`.
2. **Impor pertama:** membandingkan DatabaseId; melewati cabang expiry dan pemeriksaan SchoolId lama karena belum ada lisensi.
3. **Perpanjangan:** menolak Sequence lebih kecil/sama, SchoolId berbeda, DatabaseId berbeda, dan LimitDate lebih awal daripada waktu database yang disimpan aplikasi.
4. Menyalin 12 kolom ke tabel lokal dan menulis cache lewat `0x06000EB7`.

Tidak ada validasi tanda tangan pada jalur importer statis ini. Pernyataan itu dibatasi pada kode yang dilacak; tidak menyatakan server remote menerima lisensi ini. Pemeriksa Python lebih ketat pada expiry, kapasitas positif, struktur token dan format tabel untuk mencegah keluaran yang tidak sesuai. `0x06000EBC` memeriksa status lisensi dan kecocokan DatabaseId secara lokal; aktivasi remote adalah proses tambahan yang belum dijalankan.

## Hasil dan reproduksi

[run_oracle.py](../../Codex/bukti/sjs/run_oracle.py) mengompilasi [SjsImportProbe.cs](../../Codex/bukti/sjs/SjsImportProbe.cs) di direktori temporer lalu memanggil importer asli tanpa hook/patch. Path cache, DatabaseId dan waktu database ditetapkan hanya di memori proses harness; aplikasi Main, koneksi DB dan koneksi jaringan tidak dijalankan. Jalur importer yang ditinjau hanya menulis cache temporer. Hash executable, config dan cache instalasi sebelum/sesudah sama.

Matriks 11 kontrol: tiga Database ID positif, Database ID salah negatif, expiry lama diterima pada impor pertama, expiry lama ditolak pada perpanjangan, renewal Sequence naik positif, Sequence sama/turun negatif, School ID berbeda negatif, dan file tanpa header positif. Default group/Jenis kosong dan Services `[]` ikut diterima pada kontrol positif. Ini membuktikan kompatibilitas impor/cache lokal, bukan registrasi sekolah atau aktivasi layanan produksi.

Jalankan dari `Codex/`:

```powershell
python -m pytest tests/test_sjs_codec.py -q
python bukti/sjs/run_oracle.py
```

Saat bukti ini dibuat, 23 tes Python lulus dan seluruh 11 kontrol original sesuai ekspektasi. Tes negatif token meliputi prefix di luar rentang, Base64 rusak, payload tidak sesuai dan token kosong. Informasi layanan online, alokasi School ID, makna elemen Services dan pembuktian entitlement tetap belum diselesaikan dan tidak dipalsukan.
