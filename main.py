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

def set_macos_dock_icon():
    """Sets the native macOS Dock icon to Parrot's 3D Green Parrot icon."""
    try:
        from AppKit import NSApplication, NSImage
        app_kit = NSApplication.sharedApplication()
        icon_path = str(BASE_DIR / "assets" / "icon.png")
        if os.path.exists(icon_path):
            icon = NSImage.alloc().initWithContentsOfFile_(icon_path)
            if icon:
                app_kit.setApplicationIconImage_(icon)
    except Exception:
        pass

def main():
    print("=" * 60)
    print("🦜 PARROT — Aplicação Desktop de Tradução em Tempo Real")
    print("=" * 60)
    print(f"[*] Engine ativo: {settings.engine.upper()}")
    print(f"[*] Modelo OpenAI: {settings.openai_model}")
    print(f"[*] Tema Padrão: {settings.theme.upper()} MODE")
    print(f"[*] Servidor backend: http://{HOST}:{PORT}")

    # Start FastAPI server in background thread if not already running
    if not is_port_in_use(PORT):
        server_thread = threading.Thread(target=run_uvicorn_server, daemon=True)
        server_thread.start()
        time.sleep(0.8)
    else:
        print(f"[!] Porta {PORT} já ativa, conectando backend...")

    # If user explicitly specifies --web, open browser
    if "--web" in sys.argv or "--server-only" in sys.argv:
        print(f"[+] Modo Web ativado: http://{HOST}:{PORT}")
        webbrowser.open(f"http://{HOST}:{PORT}")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[!] Encerrando Parrot...")
            sys.exit(0)

    # Launch Native macOS Desktop Application Window
    set_macos_dock_icon()
    try:
        import webview
        print("[+] Abrindo janela nativa do aplicativo desktop Parrot (macOS)...")
        window = webview.create_window(
            title="Parrot — Tradutor em Tempo Real para Chamadas",
            url=f"http://{HOST}:{PORT}",
            width=1200,
            height=860,
            resizable=True,
            min_size=(920, 640),
            background_color="#F8FAFC", # Light Mode Default
            text_select=True,
        )
        webview.start(debug=False)
    except Exception as e:
        print(f"[!] Erro ao abrir janela desktop nativa: {e}")
        print(f"[+] Abrindo no navegador como alternativa: http://{HOST}:{PORT}")
        webbrowser.open(f"http://{HOST}:{PORT}")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[!] Encerrando Parrot...")
            sys.exit(0)

if __name__ == "__main__":
    main()
