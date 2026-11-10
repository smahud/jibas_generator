# Pengujian akhir — Windows, 10 November 2026

Python 3.12, cryptography 50.0.2, PyMySQL 1.2.4, pytest 9.2.0.

`python -X utf8 -m pytest tests -q`: **49 passed**, 3.57 detik.
Termasuk regresi header impor/cache, ID berbeda, entrypoint subprocess,
perpanjangan eksplisit, Int32 overflow, serta spasi serial dan ASCII .NET.

GUI: Tkinter root dibuat, LicenseApp berhasil dibangun (28 child widgets),
update layout dan destroy berhasil. Ini smoke test, bukan klik-through lengkap.
Launcher CLI dijalankan di path yang mengandung spasi; detect menghasilkan
V4YNE/DDCB4 dan generate menghasilkan file .lic berheader, valid offline.

Integrasi repository remote main: **71 passed, 1 skipped** di Windows,
8.58 detik. Satu bug lama ditemukan: os.open(folder) melempar PermissionError
di Windows sebelum fstat sehingga kode error salah. Ditambahkan pemeriksaan
direktori awal tanpa menghapus fstat pasca-open; patch disalin ke
`patches/diagnostics_windows.patch`. Root pytest.ini memisahkan suite diagnostik
dari suite tool standalone agar nama modul tes yang sama tidak berbenturan.

Oracle eksternal: executable asli .NET Framework 4.8, tidak dipatch.

| Pengujian | Hasil | Evidence |
|---|---|---|
| Server importer | 31/31 skenario sesuai | bukti/server_matrix/matrix_summary.json |
| Server predicate runtime | 117 kasus sesuai | JSON per skenario server_matrix |
| Client importer + cache validator | 8 skenario, 11 percobaan sesuai | bukti/client_import/matrix_results.json |
| Database ID original vs Python | 5 ID cocok + bootstrap cocok | bukti/id_audit/isolated_db_matrix.json |
| Hardware/hash original vs Python | 6 vector cocok; live DDCB4 | bukti/id_audit/original_hardware_vectors.json |

Multi-ID dilakukan dengan kontrol lingkungan per proses, sedangkan Database ID
dibuktikan juga lewat instance MariaDB sandbox port3435. Tidak ada penggantian
ID atau routine live. Sandbox telah dihentikan. JIBAS-Database dan WebService
tetap running. Hash file instalasi/routine dibandingkan sebelum dan sesudah.
Seluruh 818 file instalasi identik; tidak ada path berubah pada live_integrity.json.

Tidak menguji aktivasi GUI penuh, seluruh workflow presensi, fingerprint, atau
layanan validasi online. Hasil `valid`/`ready` dari Python tetap pemeriksaan lokal.
