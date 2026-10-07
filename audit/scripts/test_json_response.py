"""Unit tests for the framework-agnostic JSON serialization layer."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from json_response import (
    build_api_response, to_json_string, build_batch_response,
    RESPONSE_SCHEMA_VERSION,
)


def _sample_result(warning="YES"):
    return {
        "claim_id": 719069,
        "risk": {
            "probability": np.float64(0.7820),
            "threshold": 0.50,
            "warning": warning,
            "recommendation": "REVIEW" if warning == "YES" else "OK",
        },
        "validation": {
            "total_findings": 1,
            "findings": [{
                "rule_id": "D01",
                "rule_name": "Diagnosis code not in primary field",
                "category": "STRUCTURAL_COMPLETENESS",
                "status": "REVIEW",
                "severity": "INFO",
                "observed_value": "primary=<null> grouper=['M75.1']",
                "message": "Kode diagnosis primer tidak terisi.",
                "suggestion": "Kode diagnosis sudah tersedia di grouper.",
                "source_reference": "Permenkes 26/2021 §3",
            }],
        },
    }


def test_schema_version_present():
    r = build_api_response(_sample_result())
    assert r["schema_version"] == RESPONSE_SCHEMA_VERSION


def test_claim_id_serialized():
    r = build_api_response(_sample_result())
    assert r["claim_id"] == 719069


def test_probability_is_python_float():
    r = build_api_response(_sample_result())
    assert isinstance(r["prediction"]["pending_risk"], float)
    assert abs(r["prediction"]["pending_risk"] - 0.7820) < 1e-9


def test_warning_is_bool():
    r = build_api_response(_sample_result(warning="YES"))
    assert r["prediction"]["warning"] is True
    r2 = build_api_response(_sample_result(warning="NO"))
    assert r2["prediction"]["warning"] is False
    assert r2["prediction"]["recommendation"] == "OK"


def test_findings_serialized():
    r = build_api_response(_sample_result())
    assert r["validation"]["total_findings"] == 1
    f = r["validation"]["findings"][0]
    for k in ["rule_id", "category", "severity", "message", "suggestion", "source_reference"]:
        assert k in f


def test_json_serializable():
    r = build_api_response(_sample_result())
    s = json.dumps(r)
    assert '"schema_version"' in s
    parsed = json.loads(s)
    assert parsed["prediction"]["warning"] is True


def test_no_target_leak():
    """JSON output must NOT contain the ground-truth target field or its value."""
    r = build_api_response(_sample_result())
    # No target field in any nested key
    def all_keys(d):
        keys = set()
        for k, v in d.items():
            keys.add(k)
            if isinstance(v, dict):
                keys |= all_keys(v)
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        keys |= all_keys(item)
        return keys
    keys = all_keys(r)
    assert "target" not in keys
    assert "label" not in keys
    assert "historical_actual" not in keys
    # The top-level response must not carry the ground-truth label
    assert "target" not in r
    assert "label" not in r


def test_nan_handling():
    res = _sample_result()
    res["risk"]["probability"] = np.nan
    r = build_api_response(res)
    assert r["prediction"]["pending_risk"] is None  # NaN -> None


def test_observed_values_can_be_stripped():
    r = build_api_response(_sample_result(), include_observed_values=False)
    assert "observed_value" not in r["validation"]["findings"][0]


def test_batch_response():
    batch = build_batch_response([_sample_result(), _sample_result()])
    assert batch["count"] == 2
    assert len(batch["results"]) == 2
    assert batch["schema_version"] == RESPONSE_SCHEMA_VERSION


def test_empty_findings():
    res = _sample_result()
    res["validation"]["findings"] = []
    r = build_api_response(res)
    assert r["validation"]["total_findings"] == 0
    assert r["validation"]["findings"] == []


if __name__ == "__main__":
    tests = [(n, f) for n, f in list(globals().items()) if n.startswith("test_")]
    passed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  [PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
    print(f"\n{passed}/{len(tests)} tests passed")
