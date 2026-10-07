# Data Dictionary — 61 Fitur Model

Definisi setiap fitur yang digunakan model. Terdiri atas **42 kategorikal** + **19 numerik**.

> Fitur bertanda (†) adalah fitur turunan hasil *feature engineering*.

---

## Fitur Kategorikal (42)

| No | Fitur | Deskripsi |
| :---: | ----- | ----- |
| 1 | `clinic_id` | Klinik/poliklinik tempat pasien menerima layanan |
| 2 | `continue_id` | Kode jenis kelanjutan kunjungan |
| 3 | `admission_type_id` | Tipe kedatangan/admisi pasien |
| 4 | `pengirim_jenis_id` | Kode jenis pengirim atau asal rujukan |
| 5 | `jenis_kunjungan` | Jenis kunjungan (L = lama/berulang, B = baru) |
| 6 | `triage_esi` | Tingkat kegawatan (*Emergency Severity Index*, 1–5) |
| 7 | `triage_morse_step` | Langkah penilaian risiko jatuh (*Morse Fall Scale*) |
| 8 | `triage_morse_result` | Hasil skor risiko jatuh Morse |
| 9 | `triage_humpty_dumpty_step` | Skor risiko jatuh pasien anak (*Humpty Dumpty*) |
| 10 | `triage_sydney_scoring_step` | Skor triase Sydney |
| 11 | `resiko_jatuh_gugo_a` | Komponen A penilaian risiko jatuh |
| 12 | `resiko_jatuh_gugo_b` | Komponen B penilaian risiko jatuh |
| 13 | `resiko_jatuh_model` | Model penilaian risiko jatuh yang digunakan |
| 14 | `psikososial_versi_1` | Hasil penilaian psikososial pasien |
| 15 | `skala_nyeri` | Skala intensitas nyeri (0–10) |
| 16 | `ada_alergi_obat` | Indikator alergi obat (1/0) |
| 17 | `ada_alergi_makanan` | Indikator alergi makanan (1/0) |
| 18 | `bpjs_tujuan_kunjungan` | Tujuan kunjungan menurut data BPJS |
| 19 | `bpjs_asal_rujukan` | Asal rujukan peserta BPJS |
| 20 | `bpjs_jenis_peserta_code` | Kode jenis peserta BPJS (PBI/non-PBI) |
| 21 | `bpjs_kelas_tanggungan_code` | Kode kelas tanggungan (1/2/3) |
| 22 | `bpjs_pisa` | Kode segmen peserta BPJS (PISA) |
| 23 | `bpjs_provider_code` | Kode fasilitas kesehatan penyedia |
| 24 | `bpjs_sex` | Jenis kelamin (L/P) |
| 25 | `bpjs_skdp_dpjp_code` | Kode DPJP pada SKDP |
| 26 | `cbg_code` | Kode INA-CBG hasil *grouping* |
| 27 | `idrg_code` | Kode kelompok iDRG |
| 28 | `idrg_mdc_number` | Nomor *Major Diagnostic Category* (MDC) |
| 29 | `prosedur_bedah` | Komponen biaya prosedur bedah (kategorikal) |
| 30 | `konsultasi` | Komponen biaya konsultasi |
| 31 | `penunjang` | Komponen biaya penunjang |
| 32 | `radiologi` | Komponen biaya radiologi |
| 33 | `pelayanan_darah` | Komponen biaya pelayanan darah |
| 34 | `rehabilitasi` | Komponen biaya rehabilitasi |
| 35 | `antrian_cara_masuk` | Cara masuk antrian layanan |
| 36 | `covid19_data` | Data terkait COVID-19 |
| 37 | `fpo_text` | Kode/teks FPO (Formulir Pengajuan Obat) |
| 38 | `has_rujukan` † | Indikator keberadaan nomor rujukan (1/0) |
| 39 | `has_skdp` † | Indikator keberadaan SKDP (1/0) |
| 40 | `has_surat_kontrol` † | Indikator keberadaan surat kontrol (1/0) |
| 41 | `icd_chapter` † | Bab ICD-10 dari kode diagnosis (22 bab) |
| 42 | `visit_dayofweek` † | Hari kunjungan (0=Senin … 6=Minggu) |

---

## Fitur Numerik (19)

| No | Fitur | Deskripsi |
| :---: | ----- | ----- |
| 1 | `sistole` | Tekanan darah sistolik (mmHg) |
| 2 | `diastole` | Tekanan darah diastolik (mmHg) |
| 3 | `weight` | Berat badan (kg) |
| 4 | `heart_rate` | Denyut jantung (kali/menit) |
| 5 | `respiration_rate` | Laju pernapasan (kali/menit) |
| 6 | `temperature` | Suhu tubuh (°C) |
| 7 | `spo2` | Saturasi oksigen (%) |
| 8 | `tarif_rs_visit` | Tarif rumah sakit dari data kunjungan (Rp) |
| 9 | `tarif_rs_claim` | Tarif rumah sakit dari data klaim (Rp) |
| 10 | `prosedur_non_bedah` | Biaya prosedur non-bedah (Rp) |
| 11 | `laboratorium` | Biaya pemeriksaan laboratorium (Rp) |
| 12 | `obat` | Biaya obat (Rp) |
| 13 | `cbg_tarif` | Tarif CBG hasil *grouping* (Rp) |
| 14 | `visit_hour` † | Jam kunjungan (0–23) |
| 15 | `patient_age` † | Usia pasien (tahun) |
| 16 | `visit_duration_min` † | Durasi kunjungan (menit) |
| 17 | `job_id` | Kode pekerjaan (diperlakukan numerik) |
| 18 | `education_id` | Kode pendidikan (diperlakukan numerik) |
| 19 | `family_relationship_id` | Kode hubungan keluarga penanggung jawab (diperlakukan numerik) |

---

## Fitur yang Dikecualikan

| Kategori | Jumlah | Alasan |
|---|---|---|
| Kebocoran data (*POST_BPJS_LEAKAGE*) | 18 | Baru tersedia setelah klaim dikirim ke BPJS |
| Identitas pasien (PII) | 17 | Privasi |
| Pengenal sistem | 19 | Bukan ciri klinis |
| Kosong/konstan | 256 | Tidak ada variasi |
| Perlu review domain | 7 | Makna belum jelas |
| Catatan klinis teks bebas | 27 | Butuh NLP |

---

## Keterangan Singkatan

| Singkatan | Arti |
| ----- | ----- |
| INA-CBG | *Indonesia Case Base Groups* |
| iDRG | *Indonesian Diagnosis Related Group* |
| MDC | *Major Diagnostic Category* |
| DPJP | Dokter Penanggung Jawab Pelayanan |
| SKDP | Surat Kontrol Dokter Pelaksana |
| SEP | Surat Eligibilitas Peserta |
| ESI | *Emergency Severity Index* |
| SpO₂ | Saturasi oksigen |
| PBI | Penerima Bantuan Iuran |
| FPO | Formulir Pengajuan Obat |
