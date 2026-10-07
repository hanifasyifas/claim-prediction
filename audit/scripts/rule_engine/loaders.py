"""Rule engine loaders: ICD-10 and ICD-9-CM reference dictionaries.

Reference files berada di `audit/reference_data/` (disertakan di repository).
Path dihitung relatif terhadap lokasi file ini agar portabel di mesin mana pun.
"""
import pandas as pd
from pathlib import Path

# audit/scripts/rule_engine/loaders.py -> audit/
_AUDIT_DIR = Path(__file__).resolve().parent.parent.parent
_REFERENCE_DIR = _AUDIT_DIR / "reference_data"

# Nama file referensi (bisa .xlsx atau .csv)
_ICD10_XLSX = _REFERENCE_DIR / "icd10_master.xlsx"
_ICD9CM_XLSX = _REFERENCE_DIR / "icd9cm_master.xlsx"


def _read_reference(path_xlsx: Path) -> pd.DataFrame:
    """Baca file referensi (mendukung .xlsx; fallback .csv jika ada)."""
    if path_xlsx.exists():
        return pd.read_excel(path_xlsx)
    path_csv = path_xlsx.with_suffix(".csv")
    if path_csv.exists():
        return pd.read_csv(path_csv)
    raise FileNotFoundError(
        f"File referensi tidak ditemukan: {path_xlsx}\n"
        f"Pastikan folder 'audit/reference_data/' tersedia."
    )


def load_icd10_codes() -> dict:
    """Muat master ICD-10. Mengembalikan dict {code: display}."""
    df = _read_reference(_ICD10_XLSX)
    codes = {}
    for _, row in df.iterrows():
        code = str(row["CODE"]).strip().upper()
        display = str(row["DISPLAY"]) if pd.notna(row.get("DISPLAY")) else ""
        codes[code] = display
    return codes


def load_icd9cm_codes() -> dict:
    """Muat master ICD-9-CM. Mengembalikan dict {code: display}."""
    df = _read_reference(_ICD9CM_XLSX)
    codes = {}
    for _, row in df.iterrows():
        code = str(row["CODE"]).strip()
        display = str(row["DISPLAY"]) if pd.notna(row.get("DISPLAY")) else ""
        codes[code] = display
    return codes
