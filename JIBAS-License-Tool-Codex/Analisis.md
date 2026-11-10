# CATATAN HISTORIS — BACA TEMUAN.md UNTUK HASIL TERBARU

System ID live adalah DDCB4; file impor client wajib berheader.
Klaim lama yang berbeda di bawah tidak dipakai sebagai kesimpulan sesi Codex.

# Analisis Lisensi JIBAS Face Server 16.5 — Rebuild OpenCode

Dokumen ini merangkum jawaban atas tiga pertanyaan riset dengan pembuktian
runtime terhadap metode asli (semua runtime menjalankan kode asli
`FaceServer.exe` via reflection; biner tidak diubah). Analisa statis lengkap
per metode ada di tool pendahulu: `C:\Program Files\YIM\JIBAS-License-Tool-16.5\Analisis_Lisensi.md`
dan `bukti\verification_findings.md` miliknya.

## 1. Bagaimana Database ID dibentuk?

Database ID **bukan data statis**. Sebelum dipakai, `FaceServer.exe` memeriksa
skema `jbssat`: harus ada 12 prosedur `splang01..splang12` di
`information_schema.ROUTINES`, jika jumlahnya tidak 12 aplikasi menolak dengan
"Licensing system has been altered!". Lalu metode `0x06000AC3` menjalankan
`USE jbssat`, memanggil prosedur-prosedur itu (9 parameter OUT `@uha..@uhi`),
dekode hex→ASCII payload, dan mengambil karakter pada posisi tetap:

```
DbId = UPPER( hex_decode(@uhh)[14]  splang04
            + hex_decode(@uhf)[5]   splang02
            + hex_decode(@uhc)[25]  splang09
            + hex_decode(@uhe)[37]  splang11
            + hex_decode(@uhb)[47] ) splang01
```

Pembuktian runtime (bukti `bukti/detector_provenance.json`,
`bukti/import_results/*.json`):

- Dekripsi cache terpasang → DbId `V4YNE`.
- Menjalankan `0x06000AC3` asli terhadap MySQL live → `V4YNE` ✔.
- Payload prosedur splang di-ubah (`splang01/02/04/09/11` ditulis ulang),
  `0x06000AC3` asli → berubah menjadi `WRK9T`, dan resep Python
  (`DbIdDetector`) menghitung `WRK9T` juga ✔ — membuktikan rumus, bukan
  kebetulan.
- Database dipulihkan ke kondisi `V4YNE`; metode asli kembali `V4YNE` ✔.

Karena aplikasi membaca DB, perubahan isi prosedur mengganti Database ID dari
sudut pandang aplikasi — itulah yang memungkinkan uji "Database ID berbeda"
tanpa mengubah biner.

## 2. Apakah tool agent lama benar untuk ID berbeda?

Ya. Lisensi dibuat dengan generator ini untuk `WRK9T/7738F` (kondisi DB yang
sudah diubah), lalu **importer asli `0x060006CC`** dijalankan di sandbox pada
proses terpisah — field `0x040004DB` diisi hasil `0x06000AC3` asli (bukan
injeksi manual) dan `0x040004E7` diisi `0x0600059B` asli:

- `lic_wrk9t_match.enc` (WRK9T + Info1 7738F) → **diterima**, cache
  `license.enc` tertulis, semua field terisi (KlienId, Sequence=1,
  MaxClient=100000, LicenseLimitDate 31/12/2027 23:59).
- `lic_v4yne_dbid.enc` (DbId `V4YNE`, beda dengan live `WRK9T`) → **ditolak**
  dengan `System.Exception: Database Id tidak sama dengan lisensi (V4YNE)`;
  cache tidak dibuat.
- `lic_wrong_sysid.enc` (Info1 `DDCB4` ≠ `7738F`) → **diterima** oleh importer
  → membuktikan Info1/System ID **tidak** diverifikasi saat impor; hanya saat
  runtime.

## 3. Berapa System ID yang benar, dan bagaimana status lisensi terpasang?

`0x0600059B` asli menjalankan:
`SystemId = LOWER(MD5(Win32_PhysicalMedia.SerialNumber(disk C:) +
Win32_ComputerSystemProduct.UUID))[5,17,30,24,3].UPPER()` — serial mentah,
spasi dibelakang di-trim. Di mesin ini: `30029941042` +
`E0813C3C-120B-02FE-5F00-BCAEC5319E78` → **7738F** (bukan `DDCB4`).

Hasil predikat runtime `0x06000913`/`0x0600090D` terhadap cache generator ini
(bukti `bukti/verification_runtime_predicate.json`, 8 skenario):

| Skenario | Hasil | Status teks asli |
|---|---|---|
| valid (WRK9T/7738F) | diterima | Aktif |
| wrong_database (ZZZZZ) | ditolak | Database id (ZZZZZ) tidak sesuai dengan lisensi (WRK9T) |
| wrong_system (ZZZZZ) | ditolak | (jalur online dihentikan guard) |
| **Info1 = DDCB4 (cache lama)** | **ditolak** | — |
| expired | ditolak | Jangka waktu lisensi telah berakhir |
| at_capacity (100000) | diterima | Aktif |
| over_capacity (100001) | ditolak | Jumlah wajah yang aktif (100001) melebihi lisensi (100000) |
| TRIAL | ditolak | TRIAL |

Implikasinya: lisensi cache terpasang lama ber-Info1 `DDCB4` **tidak pernah
aktif** di mesin ini pada jalur predikat lokal. `DDCB4` berasal dari replay
predikat oleh tool agent lama yang meng-inject field `0x040004E7` dengan
Info1 lisensinya sendiri (lingkaran tertutup), sedangkan hasil metode asli
`0x0600059B` adalah `7738F`. Lisensi baru yang benar harus memakai
Info1 `7738F`.

## Audit end-to-end (2026-11-10, sesi kedua)

Perbandingan penuh dengan tool lawas (`C:\Program Files\YIM\JIBAS-License-Tool-16.5`)
dan pemetaan seluruh variabel: lihat `bukti/audit_lawas_vs_baru.json` dan
`bukti/variable_audit.json` (password asli 3477K3b3rS4mA4N / IV YaRAhM4nY4R4h1M#
didekode dari profil, bukan dari catatan). Implementasi kernel codec identik
baris-per-baris dengan lawas; semua 18 kolom terimplementasi; baru merupakan
superset (detect CLI/GUI, --overwrite, auto-verify).

Hasil E2E dari lisensi yang dihasilkan tool ini, terhadap kode asli:

| Kasus importer asli 0x060006CC | Hasil |
|---|---|
| baru, DbId sama (V4YNE), Info1 7738F | diterima, cache tertulis |
| baru, DbId WRK9T (beda dgn asli) | ditolak — "Database Id tidak sama dengan lisensi (WRK9T)" |
| perpanjangan, KlienId sama, Sequence 1→5 | diterima (Sequence/MaxClient/Info1 ikut baru) |
| perpanjangan, KlienId sama, Sequence 1→1 (sama) | ditolak — pesan asli "Sequence lisensi sama dengan lisensi yang terdaftar!" |
| perpanjangan, KlienId berbeda, Sequence naik | diterima namun KlienId aktif tetap nilai cache lama (nuansa merge asli; generator tool ini lebih ketat) |
| baru, Info1/DDCB4 untuk info | diterima → Info1 memang tidak diperiksa saat impor, hanya saat runtime |

Predikat runtime asli 8/8 sesuai (valid aktif, salah DB/Info1/expired/kapasitas/TRIAL ditolak).
Semua rincian ada di `bukti/e2e/`.

Penempatan: `C:\Program Files\YIM` menolak penulisan (butuh admin), sehingga
tool dipasang di `C:\YIM\JIBAS-License-Tool-OpenCode`.

## Catatan keamanan

- Tidak ada tanda tangan digital; format hanya AES dengan kunci dari password
  konstan + XML. Keaslian berkas bergantung pada tiga cek importer (DbId,
  Sequence, KlienId) dan cek runtime (Info1, masa berlaku, kapasitas,
  status TRIAL).
- Selama pembuktian: semua pengujian memakai sandbox `%TEMP%\opencode\import_*`;
  `license.enc` aktif hanya dibaca, tidak diganti; DB eksperimen dipulihkan ke
  `V4YNE` dan diverifikasi dengan metode asli.
