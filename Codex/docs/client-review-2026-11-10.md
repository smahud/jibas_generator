# Audit lanjutan client 16.10 — 10 November 2026

## Kesimpulan

Bukti yang tersedia mendukung akar masalah **pembungkus file impor**, bukan
kegagalan identitas atau dekripsi pada tahap pertama: importer client memeriksa
penanda `LISENSI JIBAS SPT FACE` pada baris pertama. Payload cache tanpa header,
header produk lain, dan header huruf kecil ditolak dengan pesan
`File terpilih bukan lisensi JIBAS Presensi Wajah`.

Audit ini mengulang satu kontrol negatif dengan executable asli yang identik,
tanpa menghasilkan lisensi baru. Penolakan berhasil direproduksi pada
2026-11-10T11:39:46Z. Matriks penerimaan sebelumnya diperiksa sebagai bukti
historis; tidak dinyatakan sebagai eksekusi baru atau aktivasi GUI penuh.

## Identitas dan bukti baru

- Target instalasi: `C:\Program Files\YIM\JIBAS Face & Fingerprint Client 16.10\FaceFgrClient.exe`.
- SHA-256: `6f5369df4d854c467d24fb067d8b79c573b35699c7b1ce7f19a310669f1ba546`.
- MVID: `0ec4d2e7-40e6-4d47-2b18-cbedb1259d09`; assembly `16.10.0.0`, .NET Framework 4.8, x86-64.
- REA `inspect_managed_artifact` pada instalasi sekarang mengonfirmasi identitas
  yang sama dengan bukti lama. Summary evidence:
  `ev_db48039a22db99e86e21729a6a5c8c9379ff538ee0d00b915c6de7f92dd0659d`;
  parent: `ev_85272d051356cb1f9372b3689a32f4663d0152f1c86fece45ab897ed3e4d77ed`.
  Metadata lengkap tanpa issue, tetapi bukan dekompilasi atau bukti eksekusi.
- [REA identity](../bukti/audit_2026_11_10/client/rea_identity.json) dan
  [verification.json](../bukti/audit_2026_11_10/client/verification.json) menyimpan
  observasi baru, hash sumber harness, executable, input, dan matriks lama.
- [audit_client.ps1](../bukti/audit_2026_11_10/client/audit_client.ps1) mengompilasi
  ulang `ClientImportVerify.cs`, memakai input negatif yang sudah ada, menjalankan
  importer dalam folder baru, dan memeriksa hasilnya. Hash biner instalasi
  sebelum/sesudah identik; tidak ada koneksi database atau penulisan instalasi.

## Korelasi importer, cache, dan error

Arsip [import_methods_il.txt](../bukti/client_import/import_methods_il.txt)
menghubungkan handler UI `0x06000650`, IL0040, dengan importer `0x06000AF9`.
Nama obfuscated pada handler menjelaskan konteks error; bukan bagian file lisensi.
AF9 merupakan wrapper VM. Arsip trace eksplorasi menunjukkan `String.IndexOf`
dengan penanda produk; trace tersebut memakai hook sementara, sehingga dipisah
dari matriks final yang harness-nya tidak memakai hook/patch.

Cache loader `0x06000AF7` membaca baris pertama (`ReadLine`, IL0011), lalu
mendekripsi dan memuat XML (`DataTable.ReadXml`, IL003E). Karena itu format cache
dan format impor berbeda pada pembungkusnya walaupun payload FACE sama.
Keberhasilan AF7 saja tidak membuktikan AF9 menerima file melalui menu impor.

Header `# LISENSI JIBAS SPT FACE` dengan CRLF adalah bentuk yang telah diuji.
Jangan mengubah temuan tersebut menjadi klaim bahwa seluruh baris harus identik
secara byte atau bahwa `#`/CRLF selalu wajib: bukti trace adalah pencarian substring.
Penerimaan semua variasi whitespace, encoding, newline, komentar, dan prefix
belum dipetakan lengkap.

## Pemeriksaan matriks historis

[matrix_results.json](../bukti/client_import/matrix_results.json) memuat 8 skenario,
11 percobaan, dengan hash dan MVID target yang cocok. Sumber harness secara
eksplisit mengisi holder Database ID `0x0400051C` dan mengarahkan cache ke sandbox;
ini adalah **controlled replay**, bukan beberapa komputer/database produksi.

| Kasus | Hasil terekam | Makna yang dapat dipertahankan |
|---|---|---|
| Tanpa header / produk lain / lowercase | Ditolak; pesan error pengguna | Pemeriksaan marker terjadi sebelum penerimaan payload |
| Header benar, V4YNE/DDCB4 | AF9 TRUE, AF7 TRUE | Importer dan cache menerima input dalam lingkungan uji |
| Sequence sama | Ditolak | Impor ulang bukan renewal |
| ClientId sama, sequence 2 | Diterima | Renewal memerlukan state lisensi sebelumnya |
| ClientId berbeda, sequence 3 | Ditolak | Sequence naik saja tidak cukup |
| Database runtime VWXYZ, lisensi V4YNE | Ditolak | Ada ikatan Database ID pada importer |
| ABCDE/ABCDE dan 12345/12345 | Diterima | Penerimaan metode tidak terbatas pada contoh pertama |
| Info1/System ID 00000 | AF9 TRUE, AF7 TRUE | Penerimaan client tidak membuktikan kecocokan System ID |

Audit byte baru memastikan payload `v4yne_new.lic`, `wrong_header.lic`, dan
`lowercase_header.lic` setelah baris pertama sama persis dengan
`missing_header.lic`. Ini mendukung isolasi variabel header. Rekaman lama tidak
menyimpan hash setiap input saat eksekusi; hash sekarang mengikat artefak yang
tersedia saat audit, bukan membuktikan riwayatnya secara kriptografis.

## Koreksi dan batas yang masih berlaku

README tool lama menyamakan berkas impor dengan cache, serta menguji AF7 untuk
masalah trial. Itu tidak cukup untuk error AF9. README/TEMUAN paket Codex sudah
mengoreksi pembungkus impor. README Codex dan README client_import dalam folder
Publish byte-identik dengan versi yang dibaca saat awal audit ini.

Tidak ditemukan bukti mekanisme penerbitan **resmi/berwenang** dalam lingkup
dokumen, harness, dan metadata client yang diperiksa. Kompatibilitas format
simetris dan penerimaan metode bukan bukti kewenangan menerbitkan lisensi.
Belum ada bukti aktivasi melalui dialog GUI, penggunaan presensi kamera sampai
penyimpanan, verifikasi layanan penerbit, atau perbandingan dengan build client
selain 16.10. Pemeriksaan System ID runtime server harus dibaca dari bukti server
terpisah; AF9/AF7 tidak boleh dijadikan penggantinya.

Eksperimen lanjutan yang relevan memerlukan lisensi resmi untuk ID tujuan dan
alur penerbitan yang dapat diverifikasi. Memasang file hasil rekonstruksi ke
instalasi aktif tidak diperlukan untuk menyimpulkan akar error pembungkus ini.
