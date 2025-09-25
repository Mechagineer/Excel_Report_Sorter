import streamlit as st
import pandas as pd
from pathlib import Path
from io import BytesIO
from sorter import (
    letter_to_index, map_letters_to_columns, apply_string_filters, apply_priority_sort,
    coerce_u_numeric, compress_sum, get_downloads_dir, write_cleaned, validate_required_columns
)
import tempfile

LETTERS = ["A", "D", "E", "H", "I", "N", "U"]
FILTER_LETTERS = ["A", "D", "E", "H"]
GROUP_LETTERS = ["I", "N"]
SUM_LETTER = "U"
DEFAULT_STRING = "8760"

st.set_page_config(page_title="Excel Report Sorter", layout="wide")
st.title("Excel Report Sorter")
st.markdown("""
Upload an Excel file (.xlsx). Configure filters and sorts for columns A, D, E, H (by letter, not name).
Rows are grouped by I & N, summing U. Output is a single cleaned Excel file in your Downloads folder and as a download button below.
""")

uploaded = st.file_uploader("Upload Excel file", type=["xlsx"])
if uploaded:
    try:
        # Read all sheets, let user pick
        xls = pd.ExcelFile(uploaded)
        sheet = st.selectbox("Select sheet", xls.sheet_names)
        df_raw = xls.parse(sheet, header=None, dtype=str)
        # Map letters to columns
        mapping = map_letters_to_columns(df_raw, LETTERS)
        # Show detected names, allow override
        st.subheader("Column Mapping (by Excel letter)")
        col_map = {}
        for l in LETTERS:
            options = list(df_raw.iloc[0].dropna().unique())
            detected = mapping[l] if mapping[l] else "(missing)"
            col_map[l] = st.selectbox(f"{l} (detected: {detected})", options, index=options.index(detected) if detected in options else 0, key=f"map_{l}") if mapping[l] else st.selectbox(f"{l} (missing)", options, key=f"map_{l}")
        # Validate required columns
        try:
            validate_required_columns(col_map, ["I", "N", "U"])
        except ValueError as e:
            st.error(str(e))
            st.stop()
        # DataFrame with headers
        df = df_raw.iloc[1:].copy()
        df.columns = [col_map.get(l, f"col_{i}") for i, l in enumerate(df_raw.iloc[0])]
        # Filter widgets
        st.subheader("Filters and Sorts")
        contains = {}
        equals = {}
        sort_orders = []
        sort_priority = []
        for l in FILTER_LETTERS:
            col = col_map[l]
            st.markdown(f"**Column {l} ({col})**")
            cval = st.text_input(f"Contains (default '{DEFAULT_STRING}')", value=DEFAULT_STRING, key=f"contains_{l}")
            contains[col] = cval
            unique_vals = sorted(df[col].dropna().unique())
            eqval = st.multiselect(f"Equals (optional)", unique_vals, key=f"equals_{l}")
            equals[col] = eqval
            sval = st.text_input(f"Priority sort value (default '{DEFAULT_STRING}')", value=DEFAULT_STRING, key=f"sortval_{l}")
            asc = st.radio(f"Sort order", ["Ascending", "Descending"], index=0, key=f"asc_{l}") == "Ascending"
            sort_priority.append((l, col, sval, asc))
        # Let user set sort order
        st.markdown("**Set sort priority order (drag to reorder):**")
        sort_order = st.multiselect("Sort order (top = highest priority)", [f"{l} ({col_map[l]})" for l in FILTER_LETTERS], default=[f"{l} ({col_map[l]})" for l in FILTER_LETTERS], key="sort_order")
        # Map back to tuples
        sort_orders = []
        for item in sort_order:
            l = item.split()[0]
            for tpl in sort_priority:
                if tpl[0] == l:
                    sort_orders.append((tpl[1], tpl[2], tpl[3]))
        if st.button("Process"):
            try:
                # Apply filters
                df_filt = apply_string_filters(df, contains, equals)
                # Apply priority sort
                df_sort = apply_priority_sort(df_filt, sort_orders)
                # Coerce U to numeric
                df_num, nonnum_count = coerce_u_numeric(df_sort, col_map[SUM_LETTER])
                # Compress/group
                df_out = compress_sum(df_num, [col_map[k] for k in GROUP_LETTERS], col_map[SUM_LETTER], [col_map[l] for l in FILTER_LETTERS])
                # Write output
                out_dir = get_downloads_dir()
                out_path = write_cleaned(df_out, out_dir)
                # Download button
                with open(out_path, "rb") as f:
                    st.download_button("Download Cleaned Excel", f, file_name=out_path.name)
                # Run summary
                st.success(f"Input rows: {len(df)} | Filtered: {len(df_filt)} | Groups: {len(df_out)} | Total Sum_U: {df_out['Sum_U'].sum()} | Non-numeric U: {nonnum_count}")
            except Exception as e:
                st.error(f"Processing error: {e}")
    except Exception as e:
        st.error(f"File error: {e}")
