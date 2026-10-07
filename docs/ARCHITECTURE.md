# Arsitektur Sistem

Dokumen ini menjelaskan **cara kerja sistem** secara keseluruhan.

---

## 1. Gambaran Umum

Sistem terdiri dari **dua komponen independen** yang menerima input yang sama (satu klaim) tetapi menjawab pertanyaan yang berbeda:

```
                         INPUT: 1 klaim (raw)
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
     ┌─────────────────┐            ┌──────────────────┐
     │  ML PIPELINE    │            │  RULE ENGINE     │
     │                 │            │                  │
     │ canonical_adapter            │ 9 aturan         │
     │   (feature eng.) │            │ (Permenkes 26/   │
     │        │        │            │  2021)           │
     │ pipeline.pkl    │            │        │         │
     │ (Random Forest) │            │ ICD-10 + ICD-9-CM│
     │        │        │            │   reference      │
     │ predict_proba() │            │        │         │
     └────────┬────────┘            └────────┬─────────┘
              │                              │
              ▼                              ▼
      RISK SCREENING                VALIDATION FINDINGS
      (skor 0–1 + warning)          (temuan + saran)
              │                              │
              └──────────────┬───────────────┘
                             ▼
                   DECISION SUPPORT OUTPUT
```

**Prinsip kunci:** Kedua komponen **tidak saling mempengaruhi**. Model tidak memakai hasil rule, rule tidak memakai skor model.

---

## 2. Alur Data

### 2.1 Tahap Persiapan Data (offline, sekali)

```
data-real/ (visit + claim)          ← data asli (tidak di repo)
        │
        ▼
Penggabungan visit–claim (1:1 via id)
        │
        ▼
Filter April–Mei + label dari monitoring BPJS (via bpjs_no_sep)
        │
        ▼
phase2_labeled_dataset.csv (7.899 baris, 462 kolom)
        │
        ▼
Klasifikasi eligibilitas 460 kolom (8 kategori)
        │
        ▼
Feature engineering → 61 fitur
        │
        ▼
Training Random Forest (April) → pipeline.pkl (frozen)
```

### 2.2 Tahap Inferensi (runtime)

```
Klaim baru (raw dict)
        │
        ▼
canonical_adapter.adapt_raw_to_model_features()
   → rekonstruksi 8 fitur engineered
   → cast kategorikal ke string
        │
        ▼
61-feature DataFrame
        │
        ▼
pipeline.pkl.predict_proba()  →  skor 0–1
        │
        ▼
threshold 0,50  →  WARNING (YES/NO)
```

---

## 3. Komponen

### 3.1 ML Pipeline

| Modul | File | Fungsi |
|---|---|---|
| Feature Adapter | `canonical_adapter.py` | Konversi raw klaim → 61 fitur |
| Model | `canonical_pkl_model/pipeline.pkl` | Praproses + Random Forest |
| Metadata | `canonical_pkl_model/metadata.json` | Konfigurasi & metrik |

**8 fitur yang direkonstruksi adapter:**
`visit_hour`, `visit_dayofweek`, `patient_age`, `visit_duration_min`, `has_rujukan`, `has_skdp`, `has_surat_kontrol`, `icd_chapter`

### 3.2 Rule Engine

| Modul | File | Fungsi |
|---|---|---|
| Reference Loader | `rule_engine/loaders.py` | Muat 18.543 ICD-10 + 4.366 ICD-9-CM |
| JSON Parser | `rule_engine/procedure_parser.py` | Ekstrak kode dari JSON grouper |
| Rules | `rule_engine/rules.py` | 9 fungsi aturan |
| Runner | `rule_engine/runner.py` | Kelas `RuleEngine` — evaluasi semua aturan |

### 3.3 Layer Aplikasi

| Modul | File | Fungsi |
|---|---|---|
| Prototipe CLI | `19_pkl_prototype.py` | Evaluasi + output (QA/demo/JSON) |
| JSON Serialization | `json_response.py` | Format response API |
| REST API | `api.py` | Endpoint FastAPI |

---

## 4. Detail Rule Engine

Rule engine menjalankan **9 pemeriksaan independen**. Tiap aturan:
- Mengembalikan `None` (PASS) atau `dict` (FINDING)
- Tidak bergantung pada aturan lain
- Tidak bergantung pada skor model

```python
engine = RuleEngine()
findings = engine.evaluate(claim_row)  # → list of findings (bisa kosong)
```

Setiap finding berisi: `rule_id`, `rule_name`, `category`, `severity`, `message`, `suggestion`, `source_reference`.

Detail 9 aturan: [`RULE_ENGINE.md`](RULE_ENGINE.md).

---

## 5. Alur Deployment (Prototipe)

```
Koder selesai coding + grouper dijalankan
        │
        ▼
Data klaim masuk ke prototipe
        │
        ├── ML: skor risiko → REVIEW / OK
        └── Rule: temuan validasi
        │
        ▼
Koder meninjau peringatan + temuan
        │
        ▼
Putusan: perbaiki / lanjutkan submit / konsultasi DPJP
        │
        ▼
Klaim lanjut ke proses submit BPJS yang sudah ada
```

Prototipe **tidak memblokir, menolak, atau memodifikasi** klaim.

---

## 6. Reproducibility

- **Seed tetap**: `random_state=42` di semua model
- **Model frozen**: `pipeline.pkl` dimuat via `pickle`, tidak training ulang
- **Regression test**: memastikan prototipe mereproduksi prediksi canonical
- **Test**: 30 + 11 + 9 = **50 test** otomatis
