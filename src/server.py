import os
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any

from src.config import settings
from src.service import parrot_service
from src.audio.devices import get_audio_devices
from src.audio.player import audio_player

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
UI_DIR = BASE_DIR / "src" / "ui"

app = FastAPI(title="Parrot — Live Call Voice Translator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount assets
if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")

class QuickSpeakRequest(BaseModel):
    text: str

class SimulateIncomingRequest(BaseModel):
    text: str
    play_audio: bool = True

class TestAudioRequest(BaseModel):
    target: str = "perssua" # "perssua" or "headphones"
    engine: str = "openai"  # "openai" or "free"

class PreviewVoiceRequest(BaseModel):
    voice: str
    engine: str = "openai"
    text: str | None = None

@app.get("/", response_class=HTMLResponse)
async def get_index():
    index_file = UI_DIR / "index.html"
    return HTMLResponse(content=index_file.read_text(encoding="utf-8"))

@app.get("/app.js")
@app.get("/src/ui/app.js")
async def get_app_js():
    js_file = UI_DIR / "app.js"
    return FileResponse(js_file, media_type="application/javascript")

@app.get("/hud", response_class=HTMLResponse)
async def get_hud():
    hud_file = UI_DIR / "hud.html"
    return HTMLResponse(content=hud_file.read_text(encoding="utf-8"))

@app.get("/api/status")
async def get_status():
    return {
        "is_active": parrot_service.is_active,
        "status": parrot_service.status,
        "engine": settings.engine,
        "source_lang": settings.source_lang,
        "target_lang": settings.target_lang,
        "devices": {
            "input": parrot_service.input_device_id,
            "virtual_output": parrot_service.virtual_output_device_id,
            "headphones": parrot_service.headphones_device_id,
        },
        "settings": settings.model_dump(),
        "history_count": len(parrot_service.history),
    }

@app.get("/api/history")
async def get_history():
    return parrot_service.history

@app.get("/api/devices")
async def list_devices():
    return get_audio_devices()

@app.post("/api/start")
async def start_session():
    await parrot_service.start_session()
    return {"success": True, "status": parrot_service.status}

@app.post("/api/stop")
async def stop_session():
    await parrot_service.stop_session()
    return {"success": True, "status": parrot_service.status}

@app.post("/api/settings")
async def update_settings(payload: Dict[str, Any]):
    parrot_service.update_settings(payload)
    return {"success": True, "settings": settings.model_dump()}

@app.post("/api/quick-speak")
async def quick_speak(payload: QuickSpeakRequest):
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Texto não pode ser vazio.")
    await parrot_service.quick_speak_text(payload.text.strip())
    return {"success": True}

@app.post("/api/simulate-incoming")
async def simulate_incoming(payload: SimulateIncomingRequest):
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Texto não pode ser vazio.")
    await parrot_service.process_incoming_meeting_speech(payload.text.strip(), play_audio=payload.play_audio)
    return {"success": True}

@app.post("/api/test-audio")
async def test_audio(payload: TestAudioRequest):
    target_device = parrot_service.virtual_output_device_id if payload.target == "perssua" else parrot_service.headphones_device_id
    if target_device is None:
        raise HTTPException(status_code=400, detail=f"Dispositivo {payload.target} não configurado.")

    engine = parrot_service.openai_engine if payload.engine == "openai" else parrot_service.free_engine
    test_phrase = "Hello! This is Parrot testing the audio connection."
    audio_bytes = await engine.synthesize(test_phrase, lang="en")
    
    await audio_player.play_audio_to_device(audio_bytes, device_id=target_device, volume=1.0)
    return {"success": True, "message": f"Áudio de teste reproduzido no dispositivo {payload.target}."}

@app.post("/api/preview-voice")
async def preview_voice_endpoint(payload: PreviewVoiceRequest):
    target_device = parrot_service.headphones_device_id or parrot_service.virtual_output_device_id
    if target_device is None:
        raise HTTPException(status_code=400, detail="Dispositivo de saída não encontrado.")

    phrase = payload.text or f"Hello! This is a preview of the {payload.voice} voice in Parrot."
    engine = parrot_service.openai_engine if payload.engine == "openai" else parrot_service.free_engine

    try:
        audio_bytes = await engine.synthesize(phrase, lang="en", voice=payload.voice)
        await audio_player.play_audio_to_device(
            audio_bytes,
            device_id=target_device,
            volume=settings.headphones_volume
        )
        return {"success": True, "voice": payload.voice, "message": f"Voz {payload.voice} reproduzida com sucesso."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao sintetizar prévia de voz: {e}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    parrot_service.clients.append(websocket)
    try:
        # Send initial status & history
        await websocket.send_json({
            "type": "init",
            "data": {
                "status": parrot_service.status,
                "is_active": parrot_service.is_active,
                "settings": settings.model_dump(),
                "history": parrot_service.history[-30:],
                "devices": get_audio_devices(),
            }
        })

        while True:
            msg = await websocket.receive_json()
            mtype = msg.get("type")
            if mtype == "start":
                await parrot_service.start_session()
            elif mtype == "stop":
                await parrot_service.stop_session()
            elif mtype == "ptt_press":
                parrot_service.set_push_to_talk(True)
            elif mtype == "ptt_release":
                parrot_service.set_push_to_talk(False)
            elif mtype == "quick_speak":
                text = msg.get("text", "")
                if text:
                    await parrot_service.quick_speak_text(text)
            elif mtype == "simulate_incoming":
                text = msg.get("text", "")
                if text:
                    await parrot_service.process_incoming_meeting_speech(text)
    except WebSocketDisconnect:
        if websocket in parrot_service.clients:
            parrot_service.clients.remove(websocket)
    except Exception as e:
        print(f"[WebSocket Error]: {e}")
        if websocket in parrot_service.clients:
            parrot_service.clients.remove(websocket)
