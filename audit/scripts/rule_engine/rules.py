"""Rule engine: individual rule implementations.
Each rule function returns a dict (or None if PASS).
All rules are VERIFIED_AUTOMATABLE per Phase 5A.2.
"""
import re
import pandas as pd
from typing import Dict, Optional, Any

# Regex for CBG format: [A-Z]-[0-9]-[0-9]{2}-[0/I/II/III]
_CBG_PATTERN = re.compile(r"^[A-Z]-\d-\d{2}-[0I]{1,3}$")


def _is_null(val):
    """Check if a value is null/NaN/None/empty-string."""
    if val is None:
        return True
    if isinstance(val, float) and pd.isna(val):
        return True
    if isinstance(val, str) and val.strip() == "":
        return True
    return False


def _finding(rule_id, name, category, status, severity, observed, message, suggestion, source):
    if observed is not None and not (isinstance(observed, float) and pd.isna(observed)):
        obs_str = str(observed)[:200]
    else:
        obs_str = "<null>"
    return {
        "rule_id": rule_id,
        "rule_name": name,
        "category": category,
        "status": status,
        "severity": severity,
        "observed_value": obs_str,
        "message": message,
        "suggestion": suggestion,
        "source_reference": source,
    }


# ============================================================
# D01 — Diagnosis code not empty
# ============================================================
def rule_D01(bpjs_diagnosa_awal_code, idrg_diagnose_json=None, ina_diagnose_json=None) -> Optional[Dict]:
    """
    D01 — Diagnosis code not empty.
    Checks bpjs_diagnosa_awal_code first. If that is null, checks grouper diagnosis
    responses (idrg_set_diagnose_response, ina_set_diagnose_response) for alternative
    ICD-10 codes. Only flags REVIEW if NO diagnosis source has a code.

    Phase 5B.1 update: 100% of claims with null bpjs_diagnosa_awal_code actually
    have diagnosis codes in the grouper JSON responses. This field alone is not
    a reliable single source — it may be empty due to workflow/field-mapping,
    not because diagnosis is truly missing.
    """
    from .procedure_parser import parse_any_codes as _parse_json_codes

    # 1. Check primary field
    if not _is_null(bpjs_diagnosa_awal_code):
        return None  # PASS — primary field has a code

    # 2. Check alternative grouper diagnosis sources
    alt_codes = set()
    for json_str in [idrg_diagnose_json, ina_diagnose_json]:
        codes = _parse_json_codes(json_str)
        alt_codes.update(codes)

    if alt_codes:
        # Diagnosis EXISTS in grouper, but primary field is empty.
        # This is a field-completeness issue, not a missing-diagnosis issue.
        return _finding("D01", "Diagnosis code not in primary field", "STRUCTURAL_COMPLETENESS",
                        "REVIEW", "INFO",
                        f"primary=<null> grouper={sorted(alt_codes)[:3]}",
                        "Kode diagnosis primer tidak terisi di field bpjs_diagnosa_awal_code, "
                        "namun kode diagnosis tersedia di grouper response.",
                        "Kode diagnosis sudah tersedia di grouper. "
                        "Pertimbangkan untuk mengisi bpjs_diagnosa_awal_code agar konsisten.",
                        "Permenkes 26/2021 §3 (updated: Phase 5B.1 multi-source check)")

    # 3. No diagnosis code anywhere
    return _finding("D01", "Diagnosis code not found in any source", "STRUCTURAL_COMPLETENESS",
                    "REVIEW", "WARNING",
                    "all sources empty",
                    "Kode diagnosis utama (ICD-10) tidak ditemukan di field primer maupun grouper.",
                    "Kode diagnosis belum diisi. Isi kode diagnosis sebelum submit klaim.",
                    "Permenkes 26/2021 §3")


# ============================================================
# D02 — ICD-10 code valid per master list
# ============================================================
def rule_D02(bpjs_diagnosa_awal_code, icd10_set) -> Optional[Dict]:
    if _is_null(bpjs_diagnosa_awal_code):
        return None  # Do not double-report with D01; D01 covers emptiness
    code = str(bpjs_diagnosa_awal_code).strip().upper()
    # Remove dots for lookup (ICD-10 codes like A00.0 vs A000)
    code_nodot = code.replace(".", "")
    code_withdot = code
    if code in icd10_set or code_nodot in icd10_set or code_withdot in icd10_set:
        return None  # PASS
    return _finding("D02", "ICD-10 code valid (master list)", "CODE_VALIDITY",
                    "REVIEW", "WARNING", code,
                    f"Kode ICD-10 '{code}' tidak ditemukan di daftar kode ICD-10 e-klaim.",
                    f"Kode ICD-10 '{code}' tidak ditemukan di master list ICD-10 (18.543 kode). Verifikasi kode diagnosis.",
                    "ICD-10 e-klaim master list (18,543 codes)")


# ============================================================
# C01 — CBG code not empty
# ============================================================
def rule_C01(cbg_code) -> Optional[Dict]:
    if _is_null(cbg_code):
        return _finding("C01", "CBG code not empty", "STRUCTURAL_COMPLETENESS",
                        "REVIEW", "WARNING", cbg_code,
                        "Kode INA-CBG tidak diisi.",
                        "Kode INA-CBG belum tersedia. Jalankan grouper sebelum submit klaim.",
                        "Permenkes 26/2021 §1")
    return None


# ============================================================
# C03 — CBG format valid
# ============================================================
def rule_C03(cbg_code) -> Optional[Dict]:
    if _is_null(cbg_code):
        return None  # C01 covers emptiness
    code = str(cbg_code).strip()
    if _CBG_PATTERN.match(code):
        return None
    return _finding("C03", "CBG format valid", "GROUPER_VALIDATION",
                    "REVIEW", "WARNING", code,
                    f"Format kode INA-CBG '{code}' tidak valid.",
                    f"Format kode INA-CBG seharusnya: [A-Z]-[0-9]-[0-9][0-9]-[0/I/II/III]. Periksa '{code}'.",
                    "Permenkes 26/2021 §1")


# ============================================================
# C04 — CBG digit-2 for outpatient
# ============================================================
_VALID_DIGIT2_RAJAL = {"2", "3", "5", "7", "9"}

def rule_C04(cbg_code) -> Optional[Dict]:
    if _is_null(cbg_code):
        return None
    code = str(cbg_code).strip()
    if not _CBG_PATTERN.match(code):
        return None  # C03 covers format
    parts = code.split("-")
    if len(parts) >= 2 and parts[1] in _VALID_DIGIT2_RAJAL:
        return None
    d2 = parts[1] if len(parts) >= 2 else "?"
    return _finding("C04", "CBG digit-2 for rawat jalan", "GROUPER_VALIDATION",
                    "REVIEW", "HIGH", code,
                    f"Digit ke-2 CBG '{code}' ({d2}) bukan kode rawat jalan (seharusnya 2/3/5/7/9).",
                    f"Digit ke-2 CBG ({d2}) tidak sesuai untuk rawat jalan. Periksa kode CBG atau jenis kunjungan.",
                    "Permenkes 26/2021 §1.1")


# ============================================================
# C05 — Severity level 0 for outpatient
# ============================================================
def rule_C05(cbg_code) -> Optional[Dict]:
    if _is_null(cbg_code):
        return None
    code = str(cbg_code).strip()
    if not _CBG_PATTERN.match(code):
        return None
    parts = code.split("-")
    if len(parts) >= 4 and parts[3] == "0":
        return None
    sev = parts[3] if len(parts) >= 4 else "?"
    return _finding("C05", "Severity level 0 for rawat jalan", "GROUPER_VALIDATION",
                    "REVIEW", "HIGH", code,
                    f"Severity level CBG '{code}' adalah '{sev}' (seharusnya 0 untuk rawat jalan).",
                    f"Severity level '{sev}' tidak lazim untuk rawat jalan (Permenkes §1.2: severity 0). Verifikasi.",
                    "Permenkes 26/2021 §1.2")


# ============================================================
# P01 — Surgical CBG requires procedure code
# ============================================================
_SURGICAL_DIGIT2 = {"2", "3"}

def rule_P01(cbg_code, procedure_codes, icd9cm_set) -> Optional[Dict]:
    if _is_null(cbg_code):
        return None
    code = str(cbg_code).strip()
    if not _CBG_PATTERN.match(code):
        return None
    parts = code.split("-")
    d2 = parts[1] if len(parts) >= 2 else ""
    if d2 not in _SURGICAL_DIGIT2:
        return None  # Not a surgical CBG, no procedure required

    if not procedure_codes or len(procedure_codes) == 0:
        return _finding("P01", "Surgical CBG requires procedure code", "CODING_CONSISTENCY",
                        "REVIEW", "HIGH", code,
                        f"CBG '{code}' adalah CBG prosedur (digit-2={d2}) tetapi tidak ada kode prosedur ICD-9-CM.",
                        f"CBG prosedural '{code}' membutuhkan kode prosedur ICD-9-CM. Input kode tindakan di e-klaim.",
                        "Permenkes 26/2021 §2")

    # Validate each procedure code against ICD-9-CM master list
    invalid_codes = [pc for pc in procedure_codes if pc not in icd9cm_set]
    if invalid_codes:
        return _finding("P01", "Surgical CBG requires procedure code", "CODING_CONSISTENCY",
                        "REVIEW", "WARNING", f"CBG={code} invalid_codes={invalid_codes}",
                        f"Kode prosedur {invalid_codes} tidak ditemukan di master list ICD-9-CM.",
                        f"Kode prosedur {invalid_codes} tidak valid. Periksa kode ICD-9-CM di e-klaim.",
                        "ICD-9-CM e-klaim master list (4,626 codes)")
    return None


# ============================================================
# A01 — SEP date present
# ============================================================
def rule_A01(bpjs_tgl_sep) -> Optional[Dict]:
    if _is_null(bpjs_tgl_sep):
        return _finding("A01", "SEP date present", "ADMINISTRATIVE_CONSISTENCY",
                        "REVIEW", "WARNING", bpjs_tgl_sep,
                        "Tanggal SEP tidak diisi.",
                        "Tanggal SEP belum diisi. Isi tanggal SEP sebelum submit klaim.",
                        "BPJS SEP requirement")
    return None


# ============================================================
# A02 — Discharge date >= visit date
# ============================================================
def rule_A02(date_val, exit_date_val) -> Optional[Dict]:
    if date_val is None or exit_date_val is None:
        return None  # Cannot evaluate
    try:
        import pandas as pd
        d = pd.to_datetime(date_val)
        e = pd.to_datetime(exit_date_val)
        if pd.isna(d) or pd.isna(e):
            return None
        if e >= d:
            return None
        return _finding("A02", "Discharge date >= visit date", "ADMINISTRATIVE_CONSISTENCY",
                        "REVIEW", "HIGH", f"visit={d.date()} exit={e.date()}",
                        f"Tanggal pulang ({e.date()}) lebih awal dari tanggal kunjungan ({d.date()}).",
                        f"Tanggal pulang ({e.date()}) < tanggal kunjungan ({d.date()}). Verifikasi tanggal kunjungan dan kepulangan.",
                        "Permenkes 26/2021 §8.1")
    except Exception:
        return None


# ============================================================
# Rule list
# ============================================================
ALL_RULES = [
    ("D01", rule_D01),
    ("D02", rule_D02),
    ("C01", rule_C01),
    ("C03", rule_C03),
    ("C04", rule_C04),
    ("C05", rule_C05),
    ("P01", rule_P01),
    ("A01", rule_A01),
    ("A02", rule_A02),
]
