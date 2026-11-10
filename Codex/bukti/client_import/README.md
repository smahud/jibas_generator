# Pembuktian importer client 16.10

Error pengguna berhasil direproduksi dengan file dari generator lama, kemudian diperbaiki dengan menambahkan baris pertama:

```text
# LISENSI JIBAS SPT FACE
<Base64 ciphertext AES dari XML lisensi>
```

Baris menggunakan ASCII dan CRLF. Cache internal `licenseface.enc` tetap **tanpa header**: validator cache membaca baris pertama sebagai Base64. Mengganti ekstensi `.enc` menjadi `.lic` tidak menambahkan header yang diperlukan importer.

## Identitas dan jalur asli

- Target salinan byte-identik: `C:\YIM\JIBAS Generator\JIBAS Face & Fingerprint Client 16.10\FaceFgrClient.exe`.
- SHA-256: `6f5369df4d854c467d24fb067d8b79c573b35699c7b1ce7f19a310669f1ba546`.
- MVID: `0ec4d2e7-40e6-4d47-2b18-cbedb1259d09`.
- Handler UI `0x06000650`, IL0040, memanggil importer `0x06000AF9(String)`.
- Importer AF9 adalah wrapper kode virtualized. Trace runtime eksplorasi menangkap panggilan `String.IndexOf("LISENSI JIBAS SPT FACE")` pada baris pertama. Huruf kecil ditolak.
- Init profil kripto FACE `0x06000AF2`; init tabel `0x06000AF1`; validator cache `0x06000AF7`; writer cache `0x06000AF6`.
- Path cache memakai holder `0x04000369`. Database ID saat ini memakai holder `0x0400051C`, bukan holder lisensi `0x040004C9`.
- Holder setelah impor: ClientId `0x040004C7`, DbId lisensi `0x040004C9`, Sequence `0x040004D0`, Info1 `0x040004D1`.

Profil AES untuk payload sama dengan server dan cache FACE lama; kegagalan ini terjadi **sebelum dekripsi** akibat pembungkus file impor yang tidak lengkap.

## Matrix final: 8 skenario, 11 percobaan impor

Hasil utama: `matrix_results.json`, dibuat oleh `run_client_matrix.py` menggunakan `generate_license` dari direktori Codex. Semua percobaan final memakai `ClientImportVerify.cs`: metode asli dipanggil tanpa hook, tanpa patch biner di disk maupun kode proses. Database ID runtime diisi secara eksplisit sebagai controlled replay; tidak ada query atau perubahan database.

| Skenario | Percobaan | Importer AF9 | Validator cache AF7 |
|---|---:|---|---|
| Payload tanpa header | 1 | Ditolak, error persis dari pengguna | FALSE |
| Header produk salah | 1 | Ditolak, error yang sama | FALSE |
| Header huruf kecil | 1 | Ditolak, error yang sama | FALSE |
| Baru V4YNE/DDCB4, sequence 1 | 1 | Diterima | TRUE |
| Impor ulang sequence 1 | 1 | Ditolak: Sequence sama | TRUE pada cache lama |
| Perpanjangan sequence 2, ClientId sama | 1 | Diterima | TRUE |
| Sequence 3 tetapi ClientId berbeda | 1 | Ditolak: Client Id berbeda | TRUE pada cache lama |
| DbId lisensi V4YNE, DbId runtime VWXYZ | 1 | Ditolak: Database Id berbeda | FALSE |
| ID berbeda ABCDE/ABCDE | 1 | Diterima | TRUE |
| ID berbeda 12345/12345 | 1 | Diterima | TRUE |
| V4YNE dengan Info1/SystemId 00000 | 1 | Diterima | TRUE |

Skenario `fresh_renewal` mencakup empat percobaan dalam satu proses, sehingga state sequence dan ClientId berasal dari impor sebelumnya. Penolakan renewal tidak menghapus cache lisensi yang telah diterima.

## Batas kesimpulan

AF9 pada percobaan ini memeriksa header, Database ID, Sequence dan Client ID perpanjangan. `Info1=00000` diterima pada mesin yang System ID aslinya dilaporkan `DDCB4`; penerimaan AF9 dan pembacaan AF7 tidak membuktikan kecocokan System ID atau izin presensi pada seluruh alur aplikasi. Pengujian runtime Face Server memiliki predikat terpisah untuk System ID, masa berlaku dan kapasitas.

AF7 membaca XML dan menyalin holder lisensi. IL-nya memakai `Convert.ToInt32(Object)` untuk `MaxClient` pada IL0130 dan `Sequence` pada IL0159; nilai di luar Int32 dapat gagal walaupun Python `int()` bisa membacanya. Lihat `import_methods_il.txt`.

Pembuktian ini menjalankan fungsi asli yang dipanggil UI; belum menjalankan klik impor melalui dialog GUI atau presensi kamera secara menyeluruh. Tidak ada file lisensi/config/biner instalasi asli yang ditulis. Semua cache percobaan berada di subdirektori bukti ini.

## Bukti REA

`rea_evidence_bundle.json` menyimpan 4 record REA (metadata statis, bukan eksekusi):

- Artifact asli: `ev_85272d051356cb1f9372b3689a32f4663d0152f1c86fece45ab897ed3e4d77ed`.
- Ringkas artifact: `ev_db48039a22db99e86e21729a6a5c8c9379ff538ee0d00b915c6de7f92dd0659d`.
- Member tipe lisensi: `ev_555208cc81f4fe7bef9bdb5f8c5763520b6a612013b9c823d8e6a7beab779b0e`.
- Ringkas member: `ev_e3bf92f49b017cfc595aceb97cebce45be5931e04a49e7e13ec6bc850776da56`.

Metadata statis tidak mengeksekusi atau mendekompilasi kode virtualized. `client_il.ps1` mengekstrak CIL dengan ReflectionOnlyLoadFrom. `ClientImportProbe.cs` dan `trace_result.json` adalah eksplorasi terpisah: opsi `trace` menggunakan hook String sementara **hanya di proses harness** untuk merekam argumen, lalu proses berakhir. Bukti penerimaan final dalam `matrix_results.json` tidak memakai hook tersebut.

## Reproduksi

Kompilasi harness bersih:

```powershell
$d = 'C:\YIM\JIBAS Generator\JIBAS-License-Tool-Codex\bukti\client_import'
& 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe' /nologo /r:System.Web.Extensions.dll /out:"$d\ClientImportVerify.exe" "$d\ClientImportVerify.cs"
& 'C:\Users\Laptop Kantor - ASUS\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -X utf8 "$d\run_client_matrix.py"
```

Script membuat sandbox baru bila folder percobaan sebelumnya telah ada. JSON keluaran utama diperbarui; tidak menggunakan state lisensi instalasi live. Pada mesin lain sesuaikan path target di harness dan path Python.
