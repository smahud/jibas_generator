# Pembuktian CBE Server 26.5

Target: `C:\Program Files\YIM\JIBAS CBE Server 26.5\CbeServer.exe`.
SHA-256 `a2b77a3fc715d1d8c2b47a29ff65444af0e829c3f2704098ed538c48ce5f140b`.
MVID `5831bc0d-d22e-4a13-67b9-f22eab4b24a8`; token berikut khusus build ini.
Identitas REA disimpan pada `rea_identity.json`.

## Jalur yang dipanggil

Handler UI asli `0x06000BB6` memanggil importer `0x060005C0`; hubungan itu
ditunjukkan oleh `identity_and_import_refs.txt`. Harness hanya memanggil metode
importer tersebut, tanpa membuat UI, memanggil Main target, atau menyiapkan
koneksi database/jaringan.

| Tujuan | Token |
|---|---|
| Folder keluaran cache terkontrol | field `0x040005D2` |
| Warm/getter path lisensi | `0x060005B7` |
| Inisialisasi pasangan kripto | `0x060005B9` |
| Skema DataTable `JibasCbeLicense` | `0x060005B8` |
| Importer resmi | `0x060005C0` |
| Loader cache | `0x060005BE` |
| Holder Database ID lingkungan | field `0x040003F3` |
| Holder KlienId / Sequence terpasang | fields `0x040003F6` / `0x040003FF` |
| Holder MaxClient nominal / turunan | fields `0x040003FD` / `0x040003FE` |
| Helper kapasitas turunan | `0x060005BF` |
| Helper tanggal murni | `0x06000E0A` |

Original loader `05BE` berakhir dengan pemanggilan `006FF`. Metode `006FF`
**secara alami memiliki body IL hanya `ret`**, sebagaimana `holder_init_il.txt`.
Ini bukan stub buatan harness, patch, hook, atau penggantian metode. Executable
target tetap utuh. Harness mengisi hanya folder keluaran sandbox dan holder
Database ID untuk mensimulasikan lingkungan.

Init gabungan `05BA` tidak dipanggil karena jalurnya meneruskan ke `0DD2` di luar
inisialisasi format. Kripto `05B9` dan skema `05B8` dipanggil terpisah. Semua cache
hasil importer berada dalam sandbox baru `%TEMP%\codex-cbe-...`; pemasangan
aktif tidak ditulis. Setelah impor, skema dikosongkan lewat `05B8` dan cache
dimuat kembali lewat `05BE` untuk membuktikan hasil serialisasi asli dapat dibaca.

## Hasil final

`matrix_summary.json`: **34 skenario / 46 percobaan**, seluruhnya sesuai
ekspektasi; **29 diterima, 17 ditolak**. Setiap penerimaan menghasilkan cache
dan loader asli mengembalikan true dengan KlienId/Sequence hasil reload sama.

- Tiga pasangan lingkungan: ABCDE/DDCB4, V4YNE/ABCDE, Z9X8W/123AB.
- Lisensi baru dan perpanjangan Sequence1→2 diterima.
- Sequence sama, menurun, Client ID berubah, dan Database ID berbeda ditolak
  dengan exception asli yang direkam per skenario.
- Header tidak wajib: tanpa header, komentar produk lain, dan komentar
  lowercase diterima. Skema dasar 18 kolom sudah mencukupi; tidak membutuhkan
  kolom tambahan `ForCbe` pada jalur yang diuji.
- Model `CBE`, `SPTFACE`, kosong, maupun elemen row Model yang tidak ditulis
  diterima. File Face dengan tabel `JibasSptFaceLicense` juga diterima karena
  profil kripto/18 kolom kompatibel. Importer tidak membuktikan identitas produk.
- File SchoolPay ditolak karena tidak memiliki kolom `MaxClient`.
- Base64 rusak, overflow Int32 pada MaxClient/Sequence, dan nilai MaxClient
  yang tidak tersedia ditolak.
- Info1 salah/kosong, Seri salah, serta tanggal kedaluwarsa lampau tetap
  diterima importer. Penerimaan impor bukan bukti aktivasi runtime.

File final dibuat menggunakan `cbe_codec.generate_license` dari source terkini;
`candidate_18_result.json` hanya eksplorasi awal dan bukan pengganti matriks final.

## Tanggal dan kapasitas

`date_oracle.json` berisi delapan vector hasil `0E0A` asli dan nilai Python yang
cocok. Formula memiliki kekhasan bulan saat ini dan unchecked Int32 tahun-menit,
seperti SchoolPay: 31Des2028 dan 1Jan2029 pada jam sama bernilai sama; tahun4084
dan4085 negatif akibat overflow, dan 9999-12-31T23:59 bernilai964677343.

`capacity_oracle.json` merekam keluaran asli `05BF`, misalnya MaxClient100
menghasilkan field turunan250. Nilai nominal tetap100 pada holder `3FD`.
Pencarian batas menghasilkan 13 segmen kandidat berdasarkan asumsi monotonicity;
nilai sample dan titik perubahan merupakan observasi langsung metode asli,
tetapi makna bisnis field turunan belum dipastikan. CIL scan hanya menemukan
pembacaan turunan pada loader; konsumen lain dapat berada dalam VM. Jangan
menyebut hasil turunan sebagai jumlah koneksi aktif atau mengganti nilai nominal
dengan hasil itu tanpa bukti tambahan.

## Reproduksi dan batas

Dari direktori `Codex` di Windows dengan target asli tersedia:

```bat
python -X utf8 -u -m bukti.cbe_validation.run_import_matrix
```

Runner mengompilasi `CbeImportProbe.cs` melalui .NET Framework64 csc, lalu membuat
sandbox baru per skenario. `CbeDateProbe.cs` dan `CbeCapacityProbe.cs` menyediakan
oracle helper murni. Executable hasil kompilasi bukan bagian paket rilis.

Tidak ada patch/hook, penulisan database, atau perubahan binary/config/cache live.
Tidak mengklaim aktivasi produksi, verifikasi penerbit online, atau perilaku
seluruh workflow ujian. Nilai identitas lingkungan pada matriks adalah simulasi
terkontrol; matriks tidak mendeteksi ID database produksi atau hardware lain.
