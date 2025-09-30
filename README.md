# Excel Report Sorter

## 🎯 Overview

Excel Report Sorter is a minimal local app that lets you **drag & drop an Excel file** and outputs a single cleaned Excel file. It is designed for fast, local processing with a focus on specific columns and aggregation rules.

**Key Features:**
- Drag & drop `.xlsx` files (Streamlit GUI)
- Filter and sort by string columns with editable default value `"8760"`
- Compress/group by columns I & N, summing column U
- Output a single worksheet named `Cleaned` to your Downloads folder
- All processing is local (no network) if not using API

---

## 🧱 Tech Stack
- Python 3.11+
- pandas, openpyxl
- Streamlit (GUI)
- pytest (tests)
- PyInstaller (Windows `.exe` packaging)

---

## 🗂 Repo Structure

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

## 🔢 Column Mapping (by Excel Letters)

The app operates by Excel column letters, not header text. The first non-empty row is treated as headers.

| Letter | 0-based index | Role in app                                          |
| -----: | :-----------: | ---------------------------------------------------- |
|      A |       0       | String **filter / priority sort** (editable default) |
|      D |       3       | String **filter / priority sort** (editable default) |
|      E |       4       | String **filter / priority sort** (editable default) |
|      H |       7       | String **filter / priority sort** (editable default) |
|      I |       8       | **Group key #1** (compress by equality)              |
|      N |      13       | **Group key #2** (compress by equality)              |
|      U |      20       | **Sum** when compressed                              |

If any of these indices are missing, the app will raise a clear error naming the missing letters.

---

## 🚀 Setup & Usage

1. **Clone the repo & install dependencies:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```
2. **Run the app:**
   ```bash
   streamlit run app.py
   ```
3. **Drag & drop your Excel file** into the app, select the sheet, and configure filters/sorts as needed.
4. **Process** to generate a cleaned file. Download from the UI or find it in your Downloads folder.

---

## 🧩 How It Works

1. **Load & Normalize:**
   - Reads `.xlsx` file; lets you pick a sheet if multiple.
   - Maps Excel letters (A, D, E, H, I, N, U) to columns by index.
2. **String Filters (A, D, E, H):**
   - Each has a **Contains** filter (default `"8760"`, editable, case-insensitive).
   - Optional **Equals** filter (multi-select unique values).
3. **Priority Sort:**
   - Each column can be sorted by a priority string (default `"8760"`, editable) and order.
   - Rows containing the priority string appear first, then natural sort.
4. **Compress & Sum:**
   - Groups by I & N (exact match after trimming).
   - Sums U (non-numeric values treated as 0 during aggregation; count is shown).
   - Passes through first non-null A, D, E, H per group.
5. **Output:**
   - Single sheet `Cleaned` saved to your Downloads folder.
   - Filename: `Excel_Report_Sorter_<YYYYMMDD_HHMMSS>.xlsx`
   - Download button and run summary (input rows, filtered rows, groups, total Sum_U, non-numeric U count).

---

## 💾 Output Location

- **Windows native:** `%USERPROFILE%\Downloads`
- **WSL:** `/mnt/c/Users/<USERNAME>/Downloads` (fallback `~/Downloads`)
- **Linux/macOS:** `~/Downloads` (fallback repo `/out`)

---

## 🧪 Testing

Run all tests with:
```bash
pytest -q
```

---

## 🛡 Guardrails
- Validates presence of required columns (A, D, E, H, I, N, U)
- Never overwrites the source file
- Counts and displays non-numeric values in U
- Warns if file >100MB
- All processing is local (no network)

---

## 📦 Windows Packaging

To build a standalone Windows `.exe` (requires PyInstaller) from PowerShell (venv active):
```powershell
# Clean old outputs (avoid locked EXEs)
Get-Process ExcelReportSorter* -ErrorAction SilentlyContinue | Stop-Process -Force
Remove-Item -Recurse -Force .\dist, .\build -ErrorAction SilentlyContinue

# Build (Windows PowerShell, venv active)
py -m PyInstaller --name ExcelReportSorter_v4 --onefile --noconsole `
   --add-data "app.py;." `
   --add-data "sorter.py;." `
   --hidden-import "streamlit.web.cli" `
   --copy-metadata streamlit `
   --collect-data streamlit `
   --collect-submodules streamlit `
   launch_gui.py
```
Result: `dist/ExcelReportSorter_v4.exe`

---

## ✅ Definition of Done
- End-to-end flow: drag-drop → filter/sort → compress I+N → sum U → one `Cleaned` output
- Default string `"8760"` prefilled and editable for both filter & priority sort
- Tests pass (`pytest -q`)
- Windows `.exe` build produced and verified
