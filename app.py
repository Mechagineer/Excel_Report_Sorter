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
    df.columns = normalize_headers(df.columns.tolist())
except Exception as e:
    st.error(f"File error: {e}")
    st.stop()


st.subheader("MVP controls (A-only)")

with st.form("mvp_controls"):
    # Auto-detect A as the first normalized header
    st.caption(f"A column (auto-detected): **{df.columns[0] if df.shape[1] > 0 else 'N/A'}**")
    filter_A = st.text_input("Contains for A", value="8760")
    submitted = st.form_submit_button("Process")

if not submitted:
    st.stop()

try:
    # Auto-detect A as first column after normalization
    if df.shape[1] == 0:
        st.error("No columns detected in the selected sheet.")
        st.stop()
    A = df.columns[0]

    # Filter on A (contains), preserve original row order
    if filter_A:
        df = df[df[A].astype(str).str.contains(filter_A, case=False, na=False)]

    # Write a single sheet named 'Cleaned' (no grouping/summing)
    out_path = write_cleaned(df, get_downloads_dir(), sheet_name="Cleaned")
    st.success(f"Saved to: {out_path}")

    # Download removed: file is saved automatically to Downloads (see guardrails)

except Exception as e:
    st.exception(e)
    st.stop()
