# CBE Server26.5

Tab **CBE Server** menggunakan input manual Database ID dan System ID, sama
dengan tab produk lain. Tidak ada koneksi database atau deteksi ID pada GUI.
Nama klien opsional; kapasitas mengisi field nominal MaxClient dalam lisensi.
Client ID dikosongkan untuk baru, atau diambil dari file lama untuk perpanjangan.

Sequence merupakan detail internal: baru1, perpanjangan previous+1. Pengguna
tidak mengisinya. Pilih **Lisensi lama** untuk perpanjangan; Client ID saja
tidak memberikan informasi urutan terpasang.

```bat
cli.cmd generate --product cbe --database-id ABCDE --system-id DDCB4 --expires 2030-12-31 --capacity 100 --out cbe.lic
cli.cmd inspect --product cbe cbe.lic
cli.cmd verify --product cbe cbe.lic --database-id ABCDE --system-id DDCB4 --for-import
```

ABCDE/DDCB4 hanya contoh. Isi ID yang ditampilkan oleh instalasi CBE tujuan.
Contoh tidak dipasang ke aplikasi asli secara otomatis.

## Format yang terbukti

- Target: CbeServer.exe26.5, managed x64 .NET Framework4.8.
- SHA256: a2b77a3fc715d1d8c2b47a29ff65444af0e829c3f2704098ed538c48ce5f140b.
- MVID:5831bc0d-d22e-4a13-67b9-f22eab4b24a8.
- Tabel JibasCbeLicense18kolom, Sequence Int32, LicenseLimitDate DateTime.
- DbId menyimpan Database ID; Info1/Seri diisi System ID.
- AES128-CBC, MD5 password profil, IV tetap, PKCS7, ASCII XML dan Base64.
- Komentar header opsional; tidak diperlukan tambahan kolom ForCbe.
- Formula tanggal meniru overflow Int32 asli, bukan ordinal Gregorian biasa.

Literal UI asli menyebut maksimum koneksi CBE Client bersamaan untuk MaxClient.
Loader menyimpan nilai mentah dan menghitung nilai sekunder melalui5BF; misalnya
100 menghasilkan250 pada holder sekunder. Fungsi nilai sekunder belum ditelusuri
sampai pembatas koneksi runtime, sehingga generator mempertahankan MaxClient
nominal dan tidak mengklaim250sebagai kapasitas koneksi aktual.

## Pengujian asli

Importer yang dipakai handler UI adalah05C0; cache loader05BE. Matriks pada
`bukti/cbe_validation/matrix_summary.json`: **34skenario/46percobaan**, seluruh
hasil sesuai ekspektasi,29diterima dan17ditolak. Semua penerimaan diuji dengan
reset skema dan pemuatan ulang cache melalui loader asli.

Tiga pasangan ID, baru/renewal, Sequence sama/turun, Client ID berbeda, Database ID
berbeda, ciphertext rusak, header opsional, field Model, overflow angka, serta
binding/tanggal diperiksa dalam proses sandbox. Delapan vector tanggal asli
cocok dengan Python. Tidak ada hook atau patch; metode pasca-load006FF memang
berisi instruksi ret pada binary asli.

Importer juga menerima payload Face dengan kolom kompatibel, System ID salah,
dan tanggal lampau. Karena itu penerimaan file tidak membuktikan keaslian produk,
aktivasi runtime, atau aktivasi online. Inspector Python tetap meminta tabel CBE
agar pengguna tidak salah memilih file produk di aplikasi terpadu.

Main, koneksi SQL, dan loop aktivasi runtime tidak dijalankan. Semua13file instalasi
CBE tetap identik; lihat `bukti/cbe_integrity.json`. Rincian lengkap dan method map
tersedia di [FORMAT.md](bukti/cbe/FORMAT.md) serta
[laporan oracle](bukti/cbe_validation/README.md).
