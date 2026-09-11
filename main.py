import os
import sys
import time
import socket
import threading
import uvicorn
import webbrowser
from pathlib import Path

# Add project root to sys.path (PyInstaller extracts resources into _MEIPASS).
BASE_DIR = Path(sys._MEIPASS) if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS") else Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from src.config import settings
from src.server import app

PORT = 8765
HOST = "127.0.0.1"

def is_parrot_server_responding() -> bool:
    try:
        import urllib.request
        with urllib.request.urlopen(f"http://{HOST}:{PORT}/api/status", timeout=0.6) as resp:
            return resp.status == 200
    except Exception:
        return False

def run_uvicorn_server():
    """Runs the FastAPI server in a background thread."""
    config = uvicorn.Config(app=app, host=HOST, port=PORT, log_level="warning")
    server = uvicorn.Server(config)
    server.run()

def set_macos_dock_icon():
    """Sets the native macOS Dock icon to Parrot's official Green Parrot logo."""
    try:
        from AppKit import NSApplication, NSImage, NSApplicationActivationPolicyRegular
        app_kit = NSApplication.sharedApplication()
        app_kit.setActivationPolicy_(NSApplicationActivationPolicyRegular)
        icon_path = str(BASE_DIR / "assets" / "icon.png")
        if os.path.exists(icon_path):
            icon = NSImage.alloc().initWithContentsOfFile_(icon_path)
            if icon:
                app_kit.setApplicationIconImage_(icon)
                dock_tile = app_kit.dockTile()
                if dock_tile:
                    dock_tile.display()
    except Exception as e:
        print(f"[!] Erro ao definir ícone da Dock: {e}")

def on_app_started(window=None):
    """Callback triggered once Cocoa/pywebview initializes."""
    set_macos_dock_icon()
    def _refresh():
        for delay in [0.2, 0.5, 1.2]:
            time.sleep(delay)
            set_macos_dock_icon()
    threading.Thread(target=_refresh, daemon=True).start()

def main():
    print("=" * 60)
    print("🦜 PARROT — Aplicação Desktop de Tradução em Tempo Real")
    print("=" * 60)
    print(f"[*] Engine ativo: {settings.engine.upper()}")
    print(f"[*] Modelo OpenAI: {settings.openai_model}")
    print(f"[*] Tema Padrão: {settings.theme.upper()} MODE")
    print(f"[*] Servidor backend: http://{HOST}:{PORT}")

    # Start FastAPI server in background thread if not already running
    if not is_parrot_server_responding():
        server_thread = threading.Thread(target=run_uvicorn_server, daemon=True)
        server_thread.start()
        for _ in range(30):
            time.sleep(0.1)
            if is_parrot_server_responding():
                break
    else:
        print(f"[!] Porta {PORT} já ativa com backend Parrot...")

    # If user explicitly specifies --web, open browser
    if "--web" in sys.argv or "--server-only" in sys.argv:
        print(f"[+] Modo Web ativado: http://{HOST}:{PORT}")
        if "--web" in sys.argv:
            webbrowser.open(f"http://{HOST}:{PORT}")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[!] Encerrando Parrot...")
            sys.exit(0)

    # Launch Native macOS Desktop Application Window
    icon_file = str(BASE_DIR / "assets" / "icon.png")
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
        webview.start(func=on_app_started, icon=icon_file, debug=False)
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
