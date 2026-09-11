import io
import asyncio
import threading
import numpy as np
import sounddevice as sd
import soundfile as sf
import miniaudio
from typing import Optional, Callable

class AudioPlayer:
    def __init__(self):
        self._is_playing = False
        self._device_locks: dict[int, asyncio.Lock] = {}
        self._streams: set[sd.OutputStream] = set()
        self._streams_lock = threading.Lock()

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

        # Check device channel capabilities and use its native sample rate.
        dev_info = sd.query_devices(device_id)
        max_ch = int(dev_info["max_output_channels"])
        if max_ch < 1:
            raise ValueError(f"Dispositivo {device_id} não possui canais de saída.")

        native_sr = int(dev_info.get("default_samplerate", sr))
        if native_sr != sr and len(data) > 1:
            source_x = np.linspace(0.0, 1.0, len(data), endpoint=False)
            target_len = max(1, round(len(data) * native_sr / sr))
            target_x = np.linspace(0.0, 1.0, target_len, endpoint=False)
            if data.ndim == 1:
                data = np.interp(target_x, source_x, data).astype(np.float32)
            else:
                data = np.column_stack([
                    np.interp(target_x, source_x, data[:, channel])
                    for channel in range(data.shape[1])
                ]).astype(np.float32)
            sr = native_sr

        if data.ndim == 1 and max_ch >= 2:
            data = np.column_stack([data, data])
        elif data.ndim == 1:
            data = data.reshape(-1, 1)
        elif data.ndim == 2 and data.shape[1] > max_ch:
            data = data[:, :max_ch]

        data = np.ascontiguousarray(data, dtype=np.float32)
        channels = 1 if data.ndim == 1 else data.shape[1]
        loop = asyncio.get_event_loop()

        def _play_blocking():
            stream = None
            try:
                stream = sd.OutputStream(
                    samplerate=sr,
                    device=device_id,
                    channels=channels,
                    dtype="float32",
                )
                with self._streams_lock:
                    self._streams.add(stream)
                    self._is_playing = True
                stream.start()
                stream.write(data)
            finally:
                if stream is not None:
                    try:
                        stream.stop()
                        stream.close()
                    except Exception:
                        pass
                    with self._streams_lock:
                        self._streams.discard(stream)
                        self._is_playing = bool(self._streams)

        # One queue per physical device prevents two translated phrases from
        # cutting each other off, while still allowing independent devices to
        # play concurrently (e.g. Perssua + headphones).
        device_lock = self._device_locks.setdefault(device_id, asyncio.Lock())
        async with device_lock:
            await loop.run_in_executor(None, _play_blocking)

    def stop(self):
        with self._streams_lock:
            streams = list(self._streams)
        for stream in streams:
            try:
                stream.abort()
                stream.close()
            except Exception:
                pass
        with self._streams_lock:
            self._streams.clear()
            self._is_playing = False

    @property
    def is_playing(self) -> bool:
        return self._is_playing

audio_player = AudioPlayer()
