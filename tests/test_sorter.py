import pytest
import pandas as pd
from sorter import (
    letter_to_index, map_letters_to_columns, get_downloads_dir, write_cleaned
)
from pathlib import Path

def make_df():
    # Minimal header and data suitable for A-only MVP tests
    data = [
        ["Acol", "Bcol", "Ucol"],
        ["8760", "x", 10],
        ["no", "y", 5],
        ["8760_sample", "z", 3],
    ]
    return pd.DataFrame(data)

def test_letter_to_index():
    assert letter_to_index("A") == 0
    assert letter_to_index("B") == 1
    assert letter_to_index("Z") == 25
    with pytest.raises(ValueError):
        letter_to_index("1")

def test_map_letters_to_columns():
    df = make_df()
    # map_letters_to_columns is expected to pick header names when given header row
    mapping = map_letters_to_columns(df, ["A"])
    assert mapping["A"] == "Acol"

def test_get_downloads_dir():
    d = get_downloads_dir()
    assert isinstance(d, Path)

def test_write_cleaned(tmp_path):
    df = make_df().iloc[1:]
    df.columns = make_df().iloc[0]
    out_path = write_cleaned(df, tmp_path)
    assert out_path.exists()
    # Check Excel file round-trip
    df2 = pd.read_excel(out_path)
    assert list(df2.columns) == list(df.columns)
