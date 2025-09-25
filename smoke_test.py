from pathlib import Path
import pandas as pd
from sorter import write_cleaned, get_downloads_dir

# Create sample data for MVP A-only
data = [
    {"A": "8760_sample", "B": "x"},
    {"A": "no", "B": "y"},
    {"A": "abc", "B": "g"},
    {"A": "8760", "B": "d"},
]

df = pd.DataFrame(data)
print("Initial rows:", len(df))

# Apply simple contains filter (simulate user input '8760')
df_filt = df[df['A'].astype(str).str.contains('8760', case=False, na=False)].copy()
print("After contains filter rows:", len(df_filt))

# Priority sort: matches first
df_filt['__match_A__'] = df_filt['A'].astype(str).str.contains('8760', case=False, na=False)
df_sort = df_filt.sort_values(['__match_A__', 'A'], ascending=[False, True], kind='mergesort')
df_sort.drop(columns=['__match_A__'], inplace=True, errors='ignore')

out_dir = get_downloads_dir()
out_path = write_cleaned(df_sort, out_dir, sheet_name='Cleaned')
print("Wrote output to:", out_path)

assert out_path.exists(), "Output file not found"
print("Smoke test passed: output file exists.")
