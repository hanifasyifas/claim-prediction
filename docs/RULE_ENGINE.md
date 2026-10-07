# Rule Engine — Validasi Koding INA-CBG

Komponen validasi **deterministik** berbasis **Permenkes RI No. 26 Tahun 2021**.

---

## 1. Konsep

Rule engine menjalankan **9 pemeriksaan independen** pada satu klaim. Tiap pemeriksaan:
- Mengecek **satu aspek** klaim
- Mengembalikan **PASS** (tidak ada masalah) atau **FINDING** (perlu review)
- **Tidak** saling bergantung
- **Tidak** bergantung pada skor model ML

> Rule engine **tidak memprediksi** Pending. Ia memvalidasi **kepatuhan koding**.

---

## 2. Cara Kerja

```
Klaim (raw)
      │
      ├── D01: cek diagnosis
      ├── D02: cek validitas ICD-10
      ├── C01: cek CBG ada
      ├── C03: cek format CBG
      ├── C04: cek digit rawat jalan
      ├── C05: cek severity
      ├── P01: cek konsistensi prosedur
      ├── A01: cek tanggal SEP
      └── A02: cek konsistensi tanggal
      │
      ▼
Daftar temuan (0–9 item) + saran
```

---

## 3. Sembilan Aturan

### Kelompok D — Diagnosis

| Kode | Cek | Kondisi FINDING | Field | Severity | Sumber |
|---|---|---|---|---|---|
| **D01** | Diagnosis tidak kosong | Field primer kosong; **INFO** jika ada di grouper, **WARNING** jika tidak ada di mana pun | `bpjs_diagnosa_awal_code`, respons grouper | INFO/WARNING | Permenkes §3 |
| **D02** | Kode ICD-10 valid | Kode tidak ada di 18.543 kode master | `bpjs_diagnosa_awal_code` | WARNING | Master ICD-10 |

### Kelompok C — CBG / Grouper

| Kode | Cek | Kondisi FINDING | Field | Severity | Sumber |
|---|---|---|---|---|---|
| **C01** | CBG tidak kosong | `cbg_code` kosong | `cbg_code` | WARNING | Permenkes §1 |
| **C03** | Format CBG valid | Format ≠ `[A-Z]-[0-9]-[0-9]{2}-[0/I/II/III]` | `cbg_code` | WARNING | Permenkes §1 |
| **C04** | Digit-2 rawat jalan | Digit ke-2 ∉ {2,3,5,7,9} | `cbg_code` | HIGH | Permenkes §1.1 |
| **C05** | Severity 0 rawat jalan | Digit ke-4 ≠ "0" | `cbg_code` | HIGH | Permenkes §1.2 |

### Kelompok P — Prosedur

| Kode | Cek | Kondisi FINDING | Field | Severity | Sumber |
|---|---|---|---|---|---|
| **P01** | CBG prosedural butuh kode prosedur | Digit-2 ∈ {2,3} tanpa kode ICD-9-CM (**HIGH**); kode tidak valid (**WARNING**) | `cbg_code`, JSON grouper | HIGH/WARNING | Permenkes §2 |

### Kelompok A — Administratif

| Kode | Cek | Kondisi FINDING | Field | Severity | Sumber |
|---|---|---|---|---|---|
| **A01** | Tanggal SEP ada | `bpjs_tgl_sep` kosong | `bpjs_tgl_sep` | WARNING | Ketentuan SEP |
| **A02** | Tanggal pulang ≥ kunjungan | `exit_date < date` | `date`, `exit_date` | HIGH | Permenkes §8.1 |

---

## 4. Hasil pada 7.899 Klaim

| Kode | Finding | Review rate | Catatan |
|---|---|---|---|
| D01 | 3.172 | 40,2% | Semua severity INFO |
| D02 | 3 | 0,04% | |
| C01 | 0 | 0% | |
| C03 | 0 | 0% | |
| C04 | 0 | 0% | |
| C05 | 0 | 0% | |
| P01 | 2 | 0,03% | |
| A01 | 3 | 0,04% | |
| A02 | 0 | 0% | |

**59,8% klaim tanpa temuan sama sekali.**

### Temuan D01 (Sanity Check)
Seluruh 3.172 temuan D01 (40,2%) adalah **INFO** — artinya field primer kosong **tapi diagnosis ada di grouper response**. Ini isu *field-mapping* SIMRS, **bukan** diagnosis yang hilang. Karena itu severity diturunkan dari WARNING → INFO.

---

## 5. Klasifikasi Aturan (dari 20 Kandidat)

| Kategori | Jumlah | Aturan |
|---|---|---|
| **VERIFIED_AUTOMATABLE** (diimplementasikan) | 9 | D01, D02, C01, C03, C04, C05, P01, A01, A02 |
| **VERIFIED_REVIEW_FLAG** (ditahan) | 6 | D03–D08 |
| Perlu konfirmasi domain | 5 | A03, R01, R02, C02, M02 |

---

## 6. Struktur Finding

```json
{
  "rule_id": "D01",
  "rule_name": "Diagnosis code not in primary field",
  "category": "STRUCTURAL_COMPLETENESS",
  "severity": "INFO",
  "status": "REVIEW",
  "observed_value": "primary=<null> grouper=['M75.1']",
  "message": "...",
  "suggestion": "...",
  "source_reference": "Permenkes 26/2021 §3"
}
```

Field `source_reference` menjadikan tiap temuan **traceable** ke pasal regulasi.

---

## 7. Modul Implementasi

| File | Fungsi |
|---|---|
| `rule_engine/loaders.py` | Muat referensi ICD-10 & ICD-9-CM |
| `rule_engine/procedure_parser.py` | Parse kode prosedur dari JSON grouper |
| `rule_engine/rules.py` | 9 fungsi aturan |
| `rule_engine/runner.py` | Kelas `RuleEngine` |

### Penggunaan
```python
from rule_engine.runner import RuleEngine

engine = RuleEngine()
findings = engine.evaluate(claim_row)  # list of findings
```

---

## 8. Pengujian

**30 unit test** PASS, mencakup:
- Kondisi valid
- Nilai kosong
- Format rusak (malformed JSON)
- Nilai batas (boundary)

---

## 9. Batasan

- Rule engine **tidak memprediksi** Pending.
- **Tidak ada ground truth** validasi (tidak ada label alasan Pending BPJS).
- 6 aturan review-flag belum diimplementasikan (butuh judgment koder).
- Temuan **bukan** penyebab Pending — ini murni validasi kepatuhan koding.
