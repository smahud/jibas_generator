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

Klik **Jalankan GUI.cmd** untuk Codex atau **Jalankan OpenCode.cmd** untuk OpenCode.
Untuk Codex, gunakan Python3.10+ dengan Tkinter dan instal:

```bat
python -m pip install -r Codex/requirements.txt
```

Perilaku aplikasi Codex terbaru:

- Database ID dan System ID diisi manual pada ketiga tab.
- Menu koneksi database serta tombol deteksi sudah dihapus.
- Input Sequence sudah dihapus. Lisensi baru mulai1; perpanjangan memakai file
  lisensi lama untuk mempertahankan Client ID dan menaikkan urutan otomatis.
- Kotak Hasil tetap enam baris dengan scrollbar.

File lama diperlukan untuk perpanjangan; Client ID sendiri tidak mengungkap
Sequence yang sedang terpasang. Hasil tidak dipasang ke instalasi JIBAS otomatis.

## Validasi

Codex: **120 tes lulus**, termasuk GUI manual, CLI tiga produk, dan codec.
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
