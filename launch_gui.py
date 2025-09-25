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
