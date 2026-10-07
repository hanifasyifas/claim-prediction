# HANDOVER — Catatan Serah Terima

Dokumen ini menjelaskan status proyek, apa yang sudah/belum selesai, dan cara melanjutkan.

---

## 1. Ringkasan Proyek

**Nama:** Sistem Skrining Risiko Klaim Pending BPJS
**Jenis:** Technical Prototype / Proof of Concept
**Pembuat:** Hanifa Syifa Safitri (PKL di CV Sahabat Mediacom, 1 Juli – 31 Agustus 2026)
**Studi kasus:** Klaim rawat jalan RSUD Kayen, April–Mei 2026

---

## 2. Status Komponen

| Komponen | Status | Lokasi |
|---|---|---|
| Dataset berlabel | ✅ Selesai | (tidak di repo — data asli) |
| Model Random Forest (frozen) | ✅ Selesai | `audit/outputs/canonical_pkl_model/pipeline.pkl` |
| Feature adapter | ✅ Selesai | `audit/scripts/canonical_adapter.py` |
| Rule engine (9 aturan) | ✅ Selesai | `audit/scripts/rule_engine/` |
| Prototipe CLI | ✅ Selesai | `audit/scripts/19_pkl_prototype.py` |
| JSON serialization | ✅ Selesai | `audit/scripts/json_response.py` |
| REST API (local) | ✅ Selesai | `audit/scripts/api.py` |
| Test suite | ✅ 50 test | `test_*.py` |

---

## 3. Yang SUDAH Selesai

- [x] Audit data & konstruksi label (7.899 klaim)
- [x] Klasifikasi eligibilitas 460 kolom → 8 kategori
- [x] Feature engineering → 61 fitur
- [x] Training Random Forest + temporal validation
- [x] Model dibekukan (`pipeline.pkl` + metadata)
- [x] Analisis SHAP (global) + error analysis
- [x] Audit rule engine (20 kandidat → 9 otomatis)
- [x] Implementasi + 30 unit test rule engine
- [x] Prototipe CLI (mode QA/demo/JSON)
- [x] Local REST API + 9 test
- [x] Regression test (reproduksi canonical) — ALL PASS

---

## 4. Yang BELUM Selesai (Rekomendasi Lanjutan)

| # | Item | Keterangan |
|---|---|---|
| 1 | **Integrasi API produksi** | Menunggu konfirmasi format request/response dari SIMRS |
| 2 | **Per-claim SHAP explanation** | Saat ini baru analisis SHAP global; belum diintegrasikan per-klaim ke API |
| 3 | **6 aturan review-flag (D03–D08)** | Butuh approval domain expert/koder |
| 4 | **UI/Dashboard** | Saat ini hanya CLI |
| 5 | **NLP fitur teks klinis (27 kolom)** | Belum diproses |
| 6 | **Perluasan data** | Periode lebih panjang + Rehabilitasi Medik |

---

## 5. Cara Menjalankan

```bash
# Instalasi
pip install -r requirements.txt

# Prototipe CLI (demo)
python audit\scripts\19_pkl_prototype.py --mode demo

# Prototipe CLI (QA/regression test)
python audit\scripts\19_pkl_prototype.py --mode qa

# API
cd audit\scripts
python -m uvicorn api:app --reload --port 8000
# → http://127.0.0.1:8000/docs

# Test
python audit\scripts\test_rule_engine.py
python audit\scripts\test_json_response.py
python audit\scripts\test_api.py
```

---

## 6. Cara Memperluas

### Menambah aturan rule engine
1. Tambahkan fungsi di `rule_engine/rules.py` (pola: return `None` jika PASS, `dict` jika FINDING).
2. Daftarkan di `ALL_RULES`.
3. Panggil di `runner.py`.
4. Tambahkan unit test di `test_rule_engine.py`.
5. Pastikan aturan punya `source_reference` (traceability).

### Melatih ulang model
1. Siapkan dataset berlabel (`phase2_labeled_dataset.csv`).
2. Jalankan ulang script freeze (`14_freeze_canonical_model.py`).
3. Verifikasi regression test (`--mode qa`).
> **Catatan:** melatih ulang memerlukan data asli (tidak disertakan di repo).

### Mengubah format API
- Edit `json_response.py` (bentuk response) dan `api.py` (endpoint).
- Model & rule engine **tidak perlu diubah**.

---

## 7. Peringatan Data (PENTING)

⚠️ **Data pasien asli tidak disertakan di repository.**

- Folder `data-real/` dan `data-pendukung/` di-*exclude* via `.gitignore`.
- Dataset turunan (`phase2_labeled_dataset.csv`) juga tidak disertakan (mengandung identifier).
- Untuk melatih ulang atau evaluasi, diperlukan akses ke data asli via rumah sakit.

Penggunaan data mengacu pada **UU No. 27 Tahun 2022** tentang Pelindungan Data Pribadi.

---

## 8. Keterbatasan yang Perlu Diketahui Pengembang Berikutnya

1. Label = status observabel (snapshot tanggal pulang), **bukan** riwayat "pernah Pending".
2. **Tidak ada label alasan Pending** → sistem tidak bisa menjelaskan "kenapa" Pending.
3. Precision rendah (~19,6%) → hanya layak sebagai **alat bantu skrining**.
4. Model tidak terkalibrasi (akibat class weighting).
5. Skor model = hasil pola **korelasi**, **bukan** sebab-akibat.
6. SHAP menjelaskan perilaku model, bukan alasan BPJS.
7. Rule engine memvalidasi koding, **bukan** memprediksi Pending.

---

## 9. Referensi Dokumentasi

| Dokumen | Isi |
|---|---|
| `README.md` | Overview & quick start |
| `docs/ARCHITECTURE.md` | Cara kerja sistem |
| `docs/API.md` | Dokumentasi API |
| `docs/MODEL.md` | Model card |
| `docs/RULE_ENGINE.md` | 9 aturan validasi |
| `docs/DATA_DICTIONARY.md` | Definisi fitur |
| `docs/METHODOLOGY.md` | Alur CRISP-DM |

---
