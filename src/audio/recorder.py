import io
import time
import math
import asyncio
import collections
import numpy as np
import sounddevice as sd
import soundfile as sf
from typing import Callable, Optional

class AudioRecorder:
    def __init__(
        self,
        sample_rate: int = 48000,
        channels: int = 1,
        energy_threshold: float = 0.015,
        silence_threshold_ms: int = 300,
        min_speech_duration_ms: int = 350,
        max_phrase_duration_s: float = 4.0,
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.energy_threshold = energy_threshold
        self.silence_threshold_ms = silence_threshold_ms
        self.min_speech_duration_ms = min_speech_duration_ms
        self.max_phrase_duration_s = max_phrase_duration_s

        self.stream: Optional[sd.InputStream] = None
        self.is_recording = False
        self.is_speaking = False
        self.push_to_talk_active = False
        self.is_suppressed = False  # Echo suppression (used when Parrot is playing audio)

        self._audio_buffer: list[np.ndarray] = []
        # Ring buffer for pre-roll (keeps last ~150ms of audio so initial consonants are never cut)
        self._preroll_buffer = collections.deque(maxlen=3)
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
        self._preroll_buffer.clear()
        self._silence_start_time = None
        self._speech_start_time = None

        # Automatically adapt sample rate and channel count to native CoreAudio device capabilities
        try:
            dev = sd.query_devices(device_id) if device_id is not None else sd.query_devices(sd.default.device[0])
            self.sample_rate = int(dev.get("default_samplerate", 48000))
            max_in = int(dev.get("max_input_channels", 1))
            self.channels = min(max_in, self.channels) if self.channels > 0 else max_in
            if self.channels == 0:
                self.channels = 1
        except Exception:
            self.sample_rate = 48000
            self.channels = 1

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
            self._audio_buffer = list(self._preroll_buffer)
            self.is_speaking = True
            self._speech_start_time = time.time()
        elif not active and self.push_to_talk_active:
            self.push_to_talk_active = False
            self.is_speaking = False
            if self._audio_buffer:
                duration = time.time() - (self._speech_start_time or time.time())
                self._dispatch_segment(duration)
            self._audio_buffer = []

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status):
        if not self.is_recording:
            return

        # If suppressed (e.g. Parrot is currently playing translated audio), discard input
        if self.is_suppressed:
            if self.is_speaking:
                self.is_speaking = False
                self._audio_buffer = []
                self._silence_start_time = None
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
                # Include pre-roll so initial consonants/vowels are intact
                self._audio_buffer = list(self._preroll_buffer)
            
            self._silence_start_time = None
            self._audio_buffer.append(indata.copy())

            # Fast chunking: if speech duration exceeds max_phrase_duration_s (e.g. 4s),
            # split and dispatch current phrase immediately so translation starts right away!
            speech_elapsed = now - (self._speech_start_time or now)
            if speech_elapsed >= self.max_phrase_duration_s and self._audio_buffer:
                self._dispatch_segment(speech_elapsed)
                # Keep recording the rest of the speech seamlessly
                self._audio_buffer = []
                self._speech_start_time = now
        else:
            if not self.is_speaking:
                # Store silence in pre-roll buffer
                self._preroll_buffer.append(indata.copy())
            else:
                self._audio_buffer.append(indata.copy())
                if self._silence_start_time is None:
                    self._silence_start_time = now

                speech_elapsed = now - (self._speech_start_time or now)
                silence_elapsed_ms = (now - self._silence_start_time) * 1000

                # Adaptive pause threshold:
                # If speech was longer than 2.0s, detect phrase boundary faster (180ms breath pause)
                effective_silence_ms = 180 if speech_elapsed >= 2.0 else self.silence_threshold_ms

                if silence_elapsed_ms >= effective_silence_ms:
                    self.is_speaking = False
                    speech_duration = now - (self._speech_start_time or now)
                    if speech_duration * 1000 >= self.min_speech_duration_ms and self._audio_buffer:
                        self._dispatch_segment(speech_duration)
                    self._audio_buffer = []
                    self._silence_start_time = None

    def _dispatch_segment(self, duration: float):
        if not self._audio_buffer:
            return

        audio_data = np.concatenate(self._audio_buffer, axis=0)
        # Downmix stereo to mono if multi-channel
        if audio_data.ndim > 1 and audio_data.shape[1] > 1:
            audio_data = np.mean(audio_data, axis=1)
        elif audio_data.ndim > 1 and audio_data.shape[1] == 1:
            audio_data = audio_data.squeeze(axis=1)

        # Convert float32 [-1, 1] to 16-bit PCM WAV bytes
        buf = io.BytesIO()
        buf.name = "speech.wav"
        sf.write(buf, audio_data, self.sample_rate, format="WAV", subtype="PCM_16")
        wav_bytes = buf.getvalue()

        if self.on_speech_segment and self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self.on_speech_segment, wav_bytes, duration)

