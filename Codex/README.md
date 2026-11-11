# Codex — Generator Lisensi JIBAS

Satu aplikasi Python dengan enam tab: **Absensi Wajah**, **Absensi Finger**,
**SchoolPay**, **CBE Server**, **SJS**, lalu **LetterStore**. Identitas diisi
manual sesuai produk. Menu koneksi database, deteksi ID, dan input Sequence
tidak tersedia. Panduan lintas agent berada di [SharedDocs](../SharedDocs/README.md),
sejajar dengan direktori Codex.

Direktori implementasi utama adalah **Codex**. Jika instalasi lokal masih memiliki
`JIBAS-License-Tool-Codex`, jalankan `python -m riset.migrate_legacy_launchers`
dari direktori ini untuk mengarahkan entry point lama ke aplikasi yang sama.
File entry point lama dicadangkan dengan akhiran `.legacy-backup` sebelum diganti.

## Menjalankan

Versi standalone Windows64-bit tersedia sebagai **JIBAS-Generator-Codex.exe**
di direktori ini. Cukup salin dan jalankan satu file tersebut; tidak perlu Python,
file `.py`, schema, atau profil JSON terpisah. Keenam tab memakai input manual yang
sama seperti versi Python. Cara build dan bukti pemeriksaan ada di [STANDALONE.md](STANDALONE.md).

Klik **Jalankan GUI.cmd** pada direktori ini, atau launcher yang sama di root
repository. Python 3.10+ dengan Tkinter diperlukan. Instal dependensi dengan:

```bat
python -m pip install -r requirements.txt
```

Launcher mendukung `.venv` pada direktori ini maupun root repository, runtime
lokal yang sudah tersedia, dan Python launcher Windows.

## Membuat lisensi

1. Pilih tab produk yang sesuai.
2. Isi identitas sesuai tabel berikut; jangan menukar jenis ID antarproduk.
3. Isi field wajib yang muncul pada tab tersebut. Nama klien opsional.
4. Client ID bersama pada Face/SchoolPay/CBE dikosongkan untuk lisensi baru.
5. Klik **Buat & simpan…**. Hasil tidak dipasang ke instalasi aktif otomatis.

Untuk produk dengan perpanjangan, pilih **Lisensi lama**. Identitas dipertahankan dan Sequence
naik otomatis. Lisensi baru dimulai dengan Sequence1. Client ID saja tidak cukup
untuk mengetahui urutan terpasang; aplikasi meminta file lama jika diperlukan.
Tidak ada input urutan yang perlu diisi pengguna.

**Hasil** tetap setinggi enam baris dengan scrollbar; memperbesar jendela tidak
membuat kotak hasil memenuhi seluruh layar. Database ID, file, dan hasil tiap tab terpisah.

## Field bersama dan Save All

System ID dan Client ID terhubung pada Face/SchoolPay/CBE. Nama klien terhubung
pada semua tab. Tanggal dan kapasitas terhubung pada Face/SchoolPay/CBE/SJS.
Mengetik, mengedit, atau menghapus salah satunya langsung mengubah field relevan
di tab lain. Label kapasitas tetap mengikuti produk.

| Tab | Identitas wajib | Tanggal/kapasitas | Perpanjangan |
|---|---|---|---|
| Absensi Wajah | Database ID + System ID | Ya / wajah | File lama, Client ID sama, Sequence +1 |
| Absensi Finger | Nomor seri scanner + tujuan Manager/Client/keduanya | Tidak | Tidak memiliki Sequence |
| SchoolPay | Database ID + System ID | Ya / vendor | File lama, Client ID sama, Sequence +1 |
| CBE Server | Database ID + System ID | Ya / klien | File lama, Client ID sama, Sequence +1 |
| SJS | Database ID + Registration Token + School ID asli untuk lisensi baru | Ya / agent | School ID dari file lama, Sequence +1 |
| LetterStore | Database ID | Tidak | Satu registrasi; aplikasi asli menolak impor ulang |

Serial scanner dan tujuan Finger, Registration Token dan School ID SJS adalah
field privat. **School ID SJS bukan System ID atau Client ID bersama.** Token
SJS berisi statistik registrasi lokal dan tidak mengungkap School ID; aplikasi
meminta nilai asli, bukan membuat identitas layanan remote secara acak.

**Database ID tetap terpisah**. Lokasi berkas, lisensi lama, dan pilihan overwrite
juga tetap milik tab masing-masing.

Tombol **Save All**, tepat di kiri **Buat & simpan…**, membuat keenam lisensi:

1. Lengkapi identitas sesuai tabel. Database ID selalu terpisah per produk.
2. Klik Save All. Semua formulir diperiksa sebelum dialog folder dibuka.
3. Pilih satu folder tujuan. Hasilnya `absensi-wajah.lic`, `absensi-finger.lic`,
   `schoolpay.lic`, `cbe-server.lic`, `sjs.lic`, dan `letterstore.lic`.
   Lokasi berkas di tiap tab diperbarui setelah berhasil.

Semua hasil dibuat dan diperiksa di staging dahulu. Kegagalan satu produk tidak
menerbitkan hasil sebagian; kegagalan saat mengganti file memulihkan keluaran
sebelumnya. File yang sudah ada memerlukan pilihan **Timpa berkas keluaran** pada
tab terkait. Save All menonaktifkan kontrol semua tab selama proses berjalan.

Untuk perpanjangan, pilih file lama masing-masing produk. Jika Client ID bersama
diisi, nilainya harus cocok dengan file-file lama tersebut; bila dikosongkan,
Client ID masing-masing diambil dari file lama. Sequence tetap otomatis.

## CLI dengan input manual

Face tetap menjadi produk bawaan. Pilihan `--product`: `face`, `fingerprint`,
`schoolpay`, `cbe`, `sjs`, dan `letterstore`. `detect`, `--auto`, dan `--sequence`
tidak tersedia.

```bat
cli.cmd generate --product face --database-id V4YNE --system-id DDCB4 --expires 2030-12-31 --capacity 100 --out wajah.lic
cli.cmd generate --product schoolpay --database-id 7VJM4 --system-id DDCB4 --expires 2030-12-31 --capacity 10 --out schoolpay.lic
cli.cmd generate --product cbe --database-id ABCDE --system-id DDCB4 --expires 2030-12-31 --capacity 100 --out cbe.lic
cli.cmd inspect --product cbe cbe.lic
cli.cmd verify --product cbe cbe.lic --database-id ABCDE --system-id DDCB4 --for-import
cli.cmd generate --product fingerprint --serial SERIAL-TEST --license-scope both --out finger.lic
cli.cmd generate --product letterstore --database-id ABCDE --out letterstore.lic
cli.cmd generate --product sjs --database-id AB123 --registration-token TOKEN_ASLI --school-id SCHOOL_ID_ASLI --expires 2030-12-31 --capacity 2 --out sjs.lic
```

ID di contoh hanya contoh; gunakan ID instalasi tujuan. Untuk perpanjangan:

```bat
cli.cmd generate --product cbe --database-id ABCDE --system-id DDCB4 --previous-license cbe.lic --expires 2031-12-31 --capacity 100 --out cbe-perpanjangan.lic
```

`inspect` membaca field lisensi. `verify` memeriksa struktur, ID, tanggal dan angka
secara offline; `--for-import` memeriksa syarat file impor produk. Hasil tersebut
bukan konfirmasi aktivasi atau keaslian dari penerbit.

## Format dan bukti

| Produk | Tabel | Catatan |
|---|---|---|
| Face16.5 / client16.10 | JibasSptFaceLicense | Header FACE wajib pada menu impor client; System ID pada Info1 |
| SchoolPay10.5 | JibasSchoolPayLicense | Input membutuhkan kolom skema ForSchoolPay; SystemId eksplisit; header komentar opsional |
| CBE26.5 | JibasCbeLicense | Skema18 kolom; System ID pada Info1; MaxClient berisi kapasitas nominal |
| Fingerprint Manager16.5 / Client14.0 dan16.10 | JSL | Serial scanner pada Seri; cakupan CM untuk Manager dan Client; marker FINGERPRINT |
| SJS7.10 | JibasJsLicense | DatabaseId + SchoolId; token statistik terpisah dari payload lisensi |
| LetterStore7.0 | JLS | Database ID pada Info3; Versi2.0; satu registrasi |

Rincian: [TEMUAN.md](TEMUAN.md), [SCHOOLPAY.md](SCHOOLPAY.md),
[CBE.md](CBE.md), dan [TEST_REPORT.md](TEST_REPORT.md).
Ringkasan lengkap tiga produk baru: [Fingerprint](../SharedDocs/products/absensi-finger.md),
[SJS](../SharedDocs/products/sjs.md), [LetterStore](../SharedDocs/products/letterstore.md).
Evidence serta harness berada dalam `bukti/` dan `riset/`; compiled executable,
binary JIBAS, dan datadir eksperimen tidak disertakan dalam rilis.

Modul detector lama tetap menjadi bahan penelitian/regresi. Aplikasi GUI dan CLI
manual tidak memanggilnya atau meminta credential database. Dokumen serta bukti
lama yang menyebut deteksi/Sequence manual adalah catatan historis; panduan ini
menjelaskan perilaku aplikasi terbaru.

## Pengujian

```bat
python -m pip install -r requirements-dev.txt
python -m pytest tests -q -W error::pytest.PytestUnraisableExceptionWarning
```

Semua tulisan eksperimen berada pada folder sementara, bukan instalasi JIBAS
aktif. Penerimaan file oleh importer dan loader berbeda dari aktivasi runtime
atau online; batas pembuktian dijelaskan per produk.
