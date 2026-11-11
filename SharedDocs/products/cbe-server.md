# CBE Server26.5

CbeServer.exe SHA256 a2b77a3fc715d1d8c2b47a29ff65444af0e829c3f2704098ed538c48ce5f140b,
MVID5831bc0d-d22e-4a13-67b9-f22eab4b24a8, managed x64 .NET4.8.

| Token | Makna |
|---|---|
| 05B8/05B9 | schema18kolom JibasCbeLicense /crypto FACE-profile |
| 05C0 | importer resmi, dipanggil UI0BB6 |
| 05BE | loader cache |
| 040003F3 | currentDBID holder untuk controlled replay |
| 040003FD/3FE | MaxClient nominal /hasil turunan05BF |
| 0E0A | formula minute, Int32 yearterm sama SchoolPay |
| 006FF | metode pasca-load benar-benar hanya ret; bukan hook/stub harness |

File18kolom cukup; header dan ForCbe tidak diperlukan. Original importer juga
menerima tabel FACE yang kompatibel, SystemID salah pada Info1/Seri dan expiry
lampau. Inspector Python tetap meminta tabel CBE untuk mencegah salah pilih.

Literal UI MaxClient menyebut koneksi klien bersamaan. Nominal100 disimpan pada
3FD; hasil turunan250 pada3FE. Consumer VM3FE belum terbukti pada gate koneksi,
jadi jangan menamai250 kapasitas aktual atau mengubahinput100menjadi250.
runtime_capacity_proven tetapfalse.

Kode: ../../Codex/cbe_codec.py,cbe_schema.xml. Evidence: cbe,cbe_validation,
34skenario/46percobaan,29diterima17ditolak; delapan vector tanggal asli cocok.
Semua13file instalasi tetap utuh. Main,SQL,onlineaktivasi dan loop runtime tidak
dijalankan. Lihat ../../Codex/CBE.md untuk penggunaan dan batas.
