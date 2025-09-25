# copilot.md

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


# GUARDRAILS (MANDATORY)

1) UI gating
   - All DataFrame processing must run only after `st.form_submit_button("Process")` returns True. No live processing during input changes.

2) Header normalization + safe lookup
   - Normalize headers once (`normalize_headers`) and use the normalized names for dropdowns and processing.
   - Resolve columns via `safe_col(df, name)` (trim + casefold). Never index df with raw, unnormalized strings.

3) Exception hygiene
   - Every `try:` must have at least one `except` or `finally`. No partial blocks.
   - Wrap the entire processing pipeline in `try/except`. On user error (`KeyError`) show `st.error(...)` + `st.stop()`. On unexpected errors, `st.exception(e)` + `st.stop()`.

4) Output contract
   - Single Excel output, one sheet named `Cleaned`.
   - Group by I & N, sum U; keep A/D/E/H as first non-null per group.

5) Sorting & filtering
   - Filters are case-insensitive “contains”. If the box is empty, no filter for that column.
   - Priority sort = matches-first (flag False last), then natural order; multi-key stable (`kind="mergesort"`).

6) Launcher/runtime
   - Use `streamlit.web.cli.main`, set `STREAMLIT_GLOBAL_DEVELOPMENT_MODE=0`, prefer 127.0.0.1 headless.
   - If forced `--server.port` conflicts, retry without forcing the port.

7) Packaging
   - PyInstaller must include: `--hidden-import streamlit.web.cli --copy-metadata streamlit --collect-data streamlit --collect-submodules streamlit`
   - Always add data: `--add-data "app.py;." --add-data "sorter.py;."`

8) Build hygiene
   - Kill running EXEs and delete `dist/` and `build/` before builds; rename output if locked.


# Notes
- From now on, follow these guardrails for every change and PR.
- For syntax checking before running the app: `python -m compileall -q .` or `python -m pyflakes app.py` if installed.
