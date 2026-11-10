# JIBAS Face Server 16.5 — Alat Lisensi (OpenCode)

> **Lokasi terpasang**: `C:\YIM\JIBAS-License-Tool-OpenCode` (kopi kerja juga ada di
> `C:\Users\Laptop Kantor - ASUS\agent-enhancements\unified-integration\JIBAS-License-Tool-OpenCode`).
> Penempatan ke `C:\Program Files\YIM` ditolak oleh sistem karena butuh izin
> administrator (Access denied); `C:\YIM` dipilih karena aman ditulis, bebas
> spasi di path, dan tetap di dalam pohon instalasi JIBAS.

Tool ini membaca, memeriksa, membuat, dan memperpanjang berkas lisensi
JIBAS Face Server 16.5, mendeteksi Database ID / System ID instalasi
secara otomatis memakai cara yang persis seperti aplikasi asli, dan (baru)
memperbaiki pesan uji coba **JIBAS Face & Fingerprint Client 16.10** dengan
menulis cache `licenseface.enc` dari baris lisensi efektif Face Server.

Berdasarkan analisa biner `FaceServer.exe`
(SHA-256 `8a123015b2ee095ceda51ece6d47436e9760c88be8f92fb76ed7c120c923c364`)
dan `FaceFgrClient.exe`
(SHA-256 `6f5369df…ba546`, Versi 16.10.0.0)
dan pembuktian runtime terhadap instalasi asli di mesin ini — lihat
`Analisis.md`, `bukti/`, dan `bukti/variable_audit.json` (pemetaan seluruh
variabel lisensi). Perbandingan fitur dengan tool pendahulu
`C:\Program Files\YIM\JIBAS-License-Tool-16.5` ada di `bukti/audit_lawas_vs_baru.json`.

## Komponen

| Berkas | Isi |
|---|---|
| `license_codec.py` | Codec lisensi server + dukungan cache klien 16.10 (`inspect_client_cache`, `write_client_cache`, `fix_client_cache`) |
| `id_detect.py` | `DbIdDetector` (resep splang asli `0x06000AC3`) dan `SystemIdDetector` (WMI + MD5 `0x0600059B`) |
| `dbid_recipe.py` | Konstanta resep Database ID terbukti |
| `cli.py` + `cli.cmd` | CLI |
| `app.py` + `Jalankan GUI.cmd` | GUI tkinter (dengan deteksi otomatis) |
| `search_db.py` | Util audit: cari teks Database ID di seluruh basis data JIBAS (baca-saja) |
| `schema.xml`, `format_profile.json` | Skema DataTable & profil kripto terbukti |
| `contoh/` | Lisensi contoh `V4YNE-7738F.lic` + penjelasan |
| `tests/` | 39 test pytest (vektor metode tanggal asli, fixture importer asli, dan uji cache klien 16.10) |
| `bukti/` | Hasil pembuktian runtime terhadap metode asli (termasuk `bukti/e2e/client/`) |
| `riset/` | Harness pembuktian (C#) yang dipakai saat analisa; `riset/client16/` untuk FaceFgrClient 16.10 (oracle string VM, probe validator/loader, probe predikat DB, probe dekriptor kata sandi config) |

## Cara pakai

### CLI

```cmd
cli.cmd detect                          :: deteksi Database ID + System ID
cli.cmd inspect lisensi.enc             :: baca isi berkas
cli.cmd verify lisensi.enc --auto       :: periksa terhadap ID hasil deteksi
cli.cmd generate --database-id V4YNE --system-id 7738F ^
     --expires 2027-12-31 --capacity 100 --out baru.enc
cli.cmd generate --database-id V4YNE --system-id 7738F ^
     --expires 2028-03-31 --capacity 200 --previous-license lisensi-aktif.enc ^
     --out perpanjang.enc
cli.cmd tulis-cache-client              :: FIX TRIAL klien 16.10 (lihat bawah)
cli.cmd tulis-cache-client --dari "C:\Program Files\YIM\JIBAS Face Server 16.5\license.enc" ^
     --tujuan "C:\Program Files\YIM\JIBAS Face & Fingerprint Client 16.10" --overwrite
```

Detail format output tiap perintah berbentuk JSON.

### GUI

Jalankan `Jalankan GUI.cmd`. Isi ID (atau tekan tombol deteksi), tentukan
masa berlaku + kapasitas + lokasi simpan, lalu klik **Buat Lisensi**.
Untuk perpanjangan pilih berkas lisensi sebelumnya.

## Format lisensi (terbukti)

`license.enc` / berkas impor:

```
base64( AES-128-CBC( ASCII(XML NewDataSet/JibasSptFaceLicense, 18 kolom),
                     key = MD5("3477K3b3rS4mA4N"),
                     iv  = "YaRAhM4nY4R4h1M#" ) ) + "\r\n"
```

Kolom: Versi, KlienId, Klien, Tanggal, Model, Seri, Size, Sequence, KodeRs,
KodeTx, DbId, LicenseLimit, LicenseLimitDate, MaxClient, Keterangan, Info1,
Info2, Info3. Importer asli `0x060006CC` menyalin 17 kolom (kolom `Model`
tidak ikut), memaksa DbId sama dengan ID saat runtime, dan untuk perpanjangan
menyuruh Sequence naik serta KlienId sama.

## Peta resep Database ID

```
   jbssat.splang01 ──CALL──▶ @uha @uhb @uhc @uhd @uhe @uhf @uhg @uhh @uhi
                              ─── payload hex ──▶ ASCII ──▶ ambil posisi ─┐
   jbssat.splang02 ──────────────────────────────────── posisi  5  (@uhf)  │
   jbssat.splang04 ──────────────────────────────────── posisi 14  (@uhh)  │
   jbssat.splang09 ──────────────────────────────────── posisi 25  (@uhc)  ├─▶ GABUNG ─▶ UPPER ─▶ Database ID
   jbssat.splang11 ──────────────────────────────────── posisi 37  (@uhe)  │
   jbssat.splang01 ──────────────────────────────────── posisi 47  (@uhb)  ┘
```

Sistem asli juga memverifikasi ke-12 prosedur `splang01..splang12` lewat
`information_schema.ROUTINES` — jika kurang maka aplikasi menolak beralasan
"Licensing system has been altered!".

## System ID

```
serial = Win32_PhysicalMedia.SerialNumber (disk yang memuat C:\, spasi
         di akhir di-trim oleh kode asli)
uuid   = Win32_ComputerSystemProduct.UUID
System ID = LOWER(MD5(serial + uuid))[5,17,30,24,3] lalu UPPER
```

`Info1` lisensi (disalin dari `Seri` pembuatnya) dibanding dengan nilai ini
oleh predikat runtime `0x06000913`/`0x0600090D`:
ID lama `DDCB4` pada instalasi ini **tidak** cocok (nilai asli `7738F`).

## Client 16.10 — perkara "Tidak dapat menyimpan presensi wajah karena status lisensi trial"

Akar masalah (dibuktikan runtime di salinan sandbox; biner tidak diubah):

- Validator cache FACE `0x06000AF7` mendekripsi `licenseface.enc` folder klien
  dengan pasangan `3477K3b3rS4mA4N`/`YaRAhM4nY4R4h1M#` (holder `0x04000375/76`,
  diisi pre-init dinamis `0x06000AF2`), membaca **baris base64 pertama** berkas
  lewat `UnicodeEncoding.ASCII + ReadLine` lalu `DataTable.ReadXml`.
- Skeleton bawaan **tanpa baris** → `rows == 0` → validator FALSE → holder mode
  global `0x040004C7..D1` tetap bernilai default cctor (`TRIAL` semua).
- Handler simpan `0x0600051E` (pesan VM `-121135179` = "Tidak dapat menyimpan
  presensi wajah karena ") menolak penyimpanan ketika mode masih `TRIAL`.
- `licensefgr.enc` (skema `JSL`, pasangan berbeda `3477K3b3rS4ma4N`/
  `YaRahM@nY4R4h1M#`, validator `0x060008C0`) sah meski tanpa baris — tidak
  memberi kontribusi pada pesan trial dan **tidak disentuh tool**.

Fix: `cli.cmd tulis-cache-client` menyalin **satu baris** dari lisensi efektif
Face Server (`license.enc` terpasang, atau berkas pilihan `--dari`) ke
`licenseface.enc`. Terbukti runtime: validator `0x06000AF7` → TRUE, mode
`0x040004C7` terisi KlienId, Klien/DbId sesuai (bukti:
`bukti/e2e/client/licenseface_fix_runtime.json`). Pengaman:

- folder target wajib memuat `FaceFgrClient.exe`;
- cache lama pindah ke `licenseface.enc.bak-<stempel>` saat timpa;
- `licensefgr.enc` dan `config.ini` selalu utuh;
- byte hasil dibaca ulang dan dibandingkan kolom demi kolom sebelum selesai.

Predikat registrasi klien (`0x0600052D`) tetap memerlukan MySQL JIBAS
(read-only: `SELECT NOW()` + hitung skema `jbsakad/jbssdm/jbssms`) — dibuktikan
TRUE terhadap server basis data lokal; tidak ada mutasi basis data.
Penghitung wajah (`jbssat.fcface` aktif) saat pengujian 0, jadi kuota tidak
menghambat.

## Batasan

- crypto tidak menandatangani apa pun: importer asli hanya memeriksa DbId,
  Sequence, dan KlienId.
- Alat ini tidak mengubah biner, tidak menjalankan engine/UI server, dan
  tidak menyentuh `license.enc` yang sedang dipakai instalasi asli.
- `verify_license` mengikuti aturan asli untuk tahun yang habis bagiannya
  (perbandingan menit _legacy_), jam pakai Asia/Jakarta, bukan dari DB.
- `tulis-cache-client` tidak pernah menyentuh biner klien; pengaturan data
  (`licenseface.enc`) saat dipakai ke folder klien sebelumnya dibuat
  cadangan timestamped dan baris harus lolos verifikasi kolom.
