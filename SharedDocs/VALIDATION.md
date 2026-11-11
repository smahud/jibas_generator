# Status validasi 11 November 2026

Implementasi aktif: Codex, enam tab berurutan Absensi Wajah, Absensi Finger,
SchoolPay, CBE Server, SJS, LetterStore. OpenCode tidak diubah dalam penambahan ini.

| Pemeriksaan | Hasil | Bukti |
|---|---|---|
| Suite source | 240 passed,1 skipped;20.48detik | Codex/TEST_REPORT.md |
| Codec baru | Finger15, LetterStore12, SJS23 | Codex/tests/test_*_codec.py |
| GUI/layout | 12/12 scene normal880x650 dan minimum760x560; tidak ada overlap/label terpotong | Codex/bukti/shared_save_all |
| Standalone | Enam produk generate/inspect/verify dan identitas salah;4renewal+2regenerasi | Codex/bukti/standalone/verification.json |
| Save All EXE | Preflight sebelum folder;6file baru lalu6file batch kedua | Codex/bukti/standalone/verification.json |
| Finger metode asli | 3build: importer, cache reload, serial benar/salah, scope/header | Codex/bukti/fingerprint/final_replay_summary.json |
| LetterStore metode asli | 3DBID+headerless, cache, flag, negative/duplicate | Codex/bukti/letterstore/original_import_results.json |
| SJS metode asli | 11kontrol importer/renewal;encoder token asli | Codex/bukti/sjs/oracle_matrix.json |

Satu skip suite adalah cache FACE terpasang tanpa row lisensi; fixture dan codec
tetap diuji. Test warning finalizer Tk dianggap error. Semua perubahan lisensi
percobaan masuk folder sementara; hash binary/config/cache live yang diperiksa
tetap sama. Pemeriksaan field bersama/privat serta rollback batch6produk tidak
menggantikan oracle per codec.

Build EXE akhir, versi package, ukuran dan SHA256 ada di
`Codex/bukti/standalone/build_manifest.json`. Manifest rilis keseluruhan ada di
`Codex/MANIFEST.json`; manifest tidak memasukkan hash dirinya sendiri. Jangan
mengandalkan hash EXE dari catatan build lama.

Belum dibuktikan: aktivasi online, alokasi School ID SJS di server, hak remote
Services/Jenis, operasi scanner/presensi penuh, maupun seluruh gate runtime
SchoolPay/CBE. Local import/cache/registration flag adalah tingkat bukti yang
berbeda. Gunakan [panduan reproduksi](EVIDENCE_AND_REPRO.md) dan halaman produk.
