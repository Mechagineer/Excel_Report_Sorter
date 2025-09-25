# launch_gui.py — robust launcher for PyInstaller + Streamlit
import os
import sys
import socket
import webbrowser
from pathlib import Path

def find_free_port(start=8501, end=8999):
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return 8501  # safe default

def resolve_app_path() -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    for p in (base / "app.py", Path(__file__).parent / "app.py", Path.cwd() / "app.py"):
        if p.exists():
            return p
    raise FileNotFoundError("Could not locate app.py next to the launcher or in CWD.")

def run_streamlit(argv):
    import streamlit.web.cli as stcli
    sys.argv = argv
    return stcli.main()

def main():
    # Guardrail: disable dev mode so server.port and headless configs are allowed.
    os.environ.setdefault("STREAMLIT_GLOBAL_DEVELOPMENT_MODE", "0")

    app_path = resolve_app_path()
    port = find_free_port()
    url = f"http://127.0.0.1:{port}"

    try:
        webbrowser.open(url, new=2, autoraise=True)
    except Exception:
        pass

    base_argv = [
        "streamlit", "run", str(app_path),
        "--server.address", "127.0.0.1",
        "--server.headless", "true",
    ]

    # First try: explicit port
    try:
        return run_streamlit(base_argv + ["--server.port", str(port)])
    except Exception as e:
        # Fallback: if any devMode/port conflict happens, run without forcing port.
        if "developmentMode" in str(e) or "server.port" in str(e):
            return run_streamlit(base_argv)
        raise

if __name__ == "__main__":
    main()
import sys
import os
import socket
import webbrowser
from pathlib import Path

# For PyInstaller _MEIPASS support
def get_app_path():
    if hasattr(sys, '_MEIPASS'):
        return str(Path(sys._MEIPASS) / 'app.py')
    # Fallback to repo
    return str(Path(__file__).parent / 'app.py')

def find_free_port(start=8501, end=8999):
    for port in range(start, end+1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port
    raise RuntimeError('No free port found')

def main():
    app_path = get_app_path()
    port = find_free_port()
    url = f'http://127.0.0.1:{port}'
    # Import streamlit bootstrap only here (for PyInstaller hidden import)
    from streamlit.web import bootstrap
    import threading
    threading.Thread(target=lambda: webbrowser.open(url), daemon=True).start()
    bootstrap.run(app_path, '', [], {}, port)

if __name__ == '__main__':
    main()
