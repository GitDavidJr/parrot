import asyncio
import threading
import time
import types
import sys
import unittest
from unittest.mock import patch

import numpy as np

from src.audio.player import AudioPlayer
from src.audio.recorder import AudioRecorder
from src.audio.system_recorder import SystemAudioRecorder
from src.config import settings
from src.service import ParrotService


class FakeEngine:
    async def transcribe(self, audio_bytes: bytes, lang: str = "en") -> str:
        await asyncio.sleep(0.01 if audio_bytes == b"first" else 0)
        return audio_bytes.decode()

    async def translate(self, text: str, source_lang: str = "en", target_lang: str = "pt") -> str:
        return f"pt:{text}"

    async def synthesize(self, text: str, lang: str = "pt", voice=None) -> bytes:
        return text.encode()


class AudioPipelineTests(unittest.IsolatedAsyncioTestCase):
    async def test_meeting_segments_are_processed_in_capture_order(self):
        old_engine = settings.engine
        old_dub = settings.dub_system_audio
        settings.engine = "free"
        settings.dub_system_audio = False
        service = ParrotService()
        service.free_engine = FakeEngine()
        service.is_active = True
        worker = asyncio.create_task(service._meeting_audio_worker())
        try:
            service._handle_meeting_speech_segment(b"first", 1.0)
            service._handle_meeting_speech_segment(b"second", 1.0)
            await asyncio.wait_for(service._meeting_audio_queue.join(), timeout=2)
            self.assertEqual(
                [entry["original"] for entry in service.history],
                ["first", "second"],
            )
        finally:
            worker.cancel()
            await worker
            settings.engine = old_engine
            settings.dub_system_audio = old_dub

    async def test_player_uses_independent_output_streams(self):
        events = []
        guard = threading.Lock()

        class FakeOutputStream:
            def __init__(self, *, device, **kwargs):
                self.device = device

            def start(self):
                with guard:
                    events.append(("start", self.device))

            def write(self, data):
                time.sleep(0.02)
                with guard:
                    events.append(("write", self.device, len(data)))

            def stop(self):
                with guard:
                    events.append(("stop", self.device))

            def abort(self):
                pass

            def close(self):
                pass

        player = AudioPlayer()
        player.decode_audio = lambda _: (np.ones(240, dtype=np.float32), 48000)
        device = {"max_output_channels": 2, "default_samplerate": 48000}
        with patch("src.audio.player.sd.query_devices", return_value=device), patch(
            "src.audio.player.sd.OutputStream", FakeOutputStream
        ):
            await asyncio.gather(
                player.play_audio_to_device(b"a", device_id=10),
                player.play_audio_to_device(b"b", device_id=11),
            )

        self.assertIn(("write", 10, 240), events)
        self.assertIn(("write", 11, 240), events)

    def test_ptt_mode_does_not_trigger_vad_when_key_is_released(self):
        recorder = AudioRecorder(capture_mode="ptt", energy_threshold=0.001)
        recorder.is_recording = True
        recorder.process_audio_block(np.ones((2400, 1), dtype=np.float32) * 0.1)
        self.assertFalse(recorder.is_speaking)
        self.assertEqual(len(recorder._audio_buffer), 0)

    def test_windows_loopback_keeps_native_stereo_channels(self):
        call = {}

        class FakeRecorder:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def record(self, numframes):
                time.sleep(0.005)
                return np.zeros((numframes, 2), dtype=np.float32)

        class FakeMicrophone:
            def recorder(self, **kwargs):
                call.update(kwargs)
                return FakeRecorder()

        fake_soundcard = types.SimpleNamespace(
            default_speaker=lambda: types.SimpleNamespace(id="speaker-id", name="Speakers"),
            get_microphone=lambda **kwargs: FakeMicrophone(),
        )
        recorder = SystemAudioRecorder(backend="wasapi")
        with patch.dict(sys.modules, {"soundcard": fake_soundcard}), patch(
            "src.audio.system_recorder.sys.platform", "win32"
        ):
            loop = asyncio.new_event_loop()
            try:
                recorder.start(loop=loop)
                time.sleep(0.02)
                recorder.stop()
            finally:
                loop.close()

        self.assertIsNone(call["channels"])
        self.assertEqual(call["blocksize"], 4800)


if __name__ == "__main__":
    unittest.main()
