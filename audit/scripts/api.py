"""
Local Inference API — FastAPI wrapper around the technical prototype.

This is a THIN FRAMEWORK LAYER. Core logic lives in:
    - canonical_adapter.py  (feature engineering)
    - canonical_pkl_model/pipeline.pkl  (frozen Random Forest)
    - rule_engine/  (9 validation rules)

If the mentor confirms a different request/response contract, ONLY this file
(and possibly json_response.py) needs to change. The model, features, rules,
and threshold are untouched.

Run:
    uvicorn api:app --reload --port 8000
    (from the audit/scripts directory)

Endpoints:
    GET  /health
    POST /screen          -> single claim (by claim_id or raw claim_data)
    POST /screen/batch    -> list of claim_ids
"""
import sys, os, importlib.util
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# --- Make sibling modules importable ---
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(SCRIPTS_DIR / "rule_engine"))

from json_response import build_api_response, build_batch_response  # noqa: E402

# --- Path relatif (portabel) ---
AUDIT_DIR = SCRIPTS_DIR.parent                       # audit/
OUT = AUDIT_DIR / "outputs"
_REFERENCE_DIR = AUDIT_DIR / "reference_data"


def _load_prototype_class():
    """Load PKLPrototype from 19_pkl_prototype.py (filename starts with a digit)."""
    spec = importlib.util.spec_from_file_location(
        "pkl_prototype_mod", SCRIPTS_DIR / "19_pkl_prototype.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.PKLPrototype


# --- Load once at startup (NOT retrained) ---
PKLPrototype = _load_prototype_class()
proto = PKLPrototype(verbose=False)
_df_lookup = None  # lazy-loaded labeled dataset for claim_id lookups


def _lookup_df():
    """Muat dataset untuk pencarian claim_id.

    Prioritas: dataset lengkap (jika tersedia) → sample de-identifikasi.
    Dataset lengkap tidak disertakan di repo (mengandung data pasien).
    """
    global _df_lookup
    if _df_lookup is None:
        import pandas as pd
        full = OUT / "phase2_labeled_dataset.csv"
        sample = _REFERENCE_DIR / "sample_claims.csv"
        path = full if full.exists() else sample
        if not path.exists():
            raise FileNotFoundError(
                "Dataset tidak tersedia. Gunakan mode 'claim_data' atau sediakan "
                "audit/reference_data/sample_claims.csv."
            )
        _df_lookup = pd.read_csv(path, low_memory=False)
    return _df_lookup


# ============================================================
# Schemas
# ============================================================
class ScreenRequest(BaseModel):
    claim_id: Optional[int] = Field(None, description="Internal SIMRS visit id (lookup from dataset)")
    claim_data: Optional[Dict[str, Any]] = Field(None, description="Raw claim row (raw visit+claim fields)")


class BatchScreenRequest(BaseModel):
    claim_ids: List[int]


# ============================================================
# App
# ============================================================
app = FastAPI(
    title="Pending Claim Risk Screening API",
    version="1.0",
    description="Technical prototype — decision support only. Does not determine BPJS decisions.",
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model": proto.metadata["model_name"],
        "features": len(proto.feature_names),
        "rules": 9,
        "threshold": 0.50,
    }


@app.post("/screen")
def screen(req: ScreenRequest):
    """Screen a single claim by claim_id OR raw claim_data."""
    try:
        if req.claim_data is not None:
            result = proto.evaluate_claim(req.claim_data)
        elif req.claim_id is not None:
            match = _lookup_df()[_lookup_df()["id"] == req.claim_id]
            if len(match) == 0:
                raise HTTPException(status_code=404, detail=f"claim_id {req.claim_id} not found")
            result = proto.evaluate_claim(match.iloc[0].to_dict())
        else:
            raise HTTPException(status_code=400, detail="Provide either claim_id or claim_data")
        return build_api_response(result)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Do not leak internals; keep message generic
        raise HTTPException(status_code=500, detail=f"Inference failed: {type(e).__name__}")


@app.post("/screen/batch")
def screen_batch(req: BatchScreenRequest):
    """Screen multiple claims by claim_id."""
    df = _lookup_df()
    results = []
    not_found = []
    for vid in req.claim_ids:
        match = df[df["id"] == vid]
        if len(match) == 0:
            not_found.append(vid)
            continue
        results.append(proto.evaluate_claim(match.iloc[0].to_dict()))
    payload = build_batch_response(results)
    if not_found:
        payload["not_found"] = not_found
    return payload
