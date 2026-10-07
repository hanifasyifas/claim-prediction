"""
JSON Serialization Layer — framework-agnostic response builder.

Converts the internal PKLPrototype.evaluate_claim() output into a clean,
JSON-serializable API response contract.

This module is intentionally framework-agnostic:
  - No FastAPI / Flask dependency
  - Pure functions, deterministic, no side effects
  - Can be wrapped in an HTTP endpoint later (~30 lines)

Design notes:
  - Does NOT include historical labels (target). Those are QA/demo only,
    not part of a real pre-submission inference contract.
  - PII-safe: only claim_id (internal SIMRS id) and rule field values are
    exposed; no patient names, NIK, MR, SEP, addresses.
  - All numpy types are coerced to native Python types for JSON safety.
"""
import json
import numpy as np
from datetime import datetime, timezone
from typing import Dict, List, Any

RESPONSE_SCHEMA_VERSION = "1.0"

DISCLAIMER = (
    "Screening only. This output estimates observable Pending risk from historical "
    "patterns and lists rule-based validation findings. It does NOT determine the "
    "BPJS decision and must not be used as an automated approval or rejection."
)


def _to_native(value: Any) -> Any:
    """Coerce numpy / pandas types to native Python for JSON serialization."""
    if value is None:
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        f = float(value)
        return None if np.isnan(f) else f
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, float):
        return None if np.isnan(value) else value
    if isinstance(value, dict):
        return {k: _to_native(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_native(v) for v in value]
    return value


def _serialize_finding(finding: Dict) -> Dict:
    """Serialize a single rule-engine finding into a clean JSON object."""
    return {
        "rule_id": _to_native(finding.get("rule_id")),
        "rule_name": _to_native(finding.get("rule_name")),
        "category": _to_native(finding.get("category")),
        "severity": _to_native(finding.get("severity")),
        "status": _to_native(finding.get("status")),
        "observed_value": _to_native(finding.get("observed_value")),
        "message": _to_native(finding.get("message")),
        "suggestion": _to_native(finding.get("suggestion")),
        "source_reference": _to_native(finding.get("source_reference")),
    }


def build_api_response(claim_result: Dict,
                       model_name: str = "RandomForest_Pending_Risk_PKL",
                       model_version: str = None,
                       include_observed_values: bool = True) -> Dict:
    """
    Build a clean, JSON-ready response dict from a PKLPrototype.evaluate_claim() result.

    Parameters
    ----------
    claim_result : dict
        Output of PKLPrototype.evaluate_claim().
        Expected keys: claim_id, risk{probability,threshold,warning,recommendation},
                       validation{total_findings,findings}.
    model_name : str
        Model identifier for traceability.
    model_version : str, optional
        Model artifact version. If None, omitted.
    include_observed_values : bool
        If False, strips the raw observed_value from findings (extra privacy).

    Returns a dict that can be passed directly to json.dumps().
    """
    risk = claim_result.get("risk", {})
    validation = claim_result.get("validation", {})
    findings = validation.get("findings", []) or []

    serialized_findings: List[Dict] = []
    for f in findings:
        sf = _serialize_finding(f)
        if not include_observed_values:
            sf.pop("observed_value", None)
        serialized_findings.append(sf)

    response = {
        "schema_version": RESPONSE_SCHEMA_VERSION,
        "claim_id": _to_native(claim_result.get("claim_id")),
        "prediction": {
            "pending_risk": _to_native(risk.get("probability")),
            "threshold": _to_native(risk.get("threshold")),
            "warning": _to_native(risk.get("warning")) == "YES",
            "recommendation": _to_native(risk.get("recommendation")),
        },
        "validation": {
            "total_findings": _to_native(len(serialized_findings)),
            "findings": serialized_findings,
        },
        "meta": {
            "model": model_name,
            "component": "technical_prototype",
            "disclaimer": DISCLAIMER,
        },
    }
    if model_version:
        response["meta"]["model_version"] = model_version

    return response


def to_json_string(claim_result: Dict,
                   indent: int = 2,
                   **kwargs) -> str:
    """Convenience: build_api_response() + json.dumps()."""
    return json.dumps(build_api_response(claim_result, **kwargs), indent=indent, ensure_ascii=False)


def build_batch_response(claim_results: List[Dict],
                         model_name: str = "RandomForest_Pending_Risk_PKL") -> Dict:
    """Wrap multiple claim responses into a batch envelope."""
    items = [build_api_response(r, model_name=model_name) for r in claim_results]
    return {
        "schema_version": RESPONSE_SCHEMA_VERSION,
        "count": len(items),
        "results": items,
    }
