# Field bersama dan Save All — 11 November 2026

System ID, Client ID, Nama klien, Berlaku sampai, dan Kapasitas memakai nilai
bersama pada tiga tab. Edit dan penghapusan berlaku dua arah. Database ID,
lisensi lama, berkas keluaran dan overwrite tetap terpisah per produk.

Save All berada langsung di kiri Buat & simpan. Ketiga formulir divalidasi
sebelum memilih satu folder. Keluaran: absensi-wajah.lic, schoolpay.lic dan
cbe-server.lic. Nama/Client ID opsional sesuai aturan sebelumnya; untuk
perpanjangan, masing-masing produk memakai file lama dan Sequence otomatis.

## Pemeriksaan

- Suite source: **153 passed,1 skipped** (10.95 detik), warning finalizer Tk
  dianggap error. Satu tes integrasi opsional dilewati karena cache lisensi
  terpasang sedang kosong; fixture serta regresi kode tetap diperiksa.
- **25 tes GUI**: semua arah edit/hapus, Database ID terpisah, button order,
  Save All real tiga produk, isian CBE belum lengkap, snapshot worker,
  gagal/unlock, close dan pelepasan variabel bersama pada main thread.
- **21 tes batch**: lisensi baru/perpanjangan tiga codec asli, preflight semua
  formulir, konflik tujuan, gagal produk ketiga/verifikasi, rollback file baru
  dan file lama saat rename gagal, mismatch Client ID serta alias path.
- Enam tampilan diperiksa pada880x650 dan760x560. Save All tepat di kiri tombol
  simpan individual dengan jarak6px; tidak ada clipping atau overlap. Hasil
  tetap6baris/102px. Bukti: bukti/shared_save_all/gui_visual_report.json dan PNG.

Batch membuat semua file di staging, memeriksa hasilnya, lalu memasang ke tujuan.
Jika commit file gagal, target yang sudah dipasang dihapus/dipulihkan. Cadangan
dipertahankan bila OS menolak pemulihan. Tidak ada perubahan pada instalasi
JIBAS atau database aktif. Worker batch memakai data biasa dan tidak dihentikan
ketika jendela ditutup, sehingga transaksi dapat selesai atau dipulihkan.

Executable dibangun ulang dari source ini. Self-check pada salinan EXE terisolasi
memeriksa sinkronisasi, Database ID terpisah, validasi sebelum pemilihan folder,
Save All tiga lisensi baru dan tiga renewal, serta workflow individual lama.
Lihat bukti/standalone/verification.json dan STANDALONE.md untuk hasil binary.

Pemeriksaan offline/importer yang sudah dicatat bukan bukti aktivasi runtime
atau online dari penerbit. Perubahan ini hanya menyatukan input dan alur simpan.
