# Pembuktian server 16.5 (Codex)

`run_matrix.py` mengompilasi `ServerMatrixProbe.cs`, membuat file melalui
engine Python, lalu menjalankan metode asli FaceServer.exe lewat refleksi.
Hash executable dan MVID direkam pada setiap hasil. Binary tidak dipatch.

REA `inspect_managed_artifact` kini mendukung target managed ini. Identitas:
SHA-256 `8a123015b2ee095ceda51ece6d47436e9760c88be8f92fb76ed7c120c923c364`,
MVID `9e7e3122-c165-4ca3-3e9c-234edb96bf24`, assembly 16.5.0.0,
.NET Framework 4.8 x64. Evidence induk
`ev_9ba7fda80fc72ec89a5958b4f2f8585417e5d01abc32a4b8d213a00afa4c1876`,
ringkasan `ev_493d688940694420dcdf44d637a5daa28812894dd0c1254662600a85f9ed9975`.
Salinan ringkasan lengkap ada di `rea_identity.json`.

## Apa yang dibuktikan

- Importer asli `0x060006CC` menerima payload baru untuk V4YNE/DDCB4,
  ABCDE/DDCB4, Z9X8W/123AB, V4YNE/7738F ketika field lingkungan sesuai.
- Importer menolak Database ID berbeda; System ID berbeda tetap dapat
  diimpor tetapi predicate runtime `0x06000913` + `0x0600090D` menolaknya.
- Perpanjangan diterima bila Sequence naik dan KlienId sama; Sequence sama,
  lebih kecil, dan KlienId berbeda ditolak melalui exception asli.
- Runtime menolak Database ID salah, System ID salah (jalur online
  dihentikan), expired jauh, over-capacity, serta TRIAL. Exact-capacity sah.
- Importer menerima komentar, baris kosong, dan Base64 terpecah beberapa
  baris. Base64 rusak dan profil kripto salah ditolak.
- Tabel asli dari `0x060006C4` adalah `JibasSptFaceLicense`, 18 kolom.
  Sequence bertipe Int32, LicenseLimitDate DateTime, sisanya String.

`matrix_summary.json` mencatat hasil agregat; file per skenario mencatat
return/exception asli, perubahan field, skema asli, dan hasil runtime.
Run final 2026-11-10: **31/31 skenario importer lulus**, dengan 117 kasus
runtime yang cocok dengan ekspektasi. File keluaran engine yang diuji pada
run final memakai header `# LISENSI JIBAS SPT FACE` sebelum Base64; server
asli tetap menerimanya. Assertion rejection memeriksa pesan exception
spesifik, Sequence/KlienId tidak berubah, dan tidak ada cache baru untuk
impor fresh yang ditolak.

## Batas dan koreksi laporan lama

Ini **controlled replay**, bukan aktivasi produksi. Database ID, System ID,
jam database, jumlah wajah, server-running dan guard online disuntikkan
sebagai field pada process terpisah. Tidak menjalankan Main/UI, tidak
menulis database, tidak mengirim permintaan online, dan tidak mengubah
license.enc/config/binary live. Semua cache hasil importer berada di
sandbox unik `%TEMP%\codex-server-matrix\...`.

7738F di sini hanya pasangan simulasi untuk membuktikan format lintas ID.
Temuan audit WMI baru menyatakan ID live **DDCB4**; trimming serial disk di
detector Python lama menghasilkan 7738F yang salah. Lihat `../id_audit/`.

Algoritme minute asli bukan ordinal kalender Gregorian. Expiry
2028-12-31T23:59 dan 2029-01-01T23:59 memiliki nilai sama, sehingga kasus
`legacy_day_after_expiry` masih diterima. `expired` memakai satu tahun
sesudah expiry dan ditolak. Ini perilaku asli, bukan cacat harness atau
alasan mengubah formula kompatibilitas Python.

Jalankan ulang dengan `python -X utf8 bukti\server_matrix\run_matrix.py`.
Setiap eksekusi mengganti evidence yang bersangkutan dan membuat sandbox
baru; hasil tidak mengklaim aktivasi pada mesin dengan hardware lain.
