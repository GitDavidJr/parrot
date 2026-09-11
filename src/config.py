import os
import sys
from pathlib import Path
from dotenv import load_dotenv, set_key
from pydantic import BaseModel

RESOURCE_DIR = Path(sys._MEIPASS) if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS") else Path(__file__).resolve().parent.parent
DEV_ENV_PATH = RESOURCE_DIR / ".env"

if getattr(sys, "frozen", False):
    if sys.platform == "darwin":
        CONFIG_DIR = Path.home() / "Library" / "Application Support" / "Parrot"
    elif sys.platform == "win32":
        CONFIG_DIR = Path(os.getenv("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / "Parrot"
    else:
        CONFIG_DIR = Path(os.getenv("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "parrot"
    ENV_PATH = CONFIG_DIR / ".env"
else:
    ENV_PATH = DEV_ENV_PATH

if DEV_ENV_PATH.exists():
    load_dotenv(DEV_ENV_PATH)
if ENV_PATH != DEV_ENV_PATH and ENV_PATH.exists():
    load_dotenv(ENV_PATH, override=True)


def optional_int_env(name: str) -> int | None:
    value = os.getenv(name, "").strip()
    try:
        return int(value) if value else None
    except ValueError:
        return None

class Settings(BaseModel):
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    engine: str = os.getenv("DEFAULT_ENGINE", "openai")  # "openai" or "free"
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
    theme: str = os.getenv("DEFAULT_THEME", "light") # "light" by default!
    source_lang: str = os.getenv("DEFAULT_SOURCE_LANG", "pt")
    target_lang: str = os.getenv("DEFAULT_TARGET_LANG", "en")
    openai_voice: str = os.getenv("OPENAI_VOICE", "alloy")
    edge_voice_en: str = os.getenv("EDGE_VOICE_EN", "en-US-ChristopherNeural")
    edge_voice_pt: str = os.getenv("EDGE_VOICE_PT", "pt-BR-AntonioNeural")
    
    # Audio Devices
    input_device_id: int | None = optional_int_env("INPUT_DEVICE_ID")
    virtual_output_device_id: int | None = optional_int_env("VIRTUAL_OUTPUT_DEVICE_ID") # Perssua
    headphones_device_id: int | None = optional_int_env("HEADPHONES_DEVICE_ID")
    meeting_device_id: int | None = optional_int_env("MEETING_DEVICE_ID") # Legacy Perssua / BlackHole fallback
    input_device_name: str = os.getenv("INPUT_DEVICE_NAME", "")
    virtual_output_device_name: str = os.getenv("VIRTUAL_OUTPUT_DEVICE_NAME", "")
    headphones_device_name: str = os.getenv("HEADPHONES_DEVICE_NAME", "")
    meeting_device_name: str = os.getenv("MEETING_DEVICE_NAME", "")
    
    # VAD & Capture
    vad_silence_threshold_ms: int = int(os.getenv("VAD_SILENCE_THRESHOLD_MS", "350"))
    vad_energy_threshold: float = float(os.getenv("VAD_ENERGY_THRESHOLD", "0.015"))
    capture_mode: str = os.getenv("CAPTURE_MODE", "vad") # "vad" or "ptt" (push-to-talk)

    # Computer audio dubbing (EN -> PT)
    system_audio_capture: bool = os.getenv("SYSTEM_AUDIO_CAPTURE", "true").lower() == "true"
    system_audio_backend: str = os.getenv("SYSTEM_AUDIO_BACKEND", "auto")
    dub_system_audio: bool = os.getenv("DUB_SYSTEM_AUDIO", "true").lower() == "true"
    system_audio_energy_threshold: float = float(os.getenv("SYSTEM_AUDIO_ENERGY_THRESHOLD", "0.006"))
    
    # Test Monitor (Ouvir a tradução nos próprios fones)
    play_translated_to_headphones: bool = os.getenv("PLAY_TRANSLATED_TO_HEADPHONES", "false").lower() == "true"

    # Volume levels
    virtual_mic_volume: float = float(os.getenv("VIRTUAL_MIC_VOLUME", "1.0"))
    headphones_volume: float = float(os.getenv("HEADPHONES_VOLUME", "0.9"))

settings = Settings()

def save_settings():
    """Persist settings to .env"""
    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    values = {
        "OPENAI_API_KEY": settings.openai_api_key,
        "DEFAULT_ENGINE": settings.engine,
        "OPENAI_MODEL": settings.openai_model,
        "DEFAULT_THEME": settings.theme,
        "DEFAULT_SOURCE_LANG": settings.source_lang,
        "DEFAULT_TARGET_LANG": settings.target_lang,
        "OPENAI_VOICE": settings.openai_voice,
        "EDGE_VOICE_EN": settings.edge_voice_en,
        "EDGE_VOICE_PT": settings.edge_voice_pt,
        "INPUT_DEVICE_ID": "" if settings.input_device_id is None else str(settings.input_device_id),
        "MEETING_DEVICE_ID": "" if settings.meeting_device_id is None else str(settings.meeting_device_id),
        "VIRTUAL_OUTPUT_DEVICE_ID": "" if settings.virtual_output_device_id is None else str(settings.virtual_output_device_id),
        "HEADPHONES_DEVICE_ID": "" if settings.headphones_device_id is None else str(settings.headphones_device_id),
        "INPUT_DEVICE_NAME": settings.input_device_name,
        "MEETING_DEVICE_NAME": settings.meeting_device_name,
        "VIRTUAL_OUTPUT_DEVICE_NAME": settings.virtual_output_device_name,
        "HEADPHONES_DEVICE_NAME": settings.headphones_device_name,
        "VAD_SILENCE_THRESHOLD_MS": str(settings.vad_silence_threshold_ms),
        "VAD_ENERGY_THRESHOLD": str(settings.vad_energy_threshold),
        "CAPTURE_MODE": settings.capture_mode,
        "SYSTEM_AUDIO_CAPTURE": str(settings.system_audio_capture).lower(),
        "SYSTEM_AUDIO_BACKEND": settings.system_audio_backend,
        "DUB_SYSTEM_AUDIO": str(settings.dub_system_audio).lower(),
        "SYSTEM_AUDIO_ENERGY_THRESHOLD": str(settings.system_audio_energy_threshold),
        "PLAY_TRANSLATED_TO_HEADPHONES": str(settings.play_translated_to_headphones).lower(),
        "VIRTUAL_MIC_VOLUME": str(settings.virtual_mic_volume),
        "HEADPHONES_VOLUME": str(settings.headphones_volume),
    }
    for key, value in values.items():
        set_key(str(ENV_PATH), key, value, quote_mode="auto")
