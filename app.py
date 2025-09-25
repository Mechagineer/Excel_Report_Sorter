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
        import streamlit as st
        import pandas as pd
        from pathlib import Path
        from io import BytesIO
        from sorter import get_downloads_dir, write_cleaned


        def normalize_headers(cols):
            # trim and collapse whitespace
            return [(" ".join(str(c).split())).strip() for c in cols]


        def safe_col(df, name: str):
            # tolerant resolution for dropdown-selected names
            if name in df.columns:
                return name
            target = str(name).strip().casefold()
            for c in df.columns:
                if str(c).strip().casefold() == target:
                    return c
            raise KeyError(name)


        st.set_page_config(page_title="Excel Report Sorter", layout="wide")
        st.title("Excel Report Sorter")
        st.markdown(
            """
        Upload an Excel file (.xlsx). Configure filters and sorts for columns A, D, E, H (by letter, not name).
        Rows are grouped by I & N, summing U. Output is a single cleaned Excel file in your Downloads folder and as a download button below.
        """
        )

        uploaded = st.file_uploader("Upload Excel file", type=["xlsx"])
        if not uploaded:
            st.info("Upload an Excel file to begin.")
            st.stop()

        try:
            xls = pd.ExcelFile(uploaded)
            sheet = st.selectbox("Select sheet", xls.sheet_names)
            # read with header row (first row as header)
            df = xls.parse(sheet, header=0, dtype=str)

            # normalize headers once and reuse
            df.columns = normalize_headers(df.columns.tolist())

        except Exception as e:
            st.error(f"File error: {e}")
            st.stop()


        with st.form("controls"):
            # mapping dropdowns; list(df.columns) is the source of truth
            col_A = st.selectbox("A (filter/sort)", options=list(df.columns), key="map_A")
            col_D = st.selectbox("D (filter/sort)", options=list(df.columns), key="map_D")
            col_E = st.selectbox("E (filter/sort)", options=list(df.columns), key="map_E")
            col_H = st.selectbox("H (filter/sort)", options=list(df.columns), key="map_H")
            col_I = st.selectbox("I (group key)",  options=list(df.columns), key="map_I")
            col_N = st.selectbox("N (group key)",  options=list(df.columns), key="map_N")
            col_U = st.selectbox("U (sum col)",    options=list(df.columns), key="map_U")

            # editable defaults for filters (contains) and priority sort
            fA = st.text_input("Contains for A", value="8760")
            fD = st.text_input("Contains for D", value="")
            fE = st.text_input("Contains for E", value="")
            fH = st.text_input("Contains for H", value="")

            sA = st.text_input("Priority sort string for A", value="8760")
            sD = st.text_input("Priority sort string for D", value="")
            sE = st.text_input("Priority sort string for E", value="")
            sH = st.text_input("Priority sort string for H", value="")

            asc_A = st.checkbox("A ascending", True)
            asc_D = st.checkbox("D ascending", True)
            asc_E = st.checkbox("E ascending", True)
            asc_H = st.checkbox("H ascending", True)

            submitted = st.form_submit_button("Process")

        if not submitted:
            st.stop()

        try:
            # resolve columns safely
            A, D, E, H = (safe_col(df, col_A), safe_col(df, col_D), safe_col(df, col_E), safe_col(df, col_H))
            I, N, U    = (safe_col(df, col_I), safe_col(df, col_N), safe_col(df, col_U))

            # apply "contains" filters if provided
            for col, val in [(A, fA), (D, fD), (E, fE), (H, fH)]:
                if val:
                    df = df[df[col].astype(str).str.contains(val, case=False, na=False)]

            # priority sort: matches first, then natural order; stable multi-key
            order_cols, asc_flags, temp_flags = [], [], []
            for col, pval, asc in [(A, sA, asc_A), (D, sD, asc_D), (E, sE, asc_E), (H, sH, asc_H)]:
                if pval:
                    flag = f"__match__{col}"
                    df[flag] = df[col].astype(str).str.contains(pval, case=False, na=False)
                    order_cols += [flag, col]
                    asc_flags  += [False, asc]
                    temp_flags.append(flag)
            if order_cols:
                df = df.sort_values(order_cols, ascending=asc_flags, kind="mergesort")
                df.drop(columns=temp_flags, inplace=True, errors="ignore")

            # group by I & N, sum U
            df[U] = pd.to_numeric(df[U], errors="coerce")
            result = df.groupby([I, N], dropna=False, as_index=False).agg(
                Sum_U=(U, "sum"),
                A_first=(A, "first"),
                D_first=(D, "first"),
                E_first=(E, "first"),
                H_first=(H, "first"),
            )

            # write single 'Cleaned' sheet + download
            out_path = write_cleaned(result, get_downloads_dir(), sheet_name="Cleaned")
            st.success(f"Saved to: {out_path}")

            # prepare bytes for download button
            buf = BytesIO()
            result.to_excel(buf, index=False, engine="openpyxl")
            buf.seek(0)
            st.download_button(
                "Download cleaned file",
                data=buf.getvalue(),
                file_name=Path(out_path).name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        except KeyError as e:
            st.error(f"Column not found: {e}. Please re-select the correct column and try again.")
            st.stop()
        except Exception as e:
           st.exception(e)
           st.stop()
