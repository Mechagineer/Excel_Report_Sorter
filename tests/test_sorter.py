import pytest
import pandas as pd
from sorter import (
    letter_to_index, map_letters_to_columns, apply_string_filters, apply_priority_sort,
    coerce_u_numeric, compress_sum, get_downloads_dir, write_cleaned, validate_required_columns
)
from pathlib import Path
import tempfile

def make_df():
    # Simulate a DataFrame with header row and data
    data = [
        ["Acol", "Bcol", "Ccol", "Dcol", "Ecol", "Fcol", "Gcol", "Hcol", "Icol", "Jcol", "Kcol", "Lcol", "Mcol", "Ncol", "Ocol", "Pcol", "Qcol", "Rcol", "Scol", "Tcol", "Ucol"],
        ["8760", "x", "x", "8760", "foo", "x", "x", "bar", "g1", "x", "x", "x", "x", "h1", "x", "x", "x", "x", "x", "x", "10"],
        ["1234", "x", "x", "abcd", "foo", "x", "x", "baz", "g1", "x", "x", "x", "x", "h1", "x", "x", "x", "x", "x", "x", "notnum"],
        ["8760", "x", "x", "8760", "bar", "x", "x", "bar", "g2", "x", "x", "x", "x", "h2", "x", "x", "x", "x", "x", "x", "5"],
        ["", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""]
    ]
    return pd.DataFrame(data)

def test_letter_to_index():
    assert letter_to_index("A") == 0
    assert letter_to_index("D") == 3
    assert letter_to_index("AA") == 26
    assert letter_to_index("U") == 20
    with pytest.raises(ValueError):
        letter_to_index("1")

def test_map_letters_to_columns():
    df = make_df()
    mapping = map_letters_to_columns(df, ["A", "D", "E", "H", "I", "N", "U"])
    assert mapping["A"] == "Acol"
    assert mapping["D"] == "Dcol"
    assert mapping["U"] == "Ucol"

def test_apply_string_filters():
    df = make_df().iloc[1:]
    df.columns = make_df().iloc[0]
    contains = {"Acol": "8760", "Dcol": "", "Ecol": "", "Hcol": ""}
    equals = {"Acol": [], "Dcol": [], "Ecol": [], "Hcol": []}
    out = apply_string_filters(df, contains, equals)
    assert all(out["Acol"].str.contains("8760"))
    # Test equals filter
    eq = {"Acol": [], "Dcol": ["8760"], "Ecol": [], "Hcol": []}
    out2 = apply_string_filters(df, contains, eq)
    assert all(out2["Dcol"] == "8760")
    # Test AND
    contains = {"Acol": "8760", "Dcol": "8760", "Ecol": "", "Hcol": ""}
    eq = {"Acol": [], "Dcol": ["8760"], "Ecol": [], "Hcol": []}
    out3 = apply_string_filters(df, contains, eq)
    assert all((out3["Acol"] == "8760") & (out3["Dcol"] == "8760"))

def test_apply_priority_sort():
    df = make_df().iloc[1:]
    df.columns = make_df().iloc[0]
    orders = [("Acol", "8760", True), ("Dcol", "8760", True)]
    out = apply_priority_sort(df, orders)
    # Rows with '8760' in Acol should come first
    assert out.iloc[0]["Acol"] == "8760"
    # Stable sort: if all match, order by Dcol
    assert out.iloc[0]["Dcol"] == "8760"

def test_coerce_u_numeric():
    df = make_df().iloc[1:]
    df.columns = make_df().iloc[0]
    newdf, count = coerce_u_numeric(df, "Ucol")
    assert count == 1  # 'notnum' is non-numeric
    assert newdf["Ucol"].dtype.kind in 'fi'

def test_compress_sum():
    df = make_df().iloc[1:]
    df.columns = make_df().iloc[0]
    df["Ucol"] = pd.to_numeric(df["Ucol"], errors="coerce")
    out = compress_sum(df, ["Icol", "Ncol"], "Ucol", ["Acol", "Dcol", "Ecol", "Hcol"])
    # Should have two groups: (g1,h1), (g2,h2)
    assert len(out) == 2
    assert "Sum_U" in out.columns
    # First non-null passthrough
    assert out.iloc[0]["Acol"] == "8760"

def test_get_downloads_dir():
    d = get_downloads_dir()
    assert isinstance(d, Path)

def test_write_cleaned(tmp_path):
    df = make_df().iloc[1:]
    df.columns = make_df().iloc[0]
    out_path = write_cleaned(df, tmp_path)
    assert out_path.exists()
    # Check Excel file
    df2 = pd.read_excel(out_path)
    assert list(df2.columns) == list(df.columns)

def test_validate_required_columns():
    mapping = {"I": "Icol", "N": "Ncol", "U": "Ucol"}
    # Should not raise
    validate_required_columns(mapping, ["I", "N", "U"])
    mapping = {"I": None, "N": "Ncol", "U": "Ucol"}
    with pytest.raises(ValueError):
        validate_required_columns(mapping, ["I", "N", "U"])
