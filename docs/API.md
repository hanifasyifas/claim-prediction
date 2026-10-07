# Dokumentasi API

Local REST API untuk skrining risiko klaim Pending BPJS. Dibuat dengan **FastAPI**.

> **Status:** Local prototype. Dapat diperluas untuk integrasi SIMRS setelah kontrak request/response final disepakati.

---

## Menjalankan Server

```bash
cd audit/scripts
python -m uvicorn api:app --reload --port 8000
```

- Base URL: `http://127.0.0.1:8000`
- **Swagger UI (interaktif):** `http://127.0.0.1:8000/docs`
- **ReDoc:** `http://127.0.0.1:8000/redoc`

---

## Endpoints

### 1. `GET /health`

Cek status server & model.

**Response:**
```json
{
  "status": "ok",
  "model": "RandomForest_Pending_Risk_PKL",
  "features": 61,
  "rules": 9,
  "threshold": 0.5
}
```

---

### 2. `POST /screen`

Skrining **satu klaim**. Terima `claim_id` (lookup) ATAU `claim_data` (data mentah).

**Request body (opsi A — by claim_id):**
```json
{
  "claim_id": 719069
}
```

**Request body (opsi B — data mentah):**
```json
{
  "claim_data": {
    "date": "2026-05-19 08:00:00",
    "exit_date": "2026-05-19 10:00:00",
    "cbg_code": "M-3-16-0",
    "bpjs_diagnosa_awal_code": "M75.1",
    "bpjs_tgl_sep": "2026-05-19",
    "...": "..."
  }
}
```

**Response (200 OK):**
```json
{
  "schema_version": "1.0",
  "claim_id": 719069,
  "prediction": {
    "pending_risk": 0.782,
    "threshold": 0.5,
    "warning": true,
    "recommendation": "REVIEW"
  },
  "validation": {
    "total_findings": 1,
    "findings": [
      {
        "rule_id": "D01",
        "rule_name": "Diagnosis code not in primary field",
        "category": "STRUCTURAL_COMPLETENESS",
        "severity": "INFO",
        "status": "REVIEW",
        "observed_value": "primary=<null> grouper=['M75.1']",
        "message": "Kode diagnosis primer tidak terisi di field bpjs_diagnosa_awal_code...",
        "suggestion": "Kode diagnosis sudah tersedia di grouper...",
        "source_reference": "Permenkes 26/2021 §3"
      }
    ]
  },
  "meta": {
    "model": "RandomForest_Pending_Risk_PKL",
    "component": "technical_prototype",
    "disclaimer": "Screening only. This output estimates observable Pending risk..."
  }
}
```

**Error:**
| Status | Kondisi |
|---|---|
| `400` | Tidak ada `claim_id` maupun `claim_data` |
| `404` | `claim_id` tidak ditemukan |
| `500` | Gagal inference |

---

### 3. `POST /screen/batch`

Skrining **banyak klaim** sekaligus.

**Request body:**
```json
{
  "claim_ids": [719069, 719215, 719071]
}
```

**Response:**
```json
{
  "schema_version": "1.0",
  "count": 3,
  "results": [ { "...": "..." }, { "...": "..." }, { "...": "..." } ],
  "not_found": []
}
```

Jika ada ID yang tidak ditemukan, dikembalikan di array `not_found`.

---

## Skema Response

| Field | Tipe | Keterangan |
|---|---|---|
| `schema_version` | string | Versi kontrak (saat ini `"1.0"`) |
| `claim_id` | int | ID kunjungan internal |
| `prediction.pending_risk` | float | Skor risiko 0–1 |
| `prediction.threshold` | float | Threshold (0,50) |
| `prediction.warning` | bool | `true` jika skor ≥ threshold |
| `prediction.recommendation` | string | `"REVIEW"` atau `"OK"` |
| `validation.total_findings` | int | Jumlah temuan |
| `validation.findings[]` | array | Daftar temuan rule engine |
| `meta` | object | Model, komponen, disclaimer |

### Severity Finding

| Nilai | Arti |
|---|---|
| `INFO` | Ringan (catatan) |
| `WARNING` | Perlu diperhatikan |
| `HIGH` | Serius |

---

## Contoh dengan `curl`

```bash
# Health check
curl http://127.0.0.1:8000/health

# Screen satu klaim
curl -X POST http://127.0.0.1:8000/screen \
  -H "Content-Type: application/json" \
  -d "{\"claim_id\": 719069}"

# Batch
curl -X POST http://127.0.0.1:8000/screen/batch \
  -H "Content-Type: application/json" \
  -d "{\"claim_ids\": [719069, 719215]}"
```

## Contoh dengan Python

```python
import requests

resp = requests.post(
    "http://127.0.0.1:8000/screen",
    json={"claim_id": 719069},
)
data = resp.json()
print(data["prediction"]["pending_risk"])  # 0.782
print(data["prediction"]["warning"])       # True
```

---

## Catatan Integrasi

- **Response format** dapat diubah dengan mengedit `json_response.py` dan `api.py` — model & rules **tidak perlu diubah**.
- **Arsitektur bersifat thin layer**: `api.py` hanya membungkus `canonical_adapter` + `pipeline.pkl` + `rule_engine`.
- **PII-safe**: response tidak menyertakan nama, NIK, No.MR, atau SEP.
- **Tidak menyertakan label target historis** (itu hanya untuk QA/demo).
