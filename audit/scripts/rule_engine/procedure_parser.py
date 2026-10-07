"""Procedure JSON parser for idrg/ina grouper response JSON blobs.
Extracts ICD-9-CM (procedure) or ICD-10 (diagnosis) codes from e-Claim JSON.
Supports: single code, multiple codes (separated by '#'), null, malformed JSON.
"""
import json
import math
import re
from typing import List, Optional

_ICD9_PATTERN = re.compile(r"^\d{2}\.\d{1,2}$")

def parse_codes_from_grouper_json(json_str: Optional[str], pattern=None) -> List[str]:
    """
    Extract codes from a grouper response JSON (procedure or diagnosis).

    JSON structure:
    {
      "data": {
        "string": "89.08#94.39",
        "expanded": [{"code":"89.08","display":"..."}, {"code":"94.39","display":"..."}]
      }
    }

    If pattern is None, all non-empty code strings are returned.
    If pattern is provided, only codes matching the regex are returned.

    Returns a list of code strings. Empty list if nothing found.
    """
    if json_str is None:
        return []
    if isinstance(json_str, float) and math.isnan(json_str):
        return []
    if not isinstance(json_str, str) or json_str.strip() == "":
        return []

    try:
        data = json.loads(json_str)
    except (json.JSONDecodeError, TypeError, ValueError):
        return []

    expanded = data.get("data", {}).get("expanded", [])
    if isinstance(expanded, list) and len(expanded) > 0:
        codes = []
        for item in expanded:
            if isinstance(item, dict):
                code = str(item.get("code", "")).strip()
                if code:
                    if pattern is None or pattern.match(code):
                        codes.append(code)
        if codes:
            return codes

    raw_str = data.get("data", {}).get("string", "")
    if not raw_str or not isinstance(raw_str, str):
        return []
    parts = raw_str.split("#")
    codes = [p.strip() for p in parts if p.strip()]
    if pattern is not None:
        codes = [c for c in codes if pattern.match(c)]
    return codes


def parse_procedure_codes(json_str: Optional[str]) -> List[str]:
    """Extract ICD-9-CM procedure codes only (XX.XX pattern)."""
    return parse_codes_from_grouper_json(json_str, pattern=_ICD9_PATTERN)


def parse_any_codes(json_str: Optional[str]) -> List[str]:
    """Extract any codes from grouper JSON (no pattern filter)."""
    return parse_codes_from_grouper_json(json_str, pattern=None)
