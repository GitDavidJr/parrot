import io
import os
import asyncio
import subprocess
import speech_recognition as sr
from deep_translator import GoogleTranslator
import edge_tts
from src.engines.base import BaseTranslationEngine

class FreeEngine(BaseTranslationEngine):
    def __init__(
        self,
        default_voice_en: str = "en-US-ChristopherNeural",
        default_voice_pt: str = "pt-BR-AntonioNeural"
    ):
        self.default_voice_en = default_voice_en
        self.default_voice_pt = default_voice_pt
        self.recognizer = sr.Recognizer()

    async def transcribe(self, audio_bytes: bytes, lang: str = "pt") -> str:
        if not audio_bytes:
            return ""

        lang_code = "pt-BR" if lang == "pt" else "en-US"
        loop = asyncio.get_event_loop()

        def _recognize():
            buf = io.BytesIO(audio_bytes)
            with sr.AudioFile(buf) as source:
                audio_data = self.recognizer.record(source)
                try:
                    return self.recognizer.recognize_google(audio_data, language=lang_code)
                except sr.UnknownValueError:
                    return ""
                except sr.RequestError as e:
                    raise RuntimeError(f"Erro no serviço gratuito de reconhecimento: {e}")

        return await loop.run_in_executor(None, _recognize)

    async def translate(self, text: str, source_lang: str = "pt", target_lang: str = "en") -> str:
        if not text:
            return ""

        loop = asyncio.get_event_loop()

        def _do_translate():
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            return translator.translate(text)

        return await loop.run_in_executor(None, _do_translate)

    async def synthesize(self, text: str, lang: str = "en", voice: str | None = None) -> bytes:
        if not text:
            return b""

        use_voice = voice
        if not use_voice:
            use_voice = self.default_voice_en if lang == "en" else self.default_voice_pt

        # 1. Try Microsoft Edge Neural TTS (Ultra realistic neural voice)
        try:
            communicate = edge_tts.Communicate(text, use_voice)
            mp3_data = bytearray()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    mp3_data.extend(chunk["data"])
            if mp3_data:
                return bytes(mp3_data)
        except Exception as e:
            print(f"[FreeEngine] Edge-TTS warning: {e}, falling back to native macOS say")

        # 2. Fallback to native macOS 'say' (Offline & built-in)
        loop = asyncio.get_event_loop()
        def _macos_say():
            temp_aiff = "/tmp/parrot_say.aiff"
            temp_wav = "/tmp/parrot_say.wav"
            voice_name = "Samantha" if lang == "en" else "Luciana"
            subprocess.run(["say", "-v", voice_name, "-o", temp_aiff, text], check=True)
            subprocess.run(["ffmpeg", "-y", "-i", temp_aiff, temp_wav], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            with open(temp_wav, "rb") as f:
                return f.read()

        return await loop.run_in_executor(None, _macos_say)
