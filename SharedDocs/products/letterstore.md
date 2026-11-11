# JIBAS Letter Store 7.0

Status bukti 2026-11-11: backend Python sudah lolos importer asli, pembacaan ulang cache, dan pemeriksaan flag registrasi lokal untuk tiga Database ID sintetis. Input pengguna hanya **Database ID** dan nama klien opsional. Produk ini tidak memakai input System ID, Client ID, tanggal kedaluwarsa, kapasitas, atau Sequence pada jalur registrasi yang ditelusuri.

Target: `C:\Program Files (x86)\YIM\JIBAS Letter Store 7.0\LetterStore.exe`; assembly `LetterStore` 7.0.0.0, .NET Framework 4.8 / AnyCPU. SHA-256 `1bdf678980b4ad985838a1b9ce2233550b3e00f49cd578b481dd01c5e5690915`, MVID `9ee8d800-ba0c-4c48-1d5b-281c730e6bc2`. Semua token di halaman ini berlaku hanya untuk build tersebut.

## Input dan aturan produk

| Nilai | Lokasi asli / perilaku | Backend |
|---|---|---|
| Database ID | `Info3`; importer membandingkan dengan holder `0x04000605` secara tepat | Wajib; 5 huruf/angka, dinormalisasi uppercase |
| Nama klien | `Klien`, ditampilkan kembali pada data registrasi | Opsional; Unicode memakai referensi karakter XML |
| Versi format | `Versi` harus `2.0`; berbeda dari versi aplikasi 7.0 | Tetap `2.0` |
| Tanggal | `Tanggal` bertipe string; importer menyalinnya tanpa pemeriksaan kedaluwarsa | Waktu pembuatan dengan zona Asia/Jakarta |
| Seri | String pada daftar registrasi; metode `0x06000917` mencari `{Seri}` pada string daftar | UUID baru 32 karakter hex; pilihan implementasi generator |
| KodeRs / KodeTx | String yang disalin importer; KodeTx ditampilkan UI | Kosong; bukan input wajib importer yang diuji |
| Keterangan / Info1 / Info2 | String yang disalin importer | Kosong |
| System ID / expiry / capacity / Client ID / Sequence | Tidak ada di skema JLS maupun syarat importer/flag lokal yang ditelusuri | Tidak disediakan |
| Registrasi tambahan | Importer menolak jika tabel lisensi telah mempunyai baris: `Kode lisensi sudah dimasukkan!` | Tidak ada mode perpanjangan atau Sequence |

Getter ID `0x06000A1C` mengambil lima karakter dari hasil decode hex nilai routine database, kemudian `ToUpper()`. Jalur inisialisasi seed memakai alfabet `ABCDEFGHJKLMNPQRSTUVWXYZ123456789`; generator Python menerima bentuk 5 alfanumerik untuk mencakup nilai yang importer terima. Replay `9Z8Y7` juga diterima oleh importer. Getter database tidak dijalankan: kode inisialisasinya dapat membuat routine di `jbsletter`.

## Format berkas

File `.lic` berisi komentar opsional dan payload Base64 ASCII. Payload adalah AES-128-CBC dengan PKCS#7 atas XML ASCII; key berasal dari MD5 password ASCII dan IV ASCII 16 byte. Pasangan format diambil langsung melalui initializer asli `0x06000911` dan helper crypto `0x060006F4`/`0x060006F6`, bukan diasumsikan dari produk lain. Nilai konstanta ada pada [backend](../../Codex/letterstore_codec.py); ini bukan kredensial koneksi database.

XML `NewDataSet` membawa skema DataTable **JLS**, semua kolom `xs:string`, urutan:

`Versi, Klien, Tanggal, Seri, KodeRs, KodeTx, Keterangan, Info1, Info2, Info3`.

Skema hasil method asli disimpan di [original_schema.xml](../../Codex/bukti/letterstore/original_schema.xml). `license.enc` lokal adalah payload Base64 satu baris tanpa header. Importer melewati baris komentar `#`; payload tanpa header juga diterima. Header generator `# LISENSI JIBAS LETTER STORE` adalah label keluaran yang dipilih implementasi, bukan marker wajib target.

Python menolak tabel produk lain, DTD/entity, berkas lebih dari 4 MiB, dan beberapa baris JLS. Batas parser ini merupakan kebijakan generator; bukan klaim bahwa importer asli melakukan pemeriksaan yang sama. Hasil `verify_license` adalah pemeriksaan berkas offline.

## Peta token dan variabel

| Token | Peran / fakta |
|---|---|
| `0x06000910` | Membentuk tabel JLS beserta 10 kolom |
| `0x06000911` | Menginisialisasi pasangan crypto ke holder `0x04000245`/`0x04000246` |
| `0x0600090D` / `0x0600090E` | Getter/setter DataTable |
| `0x0600090F` | Path `license.enc`, berdasarkan direktori holder `0x04000236` |
| `0x06000914` | Menulis DataTable sebagai XML berskema lalu mengenkripsi cache |
| `0x06000915` | Membaca cache, memuat Klien dan Info3, membentuk daftar `{Seri}` |
| `0x06000916` | Import `.lic`; menolak tabel yang sudah terisi, versi bukan 2.0, atau Info3 berbeda; menyalin satu baris dan menyimpan cache |
| `0x06000917` | Memeriksa keberadaan `{Seri}` dalam daftar; bukan validasi tanda tangan |
| `0x04000605` | Database ID saat ini; disuplai harness sebagai data simulasi |
| `0x04000606` / `0x04000607` | Klien dan Database ID dari lisensi/cache |
| `0x06000989` | Membandingkan holder `605` dan `607`, meneruskan hasil ke setter flag |
| `0x06000987` / `0x06000988` / `0x04000608` | Getter/setter/holder bool registrasi lokal |
| `0x06000A1B` / `0x06000A1C` | Getter Database ID dengan koneksi sendiri / koneksi parameter; dianalisis statis saja |
| `0x060003C2` | Decoder literal string obfuscator |

Importer `916`, initializer `911`, pemeriksa daftar `917`, dan updater `989` dibungkus VM. [VmDisasm.cs](../../Codex/bukti/letterstore/VmDisasm.cs) memakai decoder operand dan resolver metadata asli untuk menampilkan bytecode tanpa menjalankan tubuh bisnisnya. Referensi metode dan operand hasil decode terdapat di `vm_import_disasm.json`, `vm_verify_disasm.json`, dan `vm_activation_disasm.json`. Penafsiran semantik bytecode adalah rekonstruksi; penerimaan berkas dan perubahan flag di bawah diamati lewat metode asli tanpa patch/hook.

## Bukti penerimaan dan batasnya

[original_import_results.json](../../Codex/bukti/letterstore/original_import_results.json) menyimpan hash executable/MVID, hash setiap fixture, hasil return, exception asli, dan kondisi setelah reload.

| Skenario | Hasil asli |
|---|---|
| Info3 sama dengan ID `ABCDE`, `12XYZ`, `9Z8Y7` | Import true; flag registrasi true |
| Payload sama tanpa header | Import true |
| Cache dari import dibaca ulang dengan `915` | Return true; flag registrasi tetap true |
| Holder ID runtime diganti `ZZZZZ` setelah import | Updater `989` mengubah flag menjadi false |
| File ABCDE dengan holder ID `QWERT` | Exception `Database Id tidak sama dengan lisensi` |
| Versi 1.0 | Ditolak dengan pesan kode lisensi lama |
| DataTable tanpa baris | Exception `Empty Registration File?` |
| Impor kedua setelah registrasi pertama | Exception `Kode lisensi sudah dimasukkan!` |

Harness memuat assembly asli, mengarahkan holder direktori ke folder TEMP, memasok holder ID saat ini, lalu menjalankan importer/cache-loader/updater asli. Main, UI, getter DB, routine DB, konfigurasi koneksi, dan jaringan tidak dijalankan. Tidak ada file instalasi yang ditulis. [live_integrity.json](../../Codex/bukti/letterstore/live_integrity.json) membandingkan SHA-256 executable, `config.ini`, dan `license.enc` sebelum/sesudah replay.

Bukti ini menetapkan kompatibilitas format, penerimaan importer, persistensi cache, penolakan ID salah, dan flag registrasi lokal. Aktivasi penerbit/layanan remote, seluruh startup aplikasi dengan database live, dampak pada operasi surat, dan kompatibilitas versi lain belum dibuktikan. Tidak ada aktivasi produksi yang dilakukan. `activation_proven: false` tetap dipakai pada verifier publik karena ia sendiri tidak menjalankan pemeriksaan target atau layanan penerbit.

## Reproduksi dan API

Jalankan dari folder `Codex` pada Windows dengan executable build yang cocok:

```powershell
python bukti/letterstore/run_oracle.py
python -m pytest tests/test_letterstore_codec.py -q
```

Runner mengompilasi [LetterStoreImportProbe.cs](../../Codex/bukti/letterstore/LetterStoreImportProbe.cs) ke TEMP, membuat ulang fixture sintetis dan bukti hash, memeriksa hasil serta integritas live. Cache uji ditulis hanya di folder TEMP unik. Binary harness tidak termasuk paket sumber.

```python
import letterstore_codec as ls
ls.generate_license(database_id="ABCDE", output_path="letterstore.lic", client_name="Nama Sekolah")
ls.inspect_license("letterstore.lic")
ls.verify_license("letterstore.lic", "ABCDE", for_import=True)
```

Verifikasi unit terarah: **12 passed**. Fixture unit terikat dengan SHA-256 berkas yang diterima/ditolak metode asli, sehingga perubahan data bukti yang tidak selaras terdeteksi.

Evidence REA: identitas artifact `ev_4e9d9a7e6d198d99cf70b6d251415f472c238e46df4dc4e6db0b77bfd13972cf` di [rea_artifact.json](../../Codex/bukti/letterstore/rea_artifact.json); anggota 4 tipe terpilih, 40 method, `ev_7c9751473a14386f1ff766dd691345963e7e8cef141989243d9cc38ea81661c6` di [rea_license_members.json](../../Codex/bukti/letterstore/rea_license_members.json). Keduanya observasi statis; tidak menyatakan bahwa aplikasi telah dijalankan.
