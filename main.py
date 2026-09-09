import os
import sys
import time
import socket
import threading
import uvicorn
import webbrowser
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from src.config import settings
from src.server import app

PORT = 8765
HOST = "127.0.0.1"

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((HOST, port)) == 0

def run_uvicorn_server():
    """Runs the FastAPI server in a background thread."""
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")

def main():
    print("=" * 60)
    print("🦜 PARROT — Tradutor de Voz em Tempo Real para Chamadas")
    print("=" * 60)
    print(f"[*] Engine ativo: {settings.engine.upper()}")
    print(f"[*] Servidor backend: http://{HOST}:{PORT}")

    # Start FastAPI server in background thread if not already running
    if not is_port_in_use(PORT):
        server_thread = threading.Thread(target=run_uvicorn_server, daemon=True)
        server_thread.start()
        # Wait a moment for server to bind
        time.sleep(1.0)
    else:
        print(f"[!] Porta {PORT} já está em uso, conectando à instância existente...")

    # Check command-line flags
    if "--server-only" in sys.argv or "--web" in sys.argv:
        print(f"[+] Modo Web ativado. Abra o Parrot em seu navegador:")
        print(f"👉 http://{HOST}:{PORT}")
        webbrowser.open(f"http://{HOST}:{PORT}")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[!] Encerrando Parrot...")
            sys.exit(0)

    # Launch PyWebView Native macOS Desktop Window
    try:
        import webview
        print("[+] Abrindo janela desktop nativa do Parrot (macOS)...")
        window = webview.create_window(
            title="Parrot — Tradutor em Tempo Real para Chamadas",
            url=f"http://{HOST}:{PORT}",
            width=1200,
            height=860,
            resizable=True,
            min_size=(900, 600),
            background_color="#0F172A",
            text_select=True,
        )
        webview.start(debug=False)
    except Exception as e:
        print(f"[!] Não foi possível abrir janela nativa pywebview ({e}). Abrindo no navegador...")
        webbrowser.open(f"http://{HOST}:{PORT}")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[!] Encerrando Parrot...")
            sys.exit(0)

if __name__ == "__main__":
    main()
