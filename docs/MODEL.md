# Model Card — Random Forest Risiko Klaim Pending

Dokumentasi model machine learning untuk prediksi risiko klaim Pending BPJS.

---

## 1. Ringkasan Model

| Item | Detail |
|---|---|
| **Nama** | RandomForest_Pending_Risk_PKL |
| **Jenis** | Klasifikasi biner (Pending / Claimed) |
| **Algoritma** | Random Forest (ensemble bagging) |
| **Framework** | scikit-learn 1.6.1 |
| **Tugas** | Estimasi risiko klaim berstatus *observable Pending* |
| **Output** | Skor probabilitas 0–1 |

---

## 2. Konfigurasi

```python
RandomForestClassifier(
    n_estimators=200,        # jumlah pohon
    max_depth=15,            # kedalaman maksimum
    min_samples_leaf=10,     # minimum sampel di daun
    class_weight='balanced', # bobot kelas untuk imbalance
    random_state=42,         # seed reproducibility
)
```

**Praproses** (dalam pipeline yang sama):
- Fitur numerik: `SimpleImputer(strategy='median')`
- Fitur kategorikal: `SimpleImputer(constant)` + `OrdinalEncoder`

**Hiperparameter ditetapkan manual** — tidak melalui tuning.

---

## 3. Data

| Item | Detail |
|---|---|
| **Sumber** | Klaim rawat jalan RSUD Kayen, April–Mei 2026 |
| **Total** | 7.899 klaim berlabel |
| **Fitur** | 61 (42 kategorikal + 19 numerik) |
| **Kelas** | 317 Pending (4,01%) ; 7.582 Claimed |
| **Data latih** | April, 3.870 baris (5,61% Pending) |
| **Holdout** | Mei, 4.029 baris (2,48% Pending) |
| **Skema validasi** | Temporal split (April latih → Mei uji) |

**Definisi label:** `Y=1` jika SEP teramati berstatus *Klaim Pending* pada snapshot tanggal pulang; `Y=0` jika *Klaim*. Ini **status observabel**, bukan "pernah Pending".

---

## 4. Performa (Holdout Mei, Threshold 0,50)

### Confusion Matrix
|  | Pred. Pending | Pred. Claimed |
|---|---|---|
| **Actual Pending** | TP = 44 | FN = 56 |
| **Actual Claimed** | FP = 180 | TN = 3.749 |

### Metrik
| Metrik | Nilai | Arti |
|---|---|---|
| **Recall** | 44,0% | 44 dari 100 Pending tertangkap |
| **Precision** | 19,6% | ~20% warning benar |
| **F1-Score** | 0,272 | keseimbangan precision-recall |
| **PR-AUC** | 0,2049 | 8,3× baseline acak (0,0248) |
| **ROC-AUC** | 0,8620 | kemampuan ranking |
| **Warning rate** | 5,6% | 224 dari 4.029 klaim diwarning |

### Perbandingan Latih vs Uji
| Data | PR-AUC | F1 | Prevalensi |
|---|---|---|---|
| April (CV 5-fold) | 0,243 | 0,310 | 5,61% |
| Mei (holdout) | 0,2049 | 0,272 | 2,48% |

Penurunan April→Mei konsisten dengan prevalensi Pending yang lebih rendah — menandakan model tidak overfit.

### Sensitivitas Threshold
| Threshold | Recall | Precision | Warning rate |
|---|---|---|---|
| 0,35 | 74,0% | 8,9% | 20,7% |
| 0,45 | 51,0% | 14,0% | 9,0% |
| **0,50** (dipakai) | **44,0%** | **19,6%** | **5,6%** |

---

## 5. Fitur Paling Berpengaruh (SHAP Global)

1. `bpjs_skdp_dpjp_code`
2. `obat`
3. `patient_age`
4. `prosedur_non_bedah`
5. `cbg_code`

> **Catatan:** SHAP menjelaskan **perilaku model**, bukan alasan BPJS mem-pending klaim.

---

## 6. Keterbatasan

1. **Label observabel** — status pada snapshot, bukan riwayat "pernah Pending".
2. **Tanpa label alasan Pending** — model tidak bisa menjelaskan penyebab Pending.
3. **Ruang lingkup terbatas** — hanya rawat jalan, hanya April–Mei 2026, satu rumah sakit.
4. **Precision rendah** (~80% warning false positive) → hanya untuk skrining, bukan keputusan otomatis.
5. **Skor tidak terkalibrasi** — akibat `class_weight='balanced'`, skor 0,78 **bukan** berarti peluang 78%.
6. **Kelas minoritas kecil** (317 Pending) → estimasi performa kurang stabil.
7. **Prevalensi antar bulan tidak stabil** (April 5,61% vs Mei 2,48%).
8. **Sebagian besar sinyal dari cluster Physical Therapy** (CBG M-3-16-0) — di luar cluster precision hanya ~10%.
9. **27 fitur teks klinis belum dipakai** (butuh NLP).
10. **Hiperparameter manual**, threshold default (bukan optimasi).

---

## 7. Cara Memuat Model

```python
import pickle

with open("audit/outputs/canonical_pkl_model/pipeline.pkl", "rb") as f:
    pipeline = pickle.load(f)

# Predict (61 fitur, urutan sesuai feature_names.txt)
proba = pipeline.predict_proba(X)[0, 1]
```

Model **frozen** — dimuat tanpa training ulang.

---

## 8. Etika & Data

- Data pasien (PII) tidak digunakan sebagai fitur.
- Nomor SEP hanya sebagai kunci penggabungan.
- Output **PII-safe** (tanpa nama, NIK, No.MR).
- Mengacu UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi.

---

## 9. Referensi

- Breiman, L. (2001). Random Forests.
- Kapoor & Narayanan (2023). Leakage and the reproducibility crisis.
- Lundberg & Lee (2017). SHAP.
- Saito & Rehmsmeier (2015). Precision-Recall vs ROC.
