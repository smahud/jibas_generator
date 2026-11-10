# JIBAS Generator

Implementasi aplikasi dipisahkan menurut pembuatnya:

| Direktori | Isi |
|---|---|
| [Codex](Codex/README.md) | Aplikasi terpadu Absensi Wajah, SchoolPay, dan CBE Server; kode, tes, contoh, serta bukti REA |
| [OpenCode](OpenCode/README.md) | Implementasi OpenCode beserta tes dan arsip analisis yang sebelumnya berada di root |

Root repository hanya berisi panduan, konfigurasi repository, dan launcher.
Tidak ada kode produk Python di root. Pemindahan memakai Git rename agar
riwayat file tetap dapat ditelusuri.

## Menjalankan

Klik **Jalankan GUI.cmd** untuk Codex atau **Jalankan OpenCode.cmd** untuk
implementasi OpenCode. Keduanya juga memiliki launcher dalam direktorinya sendiri.
Python 3.10+ dengan Tkinter diperlukan. Dependensi Codex:

```bat
python -m pip install -r requirements.txt
```

Semua Database ID dan System ID pada aplikasi Codex diisi manual. Tidak ada
menu koneksi database atau deteksi ID. Sequence tidak ditampilkan: lisensi baru
memakai nilai awal, perpanjangan mengambil dan menaikkan nilai dari file lama.
Untuk perpanjangan, pilih file lisensi lama; Client ID sendiri tidak mengungkap
Sequence terpasang.

## Pengujian

Jalankan suite dari direktori implementasi masing-masing agar modul dengan nama
yang sama tidak bercampur:

```bat
cd Codex
python -m pytest tests -q
```

Untuk OpenCode, gunakan perintah yang sama dari `OpenCode`. Hasil, batas
pembuktian importer/runtime, dan identitas binary dicatat pada laporan setiap
implementasi. File instalasi JIBAS asli tidak disertakan dalam repository.
