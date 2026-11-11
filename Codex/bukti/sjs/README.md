# Bukti SJS 7.10

Lihat [laporan produk](../../../SharedDocs/products/sjs.md). Semua fixture berisi data sintetis. Binary live, config, cache dan database tidak diubah.

- `rea_summaries.json`: Evidence REA untuk inventory, metadata build, dan anggota dari empat tipe relevan.
- `focused_il.txt`: IL reflection-only terpilih; komentar string hasil decoder dipasang untuk membantu pembacaan, bukan pseudocode hasil eksekusi.
- `format.json`: output initializer/skema asli, tanpa baca konfigurasi atau lisensi pengguna.
- `token_oracle.json`: statistik sintetis lewat encoder/decoder asli yang murni; bukan token DB pengguna.
- `smoke_fixture.json`: parameter sintetis lengkap untuk Save All/frozen smoke. School ID tersebut hanya identitas contoh, bukan alokasi online.
- `oracle_matrix.json`: hasil final 11 kontrol importer asli dan hash before/after instalasi.
- `SjsStaticProbe.cs`: IL reader reflection-only. Kompilasi ke folder temporer, berikan path JsSync.exe dan token metode, misalnya `0x06000EBA`.
- `IntSites.cs`, `VmOracle.cs`, `sjs_il.ps1`: alat eksplorasi string/IL. Decoder hanya memuat resource; `VmOracle` melakukan warm melalui getter path `0x06000EB2`, bukan Main.
- `SjsFormatProbe.cs`: menjalankan hanya getter path, initializer format dan pembuat skema dalam folder temporer.
- `SjsImportProbe.cs`, `run_oracle.py`: runner final. `python bukti/sjs/run_oracle.py` mengompilasi ke temp dan menjalankan matriks tanpa server, DB atau network.

Jangan meluncurkan `JsSync.exe` Main sebagai oracle. Getter DB ID dapat bootstrap routine DB; bukan bagian runner ini. Token yang sama secara sengaja dipakai pada tiga DB ID untuk membuktikan token bukan kolom/binding importer. Nilai DB/waktu disuplai ke field memori, sehingga hasil tidak menyatakan identitas atau status DB sebenarnya.
