# SharedDocs — mulai di sini

Direktori ini sejajar dengan **Codex/** dan **OpenCode/**. Isinya adalah handoff
teknis lintas agent, terutama hasil Codex. Kode produk tetap berada di direktori
implementasinya; dokumen ini bukan implementasi generator baru.

Urutan baca yang disarankan:

1. [Status dan peta project](PROJECT_MAP.md).
2. [Format dan variabel umum](LICENSE_FORMATS.md).
3. [Bukti, reproduksi, dan batas kesimpulan](EVIDENCE_AND_REPRO.md).
4. [Arsitektur GUI/batch/standalone](APPLICATION.md).
5. Dokumen produk pada [products/](products/).
6. [Status validasi terkini](VALIDATION.md).

| Produk | Dokumen |
|---|---|
| Absensi Wajah | [absensi-wajah.md](products/absensi-wajah.md) |
| SchoolPay | [schoolpay.md](products/schoolpay.md) |
| CBE Server | [cbe-server.md](products/cbe-server.md) |
| Absensi Finger | [absensi-finger.md](products/absensi-finger.md) |
| SJS | [sjs.md](products/sjs.md) |
| LetterStore | [letterstore.md](products/letterstore.md) |

Penting: hash binary menentukan arti token metadata. Jangan memakai token dari
versi/build lain. Penerimaan importer, keberhasilan loader cache, predikat runtime,
dan aktivasi online adalah empat tingkat bukti berbeda. Jangan menulis klaim
aktivasi jika yang diuji hanya decoding atau importer.

Tidak ada PAT, password database, credential Google, atau registration token nyata
yang perlu disalin ke sini. Parameter format kripto yang dibutuhkan program ada
di profil/source terikat artifact; lihat referensi dokumen produk.
