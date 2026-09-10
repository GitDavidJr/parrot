import time
import asyncio
import uuid
from typing import Dict, List, Any, Optional
from src.config import settings, save_settings
from src.audio.devices import get_audio_devices
from src.audio.player import audio_player
from src.audio.recorder import AudioRecorder
from src.engines.openai_engine import OpenAIEngine
from src.engines.free_engine import FreeEngine

class ParrotService:
    def __init__(self):
        self.openai_engine = OpenAIEngine(
            api_key=settings.openai_api_key,
            default_voice=settings.openai_voice,
            model=settings.openai_model
        )
        self.free_engine = FreeEngine(
            default_voice_en=settings.edge_voice_en,
            default_voice_pt=settings.edge_voice_pt
        )

        # 1. User Microphone Recorder (PT -> EN)
        self.recorder = AudioRecorder(
            energy_threshold=settings.vad_energy_threshold,
            silence_threshold_ms=settings.vad_silence_threshold_ms
        )
        self.recorder.on_speech_segment = self._handle_speech_segment
        self.recorder.on_level_update = self._handle_level_update

        # 2. Meeting Audio Recorder (EN -> PT: Captures Discord / Meet / Zoom)
        self.meeting_recorder = AudioRecorder(
            energy_threshold=settings.vad_energy_threshold,
            silence_threshold_ms=settings.vad_silence_threshold_ms
        )
        self.meeting_recorder.on_speech_segment = self._handle_meeting_speech_segment
        self.meeting_recorder.on_level_update = self._handle_meeting_level_update

        self.is_active = False
        self.is_transmitting_to_call = False
        self.status = "idle"  # idle, listening, transcribing, translating, speaking
        self.clients: List[Any] = []  # WebSocket connections
        self.history: List[Dict[str, Any]] = []

        # Auto-detect audio devices
        self.device_info = get_audio_devices()
        self.input_device_id = settings.input_device_id or self.device_info["recommended"]["mic_id"]
        self.virtual_output_device_id = settings.virtual_output_device_id or self.device_info["recommended"]["virtual_mic_id"]
        self.headphones_device_id = settings.headphones_device_id or self.device_info["recommended"]["headphones_id"]
        self.meeting_device_id = settings.meeting_device_id or self.device_info["recommended"].get("meeting_device_id", self.virtual_output_device_id)

    @property
    def current_engine(self):
        if settings.engine == "openai" and settings.openai_api_key:
            return self.openai_engine
        return self.free_engine

    async def broadcast(self, event_type: str, data: Any):
        """Sends a JSON message to all connected WebSocket clients."""
        payload = {"type": event_type, "data": data}
        for ws in list(self.clients):
            try:
                await ws.send_json(payload)
            except Exception:
                if ws in self.clients:
                    self.clients.remove(ws)

    def _handle_level_update(self, level: float, is_speaking: bool):
        """Called with user microphone level."""
        if not self.is_active:
            return
        asyncio.create_task(self.broadcast("audio_level", {
            "level": level,
            "is_speaking": is_speaking,
            "status": self.status
        }))

    def _handle_meeting_level_update(self, level: float, is_speaking: bool):
        """Called with meeting audio level (when foreign participants speak)."""
        if not self.is_active:
            return
        asyncio.create_task(self.broadcast("meeting_audio_level", {
            "level": level,
            "is_speaking": is_speaking
        }))

    def _handle_speech_segment(self, audio_bytes: bytes, duration: float):
        """Called when a user speech segment has finished recording."""
        asyncio.create_task(self.process_user_speech(audio_bytes, duration))

    def _handle_meeting_speech_segment(self, audio_bytes: bytes, duration: float):
        """Called when a participant speech segment from Discord/Meet/Zoom has finished."""
        if self.is_transmitting_to_call:
            return
        asyncio.create_task(self.process_live_meeting_audio(audio_bytes, duration))

    async def start_session(self):
        """Starts listening to microphone and meeting audio."""
        if self.is_active:
            return
        self.is_active = True
        self.status = "listening"
        loop = asyncio.get_event_loop()

        # Start user microphone
        await loop.run_in_executor(None, lambda: self.recorder.start(device_id=self.input_device_id, loop=loop))

        # Start meeting audio capture stream (Discord / Zoom / Meet audio)
        if self.meeting_device_id is not None:
            try:
                await loop.run_in_executor(None, lambda: self.meeting_recorder.start(device_id=self.meeting_device_id, loop=loop))
            except Exception as e:
                print(f"[ParrotService] Erro ao iniciar meeting_recorder no dispositivo {self.meeting_device_id}: {e}")

        await self.broadcast("status_change", {
            "status": self.status,
            "is_active": True,
            "message": "Parrot ativo: ouvindo seu microfone e a reunião..."
        })

    async def stop_session(self):
        """Stops listening."""
        if not self.is_active:
            return
        self.is_active = False
        self.status = "idle"
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.recorder.stop)
        await loop.run_in_executor(None, self.meeting_recorder.stop)
        audio_player.stop()
        await self.broadcast("status_change", {
            "status": self.status,
            "is_active": False,
            "message": "Parrot pausado."
        })

    def set_push_to_talk(self, active: bool):
        if self.is_active:
            self.recorder.set_push_to_talk(active)

    async def process_user_speech(self, audio_bytes: bytes, duration: float):
        """
        User (PT) -> Call (EN):
        Transcribes Portuguese speech, translates to English, synthesizes speech,
        and streams audio to Perssua virtual microphone.
        """
        t0 = time.time()
        msg_id = str(uuid.uuid4())[:8]

        # 1. Transcribing
        self.status = "transcribing"
        await self.broadcast("status_change", {
            "status": self.status,
            "message": "Transcrevendo fala (PT)..."
        })

        engine = self.current_engine
        try:
            pt_text = await engine.transcribe(audio_bytes, lang=settings.source_lang)
        except Exception as e:
            print(f"[ParrotService] Erro na transcrição: {e}")
            self.status = "listening" if self.is_active else "idle"
            await self.broadcast("error", {"message": f"Erro na transcrição: {str(e)}"})
            return

        if not pt_text or len(pt_text.strip()) == 0:
            self.status = "listening" if self.is_active else "idle"
            await self.broadcast("status_change", {
                "status": self.status,
                "message": "Nenhuma fala detectada."
            })
            return

        # 2. Translating
        self.status = "translating"
        await self.broadcast("status_change", {
            "status": self.status,
            "message": f"Traduzindo: '{pt_text}'"
        })

        try:
            en_text = await engine.translate(
                pt_text,
                source_lang=settings.source_lang,
                target_lang=settings.target_lang
            )
        except Exception as e:
            print(f"[ParrotService] Erro na tradução: {e}")
            self.status = "listening" if self.is_active else "idle"
            await self.broadcast("error", {"message": f"Erro na tradução: {str(e)}"})
            return

        # 3. Synthesizing
        self.status = "speaking"
        await self.broadcast("status_change", {
            "status": self.status,
            "message": f"Falando em inglês na reunião: '{en_text}'"
        })

        try:
            voice = settings.openai_voice if settings.engine == "openai" else settings.edge_voice_en
            audio_out = await engine.synthesize(
                en_text,
                lang=settings.target_lang,
                voice=voice
            )
        except Exception as e:
            print(f"[ParrotService] Erro na síntese: {e}")
            self.status = "listening" if self.is_active else "idle"
            await self.broadcast("error", {"message": f"Erro na síntese de voz: {str(e)}"})
            return

        latency = round((time.time() - t0) * 1000)

        entry = {
            "id": msg_id,
            "channel": "user_to_meeting",
            "source_lang": settings.source_lang,
            "target_lang": settings.target_lang,
            "original": pt_text,
            "translated": en_text,
            "latency_ms": latency,
            "timestamp": time.strftime("%H:%M:%S"),
            "engine": settings.engine
        }
        self.history.append(entry)
        await self.broadcast("new_message", entry)

        # 4. Play audio to Virtual Microphone (Perssua) AND Headphones (if Test Monitor active)
        playback_tasks = []
        if self.virtual_output_device_id is not None and audio_out:
            playback_tasks.append(
                audio_player.play_audio_to_device(
                    audio_out,
                    device_id=self.virtual_output_device_id,
                    volume=settings.virtual_mic_volume
                )
            )

        if getattr(settings, 'play_translated_to_headphones', False) and self.headphones_device_id is not None and audio_out:
            playback_tasks.append(
                audio_player.play_audio_to_device(
                    audio_out,
                    device_id=self.headphones_device_id,
                    volume=settings.headphones_volume
                )
            )

        if playback_tasks:
            try:
                await asyncio.gather(*playback_tasks)
            except Exception as e:
                print(f"[ParrotService] Erro na reprodução de áudio: {e}")

        self.status = "listening" if self.is_active else "idle"
        await self.broadcast("status_change", {
            "status": self.status,
            "message": "Pronto para a próxima fala."
        })

    async def preview_voice(self, voice: str, text: Optional[str] = None):
        """Synthesizes a short test phrase and plays it directly through the user's headphones."""
        phrase = text or f"Hello! This is how the {voice} voice sounds in your meetings."
        engine = self.current_engine
        audio_out = await engine.synthesize(phrase, lang="en", voice=voice)
        target_device = self.headphones_device_id or self.virtual_output_device_id
        if target_device is not None and audio_out:
            await audio_player.play_audio_to_device(
                audio_out,
                device_id=target_device,
                volume=settings.headphones_volume
            )
        return audio_out

    async def quick_speak_text(self, text_pt: str):
        """Translates written Portuguese text and speaks English into the call."""
        t0 = time.time()
        msg_id = str(uuid.uuid4())[:8]
        engine = self.current_engine

        self.status = "translating"
        await self.broadcast("status_change", {"status": self.status, "message": "Traduzindo texto..."})

        en_text = await engine.translate(text_pt, source_lang="pt", target_lang="en")

        self.status = "speaking"
        await self.broadcast("status_change", {"status": self.status, "message": f"Falando: '{en_text}'"})

        voice = settings.openai_voice if settings.engine == "openai" else settings.edge_voice_en
        audio_out = await engine.synthesize(en_text, lang="en", voice=voice)

        latency = round((time.time() - t0) * 1000)
        entry = {
            "id": msg_id,
            "channel": "user_to_meeting",
            "source_lang": "pt",
            "target_lang": "en",
            "original": text_pt,
            "translated": en_text,
            "latency_ms": latency,
            "timestamp": time.strftime("%H:%M:%S"),
            "engine": settings.engine
        }
        self.history.append(entry)
        await self.broadcast("new_message", entry)

        playback_tasks = []
        if self.virtual_output_device_id is not None and audio_out:
            playback_tasks.append(
                audio_player.play_audio_to_device(
                    audio_out,
                    device_id=self.virtual_output_device_id,
                    volume=settings.virtual_mic_volume
                )
            )
        if getattr(settings, 'play_translated_to_headphones', False) and self.headphones_device_id is not None and audio_out:
            playback_tasks.append(
                audio_player.play_audio_to_device(
                    audio_out,
                    device_id=self.headphones_device_id,
                    volume=settings.headphones_volume
                )
            )
        if playback_tasks:
            try:
                await asyncio.gather(*playback_tasks)
            except Exception as e:
                print(f"[ParrotService] Erro na reprodução de áudio: {e}")

        self.status = "listening" if self.is_active else "idle"
        await self.broadcast("status_change", {"status": self.status, "message": "Pronto."})

    async def process_incoming_meeting_speech(self, text_en: str, play_audio: bool = True):
        """
        Meeting (EN) -> User (PT):
        Translates incoming English speech to Portuguese, pushes to live HUD subtitles,
        and optionally speaks Portuguese into the user's headphones.
        """
        t0 = time.time()
        msg_id = str(uuid.uuid4())[:8]
        engine = self.current_engine

        # Translate EN -> PT
        pt_text = await engine.translate(text_en, source_lang="en", target_lang="pt")
        latency = round((time.time() - t0) * 1000)

        entry = {
            "id": msg_id,
            "channel": "meeting_to_user",
            "source_lang": "en",
            "target_lang": "pt",
            "original": text_en,
            "translated": pt_text,
            "latency_ms": latency,
            "timestamp": time.strftime("%H:%M:%S"),
            "engine": settings.engine
        }
        self.history.append(entry)
        await self.broadcast("new_message", entry)

        # Optionally speak translated PT into user headphones
        if play_audio and self.headphones_device_id is not None:
            try:
                voice = "alloy" if settings.engine == "openai" else settings.edge_voice_pt
                audio_out = await engine.synthesize(pt_text, lang="pt", voice=voice)
                if audio_out:
                    asyncio.create_task(audio_player.play_audio_to_device(
                        audio_out,
                        device_id=self.headphones_device_id,
                        volume=settings.headphones_volume
                    ))
            except Exception as e:
                print(f"[ParrotService] Erro ao falar nos fones: {e}")

    async def process_live_meeting_audio(self, audio_bytes: bytes, duration: float):
        """
        Meeting (EN) -> User (PT):
        Transcribes live incoming English speech captured from Discord/Meet/Zoom,
        translates to Portuguese, broadcasts live subtitles to HUD & feed,
        and speaks Portuguese into user headphones.
        """
        if self.is_transmitting_to_call:
            return

        t0 = time.time()
        msg_id = str(uuid.uuid4())[:8]
        engine = self.current_engine

        # 1. Transcribing Meeting Speech (EN)
        try:
            en_text = await engine.transcribe(audio_bytes, lang=settings.target_lang)
        except Exception as e:
            print(f"[ParrotService] Erro na transcrição da reunião: {e}")
            return

        if not en_text or len(en_text.strip()) == 0:
            return

        # 2. Translating EN -> PT
        try:
            pt_text = await engine.translate(
                en_text,
                source_lang=settings.target_lang,
                target_lang=settings.source_lang
            )
        except Exception as e:
            print(f"[ParrotService] Erro na tradução da reunião: {e}")
            return

        latency = round((time.time() - t0) * 1000)
        entry = {
            "id": msg_id,
            "channel": "meeting_to_user",
            "source_lang": settings.target_lang,
            "target_lang": settings.source_lang,
            "original": en_text,
            "translated": pt_text,
            "latency_ms": latency,
            "timestamp": time.strftime("%H:%M:%S"),
            "engine": settings.engine
        }
        self.history.append(entry)
        await self.broadcast("new_message", entry)

        # 3. Speak Portuguese into user headphones
        if self.headphones_device_id is not None:
            try:
                voice = "alloy" if settings.engine == "openai" else settings.edge_voice_pt
                audio_out = await engine.synthesize(pt_text, lang=settings.source_lang, voice=voice)
                if audio_out:
                    asyncio.create_task(audio_player.play_audio_to_device(
                        audio_out,
                        device_id=self.headphones_device_id,
                        volume=settings.headphones_volume
                    ))
            except Exception as e:
                print(f"[ParrotService] Erro ao sintetizar nos fones: {e}")

    def update_settings(self, new_settings: Dict[str, Any]):
        """Updates runtime settings and persists to .env."""
        if "openai_api_key" in new_settings:
            settings.openai_api_key = new_settings["openai_api_key"]
            self.openai_engine.update_key(settings.openai_api_key)
        if "engine" in new_settings:
            settings.engine = new_settings["engine"]
        if "input_device_id" in new_settings:
            self.input_device_id = new_settings["input_device_id"]
            settings.input_device_id = self.input_device_id
        if "meeting_device_id" in new_settings:
            self.meeting_device_id = new_settings["meeting_device_id"]
            settings.meeting_device_id = self.meeting_device_id
        if "virtual_output_device_id" in new_settings:
            self.virtual_output_device_id = new_settings["virtual_output_device_id"]
            settings.virtual_output_device_id = self.virtual_output_device_id
        if "headphones_device_id" in new_settings:
            self.headphones_device_id = new_settings["headphones_device_id"]
            settings.headphones_device_id = self.headphones_device_id
        if "openai_voice" in new_settings:
            settings.openai_voice = new_settings["openai_voice"]
            self.openai_engine.default_voice = settings.openai_voice
        if "edge_voice_en" in new_settings:
            settings.edge_voice_en = new_settings["edge_voice_en"]
            self.free_engine.default_voice_en = settings.edge_voice_en
        if "vad_silence_threshold_ms" in new_settings:
            settings.vad_silence_threshold_ms = int(new_settings["vad_silence_threshold_ms"])
            self.recorder.silence_threshold_ms = settings.vad_silence_threshold_ms
            self.meeting_recorder.silence_threshold_ms = settings.vad_silence_threshold_ms
        if "vad_energy_threshold" in new_settings:
            settings.vad_energy_threshold = float(new_settings["vad_energy_threshold"])
            self.recorder.energy_threshold = settings.vad_energy_threshold
            self.meeting_recorder.energy_threshold = settings.vad_energy_threshold
        if "openai_model" in new_settings:
            settings.openai_model = new_settings["openai_model"]
            self.openai_engine.update_model(settings.openai_model)
        if "theme" in new_settings:
            settings.theme = new_settings["theme"]
        if "play_translated_to_headphones" in new_settings:
            settings.play_translated_to_headphones = bool(new_settings["play_translated_to_headphones"])
        if "capture_mode" in new_settings:
            settings.capture_mode = new_settings["capture_mode"]

        save_settings()

parrot_service = ParrotService()
