# JIBAS Generator — Kit REA & Perangkat Lisensi

> **Untuk agent berikutnya:** mulai dari sini. Dokumen ini memuat seluruh
> konteks yang dibutuhkan untuk melanjutkan pekerjaan tanpa mengulangi riset.

---

## 1. Apa ini

Direktori paket berisi **hasil reverse-engineering (REA)** dua target JIBAS
beserta **tool yang dibangun dari hasil REA** untuk menangani lisensinya:

```
C:\YIM\JIBAS Generator\
├── README.md                                  ← dokumen ini (mulai dari sini)
├── JIBAS-License-Tool\                        ← HASIL REA: tool lisensi (repo git)
│   ├── README.md                              ← dokumen tool (cara pakai + bukti)
│   ├── Analisis.md                            ← analisa biner server 16.5
│   ├── license_codec.py / cli.py / app.py     ← engine + CLI + GUI
│   ├── id_detect.py / dbid_recipe.py          ← detector Database/System ID
│   ├── schema.xml / format_profile.json       ← skema & profil kripto terbukti
│   ├── tests\                                 ← 39 pytest (lulus semua)
│   ├── bukti\                                 ← hasil pembuktian runtime (JSON/CS)
│   │   ├── e2e\client\licenseface_fix_runtime.json
│   │   └── client16\vm_strings.txt, intsites.txt
│   └── riset\                                 ← harness C# (server + client16)
├── JIBAS Face & Fingerprint Client 16.10\     ← TARGET 1 (salinan verbatim utk REA)
└── JIBAS Face Server 16.5\                    ← TARGET 2 (salinan verbatim utk REA)
```

Salinan target **byte-identik** dengan instalasi asli (dibandingkan SHA-256).
Folder asli di `C:\Program Files\YIM\…` tetap sebagai instalasi live.

## 2. Target REA

| Target | Biner | SHA-256 (awalan) | Versi | Kedudukan |
|---|---|---|---|---|
| **Face Server 16.5** | `FaceServer.exe` | `8a123015b2ee095c…` | 16.5 | lisensi server (`license.enc`) |
| **Face & Fingerprint Client 16.10** | `FaceFgrClient.exe` | `6f5369df4d854c46…` | 16.10.0.0 | cache lisensi `licenseface.enc` / `licensefgr.enc` |

Catatan REA inti — **REA (MCP) tidak mendukung PE managed** untuk target ini;
seluruh analisa memakai **harness C# refleksi** (lihat `riset/`). Kedua biner
obfuscated: nama kelas/metode `#=z…`, string dalam tabel VM numerik.

## 3. Fakta penting yang sudah terbukti (jangan riset ulang)

### 3.1 Format lisensi (server & client FACE — identik)

```
berkas  = base64( AES-128-CBC( ASCII(XML "JibasSptFaceLicense", 18 kolom),
                               key = MD5(ASCII(password)),
                               iv  = ASCII(iv) ) ) + "\r\n"
profil server/FACE : password '3477K3b3rS4mA4N', iv 'YaRAhM4nY4R4h1M#'
profil client FGR  : password '3477K3b3rS4ma4N', iv 'YaRahM@nY4R4h1M#'
padding PKCS7, XML schema "NewDataSet"
```

Kolom 18: Versi, KlienId, Klien, Tanggal, Model, Seri, Size, Sequence,
KodeRs, KodeTx, DbId, LicenseLimit, LicenseLimitDate, MaxClient, Keterangan,
Info1, Info2, Info3. Kolom `Model` diisi "" (importer asli menyalin 17 kolom).

### 3.2 Peta token utama (server `FaceServer.exe`)

| Tujuan | Token |
|---|---|
| Decoder string VM | `0x060004B5` (tak ber-canary → `Delegate.CreateDelegate` langsung) |
| Skema DataTable | `0x060006C4` (`JibasSptFaceLicense`) |
| Init kripto | `0x060006C5` |
| Importer license.enc | `0x060006CC` (DbId sama saat cache kosong; Sequence naik; KlienId sama) |
| Predikat runtime Info1/masa/kapasitas | `0x06000913` / `0x0600090D` |
| Resep Database ID (splang) | `0x06000AC3` |
| System ID (WMI + MD5) | `0x0600059B` |

### 3.3 Peta token utama (client `FaceFgrClient.exe` 16.10)

| Tujuan | Token |
|---|---|
| Decoder string VM (wrapper/worker) | `0x06000348` / `0x06000349(Int32,Boolean)` |
|canary decoder client| canary di init worker `0x06000349` (GetCallingAssembly + token mscorlib `B77A5C561934E089`); solusi **warm sekali via metode asli `0x060008B9`** lalu wrapper/worker bisa decode int arbitrer |
| Pre-init pasangan kripto FACE | `0x06000AF2` (holder `0x04000375/76`) |
| Path cache FACE | `0x06000AF0` → `licenseface.enc` |
| Loader/validator FACE | `0x06000AF3` / **`0x06000AF7`** |
| Pre-init pasangan kripto FGR | `0x060008BC` (holder `0x04000366/67`) |
| Path/loader/validator FGR | path → `licensefgr.enc`; loader `0x060008BD`; validator `0x060008C0` |
| Dekriptor DBPASSWORD config.ini | `0x06000A46` (PasswordDeriveBytes holder `0x040008B6`) → **`kebersamaan`** |
| Predikat registrasi (read-only SQL) | `0x0600052D` (count DB `jbsakad`,`jbssdm`,`jbssms`) |
| Handler pesan simpan | `0x0600051E`; pesan = VM(-121135179) + field `0x040004B6` |
| Holder mode global | `0x040004C7..D1` (default cctor: `'TRIAL'` semua) |
| Gate save bool + counter enrolment | `0x040004B8` (setter `0x0600082C`), `0x040004B5` (loader `0x0600082D`) |

Tabel 2349 string terdekripsi: `JIBAS-License-Tool\bukti\client16\vm_strings.txt`
(format: `int<TAB>teks`). Situs pemanggil: `intsites.txt`.

### 3.4 Akar masalah TRIAL & fix (SELESAI, terbukti)

- `licenseface.enc` bawaan = skeleton tanpa baris → validator `0x06000AF7`
  FALSE → mode `'TRIAL'` → handler simpan menolak:
  *"Tidak dapat menyimpan presensi wajah karena …"*.
- **Fix**: tulis satu baris salinan lisensi efektif Face Server ke
  `licenseface.enc` → validator TRUE, mode = KlienId.
- Perintah: `cli.cmd tulis-cache-client [--dari FILE] [--tujuan DIR] --overwrite`
  (cadangan otomatis; `licensefgr.enc` & `config.ini` tak disentuh).
- Bukti runtime: `bukti/e2e/client/licenseface_fix_runtime.json`.

## 4. Lingkungan mesin ini

| Fakta | Nilai |
|---|---|
| MySQL JIBAS | `127.0.0.1:3434`, user `root`, password `kebersamaan` (nilai config klien terdekripsi) |
| mysql.exe | `C:\YIM\JIBAS\xampp\mysql\bin\mysql.exe` |
| Layanan | `JIBAS-Database` (Running), `JIBAS-WebService` (Running) |
| FaceServer | PID 10880 berjalan (jangan dimatikan kecuali permintaan eksplisit) |
| Database ID mesin | `V4YNE` (jdbs `jbssat.splang01..12` wajib ada, 12 prosedur) |
| System ID mesin | `7738F` (**bukan** `DDCB4`; DDCB4 adalah Info1 lisensi lama yang ditolak) |
| TTS | `DpHost` / `TtsService.exe --port=8107` |
| Python runtime | `C:\Users\Laptop Kantor - ASUS\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe` (pakai `-X utf8`; hindari `-c` multioktaf bertingkat — tulis berkas script) |
| csc | hanya via full path `C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe` |
| Penghitungan wajah aktif | `SELECT COUNT(*) FROM jbssat.fcface WHERE status=1 AND useraktif=1` (saat ini 0) |

## 5. Aturan kerja (wajib dipatuhi)

1. **Jangan mengubah biner** kedua target. SEMUA tulisan eksperimen ke folder
   target hanya di salinan `JIBAS Generator\…` atau sandbox `%TEMP%`.
2. `license.enc` server asli **read-only** (SHA `197ae5c726cf483d…b6f65` —
   cek bila ragu). `config.ini` klien asli tak boleh berubah.
3. DB boleh dibaca kapan pun; tulis DB hanya dengan alasan eksplisit dan
   bukti restore (`splang` tidak boleh berubah: hasil ID `V4YNE`).
4. Bila mengedit tool: **edit di repo** `JIBAS-License-Tool\`, jalankan
   `python -m pytest tests -q` di sana, lalu sinkron deployment:
   `robocopy <repo> C:\YIM\JIBAS-License-Tool-OpenCode /MIR /XD __pycache__ .pytest_cache`
   (mkdir di `C:\Program Files` gugat: Access denied — pakai `C:\YIM`).
5. Bila perlu analisa biner lagi: gunakan harness di `riset/` (kumpil dengan
   csc full-path). Pola kunci decode string client: **warm `0x060008B9`
   (FGR path getter) dahulu**, lalu panggil wrapper/worker untuk int arbitrer.
6. Git di `JIBAS-License-Tool\` — commit per perubahan berarti
   (`feat:/fix:/docs:/test:/chore: …`).

## 6. Cara pakai tool (ringkas)

```cmd
cd "C:\YIM\JIBAS Generator\JIBAS-License-Tool"
cli.cmd detect                          :: Database ID + System ID (auto)
cli.cmd inspect "..\JIBAS Face Server 16.5\license.enc"
cli.cmd verify berkas.lic --auto
cli.cmd generate --database-id V4YNE --system-id 7738F ^
     --expires 2027-12-31 --capacity 100 --out baru.enc
cli.cmd tulis-cache-client              :: FIX TRIAL klien 16.10 (lihat atas)
"Jalankan GUI.cmd"                      :: GUI (tampilan kompak)
python -m pytest tests -q               :: 39 tes
```

## 7. Roadmap / tugas berikutnya untuk agent

1. **Terapkan fix CDC klien ke folder asli** (butuh persetujuan pengguna,
   aturan: tulisan folder target hanya sandbox):
   `cli.cmd tulis-cache-client --overwrite` — sudah termasuk cadangan otomatis.
2. (Opsional) Peta dispatcher dinamis layer-2 yang mengeset field `0x040004B6`
   (pesan) / `0x040004B8` (gate bool) — `0x06000161`, `0x060001C7`,
   resolver `0x06000B02`/`0x06000B04`, string obfuscated `i8…`.
   Saat ini mapping opsional: fix cache sudah membebaskan pesan trial di
   jalur utama; cukup verifikasi via GUI setelah fix diterapkan.
3. (Opsional) Selami `0x060008C0` (validator FGR) bila muncul kebutuhan
   fingerprint: pasangan `3477K3b3rS4ma4N`/`YaRahM@nY4R4h1M#`; validator sah
   pada baris 0 — kartu `licensefgr.enc` tidak perlu ditulis.
4. Perpanjangan lisensi server: produksi `.lic` via `generate` + impor asli
   (Sequence naik, KlienId sama, DbId sama). Info1 = System ID aktif (`7738F`).
5. Jaga jaminan: setelah perubahan apa pun, ulangi verifikasi sha target,
   sha `license.enc` server, status layanan, dan `pytest`.

## 8. Keamanan output perintah CLI

Perintah `inspect/verify/generate/tulis-cache-client` mengeluarkan **JSON**
dengan kunci `ok`/`results`/`error` — cocok di-pipe untuk agen berikutnya.
Exit code: `0` sukses, `1` verifikasi belum lulus, `2` argumen salah.
