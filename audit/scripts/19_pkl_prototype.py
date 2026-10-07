"""
Technical Prototype — Pending Claim Pre-Submission Screening
  --mode qa    : Developer regression test + per-claim detail
  --mode demo  : Mentor presentation (clean output)
  --demo-id    : Custom claim IDs for demo mode (default: TP/FP/FN/TN)

Canonical model: frozen pipeline.pkl (61 features, threshold=0.50, Random Forest)
Rule engine: 9 VERIFIED_AUTOMATABLE rules (Permenkes 26/2021)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "rule_engine"))

import argparse, pickle, json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List

from canonical_adapter import adapt_raw_to_model_features
from rule_engine.runner import RuleEngine
from json_response import build_api_response, build_batch_response

# --- Path relatif (portabel di mesin mana pun) ---
_SCRIPTS = Path(__file__).resolve().parent          # audit/scripts
_AUDIT = _SCRIPTS.parent                            # audit/
OUT = _AUDIT / "outputs"
CANONICAL = OUT / "canonical_pkl_model"
_REFERENCE_DIR = _AUDIT / "reference_data"
THRESHOLD = 0.50
DEFAULT_QA_IDS = [719069, 719074, 719071, 719215]


def _get_dataset_path() -> Path:
    """Kembalikan path dataset: lengkap jika tersedia, jika tidak → sample."""
    full = OUT / "phase2_labeled_dataset.csv"
    if full.exists():
        return full
    sample = _REFERENCE_DIR / "sample_claims.csv"
    if sample.exists():
        return sample
    raise FileNotFoundError(
        "Dataset tidak tersedia. Jalankan dengan mode '--format json' + data mentah, "
        "atau sediakan audit/reference_data/sample_claims.csv."
    )


class PKLPrototype:
    def __init__(self, verbose=True):
        if verbose:
            print("Loading canonical model...")
        with open(CANONICAL / "pipeline.pkl", "rb") as f:
            self.pipeline = pickle.load(f)
        with open(CANONICAL / "metadata.json") as f:
            self.metadata = json.load(f)
        with open(CANONICAL / "feature_names.txt") as f:
            self.feature_names = [line.strip() for line in f if line.strip()]
        if verbose:
            print(f"  Model: {self.metadata['model_name']}")
            print(f"  Features: {len(self.feature_names)}")
            print(f"  Threshold: {THRESHOLD}")
            print("Loading rule engine...")
        self.rule_engine = RuleEngine()
        if verbose:
            print(f"  ICD-10: {len(self.rule_engine.icd10_set)}  ICD-9-CM: {len(self.rule_engine.icd9cm_set)}")

    def evaluate_claim(self, raw_row: Dict) -> Dict:
        X = adapt_raw_to_model_features(raw_row)

        actual_cols = set(X.columns)
        expected_cols = set(self.feature_names)
        missing_from_input = expected_cols - actual_cols
        extra_in_input = actual_cols - expected_cols
        if missing_from_input:
            raise ValueError(f"Missing features: {missing_from_input}")
        X = X[self.feature_names]

        proba = float(self.pipeline.predict_proba(X)[0, 1])
        warning = "YES" if proba >= THRESHOLD else "NO"
        recommendation = "REVIEW" if warning == "YES" else "OK"

        risk = {
            "probability": round(proba, 4),
            "threshold": THRESHOLD,
            "warning": warning,
            "recommendation": recommendation,
        }

        findings = self.rule_engine.evaluate(raw_row)

        return {
            "claim_id": raw_row.get("id", "?"),
            "risk": risk,
            "validation": {
                "total_findings": len(findings),
                "findings": findings,
            },
        }

    def evaluate_by_visit_id(self, visit_id: int) -> Dict:
        df = pd.read_csv(_get_dataset_path(), low_memory=False)
        match = df[df["id"] == visit_id]
        if len(match) == 0:
            raise ValueError(f"Visit ID {visit_id} not found in dataset")
        raw_row = match.iloc[0].to_dict()
        if "target" in match.columns:
            raw_row["_target"] = int(match.iloc[0]["target"])  # historical label for demo
        return self.evaluate_claim(raw_row)

    def regression_test(self, test_ids: List[int] = None) -> Dict:
        if test_ids is None:
            test_ids = DEFAULT_QA_IDS
        preds_path = CANONICAL / "may_predictions.csv"
        if not preds_path.exists():
            # Dataset prediksi historis tidak disertakan di repo publik.
            return {"all_pass": None, "results": [],
                    "skipped": "may_predictions.csv tidak tersedia (data historis tidak disertakan)."}
        preds_csv = pd.read_csv(preds_path)
        preds_csv.rename(columns={"Unnamed: 0": "row_idx"}, inplace=True)
        df = pd.read_csv(_get_dataset_path(), low_memory=False)
        results = []
        all_pass = True
        for vid in test_ids:
            match = df[df["id"] == vid]
            if len(match) == 0:
                results.append({"visit_id": vid, "status": "NOT_FOUND"})
                all_pass = False
                continue
            raw_row = match.iloc[0].to_dict()
            result = self.evaluate_claim(raw_row)
            proto_proba = result["risk"]["probability"]
            row_idx = match.index[0]
            pred_row = preds_csv[preds_csv["row_idx"] == row_idx]
            if len(pred_row) == 0:
                stored_proba, stored_pred = None, None
            else:
                stored_proba = float(pred_row.iloc[0]["proba_pending"])
                stored_pred = int(pred_row.iloc[0]["y_pred"])
            proto_pred = 1 if proto_proba >= THRESHOLD else 0
            diff = abs(stored_proba - proto_proba) if stored_proba is not None else None
            match_ok = (diff is not None and diff < 1e-4)
            pred_ok = (stored_pred == proto_pred)
            if not match_ok or not pred_ok:
                all_pass = False
            results.append({
                "visit_id": vid, "row_idx": row_idx,
                "stored_proba": round(stored_proba, 6) if stored_proba else None,
                "proto_proba": round(proto_proba, 6),
                "abs_diff": round(diff, 8) if diff else None,
                "stored_pred": stored_pred, "proto_pred": proto_pred,
                "proba_match": match_ok, "pred_match": pred_ok,
                "n_findings": result["validation"]["total_findings"],
                "rule_ids": ", ".join(f["rule_id"] for f in result["validation"]["findings"]) if result["validation"]["findings"] else "none",
            })
        return {"all_pass": all_pass, "results": results}

    def evaluate_ids(self, visit_ids: List[int], df_lookup=None) -> List[Dict]:
        """Evaluate a list of visit_ids, returning raw claim results (for JSON)."""
        if df_lookup is None:
            df_lookup = pd.read_csv(_get_dataset_path(), low_memory=False)
        results = []
        for vid in visit_ids:
            match = df_lookup[df_lookup["id"] == vid]
            if len(match) == 0:
                results.append({"claim_id": vid, "error": "not_found"})
                continue
            results.append(self.evaluate_claim(match.iloc[0].to_dict()))
        return results


def print_demo_claim(proto, visit_id, df_lookup):
    """Print one claim in demo presentation format."""
    match = df_lookup[df_lookup["id"] == visit_id]
    if len(match) == 0:
        print(f"\n  [ERROR] Claim ID {visit_id} not found.")
        return
    raw_row = match.iloc[0]
    actual_str = "Pending" if int(raw_row["target"]) == 1 else "Claimed"
    result = proto.evaluate_claim(raw_row.to_dict())
    r = result["risk"]

    print(f"\n{'─'*50}")
    print(f"Claim ID            : {visit_id}")
    print(f"Historical Actual   : {actual_str}")
    print(f"{'─'*50}")
    print(f"\n  >>> RISK SCREENING <<<")
    print(f"  Pending Risk       : {r['probability']:.1%}")
    print(f"  Recommendation     : {r['recommendation']}")
    print(f"\n  >>> VALIDATION FINDINGS <<<")
    v = result["validation"]
    if v["findings"]:
        for f in v["findings"]:
            print(f"  [{f['severity']}] {f['rule_id']} — {f['category']}")
            print(f"    {f['suggestion']}")
    else:
        print(f"  No validation findings.")


# ============================================================
# CLI
# ============================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Technical Prototype — Pending Claim Pre-Submission Screening")
    parser.add_argument("--mode", choices=["qa", "demo"], default="qa",
                        help="qa = developer regression test | demo = mentor presentation")
    parser.add_argument("--demo-id", type=int, nargs="*", default=None,
                        help="Claim ID(s) for demo mode (default: TP/FP/FN/TN quartet)")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="Output format: text (default) or json (API-ready serialization)")
    args = parser.parse_args()

    demo_ids = args.demo_id if args.demo_id else DEFAULT_QA_IDS

    # ---- JSON output mode (framework-agnostic serialization) ----
    if args.format == "json":
        proto = PKLPrototype(verbose=False)
        df_lookup = pd.read_csv(_get_dataset_path(), low_memory=False)
        valid_results = [r for r in proto.evaluate_ids(demo_ids, df_lookup) if "error" not in r]
        if len(valid_results) == 1:
            payload = build_api_response(valid_results[0])
        else:
            payload = build_batch_response(valid_results)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        sys.exit(0)

    # ---- Text output modes ----
    proto = PKLPrototype()
    df_lookup = pd.read_csv(_get_dataset_path(), low_memory=False)

    if args.mode == "qa":
        print("\n>>> REGRESSION TEST <<<")
        reg = proto.regression_test(demo_ids)
        if reg.get("all_pass") is None:
            print(f"  SKIPPED: {reg.get('skipped')}")
        else:
            print(f"  Overall: {'ALL PASS' if reg['all_pass'] else 'SOME FAILURES'}")
            print(f"  {'visit_id':>10} {'stored':>10} {'proto':>10} {'diff':>12} {'pred_match':>11} {'findings'}")
            print(f"  {'─'*10} {'─'*10} {'─'*10} {'─'*12} {'─'*11} {'─'*30}")
            for r in reg["results"]:
                sp = f"{r['stored_proba']:.6f}" if r['stored_proba'] else "N/A"
                pp = f"{r['proto_proba']:.6f}"
                df = f"{r['abs_diff']:.8f}" if r['abs_diff'] else "N/A"
                pm = "OK" if r['proba_match'] else "FAIL"
                print(f"  {r['visit_id']:>10} {sp:>10} {pp:>10} {df:>12} {pm:>11} {r['rule_ids'][:30]}")

        print("\n" + "=" * 60)
        print("PER-CLAIM QA DETAIL")
        print("=" * 60)
        for vid in demo_ids:
            print_demo_claim(proto, vid, df_lookup)

        print(f"\n{'='*50}")
        print("QA COMPLETE.")

    elif args.mode == "demo":
        print("=" * 50)
        print("BPJS CLAIM PRE-SUBMISSION SCREENING")
        print("Technical Prototype — Decision Support")
        print("=" * 50)
        print(f"Model   : Random Forest (61 features, threshold={THRESHOLD})")
        # print(f"Rules   : 9 VERIFIED_AUTOMATABLE (Permenkes 26/2021)")
        print(f"Scope   : Rawat Jalan, April–Mei 2026")
        # print(f"Disclaimer: Screening only — does not determine BPJS decision.")

        for vid in demo_ids:
            print_demo_claim(proto, vid, df_lookup)

        print(f"\n{'='*50}")
        print("SCREENING COMPLETE.")
