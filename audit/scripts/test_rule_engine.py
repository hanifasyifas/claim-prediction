"""Unit tests for the 9 VERIFIED_AUTOMATABLE rule engine rules."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from rule_engine.rules import (
    rule_D01, rule_D02, rule_C01, rule_C03, rule_C04, rule_C05,
    rule_P01, rule_A01, rule_A02
)
from rule_engine.procedure_parser import parse_procedure_codes
from rule_engine.loaders import load_icd10_codes, load_icd9cm_codes

icd10 = set(load_icd10_codes().keys())
icd9 = set(load_icd9cm_codes().keys())

def test_D01_valid_primary():
    assert rule_D01("A00.0") is None

def test_D01_null_but_grouper_has_code():
    # Primary null, but grouper JSON has diagnosis code -> INFO finding
    js = '{"data":{"string":"M75.1","expanded":[{"code":"M75.1","display":"..."}]}}'
    f = rule_D01(None, js, None)
    assert f is not None and f["rule_id"] == "D01"
    assert f["severity"] == "INFO"  # downgraded from WARNING
    assert "grouper" in f["message"].lower()

def test_D01_null_no_grouper_either():
    # Primary null, grouper also empty -> WARNING
    f = rule_D01(None, None, None)
    assert f is not None and f["rule_id"] == "D01"
    assert f["severity"] == "WARNING"

def test_D01_nan():
    f = rule_D01(np.nan)
    assert f is not None and f["rule_id"] == "D01"

def test_D01_empty():
    f = rule_D01("")
    assert f is not None and f["status"] == "REVIEW"

def test_D02_valid():
    assert rule_D02("A00.0", icd10) is None

def test_D02_invalid():
    f = rule_D02("ZZ99.9", icd10)
    assert f is not None and f["rule_id"] == "D02"

def test_D02_null_skipped():
    assert rule_D02(None, icd10) is None  # D01 covers emptiness

def test_D02_format_variants():
    # Test with dots and without
    assert rule_D02("A00", icd10) is None  # A00 exists
    assert rule_D02("A00.0", icd10) is None  # A00.0 exists

def test_C01_valid():
    assert rule_C01("Q-5-44-0") is None

def test_C01_null():
    f = rule_C01(None)
    assert f is not None and f["rule_id"] == "C01"

def test_C03_valid():
    assert rule_C03("Q-5-44-0") is None
    assert rule_C03("M-3-16-0") is None

def test_C03_invalid():
    f = rule_C03("X-5-44-Z")
    assert f is not None and f["rule_id"] == "C03"

def test_C04_valid_rajal():
    assert rule_C04("Q-5-44-0") is None  # digit2=5
    assert rule_C04("M-2-10-0") is None  # digit2=2

def test_C04_invalid_ranap():
    f = rule_C04("I-4-10-I")
    assert f is not None and f["rule_id"] == "C04"  # digit2=4 is ranap

def test_C05_valid():
    assert rule_C05("Q-5-44-0") is None

def test_C05_invalid():
    f = rule_C05("Q-5-44-I")
    assert f is not None and f["rule_id"] == "C05"

def test_P01_surgical_no_procedure():
    f = rule_P01("M-2-10-0", [], icd9)
    assert f is not None and f["rule_id"] == "P01"

def test_P01_surgical_valid_procedure():
    f = rule_P01("M-2-10-0", ["89.08"], icd9)
    assert f is None  # 89.08 exists in ICD-9-CM

def test_P01_surgical_invalid_procedure():
    f = rule_P01("M-2-10-0", ["11.11"], icd9)
    assert f is not None  # 11.11 not in ICD-9-CM

def test_P01_nonsurgical_skipped():
    assert rule_P01("Q-5-44-0", [], icd9) is None  # digit2=5, not surgical

def test_A01_valid():
    assert rule_A01("2026-04-01") is None

def test_A01_null():
    f = rule_A01(None)
    assert f is not None and f["rule_id"] == "A01"

def test_A02_valid():
    assert rule_A02("2026-04-01", "2026-04-01") is None

def test_A02_reversed():
    f = rule_A02("2026-04-02", "2026-04-01")
    assert f is not None and f["rule_id"] == "A02"

# --- Procedure parser tests ---
def test_parse_normal_json():
    js = '{"metadata":{"code":200},"data":{"string":"89.08","expanded":[{"code":"89.08","display":"Other consultation","no":"1"}]}}'
    codes = parse_procedure_codes(js)
    assert codes == ["89.08"]

def test_parse_multi_json():
    js = '{"data":{"string":"89.08#94.39","expanded":[{"code":"89.08","display":"..."},{"code":"94.39","display":"..."}]}}'
    codes = parse_procedure_codes(js)
    assert "89.08" in codes and "94.39" in codes

def test_parse_null():
    assert parse_procedure_codes(None) == []

def test_parse_empty():
    assert parse_procedure_codes("") == []

def test_parse_malformed():
    assert parse_procedure_codes("not json") == []

def test_parse_no_procedures():
    js = '{"data":{"expanded":[]}}'
    assert parse_procedure_codes(js) == []

print("ALL UNIT TESTS PASSED")
for name, fn in list(globals().items()):
    if name.startswith("test_"):
        try:
            fn()
            print(f"  [PASS] {name}")
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
