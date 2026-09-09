import io
import asyncio
import numpy as np
import sounddevice as sd
import soundfile as sf
import miniaudio
from typing import Optional, Callable

class AudioPlayer:
    def __init__(self):
        self._current_stream = None
        self._is_playing = False

    def decode_audio(self, audio_bytes: bytes) -> tuple[np.ndarray, int]:
        """Decodes WAV or MP3 bytes into a float32 numpy array [-1.0, 1.0] and sample_rate."""
        # Try soundfile first (WAV format)
        try:
            buf = io.BytesIO(audio_bytes)
            data, sr = sf.read(buf, dtype="float32")
            return data, sr
        except Exception:
            pass

        # Try miniaudio (MP3 format from Edge-TTS or OpenAI)
        try:
            decoded = miniaudio.mp3_read_s16(audio_bytes)
            arr = np.frombuffer(decoded.samples, dtype=np.int16).astype(np.float32) / 32768.0
            if decoded.nchannels == 1:
                return arr, decoded.sample_rate
            else:
                arr = arr.reshape(-1, decoded.nchannels)
                return arr, decoded.sample_rate
        except Exception as e:
            raise ValueError(f"Failed to decode audio bytes: {e}")

    async def play_audio_to_device(
        self,
        audio_bytes: bytes,
        device_id: int,
        volume: float = 1.0,
        on_progress: Optional[Callable[[float], None]] = None
    ):
        """
        Plays audio to a specific device (e.g. Perssua or Headphones) asynchronously.
        Ensures proper channel alignment (mono -> stereo if needed).
        """
        data, sr = self.decode_audio(audio_bytes)

        # Apply volume
        data = data * max(0.0, min(2.0, volume))

        # Check device channel capabilities
        dev_info = sd.query_devices(device_id)
        max_ch = dev_info["max_output_channels"]

        if data.ndim == 1 and max_ch >= 2:
            data = np.column_stack([data, data])
        elif data.ndim == 2 and data.shape[1] > max_ch:
            data = data[:, :max_ch]

        self._is_playing = True
        loop = asyncio.get_event_loop()

        def _play_blocking():
            try:
                sd.play(data, samplerate=sr, device=device_id)
                sd.wait()
            finally:
                self._is_playing = False

        await loop.run_in_executor(None, _play_blocking)

    def stop(self):
        sd.stop()
        self._is_playing = False

    @property
    def is_playing(self) -> bool:
        return self._is_playing

audio_player = AudioPlayer()
