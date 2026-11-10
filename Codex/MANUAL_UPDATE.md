# Pembaruan11November2026

Permintaan GUI manual selesai: tiga tab produk, tanpa menu koneksi database,
deteksi Database/System ID, atau input Sequence. GUI dan CLI manual memakai
file lama untuk menghitung perpanjangan. Kotak hasil tetap6baris dan scrollable.

Struktur repository kini Codex/ dan OpenCode/. Root hanya panduan, launcher dan
konfigurasi pendukung. Implementasi OpenCode dipertahankan terpisah; tidak ada
produk Python yang ditempatkan langsung di root. README root dan Codex diperbarui.

Suite source Codex: **120passed8.56s**, dengan
PytestUnraisableExceptionWarning diperlakukan sebagai error. Termasuk14tes codec
CBE,12tes GUI manual, integrasi CLI tiga produk, legacy crypto/ID/regresi dan
uji lifecycle worker. Fixture GUI memakai satu interpreter Tk dengan jendela
terpisah, sesuai satu proses aplikasi; tidak mengulang inisialisasi interpreter.

Paket hasil salinan juga lulus **120 tes (9.98 detik)** dengan warning finalizer
sebagai error. Suite OpenCode yang dipertahankan terpisah: **80 passed,1 skipped**
(8.26 detik). Verifikasi manifest memeriksa hash setiap file rilis; binary JIBAS,
compiled harness, datadir sandbox, dan token GitHub tidak masuk paket Codex.

Oracle CBE: **34skenario/46percobaan** originalimporter05C0 dan loader05BE,
semua sesuai. Snapshot instalasi13file identik. Batas runtime dijelaskan CBE.md.
Screenshot normal880x650 dan minimum760x560 tersedia di bukti/cbe; data sintetis.

Commit fitur dikerjakan pada branch codex/complete-manual-cbe-20261111,
kemudian digabung ke main melalui merge commit dan dipush. Hash akhir serta
hasil verifikasi publikasi dicatat pada PUBLISH_RESULT.json lokal.
