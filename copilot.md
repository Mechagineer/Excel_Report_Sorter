# copilot.md

## 🛡 Guardrails

* Validate presence of required letters; show actionable error if missing.
* Never overwrite source file.
* Count & display non-numeric values in `U` during coercion.
* Warn if file >100MB (memory tip).
* All processing is local (no network).

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

9) Try/Except Scoping (No dangling or overlapping tries)
   - Never open a `try:` that spans across unrelated UI sections.
   - If a `try:` is introduced, it must be fully closed with `except`/`finally` **before** starting another `try:` at the same or outer indent.
   - No nested `try` unless each has its own `except`/`finally` and scopes do not overlap accidentally.
   - CI/Pre-commit: run `python -m compileall -q app.py` to fail builds on `SyntaxError`.

   Packaging Guardrail — Keep archives lean
   - Source zips must exclude: .venv/, dist/, build/, __pycache__/, .pytest_cache/, .streamlit/, *.xlsx, *.spec
   - Binary releases ship ONLY dist/*.exe (no venv, no build tree).
   - Enforce via .gitignore + .gitattributes (export-ignore) and the make-zip scripts.

   ## Excel Download Guardrail (MANDATORY)
   - Never pass `DataFrame.to_excel()` directly to `st.download_button`.
   - Always create a BytesIO buffer and write via `pd.ExcelWriter`, then `seek(0)` and pass the buffer (or its bytes) to `download_button`.
   - Example:
      buf = BytesIO()
      with pd.ExcelWriter(buf, engine="openpyxl") as w:
         df.to_excel(w, index=False, sheet_name="Cleaned")
      buf.seek(0)
      st.download_button(..., data=buf, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
   - Ensure `openpyxl` is listed in requirements for .xlsx output.

   ## MVP Freeze — A-only (ENFORCED)
   - The app is frozen to A-only behavior until explicitly lifted: no D/E/H or I/N/U features, no groupby/compress_sum, and no U coercion or aggregation code paths should be used in `app.py`.

   ## Packaging Guardrails (MANDATORY)
   1) Streamlit modules
      - ALWAYS bundle Streamlit CLI and runtime packages:
        hiddenimports must include:
          - streamlit.web.cli
          - streamlit.runtime.scriptrunner.magic_funcs
        and collect subpackages:
          - collect_submodules('streamlit.runtime')
          - collect_submodules('streamlit.web')
      - Do NOT remove these to “reduce size.” Any optimization must keep the above.

   2) Metadata & data
      - Always include: copy_metadata('streamlit'), collect_data_files('streamlit').

   3) Optional excludes
      - It's OK to exclude unused optional extras (e.g., 'streamlit.external.langchain'), but never exclude runtime or web subpackages.

   4) Build hygiene & smoke test
      - Kill running EXEs; delete dist/ and build/ before building.
      - After building, run a smoke test: launching the EXE must open the UI without ModuleNotFoundError.

   5) Version stability
      - Keep Streamlit pinned to a tested minor range (e.g., >=1.30,<2) unless we consciously upgrade and re-run packaging smoke tests.

      ## Packaging Guardrails (ENFORCED)
      1) App sources must be bundled:
          - The .spec must include:
             datas += [('app.py','.'), ('sorter.py','.')]
          - Do not remove or rename these without updating the launcher and verification script.

      2) Streamlit runtime:
          - hiddenimports must include:
             - 'streamlit.web.cli'
             - 'streamlit.runtime.scriptrunner.magic_funcs'
          - Also collect subpackages:
             - collect_submodules('streamlit.runtime')
             - collect_submodules('streamlit.web')
          - Include metadata/data:
             - copy_metadata('streamlit'), collect_data_files('streamlit')

      3) Build hygiene:
          - Kill running EXEs; delete dist/ and build/ before building.
          - Run `python scripts/verify_packaging.py` and fail the build if it reports missing items.

      4) Launcher contract:
          - `launch_gui.py` must be able to resolve `app.py` from `_MEIPASS` (packaged) or CWD (dev).
          - Do not change the launcher’s `resolve_app_path()` semantics without updating the spec accordingly.
