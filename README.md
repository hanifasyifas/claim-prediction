# Sistem Skrining Risiko Klaim Pending BPJS

**Technical Prototype / Proof of Concept**
Machine Learning (Random Forest) + Validasi Aturan Koding INA-CBG
Studi Kasus: Klaim Rawat Jalan RSUD Kayen | April–Mei 2026

---

## Ringkasan

Sistem **decision-support** yang berjalan **sebelum klaim dikirim ke BPJS e-Claim**. Sistem menerima data klaim rawat jalan (setelah coding ICD-10/ICD-9-CM dan INA-CBG grouping), lalu menghasilkan dua keluaran yang **terpisah**:

| Komponen | Keluaran | Sumber |
|---|---|---|
| **Model ML (Random Forest)** | Skor risiko Pending (0–1) + status warning | Pola historis 7.899 klaim |
| **Rule Engine** | Temuan validasi koding (PASS/FINDING) | Permenkes No. 26 Tahun 2021 |

> **Penting:** Sistem ini **alat bantu**, bukan pengambil keputusan otomatis. Ia tidak memblokir, menolak, atau memodifikasi klaim. Model ML dan rule engine bekerja **independen** — tidak saling memengaruhi.

---

## Fitur Utama

- **Prediksi risiko Pending** dengan Random Forest (61 fitur, class weighting untuk data tidak seimbang)
- **Validasi koding INA-CBG** dengan 9 aturan berbasis Permenkes 26/2021 (traceable ke pasal sumber)
- **Prototipe CLI** dengan mode QA (regression test) dan demo (presentasi)
- **Local REST API** (FastAPI) untuk integrasi
- **Reproducible**: model dibekukan (frozen), tidak perlu training ulang

---

## Struktur Folder

```
claim-prediction-pkl/
├── README.md                       ← dokumen ini
├── HANDOVER.md                     ← catatan serah terima
├── requirements.txt                ← dependency Python
├── .gitignore
├── docs/                           ← dokumentasi lengkap
│   ├── ARCHITECTURE.md             ← cara kerja sistem
│   ├── API.md                      ← cara pakai API
│   ├── MODEL.md                    ← model card
│   ├── RULE_ENGINE.md              ← 9 aturan validasi
│   ├── DATA_DICTIONARY.md          ← definisi 61 fitur
│   └── METHODOLOGY.md              ← alur CRISP-DM
├── audit/
│   ├── scripts/                    ← kode sumber
│   │   ├── 19_pkl_prototype.py     ← prototipe CLI
│   │   ├── api.py                  ← FastAPI
│   │   ├── json_response.py        ← JSON serialization
│   │   ├── canonical_adapter.py    ← feature adapter
│   │   ├── rule_engine/            ← modul rule engine
│   │   ├── test_rule_engine.py     ← 30 unit test
│   │   ├── test_json_response.py   ← 11 test
│   │   └── test_api.py             ← 9 test
│   ├── outputs/
│   │   └── canonical_pkl_model/    ← model beku
│   │       ├── pipeline.pkl
│   │       ├── metadata.json
│   │       ├── feature_names.txt
│   │       └── feature_lists.json
│   └── reference_data/             ← data referensi (disertakan)
│       ├── icd10_master.xlsx       ← 18.543 kode ICD-10
│       ├── icd9cm_master.xlsx      ← 4.366 kode ICD-9-CM
│       └── sample_claims.csv       ← 30 klaim contoh (de-identifikasi)
```

> **Portabilitas:** seluruh path dihitung **relatif** terhadap lokasi file, sehingga repo dapat di-*clone* dan dijalankan di mesin mana pun tanpa konfigurasi path.
>
> **Catatan data:** Folder `data-real/` dan `data-pendukung/` **tidak disertakan** karena mengandung data pasien asli (PII). Sebagai gantinya, `audit/reference_data/sample_claims.csv` menyediakan 30 klaim contoh (tanpa PII) untuk keperluan demo.

---

## Instalasi

**Prasyarat:** Python 3.12+

```bash
# 1. Clone repository
git clone <url-repo>
cd claim-prediction-pkl

# 2. (Disarankan) buat virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# 3. Install dependency
pip install -r requirements.txt
```

---

## Cara Penggunaan

### A. Prototipe CLI

**Mode demo** (presentasi — 4 klaim contoh TP/FP/FN/TN):
```bash
python audit\scripts\19_pkl_prototype.py --mode demo
```

**Mode QA** (regression test — bukti reproduksibilitas):
```bash
python audit\scripts\19_pkl_prototype.py --mode qa
```

**Klaim tertentu:**
```bash
python audit\scripts\19_pkl_prototype.py --mode demo --demo-id 719069
```

**Output JSON:**
```bash
python audit\scripts\19_pkl_prototype.py --mode demo --format json --demo-id 719069
```

### B. REST API (FastAPI)

```bash
cd audit\scripts
python -m uvicorn api:app --reload --port 8000
```

- Swagger UI: `http://127.0.0.1:8000/docs`
- Detail lengkap: [`docs/API.md`](docs/API.md)

### C. Menjalankan Test

```bash
python audit\scripts\test_rule_engine.py      # 30 test
python audit\scripts\test_json_response.py    # 11 test
python audit\scripts\test_api.py              # 9 test
```

---

## Performa Model (Holdout Mei, Threshold 0,50)

| Metrik | Nilai |
|---|---|
| Recall (Pending) | 44,0% |
| Precision (Pending) | 19,6% |
| F1-Score | 0,272 |
| PR-AUC | 0,2049 (8,3× baseline acak) |
| ROC-AUC | 0,8620 |
| Warning rate | 5,6% |

**Fitur:** 61 (42 kategorikal + 19 numerik) | **Data latih:** April (3.870) | **Holdout:** Mei (4.029)

---

## Keterbatasan (WAJIB DIBACA)

1. **Label adalah status observabel** pada snapshot tanggal pulang, bukan "pernah Pending".
2. **Tidak ada label alasan Pending** dari BPJS — model tidak bisa menjelaskan "kenapa" Pending.
3. **Hanya rawat jalan**, hanya April–Mei 2026, satu rumah sakit.
4. **Precision rendah** (~80% warning adalah false positive) → hanya layak sebagai skrining.
5. **Data tidak seimbang** (Pending hanya 4,01%) → model memakai class weighting; skor tidak terkalibrasi.
6. **Klinik Rehabilitasi Medik** tidak terwakili sepenuhnya.
7. **Rule engine** memvalidasi kepatuhan koding, **bukan** memprediksi Pending dan **bukan** alasan BPJS.

Detail lengkap: [`docs/MODEL.md`](docs/MODEL.md) dan [`HANDOVER.md`](HANDOVER.md).

---

## Dokumentasi Lengkap

| Dokumen | Isi |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Cara kerja sistem, komponen, alur data |
| [`docs/API.md`](docs/API.md) | Endpoint, request/response, contoh |
| [`docs/MODEL.md`](docs/MODEL.md) | Model card (config, performa, limitasi) |
| [`docs/RULE_ENGINE.md`](docs/RULE_ENGINE.md) | 9 aturan validasi + sumber Permenkes |
| [`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md) | Definisi 61 fitur |
| [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) | Alur CRISP-DM |
| [`HANDOVER.md`](HANDOVER.md) | Status, yang belum selesai, cara extend |

---

## Teknologi

Python 3.12 · scikit-learn 1.6.1 · pandas 2.2.3 · FastAPI 0.141.1 · SHAP 0.52.0

---

## Lisensi & Data

Kode dalam repositori ini bersifat internal. **Data pasien tidak disertakan.** Penggunaan data mengacu pada UU No. 27 Tahun 2022 tentang Perlindungan Data Pribadi.
