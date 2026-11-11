# Bukti dan reproduksi

## Kekuatan kesimpulan

1. Roundtrip Python hanya membuktikan konsistensi implementasi sendiri.
2. Metadata/IL/REA mengikat struktur ke hash,MVID dan token build tertentu.
3. Original importer acceptance membuktikan jalur impor pada input/lingkungan itu.
4. Original cache loader membuktikan file hasil importer dapat dimuat ulang.
5. Predikat runtime menambah bukti kondisi tertentu, bukan aktivasi online penuh.
6. Publisher/online activation hanya boleh diklaim jika benar-benar diamati.

Evidence Codex menyimpan batas terpisah ini. Harness memakai proses terpisah,
folder sementara dan field lingkungan terkontrol. Tidak menjalankan Main/SQL/
network hanya untuk mengejar hasil positif. Ketidakpastian disimpan sebagai unknown.

## Peta evidence

| Direktori di Codex/bukti | Isi |
|---|---|
| client_import | importer FACE AF9, header, multi-ID, renewal dan loaderAF7 |
| server_matrix | Face Server importer6CC, loader6CA, predikat913/90D |
| id_audit | original hardware, recipeDB, sandboxMariaDB dan hash routine live |
| schoolpay,schoolpay_validation | schema19/import20, ForSchoolPay, ID/date,31/43 |
| cbe,cbe_validation | schema18, official5C0, loader5BE,34/46, capacity/date |
| fingerprint | 3 importer/loader/serial matcher asli, schema JSL, scope/header negatives, live_integrity |
| letterstore | schema JLS, importer0916, cache0915, flag0989, multi-DB dan single-registration |
| sjs | token encoder0FFF, importer0EBA, 11 kontrol renewal/DB/expiry, synthetic smoke_fixture |
| shared_save_all | screenshot, sharedfield/layout, Save All QA |
| standalone | build log, source hashes, executable hash dan frozen verification |

## Batas dan praktik reproduksi

Gunakan skill reverse-engineer-anything untuk klaim binary; managed PE mulai
dengan inspect_managed_artifact dan focused inspect_managed_members. Jangan
meminta seluruh member assembly besar jika budget representasi tidak cukup.
Metadata tokens bukan alamat native atau nama source asli. Simpan parent
EvidenceID,sha256,MVID,provider,coverage,limitations dalam laporan.

Harness C# biasanya membutuhkan csc .NET Framework sesuai arsitektur target:
Face/CBE x64; SchoolPay x86. Gunakan AssemblyResolve ke DLL target hanya untuk
dependensi, dan direktori cache diarahkan ke sandbox sebelum init. Beberapa
initializer memanggil VM/DB/jaringan; pilih crypto/schema builder terpisah.

Kompilasi harness dari source yang ada dan baca README foldernya. Program asli
dan cache/config instalasi tetap utuh; ambil hash sebelum/sesudah. Jangan memuat
dump `db/` lama ke produksi: dump dapat mengandung DROP DATABASE dan data akun.
Tidak ada credential/PAT yang perlu dimasukkan ke source atau dokumentasi baru.

## Repositori

Kerjakan feature branch, uji, commit perubahan yang dapat direview, merge ke main,
dan push. Jangan reset atau menimpa perubahan agent lain. Periksa origin/main
sebelum merge. Release builder mengecualikan DLL/JIBAS/harness EXE dan sandbox,
kecuali produk final Codex/JIBAS-Generator-Codex.exe yang sengaja didistribusikan.
Manifest mengecualikan dirinya sendiri dan receipt publikasi lokal.
