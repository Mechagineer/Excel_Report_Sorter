from typing import List, Dict, Tuple, Any
from pathlib import Path
import pandas as pd
import numpy as np
import os
import re
from datetime import datetime


def letter_to_index(letter: str) -> int:
    """
    Convert Excel column letter(s) (e.g., 'A', 'D', 'AA') to 0-based index.
    """
    letter = letter.upper()
    idx = 0
    for c in letter:
        if not ('A' <= c <= 'Z'):
            raise ValueError(f"Invalid column letter: {letter}")
        idx = idx * 26 + (ord(c) - ord('A') + 1)
    return idx - 1


def map_letters_to_columns(df: pd.DataFrame, letters: List[str]) -> Dict[str, str]:
    """
    Map Excel letters to DataFrame column names by position.
    Normalizes headers: strips, collapses multiple spaces.
    Returns dict like {"A": "HeaderA", ...}
    """
    # Find first non-empty row as header
    for i, row in df.iterrows():
        if not row.isnull().all():
            headers = [str(x).strip() if pd.notnull(x) else '' for x in row.values]
            headers = [re.sub(r'\s+', ' ', h) for h in headers]
            break
    else:
        raise ValueError("No non-empty header row found.")
    mapping = {}
    for letter in letters:
        idx = letter_to_index(letter)
        if idx >= len(headers) or not headers[idx]:
            mapping[letter] = None
        else:
            mapping[letter] = headers[idx]
    return mapping


def apply_string_filters(df: pd.DataFrame, contains: Dict[str, str], equals: Dict[str, List[str]]) -> pd.DataFrame:
    """
    Filter DataFrame by case-insensitive substring (contains) and/or equals (ANDed if both present).
    Keys are column names.
    """
    mask = pd.Series([True] * len(df))
    for col, substr in contains.items():
        if substr:
            mask &= df[col].astype(str).str.contains(substr, case=False, na=False)
    for col, eq_vals in equals.items():
        if eq_vals:
            mask &= df[col].isin(eq_vals)
    return df[mask].copy()


def apply_priority_sort(df: pd.DataFrame, orders: List[Tuple[str, str, bool]]) -> pd.DataFrame:
    """
    For each (column, priority_value, ascending):
      - Rows containing priority_value (case-insensitive) come first.
      - Then natural sort by column (asc/desc).
      - Stable across multiple keys.
    """
    df = df.copy()
    sort_keys = []
    for i, (col, val, asc) in enumerate(orders):
        match_col = f'_match_{i}'
        df[match_col] = df[col].astype(str).str.contains(val, case=False, na=False) if val else False
        sort_keys.append((match_col, False))  # Matches first
        sort_keys.append((col, asc))
    by = [k for k, _ in sort_keys]
    ascending = [asc for _, asc in sort_keys]
    df = df.sort_values(by=by, ascending=ascending, kind='stable')
    # Drop temp columns
    for i in range(len(orders)):
        del df[f'_match_{i}']
    return df


def coerce_u_numeric(df: pd.DataFrame, u_col: str) -> Tuple[pd.DataFrame, int]:
    """
    Coerce column u_col to numeric. Return (new_df, count of non-numeric values).
    """
    df = df.copy()
    coerced = pd.to_numeric(df[u_col], errors='coerce')
    non_numeric = coerced.isna() & df[u_col].notna()
    count = int(non_numeric.sum())
    df[u_col] = coerced
    return df, count


def compress_sum(df: pd.DataFrame, key_cols: List[str], sum_col: str, passthrough_cols: List[str]) -> pd.DataFrame:
    """
    Group by key_cols, sum sum_col (treat NaN as 0 only during aggregation),
    passthrough first non-null for passthrough_cols. Rename sum_col to 'Sum_U'.
    """
    df = df.copy()
    # Strip whitespace in key columns
    for col in key_cols:
        df[col] = df[col].astype(str).str.strip()
    group = df.groupby(key_cols, dropna=False)
    agg = {col: lambda x: next((v for v in x if pd.notnull(v)), None) for col in passthrough_cols}
    agg[sum_col] = lambda x: np.nansum(x.fillna(0))
    out = group.agg(agg).reset_index()
    out = out.rename(columns={sum_col: 'Sum_U'})
    return out


def get_downloads_dir() -> Path:
    """
    Return the user's Downloads directory (Windows, WSL, Linux/macOS, fallback ./out).
    """
    if os.name == 'nt':
        return Path(os.path.expandvars(r'%USERPROFILE%')) / 'Downloads'
    # WSL
    if 'WSL_DISTRO_NAME' in os.environ:
        win_home = os.environ.get('USERPROFILE')
        if win_home:
            return Path('/mnt/c/Users') / Path(win_home).name / 'Downloads'
        return Path.home() / 'Downloads'
    # Linux/macOS
    downloads = Path.home() / 'Downloads'
    if downloads.exists():
        return downloads
    return Path('./out')


def write_cleaned(df: pd.DataFrame, out_dir: Path, sheet_name: str = 'Cleaned') -> Path:
    """
    Write DataFrame to Excel in out_dir with timestamped filename. Returns Path.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_path = out_dir / f'Excel_Report_Sorter_{ts}.xlsx'
    with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return out_path


def validate_required_columns(mapping: Dict[str, str], required: List[str]) -> None:
    """
    Raise ValueError listing any missing required letters.
    """
    missing = [l for l in required if not mapping.get(l)]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
