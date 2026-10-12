"""
Dashboard UI — Sistem Skrining Risiko Klaim Pending BPJS
================================================================
Antarmuka web (Streamlit) untuk:
  1. Memasukkan sampel klaim (pilih ID atau input manual)
  2. Menampilkan keluaran model ML (skor risiko Pending)
  3. Menampilkan temuan rule engine (validasi koding INA-CBG)

Jalankan:
    cd audit/scripts
    streamlit run dashboard.py
"""
import importlib.util
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# ============================================================
# Path (portabel) + agar modul sibling bisa di-import
# ============================================================
SCRIPTS_DIR = Path(__file__).resolve().parent
AUDIT_DIR = SCRIPTS_DIR.parent
OUT_DIR = AUDIT_DIR / "outputs"
REFERENCE_DIR = AUDIT_DIR / "reference_data"
THRESHOLD = 0.50

sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(SCRIPTS_DIR / "rule_engine"))


# ============================================================
# Loader (cached)
# ============================================================
@st.cache_resource(show_spinner="Memuat model & rule engine...")
def load_prototype():
    spec = importlib.util.spec_from_file_location(
        "pkl_prototype_mod", SCRIPTS_DIR / "19_pkl_prototype.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.PKLPrototype(verbose=False)


@st.cache_data(show_spinner="Memuat data klaim...")
def load_claims():
    full = OUT_DIR / "phase2_labeled_dataset.csv"
    sample = REFERENCE_DIR / "sample_claims.csv"
    path = full if full.exists() else sample
    return pd.read_csv(path, low_memory=False)


# ============================================================
# UI config
# ============================================================
st.set_page_config(
    page_title="Skrining Risiko Klaim Pending BPJS",
    page_icon="🏥",
    layout="wide",
)

SEVERITY_COLOR = {"INFO": "🔵", "WARNING": "🟠", "HIGH": "🔴"}

# ============================================================
# Header
# ============================================================
st.title("🏥 Sistem Skrining Risiko Klaim Pending BPJS")
st.caption(
    "Technical Prototype — alat bantu pendukung keputusan (bukan pengambil keputusan otomatis). "
    "Menampilkan **skor risiko model ML** dan **temuan rule engine** secara terpisah."
)

proto = load_prototype()
claims = load_claims()

# ============================================================
# Sidebar
# ============================================================
with st.sidebar:
    st.header("ℹ️ Informasi Sistem")

    st.markdown("**Model ML**")
    st.markdown("- Algoritma: Random Forest")
    st.markdown("- Fitur: 61")
    st.markdown(f"- Threshold: {THRESHOLD}")
    st.markdown("- Data latih: April (3.870 klaim)")

    st.divider()
    st.markdown("**Rule Engine**")
    st.markdown("- 9 aturan validasi koding")
    st.markdown("- Sumber: Permenkes 26/2021")

    st.divider()
    st.markdown("**Performa (Holdout Mei)**")
    st.markdown("- Recall: 44,0%")
    st.markdown("- Precision: 19,6%")
    st.markdown("- PR-AUC: 0,2049")

    st.divider()
    st.caption(
        "⚠️ Sistem ini TIDAK menentukan keputusan BPJS. "
        "Skor ML berasal dari pola historis; rule engine memvalidasi kepatuhan koding."
    )

# ============================================================
# Input klaim
# ============================================================
st.subheader("① Pilih Klaim")

# Turunkan bulan dari tanggal (April = data latih, Mei = holdout/uji)
if "date" in claims.columns:
    claims["_month"] = pd.to_datetime(claims["date"], errors="coerce").dt.month
else:
    claims["_month"] = pd.NA
has_month = claims["_month"].notna().any()

month_label = st.radio(
    "Bulan:",
    ["Mei — data uji (holdout)", "April — data latih"],
    horizontal=True,
    help="Mei = klaim yang belum pernah dilihat model (evaluasi jujur). "
         "April = klaim yang dipakai melatih model (bukan untuk evaluasi).",
)
selected_month = 5 if month_label.startswith("Mei") else 4

pool = claims[claims["_month"] == selected_month] if has_month else claims

col_a, col_b = st.columns([2, 1])
with col_a:
    available_ids = pool["id"].astype(int).tolist()
    selected = st.selectbox("Pilih ID klaim:", available_ids) if available_ids else None
with col_b:
    manual = st.text_input("Atau ketik ID manual:", value="")

claim_id = None
if manual.strip():
    try:
        claim_id = int(manual.strip())
    except ValueError:
        st.error("ID harus berupa angka.")
else:
    claim_id = selected

if claim_id is None:
    st.stop()

match = claims[claims["id"] == claim_id]
if len(match) == 0:
    st.error(f"ID {claim_id} tidak ditemukan di dataset.")
    st.stop()

raw_row = match.iloc[0].to_dict()
claim_month = int(match.iloc[0]["_month"]) if pd.notna(match.iloc[0]["_month"]) else None

# ============================================================
# Inferensi
# ============================================================
result = proto.evaluate_claim(raw_row)
risk = result["risk"]
findings = result["validation"]["findings"]

# ============================================================
# ② Risk Screening
# ============================================================
st.divider()
st.subheader("② Risk Screening (Model ML)")

actual = None
if "target" in match.columns:
    actual = "Pending" if int(match.iloc[0]["target"]) == 1 else "Claimed"

# Badge: data latih vs data uji (konteks metodologis)
if claim_month == 5:
    st.info(
        "🔬 **KLAIM DATA UJI (MEI)** — model belum pernah melihat klaim ini. "
        "Cocok untuk menilai performa secara jujur."
    )
elif claim_month == 4:
    st.warning(
        "📚 **KLAIM DATA LATIH (APRIL)** — model sudah dilatih dengan klaim ini. "
        "Skor cenderung optimistis; **bukan** untuk evaluasi. Disarankan pilih klaim Mei."
    )

info_cols = st.columns(3)
info_cols[0].metric("Claim ID", str(claim_id))
info_cols[1].metric(
    "Bulan",
    "Mei (uji)" if claim_month == 5 else ("April (latih)" if claim_month == 4 else "-"),
)
if actual is not None:
    info_cols[2].metric("Historical Actual", actual)

c1, c2, c3 = st.columns(3)
c1.metric("Pending Risk", f"{risk['probability']*100:.1f}%")
c2.metric("Threshold", f"{THRESHOLD:.2f}")
c3.metric("Recommendation", risk["recommendation"])

if risk["recommendation"] == "REVIEW":
    st.warning(
        f"⚠️ **REVIEW** — Klaim ini memiliki risiko Pending **{risk['probability']*100:.1f}%** "
        f"(di atas threshold {THRESHOLD}). Disarankan ditinjau sebelum pengiriman."
    )
else:
    st.success(
        f"✅ **OK** — Klaim ini memiliki risiko Pending **{risk['probability']*100:.1f}%** "
        f"(di bawah threshold {THRESHOLD})."
    )

st.progress(min(max(risk["probability"], 0.0), 1.0))

# ============================================================
# ③ Validation Findings
# ============================================================
st.divider()
st.subheader("③ Validation Findings (Rule Engine)")
st.caption("Temuan validasi kepatuhan koding INA-CBG (Permenkes No. 26 Tahun 2021).")

if findings:
    for f in findings:
        icon = SEVERITY_COLOR.get(f["severity"], "⚪")
        with st.container(border=True):
            st.markdown(
                f"{icon} **{f['rule_id']} — {f['rule_name']}** "
                f"&nbsp;&nbsp; `{f['severity']}` &nbsp; `{f['category']}`"
            )
            st.markdown(f"**Pesan:** {f['message']}")
            st.markdown(f"**Saran:** {f['suggestion']}")
            st.caption(f"Sumber: {f['source_reference']}")
else:
    st.info("Tidak ada temuan validasi. Semua pemeriksaan LULUS.")

# ============================================================
# Detail teknis (expander)
# ============================================================
with st.expander("🔍 Detail teknis (data mentah & penjelasan)"):
    st.markdown("**Catatan penting:**")
    st.markdown(
        "- Skor dari model ML bersifat **probabilistik** — menjelaskan pola historis, "
        "bukan alasan BPJS mem-pending klaim.\n"
        "- Rule engine bersifat **deterministik** — memvalidasi kepatuhan koding, "
        "bukan memprediksi Pending.\n"
        "- Kedua komponen **independen** (tidak saling memengaruhi)."
    )
    st.markdown("**Data mentah klaim (field terpilih):**")
    show_cols = [c for c in ["id", "date", "exit_date", "cbg_code",
                             "bpjs_diagnosa_awal_code", "bpjs_tgl_sep", "clinic_id"] if c in raw_row]
    st.json({k: (str(raw_row[k]) if pd.notna(raw_row[k]) else None) for k in show_cols})
