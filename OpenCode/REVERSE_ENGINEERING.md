# Hasil Reverse Engineering — JIBAS License Mechanism

> **Dokumen ini merangkum temuan reverse engineering terhadap JIBAS Face Server 16.5 dan JIBAS Face & Fingerprint Client 16.10.**
> Dibuat menggunakan REA (Reverse Engineering Agent) dan harness C# refleksi.

---

## 1. Target Binary

| Target | File | SHA-256 | Versi | Arsitektur |
|--------|------|---------|-------|------------|
| Face Server | `FaceServer.exe` | `8a123015b2ee095ceda51ece6d47436e9760c88be8f92fb76ed7c120c923c364` | 16.5.0.0 | x86_64 .NET Framework 4.8 |
| Face Client | `FaceFgrClient.exe` | `6f5369df4d854c467d24fb067d8b79c573b35699c7b1ce7f19a310669f1ba546` | 16.10.0.0 | x86_64 .NET Framework 4.8 |

Keduanya adalah **managed PE (CLI)**, obfuscated (nama kelas/metode `#=z...`, string dalam tabel VM numerik).

---

## 2. Format Lisensi (Terbukti)

### 2.1 Enkripsi
```
File = Base64( AES-128-CBC( ASCII(XML), Key, IV ) ) + "\r\n"
```
- **Key**: `MD5(ASCII(password))` → 16 byte AES-128 key
- **IV**: 16 byte ASCII
- **Padding**: PKCS#7
- **Plaintext encoding**: ASCII (XML character references untuk non-ASCII)

### 2.2 Struktur XML
```xml
<NewDataSet>
  <xs:schema id="NewDataSet" ...>...</xs:schema>
  <JibasSptFaceLicense>
    <Versi>16.5</Versi>
    <KlienId>32-char-hex</KlienId>
    <Klien>Nama Klien</Klien>
    <Tanggal>YYYY-MM-DD</Tanggal>
    <Model>SPTFACE</Model>
    <Seri>SystemID</Seri>
    <Size>Capacity</Size>
    <Sequence>1</Sequence>
    <KodeRs></KodeRs>
    <KodeTx></KodeTx>
    <DbId>DatabaseID</DbId>
    <LicenseLimit>YYYY-MM-DD</LicenseLimit>
    <LicenseLimitDate>YYYY-MM-DDTHH:MM:SS+07:00</LicenseLimitDate>
    <MaxClient>Capacity</MaxClient>
    <Keterangan></Keterangan>
    <Info1>SystemID</Info1>
    <Info2></Info2>
    <Info3></Info3>
  </JibasSptFaceLicense>
</NewDataSet>
```

### 2.3 Profil Kripto (Terbukti dari Binary)

| Profil | Password (base64) | IV (base64) | Dekripsi | Token Inisialisasi |
|--------|-------------------|-------------|----------|-------------------|
| `server` | `MzQ3N0szYjNyUzRtQTRO` (=`3477K3b3rS4mA4N`) | `WWFSQWhNNG5ZNFI0aDFNIw==` (=`YaRAhM4nY4R4h1M#`) | `license.enc` (Face Server) | `0x060006C5` |
| `client_face` | `MzQ3N0szYjNyUzRtQTRO` | `WWFSQWhNNG5ZNFI0aDFNIw==` | `licenseface.enc` (Client FACE) | `0x06000AF2` (holder `0x04000375/76`) |
| `client_fgr` | `MzQ3N0szYjNyUzRtYTRO` (=`3477K3b3rS4ma4N`) | `WWFSYWhNQG5ZNFI0aDFNIw==` (=`YaRahM@nY4R4h1M#`) | `licensefgr.enc` (Client FGR) | `0x060008BC` (holder `0x04000366/67`) |

---

## 3. Peta Token Penting (FaceServer.exe)

| Fungsi | Token | Catatan |
|--------|-------|---------|
| String VM Decoder | `0x060004B5` | Tak ber-canary, `Delegate.CreateDelegate` langsung |
| DataTable Schema `JibasSptFaceLicense` | `0x060006C4` | |
| Inisialisasi Kripto | `0x060006C5` | Set password/IV holder |
| Importer `license.enc` | `0x060006CC` | DbId sama saat cache kosong; Sequence naik; KlienId sama |
| Predikat Runtime (Info1/masa/kapasitas) | `0x06000913` / `0x0600090D` | |
| Resep Database ID (splang) | `0x06000AC3` | Jalankan 5 prosedur splang, ambil karakter spesifik |
| System ID (WMI + MD5) | `0x0600059B` | `MD5(disk_serial + UUID)` → hex[5,17,30,24,3].upper() |

---

## 4. Peta Token Penting (FaceFgrClient.exe 16.10)

| Fungsi | Token | Catatan |
|--------|-------|---------|
| String VM Decoder (wrapper) | `0x06000348` | |
| String VM Decoder (worker) | `0x06000349(Int32,Boolean)` | **Canary**: `GetCallingAssembly` + token mscorlib `B77A5C561934E089` |
| Canary Bypass | **Warm sekali via `0x060008B9`** (FGR path getter) lalu wrapper/worker bisa decode int arbitrer | |
| Pre-init Kripto FACE | `0x06000AF2` | Holder `0x04000375` (pwd), `0x04000376` (iv) |
| Path Cache FACE | `0x06000AF0` | → `licenseface.enc` |
| Loader FACE | `0x06000AF3` | Baca baris base64 pertama → `DataTable.ReadXml` |
| Validator FACE | **`0x06000AF7`** | `rows == 0` → FALSE (mode TRIAL); `rows >= 1` → TRUE (copy kolom ke holder) |
| Pre-init Kripto FGR | `0x060008BC` | Holder `0x04000366` (pwd), `0x04000367` (iv) |
| Path/Loader/Validator FGR | Path `0x060008BB`; Loader `0x060008BD`; Validator `0x060008C0` | Validator sah pada baris 0 |
| Dekriptor DBPASSWORD config.ini | `0x06000A46` | `PasswordDeriveBytes` holder `0x040008B6` → `"kebersamaan"` |
| Predikat Registrasi (SQL read-only) | `0x0600052D` | Count DB `jbsakad`,`jbssdm`,`jbssms` |
| Handler Pesan Simpan | `0x0600051E` | Pesan = VM(-121135179) + field `0x040004B6` |
| Holder Mode Global | `0x040004C7..D1` | Default cctor: `"TRIAL"` semua kolom |
| Gate Save Bool + Counter Enrolment | `0x040004B8` (setter `0x0600082C`), `0x040004B5` (loader `0x0600082D`) | |

---

## 5. Mekanisme Database ID (Terbukti)

### Algoritma Asli (Method `0x06000AC3`)
1. `USE jbssat`
2. Verifikasi 12 prosedur `splang01`–`splang12` ada di `information_schema.ROUTINES`
3. Untuk setiap prosedur dalam resep, call dengan 9 OUT parameter (`@uha`–`@uhi`)
4. Decode hex ASCII dari parameter tertentu, ambil karakter di posisi tertentu
5. Gabungkan 5 karakter → `UPPER()` → Database ID

### Resep (Dibuktikan Runtime)
| Prosedur | OUT Param Index | Posisi Karakter | Contoh Karakter |
|----------|-----------------|-----------------|-----------------|
| `splang04` | 7 (`@uhh`) | 14 | `V` |
| `splang02` | 5 (`@uhf`) | 5 | `4` |
| `splang09` | 2 (`@uhc`) | 25 | `Y` |
| `splang11` | 4 (`@uhe`) | 37 | `N` |
| `splang01` | 1 (`@uhb`) | 47 | `E` |
**Hasil: `V4YNE`**

---

## 6. Mekanisme System ID (Terbukti)

### Algoritma Asli (Method `0x06000599` + `0x0600059A` + `0x0600059B`)
1. Query WMI: `Win32_DiskDrive` (InterfaceType SCSI/IDE) → cari partisi → logical disk `C:` → dapatkan `DeviceID`
2. Query `Win32_PhysicalMedia` → match `Tag` dengan `DeviceID` → ambil `SerialNumber` (trim trailing space)
3. Query `Win32_ComputerSystemProduct` → ambil `UUID`
4. `SystemId = MD5(SerialNumber + UUID).hexdigest().lower()[5,17,30,24,3].upper()`

### Hasil Mesin Ini (Terbukti Runtime)
- **Disk Serial**: `30029941042`
- **UUID**: `E0813C3C-120B-02FE-5F00-BCAEC5319E78`
- **MD5**: `7738f...` → **System ID: `7738F`**

> ⚠️ **Catatan**: Nilai `DDCB4` yang lama muncul di cache bawaan BUKAN hasil mesin ini (rekayasa tool sebelumnya) dan DITOLAK predikat runtime asli.

---

## 7. Mekanisme Verifikasi Lisensi (Importer Asli)

### FaceServer.exe Importer (`0x060006CC`)
1. Dekripsi file lisensi → parse XML → ambil baris pertama `JibasSptFaceLicense`
2. **Cek DbId**: Bandingkan dengan Database ID saat ini (dari `0x06000AC3` atau field cache)
3. **Cek Sequence**: Harus > Sequence yang terpasang (untuk perpanjangan)
4. **Cek KlienId**: Harus sama dengan yang terpasang (untuk perpanjangan)
5. Simpan ke cache `license.enc` (encrypted DataTable)
6. **Tidak ada verifikasi signature** di jalur impor ini

### FaceFgrClient.exe 16.10 Validator FACE (`0x06000AF7`)
1. Pre-init kripto via `0x06000AF2` (isi holder pwd/iv)
2. Baca `licenseface.enc` → `StreamReader.ReadLine` → base64 decode → `DataTable.ReadXml`
3. Jika `rows == 0` → return `FALSE` → mode global tetap `TRIAL`
4. Jika `rows >= 1` → copy kolom baris pertama ke holder `0x040004C7..D1` → return `TRUE`
5. Mode `TRIAL` → handler simpan (`0x0600051E`) tolak dengan pesan VM(-121135179) = *"Tidak dapat menyimpan presensi wajah karena ..."*

---

## 8. Error "File terpilih bukan lisensi JIBAS Presensi Wajah"

### Investigasi
- **File dialog filter** (ditemukan di VM strings): `JIBAS Presensi Wajah License|*.lic` (token `-121159156` di method `0x06000650`)
- **Pesan error persis** TIDAK ditemukan di:
  - VM strings client (`bukti/client16/vm_strings.txt` — 2349 string)
  - PE resources
  - Binary strings ASCII/Unicode
- **Kemungkinan penyebab**:
  1. Pesan dibangun dinamis dari fragmen string VM
  2. Pesan ada di satellite assembly / resource DLL terpisah
  3. Pesan berasal dari validasi ekstensi file (hanya `.lic` diterima, bukan `.enc`)

### File Dialog Filter (Terbukti)
```
Filter: "JIBAS Presensi Wajah License|*.lic"
Method: 0x06000650 (LisensiWajahForm.btAddLicense_Click area)
```
Artinya: **Hanya file `.lic` yang diterima di dialog "Tambah Lisensi Wajah"**.
File `.enc` (cache) akan ditolak dengan error tersebut.

### Solusi
Gunakan file `.lic` (bukan `.enc`) saat import via UI FaceFgrClient.
Atau gunakan `cli.cmd fix-client-cache` untuk menulis `licenseface.enc` langsung ke folder client.

---

## 9. Perbedaan dengan Hasil Agent Sebelumnya

| Aspek | Agent Sebelumnya | Temuan Baru (Terbukti) |
|-------|------------------|------------------------|
| System ID Mesin | `DDCB4` | **`7738F`** (dari WMI runtime asli) |
| Profil Client FACE | Password sama server | **Benar**, tapi IV sama server (terbukti holder `0x04000375/76`) |
| Profil Client FGR | Berbeda | **Benar**: password `3477K3b3rS4ma4N`, IV `YaRahM@nY4R4h1M#` |
| Validator FACE | Asumsi cek DbId | **Hanya cek baris ada/tidak** (rows >= 1) |
| Importer Server | Cek signature | **Tidak ada signature check** di `0x060006CC` |
| Error "File terpilih..." | Asumsi format salah | **Filter file dialog hanya `*.lic`** |

---

## 10. Hasil Pengujian (E2E)

### Test Case: Fresh Import (Match)
```json
{
  "original_system_id": "7738F",
  "original_database_id": "V4YNE",
  "importer_returned": true,
  "after_dbid_field": "V4YNE",
  "after_info1": "7738F",
  "after_sequence": 1
}
```

### Test Case: Database ID Mismatch
```json
{
  "importer_returned": false,
  "exception": ["System.Exception: Database Id tidak sama dengan lisensi (WRK9T)"]
}
```

### Test Case: System ID Berbeda (DDCB4 vs 7738F)
```json
{
  "importer_returned": true,
  "after_info1": "DDCB4"
}
```
> Importer **menerima** System ID apapun yang ada di file; validasi machine binding dilakukan di **validator runtime** (`0x06000913`), bukan importer.

### Test Case: Client Cache Fix
```json
{
  "ready": true,
  "checks": [
    {"name": "license_row", "passed": true},
    {"name": "consumer_columns", "passed": true},
    {"name": "row_copy", "passed": true}
  ]
}
```

---

## 11. File Bukti (Evidence)

| File | Deskripsi |
|------|-----------|
| `bukti/import_results/*.json` | Hasil importer asli (method `0x060006CC`) |
| `bukti/e2e/*.json` | End-to-end test dengan ID berbeda |
| `bukti/client16/vm_strings.txt` | 2349 string terdekripsi dari VM client (format: `int<TAB>teks`) |
| `bukti/client16/intsites.txt` | Lokasi pemanggilan string (method token) |
| `bukti/detector_provenance.json` | Provenance detektor Database ID & System ID |
| `bukti/variable_audit.json` | Audit variabel holder statis |
| `bukti/strings_schema.json` | Skema string VM |

---

## 12. Kesimpulan & Rekomendasi

### Yang Sudah Terbukti (✅)
1. Format lisensi AES-128-CBC + XML DataTable 18 kolom
2. Profil kripto 3 target (server, client_face, client_fgr)
3. Algoritma Database ID (splang recipe) & System ID (WMI MD5)
4. Mekanisme importer server & validator client
5. Akar masalah TRIAL client 16.10 & solusi (`fix-client-cache`)

### Yang Perlu Validasi Lebih Lanjut (⚠️)
1. **Error message exact** — "File terpilih bukan lisensi JIBAS Presensi Wajah" belum direproduksi persis dari binary; kemungkinan di resource DLL terpisah atau dibangun dinamis
2. **Perpanjangan multi-mesin** — System ID di file lisensi bisa beda dari mesin tujuan; importer menerima, tapi validator runtime akan tolak
3. **Client FGR (fingerprint)** — Validator `0x060008C0` terpisah, tidak perlu fix cache

### Rekomendasi Penggunaan Tool
1. Selalu gunakan **Database ID & System ID hasil deteksi live** (`cli.cmd detect`)
2. Untuk client 16.10: jalankan `cli.cmd fix-client-cache --overwrite` setelah generate lisensi
3. Import ke Face Server via UI: gunakan file `.lic` (bukan `.enc`)
4. Verifikasi offline (`cli.cmd verify`) hanya cek file; **bukan bukti aktivasi**

---

## 13. Referensi Kode Sumber (Tool OpenCode)

| Modul | Fungsi Utama |
|-------|--------------|
| `jibas_license_tool.py` | Core library + CLI + GUI entry point |
| `license_codec.py` | Codec kriptografi & XML (internal) |
| `id_detect.py` | `DbIdDetector`, `SystemIdDetector` |
| `format_profile.json` | Profil kripto terstruktur |
| `schema.xml` | Skema XML DataTable |
| `gui.py` | GUI Tkinter 4 tab |

---

*Dokumen ini dibuat berdasarkan analisis statis REA + eksekusi harness C# refleksi terhadap binary asli. Semua token method/field merujuk ke metadata token .NET (bukan offset native).*