# JIBAS License Generator — Repository

Hasil *reverse engineering* lisensi JIBAS dan implementasi generatornya. Root repo hanya berisi
berkas pendukung; kode implementasi dipisah per agent di sub-direktori.

## 📁 Struktur

| Direktori / Berkas | Isi |
|--------------------|-----|
| `OpenCode/` | **Implementasi aktif (OpenCode)** — `jibas_license_tool.py` (core + CLI), `gui.py` (GUI 5 tab), `cli.py` (audit read-only), schema & profil kripto, `README.md` dokumentasi lengkap, `tests/` |
| `Codex/` | Implementasi riwayat (Codex) untuk verifikasi silang — lihat `Codex/README.md` |
| `Jalankan OpenCode.cmd` | Launcher GUI implementasi aktif (OpenCode) |
| `Jalankan GUI.cmd` | Launcher GUI implementasi riwayat (Codex) |

## 🚀 Menjalankan

```cmd
rem GUI implementasi aktif (5 tab: Inspeksi & Verifikasi, Buat & Perpanjang, SchoolPay, CBE Server, Perbaiki Client Cache)
Jalankan OpenCode.cmd

rem CLI implementasi aktif
OpenCode\jibas_license_tool.py inspect lisensi.lic
OpenCode\jibas_license_tool.py generate --database-id V4YNE --system-id 7738F --expires 2027-12-31 --capacity 100 --output baru.lic --product schoolpay
```

Detail format, profil kripto, skema XML, dan pembentukan ID: **[OpenCode/README.md](OpenCode/README.md)**.

## 🛠️ Produk yang Didukung

| Produk | Format Tabel | Status |
|--------|--------------|--------|
| JIBAS Face Server 16.5 | `JibasSptFaceLicense` (18 kolom) | ✅ Terbukti (runtime importer + predikat) |
| JIBAS Face & Fingerprint Client 16.10 | cache `licenseface.enc` / `licensefgr.enc` | ✅ Terbukti (`fix-client-cache`) |
| JIBAS SchoolPay Secure Server 10.5 | `JibasSchoolPayLicense` (19 kolom, `MaxVendor` + `SystemId`) | ⚠️ Round-trip offline terverifikasi; runtime SPayServer belum diuji |
| JIBAS CBE Server 26.5 | `JibasCbeLicense` (18 kolom, kripto sama dengan Face Server) | ⚠️ Round-trip offline terverifikasi; runtime CbeServer belum diuji |

⚠️ Verifikasi offline **bukan bukti** aktivasi/penerimaan aplikasi target. License yang terbukti valid
secara format tetap harus diuji langsung pada aplikasi aslinya.

## 📝 Konvensi Penggunaan

- **Database ID & System ID diisi manual** — menu deteksi otomatis dihapus; ambil nilai dari aplikasi asli masing-masing (Face Server menampilkan ID saat mulai tanpa lisensi; gunakan nilai itu per mesin target).
- **Sequence otomatis** — selalu `1` untuk lisensi baru, `previous + 1` untuk perpanjangan; tidak ada inputan sequence.
- Hasil simpan sebagai `.lic`.
- Tetap aman: cadangan dibuat otomatis sebelum menimpa `licenseface.enc`; `config.ini` & `licensefgr.enc` tidak disentuh.

## ⚖️ Lisensi & Hukum

Dibuat untuk analisis teknis dan manajemen lisensi internal. Hak atas software JIBAS tetap milik pemiliknya.
Gunakan hanya pada data/berkas yang Anda berhak akses. Verifikasi offline **bukan** konfirmasi aktivasi dari penerbit JIBAS.
