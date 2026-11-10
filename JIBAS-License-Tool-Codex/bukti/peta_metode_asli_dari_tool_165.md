# Alur verifikasi lisensi FaceServer 16.5

Batas bukti: SHA-256 executable 8a123015b2ee095ceda51ece6d47436e9760c88be8f92fb76ed7c120c923c364. Token aplikasi bersifat khusus build ini. Token yang berasal dari mscorlib/System.Data pada vm_metadata_resolved.txt merupakan token modul dependensinya sendiri.

## Impor berkas .lic: metode 0x060006CC

Metode adalah stub VM D/ANUBkV:3. Seluruh 2381 byte instruksi telah diparsing, operand field/metode di-resolve, dan semantik handler dibaca statis. Rujukan: verification_vm_resolved.txt, verification_vm_handlers.txt, vm_metadata_resolved.txt.

1. Baca berkas ASCII menggunakan StreamReader. Untuk setiap baris: Trim; abaikan baris kosong dan baris yang IndexOf("#", StringComparison.Ordinal) == 0; gabungkan baris lainnya tanpa newline.
2. Dekripsi gabungan dengan helper 0x060005C4 dan key/IV field 0x04000380/381.
3. Parse hasil sebagai XML melalui DataTable.ReadXml. Row harus ada; hanya row pertama yang dipakai.
4. Bila tabel lisensi runtime saat ini kosong, input["dbid"].ToString() harus sama dengan current Database ID field 0x040004DB.
5. Bila tabel runtime sudah berisi row: Sequence input harus lebih besar dari Sequence lama field 0x040004F7; KlienId input harus sama dengan KlienId lama field 0x040004EE; dbid input harus sama dengan current Database ID 0x040004DB. Jika semua lolos, row lama dihapus.
6. Isi field lisensi runtime: KlienId/EE, Klien/EF, DbId/F0, Seri/F1, LicenseLimit/F2, LicenseLimitDate/F3, expiry-minute/F4, MaxClient/F5, helper-capacity/F6, Sequence/F7, Info1/F8.
7. Buat row baru di tabel lokal dan salin 17 kolom dari input. Model tidak disalin. Tambahkan row lalu simpan melalui 0x060006C9.

Tidak ditemukan pemeriksaan signature, HMAC, KodeRs, atau KodeTx dalam seluruh jalur impor CC yang terurai. KodeRs dan KodeTx hanya disalin sebagai nilai kolom. Kesimpulan ini khusus jalur impor binary ini; bukan klaim mengenai aplikasi/server lain.

Error terdekode:
- Empty Registration File?
- Database Id tidak sama dengan lisensi (...)!
- Sequence lisensi lebih kecil daripada lisensi yang terdaftar!
- Sequence lisensi sama dengan lisensi yang terdaftar!
- Client Id tidak sama dengan lisensi sebelumnya!

## Penyimpanan lokal: 0x060006C9 dan pembacaan 0x060006CA

C9: DataTable.WriteXml(StringWriter, XmlWriteMode.WriteSchema), enkripsi helper 5C2, StreamWriter ASCII, WriteLine ke path license.enc.
CA: baca baris pertama ASCII, dekripsi helper 5C4, DataTable.ReadXml; jika rows kosong/gagal parse menghasilkan false, jika berhasil memuat field runtime di atas.
C4 menciptakan 18 kolom tabel JibasSptFaceLicense. Sequence Int32, LicenseLimitDate DateTime, lainnya String.
C6 menginisialisasi key/IV (C5), skema(C4), membuat berkas saat hilang/gagal(C8), membacanya(CA), memuat trial resource(9C6).
C8/C7 hanya membuat/mereset tabel kosong; bukan generator lisensi terdaftar.

## Status lisensi saat aplikasi berjalan: 0x06000913, 0x0600090D

913 menandai KlienId=="TRIAL" sebagai status trial. Untuk lisensi lain, 910 memperbarui jumlah wajah aktif lewat SQL COUNT(id) FROM jbssat.fcface WHERE status=1 AND useraktif=1. Kegagalan count menulis -1.

Syarat jalur aktivasi lokal pada 913:
- server-running field 0x040004E0 true;
- waktu database saat ini 0x040004DC <= expiry-minute 0x040004F4;
- current Database ID 0x040004DB == license DbId 0x040004F0;
- jumlah wajah >=0 dan <= MaxClient 0x040004F5;
- current SystemId 0x040004E7 == Info1 0x040004F8, atau Seri cocok entri daftar melalui 0x06000927.

Boolean hasil disimpan di field 0x040004DA. 90D mengembalikan true bila flag tersebut sudah true; selain itu memeriksa waktu/DbId/capacity dan mensyaratkan online-state getter77D==1. Jadi status impor sukses belum membuktikan status lisensi aktif saat service benar-benar berjalan.

Hardware input599 adalah serial physical drive yang memuat C: melalui WMI Win32_DiskDrive/PhysicalMedia; input59A adalah UUID dari Win32_ComputerSystemProduct. Bukti verification_hardware_id.txt. Current SystemId E7 diisi dari 0x0600059B pada startup C69/UI69D. 59B menggabung dua hardware string dari599 dan59A, hash MD5 helper849, ambil karakter hex zero-based [5,17,30,24,3], uppercase. Tidak ada hardware metode dijalankan dalam pemeriksaan ini.
Current DbId 4DB diambil melalui AC3 dan stored procedures jbssat; runtime DateTime dari AC4 menggunakan SELECT YEAR(NOW()), MONTH(NOW()), DAY(NOW()), HOUR(NOW()), MINUTE(NOW()), SECOND(NOW()). Tidak ada query dijalankan.

## Waktu kompatibilitas

Metode 66A/66B tidak menggunakan Unix timestamp atau ordinal Gregorian standar. Rumus:
minute + hour*60 + day*1440 + sum(days_in_month(year,m), m=1..current_month INCLUSIVE)*1440 + (floor(year/4)*366 + (year-floor(year/4))*365)*1440.
Tahun kabisat diperlakukan hanya year%4==0. Rujukan lengkap verification_dates.txt. Validator kompatibilitas perlu mempertahankan perilaku ini, termasuk rollover bulan/tahun.

## Aktivasi online (hanya diamati secara statis)

Bila machine mismatch namun syarat waktu/DbId/capacity terpenuhi, 913 memanggil780, lalu state machine790. 786 membuat InitTrans;790 membuat Validate dengan AppId=SPTFACE, SessionId, TransactionId, ClientId, ClientName, LicenseDbId, CurrentDbId, LicenseLimit. 787 mengirim HTTP POST via WebClient.UploadValues ke alamat yang dibentuk97F dari configured host/port628 dan dua komponen path97D/97E. Tidak ada request dikirim saat analisis.

Response Value==1 menandai aktif online dan memulai heartbeat KeepAlive783. Response0 pada Validate menghasilkan pesan lisensi sebelumnya masih aktif, tunggu5menit. Kesalahan/tiga heartbeat failure menonaktifkan online-state. Rujukan verification_methods.txt dan verification_checks.txt.

## Helper VM lain: 0x060006CD

CD (64 byte) membandingkan arg0.Equals(license.Seri 0x040004F1), lalu field config 0x0400038E.Equals(license.DbId 0x040004F0), atau false. Field038E dalam kelas konfigurasi database, diinisialisasi String.Empty oleh80D; tidak ditemukan penggunaan/pengisian IL biasa lainnya. CD tidak mempunyai pemanggil IL biasa yang ditemukan. Jangan menyebut038E sebagai SystemId; provenance tersebut tidak terbukti.

## Pengujian dan batas hasil

- Runtime asli telah diuji di salinan temp: loader CA menerima license.enc yang dihasilkan importer, lalu metode913/90D menghasilkan Aktif untuk V4YNE/DDCB4; salah DB, expired, over-capacity, trial ditolak; exact-capacity diterima. Wrong-SystemId menghasilkan false dengan jalur online sengaja dihentikan oleh guard343=true sebelum Task.Run. Bukti verification_runtime_predicate.json; source tools/string_decoder_runtime.cs. Semua 7 hasil sesuai ekspektasi.
- Pengujian runtime menggunakan lingkungan deterministik yang diinjeksikan (serverRunning=true, DBconnected=false, count dan DBtime disetel). Ini membuktikan logika original menerima payload pada lingkungan simulasi, bukan aktivasi produksi. Tidak ada Main/UI atau I/O DB/network yang dijalankan.
- Uji import baru, renewal Sequence meningkat, Sequence sama/lebih kecil, ClientId berbeda, DbId berbeda, komentar/blank lines, payload rusak.
- Pengujian nyata status service memerlukan database/runtime yang berjalan; analisis statis atau simulasi pure-function tidak membuktikan service end-to-end.


