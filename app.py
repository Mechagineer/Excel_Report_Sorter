import streamlit as st
import pandas as pd
from pathlib import Path
from sorter import get_downloads_dir, write_cleaned
import re


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


def detect_column_by_header(df, prefer_index=None, patterns=None):
    """
    Return the column name that best matches any of the given patterns.
    - patterns: list of compiled regex or strings (case-insensitive).
    - prefer_index: 0-based index to use as a fallback if it's a good header.
    A 'good' header is not empty, not a single letter (A/B/…),
    and not an 'Unnamed:' placeholder.
    """
    cols = list(df.columns)
    # Normalize once
    norm = [str(c).strip() for c in cols]
    lower = [c.casefold() for c in norm]

    # 1) try pattern matches
    if patterns:
        compiled = [
            re.compile(p, re.IGNORECASE) if isinstance(p, str) else p
            for p in patterns
        ]
        scores = [0] * len(cols)
        for i, s in enumerate(norm):
            for rx in compiled:
                if rx.search(s):
                    scores[i] += 1
        if any(scores):
            best = max(range(len(cols)), key=lambda i: scores[i])
            return cols[best]

    def good_header(name: str) -> bool:
        s = name.strip()
        if not s: return False
        if s.lower().startswith("unnamed:"): return False
        # Treat single letter headers as low-quality (A, B, …)
        if len(s) == 1 and s.isalpha(): return False
        return True

    # 2) prefer the provided index if it looks good
    if prefer_index is not None and 0 <= prefer_index < len(cols):
        if good_header(norm[prefer_index]):
            return cols[prefer_index]

    # 3) otherwise pick the first 'good' header; fallback to last
    for i, s in enumerate(norm):
        if good_header(s):
            return cols[i]
    return cols[-1]


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

    # Auto-detect H by header text (robust) with a soft preference for the 8th column
    H = detect_column_by_header(
        df,
        prefer_index=7,  # 0-based: the 8th column if it looks like a real header
        patterns=[
            r"\bsales\s*clerk\b",          # "Sales clerk"
            r"\bclerk\b.*\bpartner\b",     # "clerk ... partner"
            r"\bpartner\b",                # catch "(partner)"
            r"\bsales\b.*\bpartner\b",
        ],
    )

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

    # --- COMBINE BY I & N, SUM R/S/T/U ---

    # Detect group keys by header text with soft positional preferences:
    # I (Invoice no.) ~ 9th column (0-based 8), N (Order no.) ~ 14th column (0-based 13).
    I_col = detect_column_by_header(
        df,
        prefer_index=8,
        patterns=[r"\binvoice\s*no\b", r"\binvoice\b", r"\binv\b"]
    )
    N_col = detect_column_by_header(
        df,
        prefer_index=13,
        patterns=[r"\border\s*no\b", r"\border\b", r"\border\s*#\b"]
    )

    # Detect numeric sum columns with safe fallbacks to letter positions:
    # R/S/T/U are approx columns 18–21 (0-based 17–20).
    sum_targets = [
        # (prefer_index, patterns)
        (17, [r"\bmaterial\b", r"\bmat(erial)?\b"]),
        (18, [r"\blabor\b", r"\bwage\b"]),
        (19, [r"\bfreight\b", r"\bshipping\b", r"\bother\b"]),
        (20, [r"\bcosts?\b", r"\btotal\b", r"\bamount\b"]),
    ]
    sum_cols = []
    for idx, pats in sum_targets:
        c = detect_column_by_header(df, prefer_index=idx, patterns=pats)
        if c not in (I_col, N_col) and c not in sum_cols:
            sum_cols.append(c)

    # Coerce to numeric (non-numeric → NaN)
    for c in sum_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Group and sum. Named aggregation avoids any key collisions.
    if sum_cols:
        agg_spec = {c: "sum" for c in sum_cols}
        result = df.groupby([I_col, N_col], dropna=False, as_index=False).agg(agg_spec)
        # Ensure column order: I, N, then summed columns
        result = result[[I_col, N_col] + sum_cols]
    else:
        # No sum columns detected: fall back to keeping the first row per group
        result = df.groupby([I_col, N_col], dropna=False, as_index=False).first()
        # Reorder to put I_col, N_col first
        other_cols = [c for c in result.columns if c not in (I_col, N_col)]
        result = result[[I_col, N_col] + other_cols]

    # Save the grouped result (single sheet 'Cleaned')
    out_path = write_cleaned(result, get_downloads_dir(), sheet_name="Cleaned")
    st.success(f"Saved to: {out_path}")
    st.caption(f"Rows in output: {len(result):,}")

except Exception as e:
    st.exception(e)
    st.stop()
