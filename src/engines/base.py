from abc import ABC, abstractmethod
from typing import Optional

class BaseTranslationEngine(ABC):
    @abstractmethod
    async def transcribe(self, audio_bytes: bytes, lang: str = "pt") -> str:
        """Transcribes speech audio bytes to text."""
        pass

    @abstractmethod
    async def translate(self, text: str, source_lang: str = "pt", target_lang: str = "en") -> str:
        """Translates text from source language to target language."""
        pass

    @abstractmethod
    async def synthesize(self, text: str, lang: str = "en", voice: Optional[str] = None) -> bytes:
        """Synthesizes text into speech audio bytes (WAV or MP3)."""
        pass
