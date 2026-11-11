# Absensi Wajah

Target FaceServer.exe16.5 SHA256
8a123015b2ee095ceda51ece6d47436e9760c88be8f92fb76ed7c120c923c364,
MVID9e7e3122-c165-4ca3-3e9c-234edb96bf24. Client FaceFgrClient.exe16.10 SHA256
6f5369df4d854c467d24fb067d8b79c573b35699c7b1ce7f19a310669f1ba546,
MVID0ec4d2e7-40e6-4d47-2b18-cbedb1259d09.

| Metode/field | Makna |
|---|---|
| Server060006C4/6C5 | schema JibasSptFaceLicense18kolom /crypto init |
| Server060006CC | importer, DbId dan renewal |
| Server060006CA | cache loader |
| Server06000913/90D | updater/predikat runtime pada lingkungan terkontrol |
| Server06000AC3 | pembentuk DBID jbssat; bootstrap dapat menulis jika routine hilang |
| Server06000599/59A/59B | WMI raw disk/UUID/hash SystemID |
| Client06000650→AF9 | handler impor→importer dengan header |
| Client06000AF2/AF7 | crypto FACE /loader cache FACE |
| Client0400051C | holder DBID aktif untuk impor |

File impor client memerlukan marker case-sensitive `LISENSI JIBAS SPT FACE`
pada baris pertama. Generator menulis `# `+marker+CRLF sebelum Base64; cache
licenseface.enc hanya Base64. Server mengabaikan komentar sehingga satu file
impor generator diterima jalur server dan client yang diuji.

DbId harus cocok; renewal KlienId sama dan Sequence naik. Importer server tidak
menolak Info1 salah, tetapi predikat runtime yang diuji menolaknya. Exactcapacity
sah; overcapacity/trial/expiry ditolak pada kondisi simulasi yang direkam.

Evidence: ../../Codex/bukti/server_matrix (31importer,117runtime),
../../Codex/bukti/client_import (8skenario/11percobaan), id_audit, TEMUAN.md.
Kode: ../../Codex/license_codec.py. GUI hanya input manual, tanpa DB/hardware I/O.

Jangan mengulang klaim7738F sebagai ID live: rawserial dengan sembilan spasi
menghasilkanDDCB4. 7738F tetap dipakai sebagai vector simulasi, bukan identitas
mesin. Token fingerprint client berbeda; lihat halaman Absensi Finger.
