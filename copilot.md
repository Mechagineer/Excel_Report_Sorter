# copilot.md

## 🎯 Product Brief

Build a minimal local app that lets a user **drag & drop an Excel file** and outputs **one cleaned Excel**.
**Columns of interest (by Excel letters):**

* **Filters & Sorts (string-based, editable):** **A, D, E, H**
* **Compression (grouping keys):** **I & N** (rows are merged when both match)
* **Aggregation:** **sum U** during compression
* **Default string value:** `"8760"` prefilled for both **filter** (“contains”) and **priority sort**, but **fully editable** per column.

**Output:** one worksheet named **`Cleaned`** saved to the user’s **Downloads** + Download button in the UI.

---

## 🧱 Tech Stack

* **Python 3.11+**
* **pandas**, **openpyxl**
* **Streamlit** (GUI / drag-drop)
* **pytest** (tests)
* **PyInstaller** (Windows `.exe` packaging)

---

## 🗂 Repo Structure (target)

```
.
├─ app.py                 # Streamlit GUI
├─ sorter.py              # Core logic: load → map → filter/sort → compress → write
├─ launch_gui.py          # Launcher for PyInstaller (.exe)
├─ excel_report_sorter.spec  # (optional) reproducible PyInstaller spec
├─ requirements.txt
├─ tests/
│  └─ test_sorter.py
├─ README.md
└─ copilot.md
```

---

## 🔢 Column Contract (by Excel letters)

Operate by letter positions (independent of header text). First non-empty row is treated as headers.

| Letter | 0-based index | Role in app                                          |
| -----: | :-----------: | ---------------------------------------------------- |
|      A |       0       | String **filter / priority sort** (editable default) |
|      D |       3       | String **filter / priority sort** (editable default) |
|      E |       4       | String **filter / priority sort** (editable default) |
|      H |       7       | String **filter / priority sort** (editable default) |
|      I |       8       | **Group key #1** (compress by equality)              |
|      N |       13      | **Group key #2** (compress by equality)              |
|      U |       20      | **Sum** when compressed                              |

If any of these indices are missing in the loaded sheet, raise a clear error naming the missing letters.

---

## 🧩 Functional Spec

### 1) Load & Normalize

* Read `.xlsx`; if multiple sheets, user selects one.
* Normalize headers: trim whitespace, collapse double spaces.
* Map **letters → indices → actual DataFrame column names** (expose names in UI, allow overrides via dropdowns).

### 2) String Filters (A, D, E, H)

* For each column: a **“Contains”** (case-insensitive) text input **prefilled to `"8760"`**, **editable**; clearing disables that filter.
* Optional **“Equals”** multiselect of unique values (advanced; ANDed with “contains” if both used).

**Default behavior:** if a column has a non-empty “contains” string, keep rows where that column **contains** it (case-insensitive).

### 3) String “Priority Sort” (A, D, E, H)

* Per column: **priority string** input (default `"8760"`, editable) + ascending/descending toggle.
* Sorting order (stable; multi-key):

  1. Rows where column **contains** the priority string (True first),
  2. Then **natural sort** on that column (asc/desc),
  3. Respect user-chosen multi-key order.

### 4) Compress (Group) & Sum

* **Group by:** **I** and **N** (exact equality after trimming).
* **Aggregate:** **sum U** (coerce via `to_numeric(errors="coerce")`; treat NaN as 0 **only during aggregation**).
* Include in result:

  * Keys **I, N**
  * Aggregated **`Sum_U`**
  * Pass-through/context columns **A, D, E, H** as **first non-null** per group.

### 5) Output

* Single sheet **`Cleaned`**.
* Save to OS-aware **Downloads**:

  * Windows native: `%USERPROFILE%\Downloads`
  * WSL: `/mnt/c/Users/<USERNAME>/Downloads` (fallback `~/Downloads`)
  * Linux/macOS: `~/Downloads` (fallback repo `/out`)
* Filename: `Excel_Report_Sorter_<YYYYMMDD_HHMMSS>.xlsx`.
* Show a **Download button** and **run summary**: input rows, filtered rows, groups, total `Sum_U`, non-numeric U count.

---

## 🛡 Guardrails

* Validate presence of required letters; show actionable error if missing.
* Never overwrite source file.
* Count & display non-numeric values in `U` during coercion.
* Warn if file >100MB (memory tip).
* All processing is local (no network).

---

## 🧪 Acceptance Criteria (Tests)

* **Mapping:** letter→index→column name mapping returns correct columns for A/D/E/H/I/N/U.
* **Filtering:** default `"8760"` contains filter works (case-insensitive); editing or clearing changes behavior accordingly; equals filter ANDed properly.
* **Priority Sort:** rows containing the priority string appear first; multi-key stable sort honored.
* **Compression:** grouping by I & N merges rows; `Sum_U` equals numeric sum of U; A/D/E/H pass-through equals group’s first non-null.
* **Coercion:** non-numeric U values counted; treated as 0 only in aggregation.
* **Output:** single-sheet `Cleaned` written to Downloads; schema includes A, D, E, H, I, N, `Sum_U`.

---

## 🛠️ Copilot Tasks & Prompts

> Open the destination file first (e.g., `sorter.py`) so Copilot has context. Run tasks one by one and review diffs.

### A) Bootstrap

**Prompt:**
Create `requirements.txt` with: `pandas`, `openpyxl`, `streamlit`, `pytest`.
Create `.gitignore` entries for `venv/`, `__pycache__/`, `.streamlit/`, `*.xlsx`, `dist/`, `build/`, `*.spec`.

### B) Core Library (`sorter.py`)

**Prompt:**
Create `sorter.py` with typed functions and docstrings implementing:

* `letter_to_index(letter: str) -> int` (support multi-letter like “AA”).
* `map_letters_to_columns(df: pd.DataFrame, letters: list[str]) -> dict[str, str]`.
* `apply_string_filters(df: pd.DataFrame, contains: dict[str, str], equals: dict[str, list[str]]) -> pd.DataFrame` (contains = case-insensitive).
* `apply_priority_sort(df: pd.DataFrame, orders: list[tuple[str, str, bool]]) -> pd.DataFrame` where tuple = `(column, priority_value, ascending)`; rows containing `priority_value` come first, then natural sort.
* `compress_sum(df: pd.DataFrame, key_cols: list[str], sum_col: str, passthrough_cols: list[str]) -> pd.DataFrame` (sum numeric; first non-null for passthrough).
* `coerce_u_numeric(df: pd.DataFrame, u_col: str) -> tuple[pd.DataFrame, int]` returning new df + count of non-numeric.
* `get_downloads_dir() -> Path` (Windows/WSL/Linux).
* `write_cleaned(df: pd.DataFrame, out_dir: Path, sheet_name: str = "Cleaned") -> Path`.
  Raise `ValueError` if I, N, or U are missing by index.

### C) GUI (`app.py`)

**Prompt:**
Create `app.py` (Streamlit) that:

* Accepts drag-drop `.xlsx` + sheet selector.
* Detects column names for **A, D, E, H, I, N, U** using letter mapping; allow overrides via dropdowns.
* For A/D/E/H:

  * **Contains** text input default `"8760"` (editable, empty disables).
  * Optional **Equals** multiselect from unique values.
  * **Priority sort** text input default `"8760"` + asc/desc toggle; allow multi-key order (numeric priority).
* On **Process**:

  1. Build filters from UI → apply,
  2. Build sort order from UI → apply priority sort,
  3. Coerce U numeric and **compress by I & N summing U**,
  4. Write single `Cleaned` sheet to Downloads and expose a **Download button** with file bytes.
* Show run summary (rows in/out, #groups, total `Sum_U`, non-numeric U count).

### D) Tests (`tests/test_sorter.py`)

**Prompt:**
Create pytest covering:

* Letter mapping for A/D/E/H/I/N/U.
* Contains filter with default `"8760"` and edited/cleared values; equals filter interaction.
* Priority sort puts matches first; multi-key stability.
* Compression by I & N with `Sum_U`; passthrough A/D/E/H as first non-null.
* U coercion count; output written as single `Cleaned` sheet (mock `ExcelWriter`).

### E) README

**Prompt:**
Create `README.md` with setup (`python -m venv venv`, `pip install -r requirements.txt`), run (`streamlit run app.py`), explanation of letter-based mapping, default `"8760"` behavior (editable), compression rule (I+N keys, sum U), and Downloads path in Windows/WSL.

---

## 📦 Windows `.exe` Packaging

### Launcher (`launch_gui.py`)

Create a small launcher that runs Streamlit programmatically, finds a free port, and opens the browser. It must work when frozen with PyInstaller (`_MEIPASS`).

**Prompt:**
Create `launch_gui.py` that:

* Locates `app.py` whether running from source or frozen bundle (use `_MEIPASS` fallback).
* Finds a free port (8501–8999).
* Calls `streamlit.web.bootstrap.run` for `app.py`.
* Opens default browser to `http://127.0.0.1:<port>`.

### One-liner Build (simplest)

```
pyinstaller --name ExcelReportSorter --onefile --noconsole ^
  --add-data "app.py;." ^
  --add-data "sorter.py;." ^
  launch_gui.py
```

Result: `dist/ExcelReportSorter.exe`

> Use `--noconsole` for users; omit it for debugging. Ensure `--add-data` includes `app.py` and `sorter.py`.

### Optional Spec (`excel_report_sorter.spec`)

**Prompt:**
Create `excel_report_sorter.spec` for reproducible builds that bundles `app.py`/`sorter.py` as data files and includes hidden imports for `streamlit.web.bootstrap`, `pandas`, `openpyxl`. Build with:

```
pyinstaller excel_report_sorter.spec
```

### Packaging Acceptance

* Double-click `ExcelReportSorter.exe` opens the app in browser.
* Drag-drop, edit default `"8760"` values, Process → emits single `Cleaned` sheet to Downloads + Download button.
* Works on Windows 10/11 without Python installed (dependencies bundled).

---

## ✅ Definition of Done

* `streamlit run app.py` flow works end-to-end (drag-drop → filter/sort → compress I+N → sum U → one `Cleaned` output).
* Default string `"8760"` prefilled and **editable** for both filter & priority sort.
* Tests pass (`pytest -q`).
* Windows `.exe` build produced (`dist/ExcelReportSorter.exe`) and verified.

---
