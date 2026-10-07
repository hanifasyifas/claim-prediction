# Metodologi — CRISP-DM

Proyek mengikuti kerangka **CRISP-DM** (*Cross-Industry Standard Process for Data Mining*) dengan **dua jalur pengembangan** yang berjalan independen dan bertemu di tahap Deployment.

---

## Alur Dua Jalur

```
        Business Understanding
                 │
        Data Understanding
                 │
        Data Preparation
         (7.899 klaim, 61 fitur)
                 │
        ┌────────┴─────────┐
        ▼                  ▼
   JALUR ML          JALUR RULE ENGINE
   - Training RF     - Audit 20 kandidat aturan
   - class_weight    - Validasi ke Permenkes
   - Temporal split  - Implementasi 9 aturan
        │                  │
        └────────┬─────────┘
                 ▼
            Evaluation
                 ▼
            Deployment
          (Prototipe CLI)
```

---

## 1. Business Understanding

**Masalah:** Rumah sakit baru mengetahui klaim Pending **setelah** dikirim ke BPJS — terlambat, berdampak pada arus kas.

**Tujuan:**
1. Klasifikasi risiko Pending (skor per klaim) → prioritas review
2. Validasi kepatuhan koding INA-CBG (Permenkes 26/2021)

**Titik intervensi (prediction timestamp):** setelah coding + grouping, **sebelum** kirim ke BPJS.

**Keputusan pembatas:**
- Label hanya status observabel → tidak mengklaim alasan Pending
- Pending 4,01% → pakai class weighting, metrik PR-AUC (bukan akurasi)
- Hanya rawat jalan, April–Mei 2026, satu rumah sakit

---

## 2. Data Understanding

**Sumber:**
| Sumber | Isi |
|---|---|
| Tabel visit | Data kunjungan (demografi, vital signs, triase, biaya) |
| Tabel claim | Hasil grouping INA-CBG, tarif CBG, JSON grouper |
| Monitoring BPJS | Status klaim per SEP (107 file) |
| Referensi | Permenkes 26/2021, ICD-10 (18.543), ICD-9-CM (4.366) |

**Kunci join:** `id` = `visit_id` (visit↔claim) ; `bpjs_no_sep` = `SEP` (visit↔monitoring).

**Konstruksi label:** `Y=1` jika SEP berstatus *Klaim Pending*, `Y=0` jika *Klaim*.

**Masalah kualitas data:** Maret tak berlabel, SEP placeholder, label orphan, SEP ganda.

---

## 3. Data Preparation

1. Gabung visit–claim (1:1) via `visit_id`
2. Filter April–Mei, label via `bpjs_no_sep`
3. Tangani 4 SEP ganda → simpan baris terlengkap
4. Klasifikasi eligibilitas 460 kolom → 8 kategori
5. Feature engineering → **61 fitur**
6. Eliminasi 18 kolom leakage pasca-BPJS

**Dataset final:** 7.899 baris × 462 kolom (460 fitur + label + target).

---

## 4. Modeling

### Jalur ML
- **Algoritma:** Random Forest (`n_estimators=200, max_depth=15, min_samples_leaf=10, class_weight='balanced', random_state=42`)
- **Validasi:** temporal split (April latih dengan stratified 5-fold CV → Mei holdout)
- **Imbalance:** class weighting (hanya pada data latih)
- Model di-*freeze* → `pipeline.pkl`

### Jalur Rule Engine
- Audit 20 kandidat aturan (2 tahap)
- Validasi ke Permenkes 26/2021 + master ICD
- Implementasi 9 aturan VERIFIED_AUTOMATABLE
- 30 unit test

---

## 5. Evaluation

### ML (Holdout Mei, threshold 0,50)
Perbandingan class weighting:

| Konfigurasi | TP | FP | Precision | Recall | Warning rate |
|---|---|---|---|---|---|
| Tanpa class weighting | 0 | 0 | 0 | 0% | 0% |
| **Dengan class_weight='balanced'** | **44** | **180** | **0,196** | **0,440** | **5,6%** |

Metrik final: PR-AUC 0,2049 | ROC-AUC 0,8620 | F1 0,272. Sensitivitas threshold diuji pada 0,35 / 0,45 / 0,50.

### Rule Engine
9 aturan dijalankan → review rate didominasi D01 (40,2%, severity INFO).

---

## 6. Deployment

Prototipe teknis **CLI** dengan dua mode (QA, demo) + **local REST API**.

```
Koder selesai coding + grouping
        │
        ▼
Prototipe menerima data klaim
        │
        ├── ML: skor risiko → REVIEW/OK
        └── Rule: temuan validasi
        │
        ▼
Koder meninjau → putusan
        │
        ▼
Klaim lanjut ke submit BPJS
```

Prototipe tidak memblokir/menolak/modifikasi klaim.

---

## Keputusan Metodologis Penting

| Keputusan | Alasan |
|---|---|
| Prediction timestamp setelah grouping | Informasi coding & grouper sudah tersedia; mencegah leakage |
| Fitur eligible: `cbg_code`, `cbg_tarif` | Output grouper internal, tersedia pra-submission |
| Metrik PR-AUC sebagai utama | Data tidak seimbang; akurasi menipu |
| Temporal split | Meniru kondisi nyata (latih masa lalu → prediksi masa depan) |
| class weighting | Menangani imbalance tanpa modifikasi data uji |
| Rule engine tidak dari SHAP | SHAP = korelasi; rule harus dari regulasi |

---

## Referensi

- Wirth & Hipp (2000). CRISP-DM.
- Breiman (2001). Random Forests.
- Saito & Rehmsmeier (2015). PR vs ROC.
- Kapoor & Narayanan (2023). Data leakage.
