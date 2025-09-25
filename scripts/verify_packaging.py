import sys
import pathlib

spec_path = pathlib.Path('ExcelReportSorter_v8.spec')
if not spec_path.exists():
    print('Spec file not found:', spec_path)
    sys.exit(1)

spec = spec_path.read_text(encoding='utf-8')
must_datas = ["('app.py', '.'", "('sorter.py', '.'"]
must_hidden = [
    "streamlit.web.cli",
    "streamlit.runtime.scriptrunner.magic_funcs",
]
missing = []
for token in must_datas:
    if token not in spec:
        missing.append(f"datas missing {token}")
for token in must_hidden:
    if token not in spec:
        missing.append(f"hiddenimports missing {token}")
if missing:
    print("Packaging verification FAILED:")
    for m in missing:
        print(" -", m)
    sys.exit(1)
print("Packaging verification OK")
