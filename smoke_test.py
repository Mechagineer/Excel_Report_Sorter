from pathlib import Path
import pandas as pd
from sorter import apply_string_filters, apply_priority_sort, coerce_u_numeric, compress_sum, write_cleaned, get_downloads_dir

# Create sample data
data = [
    {"A": "8760_sample", "D": "x", "E": "y", "H": "h1", "I": "G1", "N": "N1", "U": 10},
    {"A": "no", "D": "8760", "E": "y", "H": "h2", "I": "G1", "N": "N1", "U": 5},
    {"A": "abc", "D": "def", "E": "g", "H": "h3", "I": "G2", "N": "N2", "U": "notnum"},
    {"A": "8760", "D": "d", "E": "e", "H": "h4", "I": "G2", "N": "N2", "U": 3},
]

df = pd.DataFrame(data)
print("Initial rows:", len(df))

# Apply contains filters: default A contains '8760'
contains = {"A": "8760", "D": "", "E": "", "H": ""}
equals = {"A": [], "D": [], "E": [], "H": []}

df_filt = apply_string_filters(df, contains, equals)
print("After contains filter rows:", len(df_filt))

# Priority sort: A priority '8760'
orders = [("A", "8760", True)]
df_sort = apply_priority_sort(df_filt, orders)
print("After priority sort rows:", len(df_sort))

# Coerce U numeric
df_num, nonnum_count = coerce_u_numeric(df_sort, "U")
print("Non-numeric U count:", nonnum_count)

# Compress/group by I,N and sum U
df_out = compress_sum(df_num, ["I", "N"], "U", ["A", "D", "E", "H"])
print("Groups produced:", len(df_out))
print(df_out)

# Write output to the user's Downloads directory
out_dir = get_downloads_dir()
out_path = write_cleaned(df_out, out_dir, sheet_name="Cleaned")
print("Wrote output to:", out_path)

# Quick checks
assert out_path.exists(), "Output file not found"
print("Smoke test passed: output file exists.")
