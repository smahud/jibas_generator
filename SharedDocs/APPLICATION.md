# Arsitektur aplikasi Codex

## Komponen

`app.py`: GUI Tk; `product_catalog.py` menentukan codec, jenis produk dan baris
field yang relevan. `product_actions.py` menyediakan normalize_values,
generate_with_backend dan verify_with_backend untuk GUI/CLI/batch; tidak mengakses Tk.
`batch_license.py`: preflight seluruh formulir, staging, verifikasi, pemasangan
file dan rollback. `cli.py`: argumen manual. Codec memegang format dan aturan
produk; GUI tidak boleh mengubah konstanta global codec lain untuk berpindah tab.

Field bersama: system_id,client_id,client_name,expires,capacity. Panel hanya
mengambil StringVar bersama bila key ada dalam product.input_keys. Nama dipakai
semua produk; system/client hanya Face/SchoolPay/CBE; tanggal/kapasitas juga SJS.
Database ID selalu milik tab. Untuk produk yang tidak menggunakan suatu field,
jangan tampilkan atau mengirimkannya sebagai syarat. Registration Token SJS harus
berdiri sendiri, bukan alias StringVar system_id. File lama/path/overwrite tetap
per produk. Hasil UI tetap6baris dengan scrollbar.

Worker menerima snapshot dict/string/module biasa, bukan widget, StringVar,
bound method yang menyimpan panel, atau callback Tk. Pembaruan GUI lewat Queue
dan polling main thread. Pada close: cancel after, destroy widget, lepaskan
variabel di main thread agar GC pada worker tidak menjalankan finalizer Tcl.
Batch non-daemon agar penyimpanan/rollback selesai ketika jendela ditutup.

Save All memeriksa field wajib keenam produk, lalu memilih satu folder. Semua
hasil digenerate ke staging dan diverifikasi sebelum target diganti. Target
yang sudah diganti dipulihkan bila commit gagal. Overwrite perlu diizinkan
per tab. Jangan mengklaim transaksi filesystem tahan semua gangguan OS/powerloss.

## Standalone

`JIBAS-Generator-Codex.spec` membundel Python/Tk/cryptography dan resource codec.
Dynamicimport codec membutuhkan hiddenimports. Resource diletakkan di root
bundle sesuai BASE __file__. Jangan mengandalkan Python/PYTHONPATH di mesin user.

```bat
python -m pip install -r requirements-build.txt
python -m build_standalone
python -m build_tools.verify_standalone
```

Verifier menyalin hanya EXE ke folder baru, membatasi PATH ke Windows, menghapus
environment Python/Tcl eksternal, lalu menguji panel Tk asli, sharedfield,
individual generation, renewal, Save All dan resourcepath dalam _MEIPASS.
Ketika codec baru ditambah, perbarui spec,datas,source_hashes, smokecheck dan
capability tests; jangan hanya menambah nama tab.

## Tes

```bat
cd Codex
python -m pytest tests -q -W error::pytest.PytestUnraisableExceptionWarning
```

GUItests memakai satu interpreter Tk dan Toplevel per kasus, meniru satu proses
aplikasi. Layout QA hanya mengambil region jendela QA sendiri dengan data sintetis.
Snapshot min/normal memeriksa clipping, overlap, urutan tombol dan tinggi hasil.
File Python hasil Codex tetap di Codex; dokumentasi bersama di SharedDocs, bukan
subdirektori Codex. Dokumen produk menyebut kebutuhan field dan batasnya.

Urutan tetap: Absensi Wajah, Absensi Finger, SchoolPay, CBE Server, SJS,
LetterStore. supports_renewal benar hanya untuk tiga produk awal dan SJS.
Fingerprint memiliki scanner_serial/license_scope privat; LetterStore tidak
memiliki System ID/expiry/capacity; SJS school_id/registration_token privat.
Saat menambah tab, ubah katalog dan adapter, bukan resep global codec Face.
