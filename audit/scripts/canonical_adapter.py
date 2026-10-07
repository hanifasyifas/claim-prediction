"""
Canonical Feature Adapter — one deterministic implementation.
Converts raw claim row → 61 engineered features expected by frozen pipeline.
Exact replica of Phase 3 feature engineering (11_phase3_baselines_v2.py).
"""
import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict

# --- Path relatif (portabel di mesin mana pun) ---
_HERE = Path(__file__).resolve().parent          # audit/scripts
_CANONICAL_DIR = _HERE.parent / "outputs" / "canonical_pkl_model"

# Muat kontrak fitur sekali saja (cached)
with open(_CANONICAL_DIR / "feature_names.txt", encoding="utf-8") as _f:
    _FEATURE_NAMES = [line.strip() for line in _f if line.strip()]
with open(_CANONICAL_DIR / "feature_lists.json", encoding="utf-8") as _f:
    _FEATURE_LISTS = json.load(_f)
_CAT_FEATURES = set(_FEATURE_LISTS.get("categorical_features", []))


def adapt_raw_to_model_features(raw_row: Dict) -> pd.DataFrame:
    """
    Convert a raw claim row dict into a 61-feature DataFrame matching
    the canonical model's feature contract (audit/outputs/canonical_pkl_model/feature_names.txt).

    Reconstructs 8 engineered features:
      visit_hour, visit_dayofweek       ← date
      patient_age                       ← bpjs_tanggal_lahir + date
      visit_duration_min                ← exit_date - date
      has_rujukan                       ← bpjs_no_rujukan notnull
      has_skdp                          ← bpjs_skdp_no notnull
      has_surat_kontrol                 ← bpjs_no_surat_kontrol notnull
      icd_chapter                       ← bpjs_diagnosa_awal_code first char

    Remaining 53 features are passed through from the raw row as-is
    (NaN/None preserved for pipeline imputer).
    """
    row = dict(raw_row)  # copy

    # === Engineered features ===

    # Parse datetime columns
    date_val = pd.to_datetime(row.get("date"), errors="coerce")
    exit_val = pd.to_datetime(row.get("exit_date"), errors="coerce")
    dob_val = pd.to_datetime(row.get("bpjs_tanggal_lahir"), errors="coerce")

    # visit_hour
    if pd.notna(date_val):
        row["visit_hour"] = int(date_val.hour)
    else:
        row["visit_hour"] = -1

    # visit_dayofweek
    if pd.notna(date_val):
        row["visit_dayofweek"] = int(date_val.dayofweek)
    else:
        row["visit_dayofweek"] = -1

    # patient_age
    if pd.notna(date_val) and pd.notna(dob_val):
        age_years = (date_val - dob_val).days / 365.25
        row["patient_age"] = float(np.clip(age_years, 0, 120))
    else:
        row["patient_age"] = np.nan  # pipeline imputer handles

    # visit_duration_min
    if pd.notna(date_val) and pd.notna(exit_val):
        dur = (exit_val - date_val).total_seconds() / 60.0
        row["visit_duration_min"] = float(np.clip(dur, 0, 1440))
    else:
        row["visit_duration_min"] = np.nan

    # Boolean presence features
    row["has_rujukan"] = 1 if pd.notna(row.get("bpjs_no_rujukan")) else 0
    row["has_skdp"] = 1 if pd.notna(row.get("bpjs_skdp_no")) else 0
    row["has_surat_kontrol"] = 1 if pd.notna(row.get("bpjs_no_surat_kontrol")) else 0

    # ICD-10 chapter (first character; NaN → placeholder "n" matching training behavior)
    dx_code = row.get("bpjs_diagnosa_awal_code")
    if pd.isna(dx_code) or dx_code is None:
        row["icd_chapter"] = "n"
    else:
        row["icd_chapter"] = str(dx_code).strip()[0] if str(dx_code).strip() else "n"

    # Build aligned 61-feature DataFrame (menggunakan kontrak fitur yang di-cache)
    aligned = {fn: row.get(fn) for fn in _FEATURE_NAMES}
    df = pd.DataFrame([aligned])

    # Cast categorical features to string EXACTLY as done during training
    # (OrdinalEncoder was fit on string data; float input would produce wrong encoding)
    for cf in _CAT_FEATURES:
        if cf in df.columns:
            df[cf] = df[cf].astype(str)

    return df
