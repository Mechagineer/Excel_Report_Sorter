#!/usr/bin/env bash
# Usage: bash scripts/make-source-zip.sh
set -euo pipefail
cd "$(dirname "$0")/.."

zip -r ../Excel_Report_Sorter-src.zip \
  app.py sorter.py launch_gui.py requirements.txt README.md copilot.md tests \
  -x "*/__pycache__/*" "*/.pytest_cache/*" "*/.streamlit/*" \
     ".venv/*" "dist/*" "build/*" "*.xlsx" "*.spec"
echo "Wrote ../Excel_Report_Sorter-src.zip"
