import streamlit as st
import pandas as pd
from pathlib import Path
from sorter import get_downloads_dir, write_cleaned
import re
import time
import requests


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


def normalize_object_id(x: str) -> str:
    """SAP CRM OBJECT_ID is 10-char, zero-padded (e.g., 0083756738)."""
    return str(x).strip().zfill(10)


class CRMApi:
    """
    GET {base_url}/crm/transactions/{object_id}/internalNotice?lang=EN
    Returns internal_notice (string) or "".
    """
    def __init__(self, base_url: str, lang: str = "EN", auth=None, rate_limit_hz: float = 2.0, timeout: int = 15):
        self.base_url = base_url.rstrip("/")
        self.lang = lang
        self.auth = auth
        self.timeout = timeout
        self._min_interval = 1.0 / max(0.1, rate_limit_hz)
        self._last = 0.0

    def _throttle(self):
        wait = self._min_interval - (time.perf_counter() - self._last)
        if wait > 0:
            time.sleep(wait)
        self._last = time.perf_counter()

    def get_internal_notice(self, object_id: str) -> str:
        oid = normalize_object_id(object_id)
        self._throttle()
        url = f"{self.base_url}/crm/transactions/{oid}/internalNotice"
        params = {"lang": self.lang}
        for attempt in range(3):
            try:
                r = requests.get(url, params=params, auth=self.auth, timeout=self.timeout)
                if r.status_code == 200:
                    data = r.json()
                    return (data.get("internal_notice") or "").strip()
                if r.status_code in (400, 404):
                    return ""
                if r.status_code in (401, 403):
                    raise PermissionError(f"Unauthorized or forbidden ({r.status_code})")
                time.sleep(1.5 * (attempt + 1))
            except requests.RequestException:
                time.sleep(1.5 * (attempt + 1))
        return ""


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

# Optional SAP CRM API controls
with st.expander("SAP CRM API (optional)", expanded=False):
    env = st.selectbox("Environment", ["Skip API", "PCR"], index=0)
    presets = {"PCR": "https://<pcr-host>/sap/your-gateway-or-icf"}
    base_url = st.text_input("Base URL", value=presets.get(env, ""), placeholder="https://.../sap/...")
    lang = st.text_input("Language", value="EN")
    use_basic = st.checkbox("Use Basic auth (service user)")
    user = pwd = ""
    if use_basic:
        user = st.text_input("User", value="", placeholder="svc_crm_reader")
        pwd = st.text_input("Password", value="", type="password")

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

    # --- (Optional) SAP CRM enrichment BEFORE grouping ---
    # Detect N (Order no.) and G (7th column) for per-row filling
    N_col = detect_column_by_header(
        df, prefer_index=13, patterns=[r"\border\s*no\b", r"\border\b", r"\border\s*#\b"]
    )
    G_col = df.columns[6] if df.shape[1] >= 7 else None  # Column G if present

    if base_url.strip() and env == "PCR":
        auth = (user, pwd) if (use_basic and user and pwd) else None
        api = CRMApi(base_url=base_url, lang=lang, auth=auth, rate_limit_hz=2.0, timeout=15)

        # Unique N (normalized) from the filtered df
        orders = (
            df[N_col]
            .dropna()
            .astype(str)
            .map(normalize_object_id)
            .unique()
            .tolist()
        )

        notice_map = {}
        if orders:
            progress = st.progress(0.0, text="Fetching Internal notice from SAP CRM (PCR)...")
            total = len(orders)
            for i, oid in enumerate(orders, 1):
                notice_map[oid] = api.get_internal_notice(oid)
                progress.progress(i / total, text=f"Fetched {i}/{total}")
            progress.empty()

        # Write notice into:
        # 1) Column G per row (if G exists),
        # 2) Also create/refresh 'Internal notice' column (for clarity).
        df["_N_norm_"] = df[N_col].astype(str).map(normalize_object_id)
        df["Internal notice"] = df["_N_norm_"].map(notice_map).fillna("")
        if G_col is not None:
            df[G_col] = df["Internal notice"]
        df.drop(columns=["_N_norm_"], inplace=True, errors="ignore")
    else:
        # If API not configured, ensure the 'Internal notice' column exists (empty)
        if "Internal notice" not in df.columns:
            df["Internal notice"] = ""

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
        # Preserve the per-row notice in the grouped output
        if "Internal notice" in df.columns and "Internal notice" not in sum_cols:
            agg_spec["Internal notice"] = "first"
        if G_col is not None and G_col in df.columns and G_col not in sum_cols:
            agg_spec[G_col] = "first"

        result = df.groupby([I_col, N_col], dropna=False, as_index=False).agg(agg_spec)
        # Ensure column order: I, N, then summed columns (and preserved fields)
        ordered = [I_col, N_col] + [c for c in sum_cols]
        # Append preserved fields if present and not already included
        for extra in ("Internal notice", G_col):
            if extra and extra in result.columns and extra not in ordered:
                ordered.append(extra)
        result = result[ordered]
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
