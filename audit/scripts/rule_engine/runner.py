"""Rule engine runner — evaluate all 9 VERIFIED_AUTOMATABLE rules on a claim row."""
from typing import List, Dict, Optional, Any
from .rules import ALL_RULES
from .loaders import load_icd10_codes, load_icd9cm_codes
from .procedure_parser import parse_procedure_codes


class RuleEngine:
    def __init__(self):
        self.icd10_set = set(load_icd10_codes().keys())
        self.icd9cm_set = set(load_icd9cm_codes().keys())

    def evaluate(self, row: Dict[str, Any]) -> List[Dict]:
        """Evaluate all 9 rules on a single claim row. Returns list of findings."""
        findings = []

        # Extract fields
        bpjs_dx_code = row.get("bpjs_diagnosa_awal_code")
        cbg_code = row.get("cbg_code")
        bpjs_tgl_sep = row.get("bpjs_tgl_sep")
        date_val = row.get("date")
        exit_date_val = row.get("exit_date")

        # Parse procedure codes from JSON
        idrg_json = row.get("idrg_set_procedure_response")
        ina_json = row.get("ina_set_procedure_response")
        proc_codes_idrg = parse_procedure_codes(idrg_json)
        proc_codes_ina = parse_procedure_codes(ina_json)
        # Merge and deduplicate
        all_proc = list(set(proc_codes_idrg + proc_codes_ina))

        # D01 — Diagnosis code not empty (checks primary + grouper sources)
        f = ALL_RULES[0][1](bpjs_dx_code,
                           row.get("idrg_set_diagnose_response"),
                           row.get("ina_set_diagnose_response"))
        if f: findings.append(f)

        # D02 — ICD-10 valid per master list
        f = ALL_RULES[1][1](bpjs_dx_code, self.icd10_set)
        if f: findings.append(f)

        # C01 — CBG not empty
        f = ALL_RULES[2][1](cbg_code)
        if f: findings.append(f)

        # C03 — CBG format
        f = ALL_RULES[3][1](cbg_code)
        if f: findings.append(f)

        # C04 — CBG digit-2 for rajal
        f = ALL_RULES[4][1](cbg_code)
        if f: findings.append(f)

        # C05 — Severity level 0
        f = ALL_RULES[5][1](cbg_code)
        if f: findings.append(f)

        # P01 — Surgical CBG needs procedure
        f = ALL_RULES[6][1](cbg_code, all_proc, self.icd9cm_set)
        if f: findings.append(f)

        # A01 — SEP date
        f = ALL_RULES[7][1](bpjs_tgl_sep)
        if f: findings.append(f)

        # A02 — Discharge >= visit
        f = ALL_RULES[8][1](date_val, exit_date_val)
        if f: findings.append(f)

        return findings

    def evaluate_batch(self, df) -> List[List[Dict]]:
        """Evaluate all rules on all rows. Returns list of finding-lists."""
        results = []
        for _, row in df.iterrows():
            results.append(self.evaluate(row.to_dict()))
        return results
