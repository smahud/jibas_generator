# Standalone Windows64-bit

File **JIBAS-Generator-Codex.exe** pada direktori Codex adalah aplikasi GUI
satu file dengan tab Absensi Wajah, SchoolPay dan CBE Server. Salin file `.exe`
itu saja ke folder lain lalu jalankan. Python, file sumber, XML, JSON, dan DLL
pendamping tidak perlu disalin atau diinstal terpisah.

Semua ID tetap diisi manual dan Sequence tetap otomatis. Ini format aplikasi
yang sama dengan versi Python; aturan dan batas validasi lisensi tidak berubah.
Lima field bersama dan tombol Save All juga tersedia pada executable.

## Isi paket dan build ulang

Python3.12 x64, Tk/Tcl, cryptography dan tiga codec dibundel menggunakan
PyInstaller6.22.3 dalam mode onefile/windowed. Build tanpa console dan tanpa UPX.
Empat resource internal: schema.xml, schoolpay_schema.xml, cbe_schema.xml,
format_profile.json. Modul detector dan PyMySQL tidak dibundel.

Lokasi resource tetap relatif ke `__file__`, sesuai
[dokumentasi runtime PyInstaller](https://pyinstaller.org/en/stable/runtime-information.html).
Mode onefile mengekstrak resource internal ke direktori sementara otomatis;
pengguna tetap hanya mendistribusikan satu file executable.

Untuk build ulang pada Windows dengan Python64-bit:

```bat
python -m pip install -r requirements-build.txt
python -m build_standalone
python -m build_tools.verify_standalone
```

Output build langsung ke direktori Codex. File spec, entry point dan skrip build
ikut disimpan di repository. Log serta versi dependency berada pada
`bukti/standalone/build.log` dan `build_manifest.json`.

## Pemeriksaan executable yang benar-benar dihasilkan

- Ukuran, SHA256 dan hash source untuk build terkini tercatat pada
  `bukti/standalone/build_manifest.json`.
- Salinan binary identik dijalankan dari folder sementara yang mula-mula hanya
  berisi file `.exe`. PATH dibatasi ke direktori Windows, environment Python/
  virtualenv/Tcl eksternal dihapus, tidak ada source/resource pendamping.
- Ketiga tab Tk dibuat dan pemilihan produk diuji. Koneksi/deteksi/Sequence
  tidak muncul sebagai input.
- Untuk setiap produk: generate baru Sequence1, inspect, verify, penolakan
  System ID berbeda, renewal Sequence2 dengan Client ID sama, verify renewal.
- Edit/hapus lima field bersama diuji; Database ID dipastikan tetap berbeda.
- Save All diuji sebelum pemilihan folder ketika tab CBE belum lengkap, lalu
  berhasil membuat tiga lisensi baru dan tiga perpanjangan dengan Client ID tetap.
- Tcl/Tk, native cryptography dan seluruh XML/JSON dibaca dari bundle sementara,
  bukan dari folder source atau instalasi Python host.

Semua pemeriksaan lulus dengan exit code0. Bukti lengkap ada pada
`bukti/standalone/verification.json`. Pemeriksaan ini tidak mengakses database,
instalasi JIBAS aktif, atau layanan online; tidak membuktikan aktivasi penerbit.

Untuk diagnosis build, executable juga menerima perintah developer
`JIBAS-Generator-Codex.exe --self-check HASIL.json`. Perintah ini menjalankan
alur UI dengan data sintetis dan menulis file lisensi uji di folder hasil.
Penggunaan biasa cukup membuka `.exe` tanpa argumen.
