# Audit lanjutan Face Server 16.5 dan identitas lisensi

Audit: 10 November 2026. Tujuan audit ini memeriksa temuan yang sudah ada,
bukan mengulang penerbitan file atau eksperimen perubahan database. Tidak ada
binary, konfigurasi, cache instalasi, atau database aktif yang ditulis oleh audit ini.

## Kesimpulan dan tingkat bukti

Temuan koreksi dalam `TEMUAN.md` lebih kuat daripada laporan OpenCode lama:
System ID yang dicatat metode asli adalah **DDCB4**, sementara **7738F** berasal
dari penghapusan spasi serial disk. Aturan perpanjangan yang dicatat matriks akhir
memerlukan Client ID tetap dan Sequence meningkat. Matriks akhir juga menunjukkan
bahwa impor sukses tidak sama dengan lisensi aktif.

Namun, **penerbitan resmi belum dibuktikan** oleh artefak yang diaudit. Rekonstruksi
format, penerimaan importer, dan predicate yang dijalankan dengan field lingkungan
yang diisi harness tidak membuktikan otorisasi penerbit, layanan online, atau
aktivasi GUI lengkap. Tidak ada API penerbit, respons penerbit terverifikasi,
atau mekanisme alokasi Client ID penerbit yang dibuktikan oleh bukti server ini.

| Klaim | Status audit | Sumber |
|---|---|---|
| Binary terpasang adalah FaceServer 16.5.0.0 .NET Framework 4.8 x64 yang dianalisis sebelumnya | Diverifikasi ulang statis dengan REA dan SHA-256 | `bukti/audit_2026_11_10/server/rea_identity.json` |
| 31 skenario importer dan 117 kasus predicate konsisten dengan ringkasan lama | Diverifikasi ulang terhadap JSON tersimpan; tidak dieksekusi ulang | `bukti/audit_2026_11_10/server/saved_evidence_audit.json` |
| Metode asli dipanggil oleh harness, bukan fungsi lisensi Python yang dijadikan oracle | Terlihat pada source harness | `bukti/server_matrix/ServerMatrixProbe.cs` |
| Perilaku tersebut sama dengan seluruh startup/UI/database/network aplikasi asli | Belum dibuktikan | Harness tidak menjalankan Main/UI dan mengisi field lingkungan sendiri |
| Lima fixture Database ID dan enam vektor hash hardware cocok | Konsistensi bukti historis dan digest .NET dihitung ulang | `bukti/id_audit/isolated_db_matrix.json` |
| Client ID baru harus UUID sebagaimana generator Python | Bukan temuan penerbit; hanya pilihan implementasi tool lama | `license_codec.py`, cabang `uuid.uuid4()` |

## Identitas target dan REA

- SHA-256: `8a123015b2ee095ceda51ece6d47436e9760c88be8f92fb76ed7c120c923c364`.
- MVID: `9e7e3122-c165-4ca3-3e9c-234edb96bf24`.
- REA parent: `ev_9ba7fda80fc72ec89a5958b4f2f8585417e5d01abc32a4b8d213a00afa4c1876`.
- REA summary: `ev_493d688940694420dcdf44d637a5daa28812894dd0c1254662600a85f9ed9975`.

`inspect_managed_artifact` tersedia dan berhasil. Klaim lama bahwa REA tidak
mendukung managed PE sudah tidak berlaku untuk sesi ini. ID evidence deterministik
sama dengan hasil lama karena input dan proyeksi sama; ini bukan identitas sesi
runtime baru. REA hanya membaca metadata, tidak menjalankan assembly/decompile C#.
Token berikut hanya berlaku untuk hash/MVID di atas.

## Alur pembacaan dan validasi server

Source harness memanggil initializer kripto `0x060006C5`, pembuat tabel
`0x060006C4`, lalu importer `0x060006CC`. Tabel asli yang dicatat bernama
`JibasSptFaceLicense`, dengan 18 kolom; `Sequence` Int32 dan
`LicenseLimitDate` DateTime, lainnya String. Data payload menggunakan format
simetris XML/Base64 yang sudah dijelaskan dalam `TEMUAN.md`; audit ini tidak
menganggap ketiadaan signature pada jalur tersebut sebagai bukti hak menerbitkan.

Importer memeriksa Database ID dan kesinambungan perpanjangan. Predicate
`0x06000913` bersama accessor `0x0600090D` mencatat hasil untuk Database ID,
System ID, waktu, kapasitas, serta status TRIAL. Harness menempatkan direktori
cache pada sandbox unik; seluruh operasi importer yang dicatat adalah pemanggilan
metode asli dalam proses terpisah, bukan aktivitas GUI produksi.

## Database ID

`bukti/id_audit/ac3_il.txt` menunjukkan `0x06000AC3` membaca routine pada `jbssat`,
memanggil pemeriksaan `0x06000ABF`, menguraikan hex hasil OUT, mengambil karakter,
lalu uppercase. Resep tersimpan adalah:

| Urutan | Routine | OUT | Posisi karakter setelah decode (mulai 0) |
|---|---|---|---:|
| 1 | splang04 | uhh | 14 |
| 2 | splang02 | uhf | 5 |
| 3 | splang09 | uhc | 25 |
| 4 | splang11 | uhe | 37 |
| 5 | splang01 | uhb | 47 |

Identitas ini persisten pada routine, bukan hash System ID atau nilai lisensi.
Laporan sandbox sebelumnya mencatat bootstrap routine kosong menghasilkan 12
routine dan ID `LTB28`; routine yang hilang sebagian menghasilkan
`Licensing system has been altered!`. Karena AC3 dapat bootstrap, memanggilnya
pada database yang tidak lengkap bukan operasi baca saja.

Hasil yang sudah tersimpan untuk V4YNE, ABCDE, WRK9T, Z9X8W, dan a1b2c/A1B2C
cocok antara metode asli dan Python. Snapshot hash 12 routine live sebelum/sesudah
dalam JSON sama. Audit ini memeriksa konsistensi snapshot tersebut; tidak melakukan
query live baru, tidak membuktikan keadaan database sekarang, dan tidak mengulang
eksperimen yang memerlukan perubahan routine.

## System ID

IL `0x0600059B` memanggil pembaca serial dan UUID (`599` dan `59A`), langsung
menggabungkan string, menghitung hash melalui `849`, mengambil indeks hex
`5,17,30,24,3`, lalu uppercase. Tidak ada Trim di jalur gabungan ini.

Bukti hardware sebelumnya mencatat panjang serial 20 karakter, termasuk 9 spasi
belakang. Hash ASCII .NET tanpa menghapus spasi menghasilkan DDCB4. Generator
lama menghapus spasi sehingga memperoleh 7738F. Audit konsistensi ini menghitung
ulang enam digest dengan `System.Text.Encoding.ASCII` dan MD5 .NET; seluruhnya
cocok dengan JSON tersimpan. Pembacaan hardware live tidak diulang karena bukti
asli serta koreksi kode sudah ada dan target binary identik.

## Client ID dan perpanjangan

Client ID disimpan pada kolom `KlienId`; bukti importer menuntut kesamaan dengan
nilai lisensi sebelumnya. Client ID bukan Database ID atau System ID.
`license_codec.py` lama membuat UUID untuk lisensi baru. Penerimaan UUID di
controlled replay tidak mengungkap bagaimana penerbit resmi mengalokasikan ID.

Empat pasangan ID diuji pada matriks sebelumnya:

| Pasangan | Fresh | DbId lingkungan berbeda | System ID lingkungan berbeda | Renewal ID tetap/Sequence naik | Sequence sama/turun | Client ID berbeda |
|---|---|---|---|---|---|---|
| V4YNE / DDCB4 | Impor true | Ditolak | Impor true, predicate false | Impor true | Ditolak | Ditolak |
| ABCDE / DDCB4 | Impor true | Ditolak | Impor true, predicate false | Impor true | Ditolak | Ditolak |
| Z9X8W / 123AB | Impor true | Ditolak | Impor true, predicate false | Impor true | Ditolak | Ditolak |
| V4YNE / 7738F | Impor true | Ditolak | Impor true, predicate false | Impor true | Ditolak | Ditolak |

Ini pasangan field yang disuntikkan pada satu komputer, bukan empat mesin dengan
hardware yang benar-benar berbeda. 7738F hanya fixture simulasi.

## Batas predicate yang perlu dinyatakan tepat

Pada kasus System ID salah, `accepted=false` dicatat bersama `status_code=-999`
dan `status_text=""`, yaitu nilai sentinel awal harness. Guard online juga
dikendalikan. Karena itu, hasil yang tepat adalah **predicate false pada keadaan
harness tersebut**, bukan bukti respons penolakan lengkap dari layanan penerbit.

Waktu juga disuntikkan. Skenario `legacy_day_after_expiry` diterima oleh metode
asli untuk pasangan tanggal tertentu karena formula waktu legacy; ini bukan
bukti bahwa kalender Gregorian dipakai atau bahwa penerbit mengizinkan grace period.

## Koreksi terhadap arsip lama

1. `JIBAS-License-Tool/README.md` menyatakan trim dilakukan kode asli dan 7738F
   adalah ID live; dibantah oleh dump IL serta vektor metode asli di audit ID Codex.
2. File cache dan file impor client semula disamakan; temuan client memisahkan
   header impor dari cache, sedangkan server dapat menerima komentar/header.
3. `Analisis.md` historis menyatakan Client ID berbeda dapat diterima ketika
   Sequence naik. Matriks akhir menampilkan exception asli Client ID berbeda
   pada keempat pasangan; gunakan hasil matriks akhir sebagai kesimpulan.
4. Klaim mendukung format tidak cukup untuk menyebut tool sebagai penerbit resmi.
   Tetap pisahkan hasil diagnosis dari penerbitan yang otoritasnya belum terbukti.

Audit source juga menemukan credential DB literal dalam `bukti/id_audit/audit_ids.py`
versi yang dibaca pada awal audit. Nilainya tidak disalin ke laporan ini. Sebelum
publikasi, pindahkan credential koneksi ke environment atau penyimpanan credential
lokal dan tinjau ulang file yang akan dikomit. Ini berbeda dari konstanta format
aplikasi yang diperoleh lewat analisis binary.

## Reproduksi audit ini

Jalankan `bukti/audit_2026_11_10/server/audit_saved_evidence.ps1` melalui PowerShell.
Skrip hanya membaca binary/JSON bukti dan menulis laporan audit ke direktorinya
sendiri. Tidak menjalankan aplikasi, tidak mengimpor lisensi, dan tidak membuka DB.

Hasil audit: SHA binary cocok; 31 skenario dan 117 kasus predicate konsisten;
5 fixture Database ID dan 6 digest hardware cocok; snapshot routine tersimpan sama.
Konsistensi JSON bukan autentikasi log historis. Untuk menyatakan aktivasi resmi
berhasil masih diperlukan lisensi/proses penerbit yang otoritasnya dapat diverifikasi
dan observasi penerimaan aplikasi lengkap dalam lingkungan pengujian yang sesuai.
