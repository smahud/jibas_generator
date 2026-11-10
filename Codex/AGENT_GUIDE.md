# Mulai dari sini

Versi sekarang menggabungkan tab Absensi Wajah dan SchoolPay dalam app.py.
Baca SCHOOLPAY.md untuk format baru: DbId dari jbsfina, SystemId eksplisit,
MaxVendor, dan kolom input ForSchoolPay pada skema (cache19, impor20).
Header SchoolPay opsional; jangan menyalin aturan header wajib Face AF9.
schoolpay_codec.py dan schoolpay_id_detect.py terpisah; jangan mengganti
konstanta atau resep global Face saat mengembangkan produk berikutnya.
Runtime SchoolPay09D0 belum diuji karena batas jaringan/DB di VM belum diketahui.

Baca README.md dan TEMUAN.md paket Codex sebelum memakai laporan historis.
Source awal berasal dari checkout lokal edb62b9; remote main saat investigasi
8732d68 sudah berisi GUI diagnostik terpisah. Publikasi menambah subfolder Codex
dan mempertahankan perubahan remote tersebut.

Koreksi yang wajib dipertahankan:

1. System ID live DDCB4. Serial WMI mempunyai trailing spaces yang ikut hash.
2. Cache base64 tanpa header berbeda dari file impor client: importer AF9
   mewajibkan marker LISENSI JIBAS SPT FACE pada baris pertama.
3. AC3 dapat bootstrap database jika semua routine splang tidak ada; jangan
   menganggap pemanggilan original method selalu read-only.
4. Importer menerima System ID salah, tetapi server runtime menolaknya.
5. Perpanjangan perlu Client ID sama dan Sequence meningkat.
6. Formula tanggal asli memiliki perilaku non-Gregorian; jangan menggantinya
   dengan formula normal tanpa memahami konsekuensi kompatibilitas.

Bukti baru berada di bukti/client_import, bukti/server_matrix, bukti/id_audit.
Output trace exploratory tidak sama otoritasnya dengan replay final tanpa hook.
JSON final merekam SHA256/MVID, parameter simulasi, hasil dan exception asli.
Tidak ada produksi yang diaktivasi dalam sesi ini. Binary dan config live
harus tetap utuh; eksperimen berikutnya gunakan sandbox seperti harness baru.

Jalankan python -m pytest tests -q setelah mengubah engine. Untuk uji oracle
gunakan runner di masing-masing folder bukti; perlu target .NET asli Windows.
Jangan commit PAT, compiled harness, database sandbox, atau binary JIBAS.
