# SchoolPay Secure Server10.5

SPayServer.exe SHA256 ca112352f1160ead541ff404354aecb3a83165798e562dea5ca3ef68191cd2f8,
MVID3f7d530d-8b12-4c29-229b-d7a7bd599cf1, managed x86 .NET4.8.

Schema0750=JibasSchoolPayLicense19kolom; crypto0751 sama profil FACE/server.
UI0799 memakai importer0757; cache loader0756. File impor memerlukan DataColumn
ForSchoolPay pada XSD (total20), bukan nilai boolean tertentu. Nilai0,false,
kosong dan XSDtanpa elemen row semuanya diterima. Header komentar opsional.

Binding nominal memakai DatabaseId pada DbId dan SystemID pada SystemId,
bukan Info1. Kapasitas MaxVendor. Renewal mempertahankan KlienId dan Sequence
meningkat. Original importer juga menerima SystemId salah/expiry lampau, jadi
acceptance tidak membuktikan gate runtime. VM09D0 tidak dijalankan karena batas
jaringan/SQL belum dipastikan.

DatabaseID0824 membaca jbsfina dengan resep berbeda dari Face. Pada mesin uji
original/Python cocok7VJM4; SystemID0945 cocokDDCB4. Sembilan vector tanggal0708
mencakup Int32 wrap pada tahun4084/4085/9999.

Kode: ../../Codex/schoolpay_codec.py dan schoolpay_schema.xml.
Evidence: ../../Codex/bukti/schoolpay,schoolpay_validation;31skenario/43percobaan.
Panduan lengkap: ../../Codex/SCHOOLPAY.md. Jangan menambah ForSchoolPay ke cache
asli atau mengubah konstanta global codec Face untuk mendukung produk ini.
