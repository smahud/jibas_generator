# JIBAS License Generator

Root repository berisi file pendukung. Semua kode aplikasi dipisahkan menurut
implementasinya:

| Direktori | Isi |
|---|---|
| [Codex](Codex/README.md) | Satu aplikasi dengan tab Absensi Wajah, SchoolPay, dan CBE Server; kode Python, tes, contoh, serta bukti REA |
| [OpenCode](OpenCode/README.md) | Implementasi OpenCode dan arsip analisisnya, dipertahankan terpisah |

Tidak ada produk Python di root. Riwayat sebelum pemisahan tetap tersedia di Git.

Direktori hasil Codex yang aktif adalah **Codex/**. Direktori lokal lama
`JIBAS-License-Tool-Codex` dapat diarahkan ke implementasi ini dengan migrasi
launcher yang dijelaskan pada [panduan Codex](Codex/README.md).

## Menjalankan

Versi satu file Windows64-bit tersedia di
[Codex/JIBAS-Generator-Codex.exe](Codex/JIBAS-Generator-Codex.exe).
Executable tersebut tidak memerlukan instalasi Python atau resource pendamping.
Lihat [panduan standalone](Codex/STANDALONE.md) untuk build dan hasil pemeriksaan.

Klik **Jalankan GUI.cmd** untuk Codex atau **Jalankan OpenCode.cmd** untuk OpenCode.
Untuk Codex, gunakan Python3.10+ dengan Tkinter dan instal:

```bat
python -m pip install -r Codex/requirements.txt
```

Perilaku aplikasi Codex terbaru:

- Database ID dan System ID diisi manual pada ketiga tab.
- System ID, Client ID, Nama klien, tanggal dan kapasitas terhubung dua arah
  antar-tab. Database ID tetap terpisah sesuai produk.
- **Save All** di kiri **Buat & simpan…** memvalidasi ketiga formulir, memilih
  satu folder, dan menyimpan tiga lisensi; keluaran dipulihkan bila gagal.
- Menu koneksi database serta tombol deteksi sudah dihapus.
- Input Sequence sudah dihapus. Lisensi baru mulai1; perpanjangan memakai file
  lisensi lama untuk mempertahankan Client ID dan menaikkan urutan otomatis.
- Kotak Hasil tetap enam baris dengan scrollbar.

File lama diperlukan untuk perpanjangan; Client ID sendiri tidak mengungkap
Sequence yang sedang terpasang. Hasil tidak dipasang ke instalasi JIBAS otomatis.

## Validasi

Codex: **153 tes lulus,1 dilewati**, termasuk sinkronisasi field, Save All,
rollback, GUI manual, CLI tiga produk, dan codec. Executable terbaru juga diuji
dari folder terisolasi untuk Save All lisensi baru dan perpanjangan.
CBE Server26.5: **34 skenario /46 percobaan** importer dan loader asli sesuai
ekspektasi. Seluruh13file instalasi CBE identik sebelum/sesudah pengujian.
Penerimaan importer tidak membuktikan aktivasi runtime atau online.

Laporan: [pembaruan manual/CBE](Codex/MANUAL_UPDATE.md),
[detail CBE](Codex/CBE.md), [SchoolPay](Codex/SCHOOLPAY.md),
[Face](Codex/TEMUAN.md).

Jalankan tes dari direktori implementasi agar modul bernama sama tidak bercampur:

```bat
cd Codex
python -m pytest tests -q -W error::pytest.PytestUnraisableExceptionWarning
```

Untuk OpenCode, jalankan suite dari direktorinya sendiri. Binary JIBAS,
compiled harness, dan datadir eksperimen tidak disertakan dalam paket Codex.
