# Codex — Generator Lisensi JIBAS

Satu aplikasi Python dengan tiga tab: **Absensi Wajah**, **SchoolPay**, dan
**CBE Server**. Input Database ID dan System ID sepenuhnya manual. Menu koneksi
database, tombol deteksi ID, dan input Sequence sudah dihapus.

Direktori implementasi utama adalah **Codex**. Jika instalasi lokal masih memiliki
`JIBAS-License-Tool-Codex`, jalankan `python -m riset.migrate_legacy_launchers`
dari direktori ini untuk mengarahkan entry point lama ke aplikasi yang sama.
File entry point lama dicadangkan dengan akhiran `.legacy-backup` sebelum diganti.

## Menjalankan

Klik **Jalankan GUI.cmd** pada direktori ini, atau launcher yang sama di root
repository. Python 3.10+ dengan Tkinter diperlukan. Instal dependensi dengan:

```bat
python -m pip install -r requirements.txt
```

Launcher mendukung `.venv` pada direktori ini maupun root repository, runtime
lokal yang sudah tersedia, dan Python launcher Windows.

## Membuat lisensi

1. Pilih tab produk yang sesuai.
2. Isi Database ID dan System ID dari aplikasi asli pada mesin tujuan.
3. Isi tanggal berlaku dan kapasitas: wajah untuk Face, vendor untuk SchoolPay,
   koneksi klien yang tercantum pada lisensi untuk CBE.
4. Client ID dan nama klien bersifat opsional untuk lisensi baru.
5. Klik **Buat & simpan…**. Hasil tidak dipasang ke instalasi aktif otomatis.

Untuk perpanjangan, pilih **Lisensi lama**. Client ID dipertahankan dan Sequence
naik otomatis. Lisensi baru dimulai dengan Sequence1. Client ID saja tidak cukup
untuk mengetahui urutan terpasang; aplikasi meminta file lama jika diperlukan.
Tidak ada input urutan yang perlu diisi pengguna.

**Hasil** tetap setinggi enam baris dengan scrollbar; memperbesar jendela tidak
membuat kotak hasil memenuhi seluruh layar. Input, file, dan hasil tiap tab terpisah.

## CLI dengan input manual

Face tetap menjadi produk bawaan. Gunakan `--product schoolpay` atau `--product cbe`
untuk memilih produk lain. `detect`, `--auto`, dan `--sequence` tidak tersedia lagi.

```bat
cli.cmd generate --product face --database-id V4YNE --system-id DDCB4 --expires 2030-12-31 --capacity 100 --out wajah.lic
cli.cmd generate --product schoolpay --database-id 7VJM4 --system-id DDCB4 --expires 2030-12-31 --capacity 10 --out schoolpay.lic
cli.cmd generate --product cbe --database-id ABCDE --system-id DDCB4 --expires 2030-12-31 --capacity 100 --out cbe.lic
cli.cmd inspect --product cbe cbe.lic
cli.cmd verify --product cbe cbe.lic --database-id ABCDE --system-id DDCB4 --for-import
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

Rincian: [TEMUAN.md](TEMUAN.md), [SCHOOLPAY.md](SCHOOLPAY.md),
[CBE.md](CBE.md), dan [TEST_REPORT.md](TEST_REPORT.md).
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
