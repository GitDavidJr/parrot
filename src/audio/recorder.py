import io
import time
import math
import asyncio
import numpy as np
import sounddevice as sd
import soundfile as sf
from typing import Callable, Optional

class AudioRecorder:
    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        energy_threshold: float = 0.015,
        silence_threshold_ms: int = 650,
        min_speech_duration_ms: int = 400,
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.energy_threshold = energy_threshold
        self.silence_threshold_ms = silence_threshold_ms
        self.min_speech_duration_ms = min_speech_duration_ms

        self.stream: Optional[sd.InputStream] = None
        self.is_recording = False
        self.is_speaking = False
        self.push_to_talk_active = False

        self._audio_buffer: list[np.ndarray] = []
        self._silence_start_time: Optional[float] = None
        self._speech_start_time: Optional[float] = None
        
        # Callbacks
        self.on_speech_segment: Optional[Callable[[bytes, float], None]] = None
        self.on_level_update: Optional[Callable[[float, bool], None]] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def start(self, device_id: Optional[int] = None, loop: Optional[asyncio.AbstractEventLoop] = None):
        if self.is_recording:
            return

        self._loop = loop or asyncio.get_event_loop()
        self.is_recording = True
        self.is_speaking = False
        self._audio_buffer = []
        self._silence_start_time = None
        self._speech_start_time = None

        block_size = int(self.sample_rate * 0.05)  # 50ms chunks

        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
            device=device_id,
            blocksize=block_size,
            callback=self._audio_callback,
        )
        self.stream.start()

    def stop(self):
        if not self.is_recording:
            return
        self.is_recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

    def set_push_to_talk(self, active: bool):
        """Called when PTT key is pressed (active=True) or released (active=False)."""
        if active and not self.push_to_talk_active:
            self.push_to_talk_active = True
            self._audio_buffer = []
            self.is_speaking = True
            self._speech_start_time = time.time()
        elif not active and self.push_to_talk_active:
            self.push_to_talk_active = False
            self.is_speaking = False
            if self._audio_buffer:
                duration = time.time() - (self._speech_start_time or time.time())
                self._dispatch_segment(duration)

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status):
        if not self.is_recording:
            return

        # Calculate RMS energy
        rms = float(np.sqrt(np.mean(indata**2)))
        # Normalize level between 0.0 and 1.0 for UI visualizer
        norm_level = min(1.0, rms * 15.0)

        # Send level update to UI
        if self.on_level_update and self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self.on_level_update, norm_level, self.is_speaking)

        # Handle Push-to-Talk mode
        if self.push_to_talk_active:
            self._audio_buffer.append(indata.copy())
            return

        # Handle VAD mode (Voice Activity Detection)
        now = time.time()
        is_above_threshold = rms >= self.energy_threshold

        if is_above_threshold:
            if not self.is_speaking:
                self.is_speaking = True
                self._speech_start_time = now
                self._audio_buffer = []
            
            self._silence_start_time = None
            self._audio_buffer.append(indata.copy())
        else:
            if self.is_speaking:
                self._audio_buffer.append(indata.copy())
                if self._silence_start_time is None:
                    self._silence_start_time = now
                elif (now - self._silence_start_time) * 1000 >= self.silence_threshold_ms:
                    # Silence threshold reached -> complete segment!
                    self.is_speaking = False
                    speech_duration = (now - (self._speech_start_time or now))
                    if speech_duration * 1000 >= self.min_speech_duration_ms and self._audio_buffer:
                        self._dispatch_segment(speech_duration)
                    self._audio_buffer = []
                    self._silence_start_time = None

    def _dispatch_segment(self, duration: float):
        if not self._audio_buffer:
            return

        audio_data = np.concatenate(self._audio_buffer, axis=0)
        # Convert float32 [-1, 1] to 16-bit PCM WAV bytes
        buf = io.BytesIO()
        buf.name = "speech.wav"
        sf.write(buf, audio_data, self.sample_rate, format="WAV", subtype="PCM_16")
        wav_bytes = buf.getvalue()

        if self.on_speech_segment and self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self.on_speech_segment, wav_bytes, duration)
