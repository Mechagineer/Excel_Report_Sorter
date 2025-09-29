import streamlit as st
import pandas as pd
from pathlib import Path
from sorter import get_downloads_dir, write_cleaned


def normalize_headers(cols):
    return [(" ".join(str(c).split())).strip() for c in cols]


def safe_col(df, name: str):
    if name in df.columns:
        return name
    target = str(name).strip().casefold()
    for c in df.columns:
        if str(c).strip().casefold() == target:
            return c
    raise KeyError(name)


st.set_page_config(page_title="Excel Report Sorter (MVP A-only)", layout="wide")
st.title("Excel Report Sorter — MVP (A-only)")
st.markdown("""
This simplified MVP supports only column A: a case-insensitive "contains" filter and a priority sort (matches first, then natural order).
Output is the filtered/sorted rows written as a single sheet named `Cleaned`.
""")

uploaded = st.file_uploader("Upload Excel file", type=["xlsx"])
if not uploaded:
    st.info("Upload an Excel file to begin.")
    st.stop()

try:
    xls = pd.ExcelFile(uploaded)
    sheet = st.selectbox("Select sheet", xls.sheet_names)
    df = xls.parse(sheet, header=0, dtype=str)

    # Normalize headers once
    df.columns = normalize_headers(df.columns.tolist())
    if df.shape[1] == 0:
        st.error("No columns detected in the selected sheet.")
        st.stop()

    # Auto-detect A = first column
    A = df.columns[0]

    # Auto-detect H = 8th column if present; otherwise heuristic, else last col
    if df.shape[1] >= 8:
        H = df.columns[7]
    else:
        H = next((c for c in df.columns if "sales clerk" in str(c).casefold()), None) \
            or next((c for c in df.columns if "partner" in str(c).casefold()), None)
        if not H:
            H = df.columns[-1]

except Exception as e:
    st.error(f"File error: {e}")
    st.stop()


# Prepare H options (stringified, blanks placeholder)
H_SERIES = df[H].astype("string")
H_DISPLAY = H_SERIES.fillna("(blank)")
H_options = sorted(H_DISPLAY.unique().tolist())

st.subheader("MVP controls (A + H)")

with st.form("mvp_controls"):
    st.caption(f"A column (auto-detected): **{A}**")
    filter_A = st.text_input("Contains for A", value="8760")

    st.caption(f"H column (auto-detected): **{H}**")
    keep_H = st.multiselect("Keep rows where H is one of:", options=H_options, default=H_options)

    submitted = st.form_submit_button("Process")

if not submitted:
    st.stop()

try:
    # Normalize H same as options
    H_norm = df[H].astype("string").fillna("(blank)")

    # A mask: if empty, treat as "no restriction" (all False)
    if filter_A:
        mask_a = df[A].astype(str).str.contains(filter_A, case=False, na=False)
    else:
        mask_a = pd.Series(False, index=df.index)

    # H mask: only restrict if user picked a subset; else "no restriction"
    if keep_H and len(keep_H) < len(H_options):
        mask_h = H_norm.isin(keep_H)
    else:
        mask_h = pd.Series(False, index=df.index)

    # Combine with OR
    combined = mask_a | mask_h

    # If both are "no restriction" (all False), keep everything
    if not combined.any():
        combined = pd.Series(True, index=df.index)

    # Apply filter (preserve row order)
    df = df.loc[combined]

    # Save single sheet 'Cleaned' to Downloads
    out_path = write_cleaned(df, get_downloads_dir(), sheet_name="Cleaned")
    st.success(f"Saved to: {out_path}")
    st.caption(f"Rows in output: {len(df):,}")

except Exception as e:
    st.exception(e)
    st.stop()
