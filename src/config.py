import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(ENV_PATH)

class Settings(BaseModel):
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    engine: str = os.getenv("DEFAULT_ENGINE", "openai")  # "openai" or "free"
    source_lang: str = os.getenv("DEFAULT_SOURCE_LANG", "pt")
    target_lang: str = os.getenv("DEFAULT_TARGET_LANG", "en")
    openai_voice: str = os.getenv("OPENAI_VOICE", "alloy")
    edge_voice_en: str = os.getenv("EDGE_VOICE_EN", "en-US-ChristopherNeural")
    edge_voice_pt: str = os.getenv("EDGE_VOICE_PT", "pt-BR-AntonioNeural")
    
    # Audio Devices
    input_device_id: int | None = None
    virtual_output_device_id: int | None = None # Perssua
    headphones_device_id: int | None = None
    
    # VAD & Capture
    vad_silence_threshold_ms: int = int(os.getenv("VAD_SILENCE_THRESHOLD_MS", "650"))
    vad_energy_threshold: float = float(os.getenv("VAD_ENERGY_THRESHOLD", "0.015"))
    capture_mode: str = "vad" # "vad" or "ptt" (push-to-talk)
    
    # Volume levels
    virtual_mic_volume: float = 1.0
    headphones_volume: float = 0.9

settings = Settings()

def save_settings():
    """Persist settings to .env"""
    lines = [
        f"OPENAI_API_KEY={settings.openai_api_key}\n",
        f"DEFAULT_ENGINE={settings.engine}\n",
        f"DEFAULT_SOURCE_LANG={settings.source_lang}\n",
        f"DEFAULT_TARGET_LANG={settings.target_lang}\n",
        f"OPENAI_VOICE={settings.openai_voice}\n",
        f"EDGE_VOICE_EN={settings.edge_voice_en}\n",
        f"EDGE_VOICE_PT={settings.edge_voice_pt}\n",
        f"VAD_SILENCE_THRESHOLD_MS={settings.vad_silence_threshold_ms}\n",
        f"VAD_ENERGY_THRESHOLD={settings.vad_energy_threshold}\n",
    ]
    with open(ENV_PATH, "w") as f:
        f.writelines(lines)
