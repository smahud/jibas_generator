# JIBAS License Tool — OpenCode Implementation

> **Implementasi Python untuk manajemen lisensi JIBAS Face Server 16.5, JIBAS Face & Fingerprint Client 16.10, JIBAS SchoolPay Secure Server 10.5, dan JIBAS CBE Server 26.5**

Tool ini dibangun berdasarkan hasil *reverse engineering* terhadap biner asli JIBAS menggunakan REA (Reverse Engineering Agent) dan harness C# refleksi. Seluruh mekanisme kriptografi, format berkas, dan validasi ID direkonstruksi dari kode asli tanpa modifikasi biner.

---

## 🎯 Fitur Utama

| Fitur | Deskripsi |
|-------|-----------|
| **Inspeksi Lisensi** | Baca dan dekripsi berkas `.lic` / `.enc`, tampilkan metadata dan 18 kolom data |
| **Verifikasi Offline** | Periksa kesesuaian Database ID, System ID, Client ID, masa berlaku, kapasitas, sequence |
| **Generate Lisensi Baru** | Buat lisensi baru dengan parameter Database ID, System ID, masa berlaku, kapasitas |
| **Perpanjangan Lisensi** | Perpanjang lisensi existing (Sequence naik otomatis, KlienId & DbId sama) |
| **Perbaiki Client Cache** | Tulis `licenseface.enc` ke FaceFgrClient 16.10 dari lisensi Face Server efektif (hilangkan mode TRIAL) |
| **Multi-Produk** | Dukung Face/Fingerprint (16.5/16.10), SchoolPay (10.5), CBE Server (26.5) |

---

## 📦 Instalasi

```bash
cd "C:\YIM\JIBAS Generator\JIBAS-License-Tool-OpenCode"

# Buat virtual environment (disarankan)
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

**Dependencies:**
- `cryptography` — AES-128-CBC, PKCS#7 padding
- `pymysql` — koneksi MySQL untuk deteksi Database ID (opsional)

---

## 🚀 Penggunaan Cepat

### CLI (Command Line)

```cmd
rem Baca isi lisensi
cli.cmd inspect license.lic

rem Verifikasi lisensi terhadap ID instalasi
cli.cmd verify license.lic --database-id V4YNE --system-id 7738F

rem Buat lisensi baru (Face/Fingerprint)
cli.cmd generate --database-id V4YNE --system-id 7738F ^
    --expires 2027-12-31 --capacity 100 --output baru.lic

rem Buat lisensi baru (SchoolPay)
cli.cmd generate --database-id V4YNE --system-id 7738F ^
    --expires 2027-12-31 --capacity 100 --output schoolpay.lic --product schoolpay

rem Buat lisensi baru (CBE Server)
cli.cmd generate --database-id V4YNE --system-id 7738F ^
    --expires 2027-12-31 --capacity 100 --output cbe.lic --product cbe

rem Perpanjang lisensi
cli.cmd renew --database-id V4YNE --system-id 7738F ^
    --expires 2028-12-31 --capacity 200 ^
    --previous-license lama.lic --output baru.lic

rem Perbaiki cache client 16.10 (hilangkan mode TRIAL)
cli.cmd fix-client-cache --overwrite
```

### GUI (Desktop)

```cmd
"Jalankan GUI.cmd"
```

ATAU:
```cmd
python gui.py
```

GUI memiliki 5 tab:
1. **Inspeksi & Verifikasi** — Baca berkas, verifikasi dengan ID manual
2. **Buat & Perpanjang** — Generate baru / perpanjangan lisensi (Face, SchoolPay, CBE)
3. **SchoolPay** — Manajemen lisensi SchoolPay Secure Server 10.5
4. **CBE Server** — Manajemen lisensi CBE Server 26.5
5. **Perbaiki Client Cache** — Tulis `licenseface.enc` ke client 16.10

---

## 🔐 Format Lisensi (Terbukti dari Binary Asli)

### Enkripsi
```
berkas = base64( AES-128-CBC( ASCII(XML "JibasSptFaceLicense" / "JibasSchoolPayLicense" / "JibasCbeLicense", 18 kolom),
                                key = MD5(ASCII(password)),
                                iv  = ASCII(iv) ) ) + "\r\n"
```

### Profil Kripto
| Profil | Password (base64) | IV (base64) | Sumber |
|--------|-------------------|-------------|--------|
| `server` | `MzQ3N0szYjNyUzRtQTRO` | `WWFSQWhNNG5ZNFI0aDFNIw==` | FaceServer.exe 0x060006C5 |
| `client_face` | `MzQ3N0szYjNyUzRtQTRO` | `WWFSQWhNNG5ZNFI0aDFNIw==` | Client 16.10 0x06000AF2 (holder 0x04000375/76) |
| `client_fgr` | `MzQ3N0szYjNyUzRtYTRO` | `WWFSYWhNQG5ZNFI0aDFNIw==` | Client 16.10 0x060008BC (holder 0x04000366/67) |
| `schoolpay` | `MzQ3N0szYjNyUzRtQTRO` | `WWFSQWhNNG5ZNFI0aDFNIw==` | SPayServer.exe (sama server) |
| `cbe` | `MzQ3N0szYjNyUzRtQTRO` | `WWFSQWhNNG5ZNFI0aDFNIw==` | CbeServer.exe (sama server) |

### Skema XML (18 Kolom)
```
Versi, KlienId, Klien, Tanggal, Model, Seri, Size,
Sequence, KodeRs, KodeTx, DbId, LicenseLimit,
LicenseLimitDate, MaxClient/MaxVendor, Keterangan, Info1, Info2, Info3
```
*Kolom `Model` diisi `""` (importer asli menyalin 17 kolom).*

---

## 🆔 Pembentukan ID

### Database ID (DbId) — 5 Alfanumerik
Dihitung oleh **FaceServer.exe method 0x06000AC3** dari database `jbssat`:
```sql
DbId = UPPER(
    hex_decode(@uhh)[14] +   -- splang04, OUT param index 7
    hex_decode(@uhf)[5]  +   -- splang02, OUT param index 5
    hex_decode(@uhc)[25] +   -- splang09, OUT param index 2
    hex_decode(@uhe)[37] +   -- splang11, OUT param index 4
    hex_decode(@uhb)[47])    -- splang01, OUT param index 1
```
Memerlukan 12 prosedur `splang01`–`splang12` di `jbssat`.

### System ID (Info1/Seri) — 5 Hex
Dihitung oleh **FaceServer.exe method 0x0600059B**:
```
serial = Win32_PhysicalMedia.SerialNumber (disk fisik yang menyimpan C:\)
uuid   = Win32_ComputerSystemProduct.UUID
SystemId = MD5_ASCII(serial + uuid) lowercase hex, chars [5,17,30,24,3], upper
```

### Client ID (KlienId) — 32 Hex
- **Lisensi baru**: UUID acak (`uuid.uuid4().hex.upper()`)
- **Perpanjangan**: Harus sama dengan lisensi sebelumnya

---

## ✅ Aturan Verifikasi (Offline)

| Check | Deskripsi |
|-------|-----------|
| `license_row` | Berkas berisi baris lisensi (bukan cache kosong) |
| `required_fields` | 17/18 kolom wajib ada (kecuali `Model`) |
| `database_id` | `DbId` berkas == Database ID instalasi |
| `system_id` | `Info1` berkas == System ID mesin |
| `non_trial` | `KlienId` tidak kosong dan bukan `"TRIAL"` |
| `client_id` | `KlienId` berkas == Client ID yang diberikan (opsional) |
| `expiry` | `LicenseLimitDate` belum lewat (perhitungan menit legacy asli) |
| `capacity` | `MaxClient`/`MaxVendor` dalam rentang 1..2147483647 |
| `sequence` | `Sequence` dalam rentang 1..2147483647 |
| `count` | Jumlah aktif ≤ kapasitas (opsional) |

⚠️ **Batasan:** Verifikasi offline **tidak membuktikan** penerimaan importer, aktivasi penerbit, status server berjalan, atau koneksi database.

---

## 🛠 Perbaikan Client 16.10 TRIAL

### Masalah
`FaceFgrClient.exe` 16.10 menampilkan pesan *"Tidak dapat menyimpan presensi wajah karena ..."*
karena cache `licenseface.enc` bawaan kosong (skeleton tanpa baris) → validator `0x06000AF7` mengembalikan `FALSE` → mode global tetap `"TRIAL"`.

### Solusi
```cmd
cli.cmd fix-client-cache --overwrite
```
Menulis satu baris lisensi efektif dari `license.enc` Face Server ke `licenseface.enc` client.
- Cadangan otomatis: `licenseface.enc.bak-<timestamp>`
- `licensefgr.enc` dan `config.ini` **tidak disentuh**

---

## 📁 Struktur Direktori

```
JIBAS-License-Tool-OpenCode/
├── jibas_license_tool.py      # Core library + CLI entry point
├── gui.py                     # GUI Tkinter (5 tab)
├── cli.cmd                    # Windows CLI launcher
├── Jalankan GUI.cmd           # Windows GUI launcher
├── license_codec.py           # Codec kriptografi & XML (internal)
├── id_detect.py               # Detektor Database ID & System ID (referensi)
├── dbid_recipe.py             # Resep Database ID (referensi)
├── diagnostics.py             # Facade read-only untuk GUI lama
├── format_profile.json        # Profil kripto (password/IV per target)
├── schema.xml                 # Skema XML Face/Fingerprint
├── schema_schoolpay.xml       # Skema XML SchoolPay
├── schema_cbe.xml             # Skema XML CBE Server
├── requirements.txt           # Dependencies Python
├── V4YNE-7738F.lic            # Contoh lisensi (Database ID V4YNE, System ID 7738F)
└── README.md                  # Dokumentasi ini
```

---

## 🧪 Pengujian

```bash
# Jalankan pytest
python -m pytest tests/ -v

# Test manual CLI
python jibas_license_tool.py inspect V4YNE-7738F.lic
python jibas_license_tool.py verify V4YNE-7738F.lic --database-id V4YNE --system-id 7738F
python jibas_license_tool.py generate --database-id V4YNE --system-id 7738F --expires 2027-12-31 --capacity 100 --output test.lic
python jibas_license_tool.py generate --database-id V4YNE --system-id 7738F --expires 2027-12-31 --capacity 100 --output test_schoolpay.lic --product schoolpay
python jibas_license_tool.py generate --database-id V4YNE --system-id 7738F --expires 2027-12-31 --capacity 100 --output test_cbe.lic --product cbe
```

---

## 📋 Catatan Penting

1. **Tidak ada modifikasi biner** — Tool ini hanya membaca/menulis berkas lisensi format standar.
2. **Credential default** — MySQL `root`/`kebersamaan` adalah default bawaan JIBAS (bukan kredensial khusus).
3. **Database ID `V4YNE` & System ID `7738F`** — Contoh pada mesin pengembang; **ganti dengan ID mesin target**.
4. **Perpanjangan** — `Sequence` naik otomatis, `KlienId` & `DbId` harus sama.
5. **System ID `DDCB4`** — Nilai lama yang muncul di cache bawaan **BUKAN** hasil mesin ini (rekayasa tool sebelumnya) dan **DITOLAK** predikat runtime asli.
6. **Sequence otomatis** — Sequence diisi otomatis (1 untuk baru, previous+1 untuk perpanjangan), tidak perlu diisi manual.

---

## 🔗 Referensi & Sumber

- **Repository GitHub**: https://github.com/smahud/jibas_generator
- **Direktori Lokal**: `C:\YIM\JIBAS Generator\`
- **Target Binary**:
  - `C:\Program Files\YIM\JIBAS Face Server 16.5\FaceServer.exe`
  - `C:\Program Files\YIM\JIBAS Face & Fingerprint Client 16.10\FaceFgrClient.exe`
  - `C:\Program Files\YIM\JIBAS SchoolPay Secure Server 10.5\SPayServer.exe`
  - `C:\Program Files\YIM\JIBAS CBE Server 26.5\CbeServer.exe`
- **Hasil REA Sebelumnya**: `C:\YIM\JIBAS Generator\JIBAS-License-Tool-Codex-Publish\`

---

## ⚖️ Lisensi & Hukum

Tool ini dibuat untuk keperluan analisis teknis dan manajemen lisensi internal.
**Hak atas software JIBAS dan materi pihak ketiga tetap mengikuti ketentuan pemiliknya.**
Gunakan hanya data dan berkas yang Anda berhak akses.

> **Disclaimer**: Hasil verifikasi offline **bukan konfirmasi aktivasi atau keaslian dari penerbit JIBAS**.
> Untuk penerbitan/perpanjangan lisensi resmi, hubungi vendor JIBAS.