# Absensi Finger — format dan bukti

Status 2026-11-11. Fingerprint mengikat **nomor seri scanner (`Seri`)**, bukan
Database ID atau System ID. Satu file dengan `LicType=CM` terbukti diterima
Manager 16.5, Fingerprint Client 14.0, dan jalur fingerprint Client 16.10.
Nama sekolah/klien adalah metadata `Klien`. Nomor seri harus sama persis,
termasuk huruf besar/kecil. Tidak ada input expiry, kapasitas, Client ID,
atau Sequence pada format JSL yang dibuktikan.

## Batas produk dan identitas build

| Target terpasang | SHA-256 executable | MVID |
|---|---|---|
| `C:\Program Files\YIM\JIBAS Face & Fingerprint Manager 16.5\FaceFingerManager.exe` | `4f4eed686831b9a6db21a263df3c94f83010bfecb1cf35f7fc7d27ce144db546` | `691ed074-4d5b-457c-c158-7d2227849bf0` |
| `C:\Program Files (x86)\YIM\JIBAS Fingerprint Client 14.0\Yim.Jibas.Sat.Fgr.Client.exe` | `34537e25e02637f902e4fc557d5b57d6551eeb931b56df96e7d8ee4821a8a8d5` | `e1a037ca-034f-4839-4340-ddb73be349db` |
| `C:\Program Files\YIM\JIBAS Face & Fingerprint Client 16.10\FaceFgrClient.exe` | `6f5369df4d854c467d24fb067d8b79c573b35699c7b1ce7f19a310669f1ba546` | `0ec4d2e7-40e6-4d47-2b18-cbedb1259d09` |

Tidak ditemukan produk Fingerprint Server terpisah dalam inventaris target
yang dipilih. Peran pengelolaan fingerprint berada pada Face & Fingerprint
Manager 16.5; jangan menyamakan lisensinya dengan Face Server 16.5.
Token berikut bersifat lokal untuk tiga build di atas.

## Peta metode asli

| Fungsi | Manager 16.5 | Client 14.0 | Client 16.10 FGR |
|---|---|---|---|
| Path cache | `06000B59` | `060006F8` | `060008B9` |
| Init crypto VM | `06000B5B` | `060006FA` | `060008BC` |
| Bangun schema | `06000B5A` | `060006F9` | `060008BB` |
| Simpan cache | `06000B5E` | `060006FD` | `060008BF` |
| Muat cache | `06000B5F` | `060006FE` | `060008C0` |
| Impor `.lic` | `06000B60` | `060006FF` | `060008C1` |
| Validasi nomor seri scanner | `06000B61` | `06000700` | `060008C2` |
| Holder tabel | `04000A56` | `040003AA` | `0400054E` |
| Holder password / IV | `040004DE/DF` | `04000424/25` | `04000366/67` |
| Holder folder dasar | `04000505` | `0400042E` | `04000369` |

Koreksi terminologi historis: `060008C0` Client 16.10 adalah **loader cache**
bernilai boolean. Validator nomor seri berada pada `060008C2(String)`.

## Format dan variabel

XML DataTable `NewDataSet`, tabel `JSL`, berisi 12 kolom string berurutan:
`Versi`, `Klien`, `Tanggal`, `Seri`, `KodeHw`, `KodeRs`, `KodeTx`, `LicType`,
`Keterangan`, `Info1`, `Info2`, `Info3`.

| Variabel | Arti yang terbukti / kebijakan generator |
|---|---|
| `Seri` | Pengikat nomor seri scanner, dibandingkan persis oleh validator asli. |
| `LicType` | `C` diterima client, `M` diterima manager, `CM` diterima keduanya. Scope salah ditolak importer asli. |
| `Klien` | Metadata nama klien; replay final juga menguji `Sekolah & École`. |
| `Versi` | Generator menulis `1.0`; nilai ini diterima pada semua tiga replay. Tidak diklaim sebagai versi executable. |
| `Tanggal` | Metadata tanggal pembuatan ISO; tidak ada kolom expiry dalam JSL. |
| `KodeHw`, `KodeRs`, `KodeTx` | Nilai kosong diterima oleh importer dan validator pada replay. Resep/kegunaan penerbitnya belum dibuktikan. |
| `Keterangan`, `Info1..3` | Generator menulis kosong, diterima pada replay. Makna lain belum dibuktikan. |

Crypto sama pada tiga build: AES-128-CBC, padding PKCS7, plaintext ASCII/XML
character references, key `MD5(ASCII(password))`, IV ASCII 16 byte. Password
`3477K3b3rS4ma4N`, IV `YaRahM@nY4R4h1M#` berasal dari holder init asli, sesuai
profil `client_fgr` yang sudah terpisah dari Face. Case password/IV wajib
dipertahankan. Tidak ada perubahan konstanta codec Face.

Cache adalah satu baris base64 + CRLF. File impor generator memakai:

```text
# LISENSI JIBAS SPT FINGERPRINT
<base64 ciphertext>
```

Marker baris pertama **wajib pada Client 16.10**. Manager 16.5 dan Client14
menerima payload tanpa header dan mengabaikan baris komentar. Header bersama
di atas terbukti diterima ketiganya. Jangan menyalin file impor dengan header
langsung menjadi cache: loader cache membaca baris base64 pertama.

## Bukti dan hasil

Seluruh bukti ada pada [`../../Codex/bukti/fingerprint`](../../Codex/bukti/fingerprint).

- `final_replay_summary.json`: hasil **tanpa hook** dari executable asli,
  file keluaran `fingerprint_codec.generate_license`, header bersama, `CM`,
  seri `{01234567-89AB-CDEF}`. Ketiganya mengembalikan impor `true`, satu row,
  cache ditulis hanya di sandbox, reload `true`, seri benar `true`, seri salah
  `false`. Detail berada pada `manager_final_replay.json`,
  `client14_final_replay.json`, `client16_final_replay.json`.
- `manager_CM_validate.json` dan `client16_CM_validate.json`: seri sama `true`,
  seri lain dan perubahan kapitalisasi `false`.
- `scope_rejection_summary.json`: manager menolak file `C`, kedua client
  menolak file `M`. `client14_renewal.json`: mengimpor ulang file yang sama
  ditolak dengan “Kode lisensi sudah dimasukkan”; format ini tidak memakai
  aturan kenaikan Sequence Face.
- `client16_CM_import.json`: payload tanpa header ditolak. File berheader
  diterima dalam replay final; kedua target lama menerima kedua bentuk.
- `manager_format.json` dan `client14_format.json`: schema dan pasangan
  crypto dari init/schema asli. Cache terpasang pada saat inventaris berisi
  schema JSL tanpa baris lisensi.
- `live_integrity.json` serta `inventory_before_final_replay.json` dan
  `inventory_after_final_replay.json`: SHA-256, ukuran, dan timestamp EXE,
  config, cache fingerprint tetap sama selama replay final.
- `*_license_il.txt` berasal dari reflection-only IL; tidak mengeksekusi
  kode target. `*_strings.txt` mendekode string melalui wrapper VM asli.
  `*_trace.json` bersifat eksplorasi dengan hook perbandingan string yang
  mempertahankan hasil perbandingan; bukan otoritas replay final.

Identitas dan metadata REA tersimpan pada `rea_identity_and_members.json`.
Evidence statis selected-type: Manager
`ev_7b8f80d5c3baabd05c36387737b5326ce98b42f2ff8ee1a6439e81f4e7fc8b56`,
Client14 `ev_dd64b392a5b7bd391492ab7839cb7119e99f6a706370dc83d35dcf8ae886db15`,
Client16 `ev_70c4c809164136f0eb1dfaff8303e0a25aee3d7810c39f59817f55910bcba8b2`.
Pemindaian managed members Manager seluruh assembly awal melebihi budget;
inventaris tipe tetap tersedia dan analisis tipe lisensi yang dipilih selesai.
Metadata/IL statis tidak diklaim sebagai pengamatan eksekusi VM.

Reproduksi dari folder `Codex`:

```powershell
python -m pytest tests/test_fingerprint_codec.py -q
python bukti/fingerprint/run_replay.py
```

Runner mengompilasi harness pada folder sementara dan hanya memanggil metode
path/init/schema/import/cache/serial. Tidak menjalankan Main, UI, scanner fisik,
database, atau layanan jaringan. Tidak mengaktifkan instalasi terpasang.

## Implementasi dan batas yang belum dibuktikan

[`fingerprint_codec.py`](../../Codex/fingerprint_codec.py) menyediakan
`generate_license(serial=..., license_scope='both'|'manager'|'client',
client_name=..., output_path=..., overwrite=False)`, `inspect_license(path)`,
dan `verify_license(path, serial, license_scope=None, for_import=False)`.
[`fingerprint_schema.xml`](../../Codex/fingerprint_schema.xml) wajib dibundel.

Pemeriksa offline mengembalikan `activation_proven=false`: hasil kompatibilitas
metode tidak sama dengan pengujian presensi lengkap menggunakan scanner.
Tidak dilakukan uji perangkat DigitalPersona fisik, komunikasi DB, atau alur
presensi end-to-end. Resep resmi kode transaksi/hardware dan perilaku build lain
tetap belum diketahui. Generator memakai nilai minimal yang sudah diterima
ketiga importer dan validator, tanpa mengarang expiry, kapasitas atau DBID.
