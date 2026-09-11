import io
import os
import sys
import asyncio
import subprocess
import tempfile
from pathlib import Path
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
            print(f"[FreeEngine] Edge-TTS warning: {e}; usando a voz nativa do sistema")

        # 2. Offline operating-system fallback.
        loop = asyncio.get_event_loop()

        def _native_speech():
            suffix = ".aiff" if sys.platform == "darwin" else ".wav"
            fd, path_str = tempfile.mkstemp(prefix="parrot_tts_", suffix=suffix)
            os.close(fd)
            path = Path(path_str)
            try:
                if sys.platform == "darwin":
                    voice_name = "Samantha" if lang == "en" else "Luciana"
                    subprocess.run(["say", "-v", voice_name, "-o", str(path), text], check=True)
                elif sys.platform == "win32":
                    script = (
                        "Add-Type -AssemblyName System.Speech; "
                        "$voice = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                        "$voice.SetOutputToWaveFile($env:PARROT_TTS_OUTPUT); "
                        "$voice.Speak($env:PARROT_TTS_TEXT); $voice.Dispose()"
                    )
                    child_env = os.environ.copy()
                    child_env["PARROT_TTS_OUTPUT"] = str(path)
                    child_env["PARROT_TTS_TEXT"] = text
                    subprocess.run(
                        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        env=child_env,
                    )
                else:
                    completed = subprocess.run(
                        ["espeak", "--stdout", "-v", "en" if lang == "en" else "pt-br", text],
                        check=True,
                        capture_output=True,
                    )
                    return completed.stdout
                return path.read_bytes()
            finally:
                path.unlink(missing_ok=True)

        return await loop.run_in_executor(None, _native_speech)
