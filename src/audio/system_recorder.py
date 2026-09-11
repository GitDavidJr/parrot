import asyncio
import os
import platform
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Callable, Optional

import numpy as np

from src.audio.recorder import AudioRecorder


def resource_root() -> Path:
    """Returns the source root in development or PyInstaller's resource root."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[2]


class SystemAudioRecorder(AudioRecorder):
    """Captures the sound currently playing on the computer.

    macOS uses a small ScreenCaptureKit helper. Windows uses WASAPI loopback
    through SoundCard. A normal CoreAudio input device remains available as a
    compatibility fallback for Perssua/BlackHole installations.
    """

    def __init__(self, *args, backend: str = "auto", **kwargs):
        super().__init__(*args, **kwargs)
        self.requested_backend = backend
        self.active_backend = "idle"
        self.last_error: Optional[str] = None
        self._worker_thread: Optional[threading.Thread] = None
        self._stderr_thread: Optional[threading.Thread] = None
        self._process: Optional[subprocess.Popen] = None
        self._soundcard_recorder = None
        self._fallback_device_id: Optional[int] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self._ready_event = threading.Event()

    def _report_error(self, message: str):
        self.last_error = message
        self._ready_event.set()
        if self.on_error and self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self.on_error, message)

    @property
    def helper_path(self) -> Path:
        filename = "parrot-system-audio.exe" if sys.platform == "win32" else "parrot-system-audio"
        return resource_root() / "src" / "native" / "bin" / filename

    def _prepare(self, loop: Optional[asyncio.AbstractEventLoop]):
        self._loop = loop or asyncio.get_event_loop()
        self.is_recording = True
        self.is_speaking = False
        self._audio_buffer = []
        self._preroll_buffer.clear()
        self._silence_start_time = None
        self._speech_start_time = None
        self._has_voice = False
        self.last_error = None
        self._ready_event.clear()

    def start(self, device_id: Optional[int] = None, loop: Optional[asyncio.AbstractEventLoop] = None):
        if self.is_recording:
            return

        self._fallback_device_id = device_id
        backend = self.requested_backend
        if backend == "auto":
            if sys.platform == "darwin":
                backend = "screencapturekit"
            elif sys.platform == "win32":
                backend = "wasapi"
            else:
                backend = "loopback"

        if backend == "screencapturekit":
            self._start_macos(loop)
        elif backend in {"wasapi", "loopback"}:
            self._start_soundcard(loop)
        elif backend == "virtual_device":
            self.active_backend = "virtual_device"
            super().start(device_id=device_id, loop=loop)
        else:
            raise ValueError(f"Backend de áudio do sistema desconhecido: {backend}")

    def _start_macos(self, loop: Optional[asyncio.AbstractEventLoop]):
        helper = self.helper_path
        if not helper.exists() and not getattr(sys, "frozen", False):
            self._build_macos_helper(helper)
        if not helper.exists():
            raise RuntimeError("Capturador nativo do macOS não foi encontrado no pacote.")

        self.sample_rate = 48000
        self.channels = 1
        self._prepare(loop)
        self.active_backend = "screencapturekit"
        self._process = subprocess.Popen(
            [str(helper), "--parent-pid", str(os.getpid())],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )

        self._worker_thread = threading.Thread(target=self._read_pcm_stdout, daemon=True)
        self._stderr_thread = threading.Thread(target=self._read_helper_stderr, daemon=True)
        self._worker_thread.start()
        self._stderr_thread.start()
        if not self._ready_event.wait(timeout=8):
            self.last_error = "O macOS não confirmou a captura do áudio do sistema em 8 segundos."
            self.stop()
            raise RuntimeError(self.last_error)
        if self.last_error:
            self.stop()
            raise RuntimeError(self.last_error)

    def _build_macos_helper(self, output: Path):
        swiftc = shutil.which("swiftc") or shutil.which("xcrun")
        source = resource_root() / "src" / "native" / "macos" / "SystemAudioCapture.swift"
        plist = resource_root() / "src" / "native" / "macos" / "HelperInfo.plist"
        if not swiftc or not source.exists():
            return
        output.parent.mkdir(parents=True, exist_ok=True)
        if Path(swiftc).name == "xcrun":
            command = [swiftc, "swiftc"]
        else:
            command = [swiftc]
        command += [
            str(source), "-parse-as-library", "-O", "-target", f"{platform.machine()}-apple-macos13.0",
            "-framework", "ScreenCaptureKit", "-framework", "AVFoundation",
            "-framework", "CoreMedia", "-Xlinker", "-sectcreate", "-Xlinker", "__TEXT",
            "-Xlinker", "__info_plist", "-Xlinker", str(plist), "-o", str(output),
        ]
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode != 0:
            self.last_error = completed.stderr.strip()
            raise RuntimeError(f"Não foi possível compilar o capturador do macOS: {self.last_error}")

    def _read_pcm_stdout(self):
        assert self._process and self._process.stdout
        block_bytes = int(self.sample_rate * 0.05) * 4
        pending = bytearray()
        while self.is_recording:
            chunk = self._process.stdout.read(block_bytes - len(pending))
            if not chunk:
                break
            pending.extend(chunk)
            if len(pending) < block_bytes:
                continue
            samples = np.frombuffer(bytes(pending), dtype="<f4").copy().reshape(-1, 1)
            pending.clear()
            self.process_audio_block(samples)

        if self.is_recording:
            code = self._process.poll()
            if not self.last_error:
                self._report_error(f"Capturador do macOS foi encerrado inesperadamente ({code}).")
            self.is_recording = False

    def _read_helper_stderr(self):
        assert self._process and self._process.stderr
        for raw_line in iter(self._process.stderr.readline, b""):
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            if line.startswith("ERROR:"):
                self._report_error(line.removeprefix("ERROR:").strip())
            elif line.startswith("READY:"):
                self._ready_event.set()
            print(f"[SystemAudio/macOS] {line}")

    def _start_soundcard(self, loop: Optional[asyncio.AbstractEventLoop]):
        try:
            import soundcard as sc
        except ImportError as exc:
            raise RuntimeError("Dependência SoundCard não instalada para captura WASAPI.") from exc

        speaker = sc.default_speaker()
        if speaker is None:
            raise RuntimeError("Nenhuma saída de áudio padrão foi encontrada.")
        try:
            loopback = sc.get_microphone(id=str(speaker.id), include_loopback=True)
        except (IndexError, RuntimeError):
            loopback = sc.get_microphone(id=str(speaker.name), include_loopback=True)
        if loopback is None:
            raise RuntimeError(f"Loopback da saída '{speaker.name}' não está disponível.")

        self.sample_rate = 48000
        self.channels = 1
        self._prepare(loop)
        self.active_backend = "wasapi" if sys.platform == "win32" else "loopback"

        def capture():
            try:
                # Keep the endpoint's native channel layout. SoundCard/WASAPI
                # has a known single-channel capture bug; AudioRecorder safely
                # downmixes the resulting stereo block before transcription.
                with loopback.recorder(samplerate=self.sample_rate, channels=None, blocksize=4800) as recorder:
                    self._soundcard_recorder = recorder
                    self._ready_event.set()
                    while self.is_recording:
                        data = recorder.record(numframes=2400)
                        self.process_audio_block(np.asarray(data, dtype=np.float32))
            except Exception as exc:
                self._report_error(str(exc))
                print(f"[SystemAudio/{self.active_backend}] {exc}")
            finally:
                self._soundcard_recorder = None
                self.is_recording = False
                self.active_backend = "idle"

        self._worker_thread = threading.Thread(target=capture, daemon=True)
        self._worker_thread.start()
        if not self._ready_event.wait(timeout=5):
            self.last_error = self.last_error or "O WASAPI não confirmou a captura em 5 segundos."
            self.stop()
            raise RuntimeError(self.last_error)
        if self.last_error:
            self.stop()
            raise RuntimeError(self.last_error)

    def stop(self):
        if self.active_backend == "virtual_device":
            super().stop()
            self.active_backend = "idle"
            return
        if not self.is_recording and not self._process:
            return

        self.is_recording = False
        if self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2)
        self._worker_thread = None
        self.active_backend = "idle"
