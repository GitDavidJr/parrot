import io
import asyncio
from openai import AsyncOpenAI
from src.engines.base import BaseTranslationEngine

class OpenAIEngine(BaseTranslationEngine):
    def __init__(self, api_key: str, default_voice: str = "alloy", model: str = "gpt-5.4-mini"):
        self.api_key = api_key
        self.default_voice = default_voice
        self.model = model
        self._client: AsyncOpenAI | None = None

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None or self._client.api_key != self.api_key:
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

    def update_key(self, api_key: str):
        self.api_key = api_key
        self._client = AsyncOpenAI(api_key=self.api_key)

    def update_model(self, model: str):
        self.model = model

    async def transcribe(self, audio_bytes: bytes, lang: str = "pt") -> str:
        if not self.api_key:
            raise ValueError("OpenAI API Key não configurada.")

        # Whisper / transcribe accepts a tuple ('filename.wav', bytes, 'content_type')
        file_tuple = ("audio.wav", audio_bytes, "audio/wav")
        try:
            response = await self.client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=file_tuple,
                language=lang,
                temperature=0.0
            )
            return response.text.strip()
        except Exception:
            response = await self.client.audio.transcriptions.create(
                model="whisper-1",
                file=file_tuple,
                language=lang,
                temperature=0.0
            )
            return response.text.strip()

    async def translate(self, text: str, source_lang: str = "pt", target_lang: str = "en") -> str:
        if not text:
            return ""
        if not self.api_key:
            raise ValueError("OpenAI API Key não configurada.")

        lang_names = {
            "pt": "Brazilian Portuguese",
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German"
        }
        src_name = lang_names.get(source_lang, source_lang)
        tgt_name = lang_names.get(target_lang, target_lang)

        system_prompt = (
            f"You are a real-time conversational voice translator in a live meeting. "
            f"Translate spoken {src_name} directly into natural, fluent, spoken {tgt_name}. "
            f"Preserve conversational nuance, colloquial flow, tone, and technical terminology. "
            f"Output ONLY the translated speech without quotes, notes, or explanations."
        )

        completion = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.2,
            max_completion_tokens=250
        )
        return completion.choices[0].message.content.strip()

    async def synthesize(self, text: str, lang: str = "en", voice: str | None = None) -> bytes:
        if not text:
            return b""
        if not self.api_key:
            raise ValueError("OpenAI API Key não configurada.")

        use_voice = voice or self.default_voice or "alloy"
        # Voices available: alloy, echo, fable, onyx, nova, shimmer
        response = await self.client.audio.speech.create(
            model="tts-1",
            voice=use_voice,
            response_format="wav",
            input=text
        )
        # response is an HttpxBinaryResponseContent
        return response.content
