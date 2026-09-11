import sounddevice as sd
import sys
from typing import Dict, List, Any

def get_audio_devices() -> Dict[str, Any]:
    """
    Scans Core Audio devices and categorizes them:
    - input_devices: microphones (Microfone Externo, Built-in, etc.)
    - virtual_output_devices: Perssua / BlackHole (used to inject audio into Zoom/Meet/Discord)
    - output_devices: headphones / speakers (Fones de Ouvido Externos, Built-in, etc.)
    """
    devices = sd.query_devices()
    default_in = sd.default.device[0]
    default_out = sd.default.device[1]

    input_devices: List[Dict[str, Any]] = []
    virtual_devices: List[Dict[str, Any]] = []
    output_devices: List[Dict[str, Any]] = []

    virtual_output_id = None
    virtual_input_id = None
    best_mic_id = None
    best_headphone_id = None

    meeting_devices: List[Dict[str, Any]] = []

    for i, dev in enumerate(devices):
        name = dev["name"]
        in_ch = dev["max_input_channels"]
        out_ch = dev["max_output_channels"]
        sr = int(dev["default_samplerate"])

        item = {
            "id": i,
            "name": name,
            "inputs": in_ch,
            "outputs": out_ch,
            "sample_rate": sr,
        }

        # Virtual cables used to inject translated speech into call apps.
        lower_name = name.lower()
        virtual_markers = (
            "perssua", "blackhole", "cable input", "cable output",
            "vb-audio", "voicemeeter input", "voicemeeter output",
        )
        is_virtual = any(marker in lower_name for marker in virtual_markers)
        if is_virtual and out_ch > 0:
            virtual_devices.append(item)
            if virtual_output_id is None:
                virtual_output_id = i

        if in_ch > 0:
            meeting_devices.append(item)
            if is_virtual and virtual_input_id is None:
                virtual_input_id = i
            if not is_virtual:
                input_devices.append(item)
                # Prefer external mic or default mic
                if "externo" in name.lower() or i == default_in:
                    if best_mic_id is None or "externo" in name.lower():
                        best_mic_id = i

        if out_ch > 0 and not is_virtual:
            output_devices.append(item)
            if "fone" in name.lower() or "headphone" in name.lower() or i == default_out:
                if best_headphone_id is None or "fone" in name.lower():
                    best_headphone_id = i

    if best_mic_id is None and input_devices:
        best_mic_id = input_devices[0]["id"]

    if best_headphone_id is None and output_devices:
        best_headphone_id = output_devices[0]["id"]

    # Duplex drivers such as Perssua may use one device ID for both directions.
    if virtual_input_id is None and virtual_output_id is not None:
        output_item = next((item for item in virtual_devices if item["id"] == virtual_output_id), None)
        if output_item and output_item["inputs"] > 0:
            virtual_input_id = virtual_output_id

    return {
        "inputs": input_devices,
        "meeting_inputs": meeting_devices,
        "virtual_outputs": virtual_devices,
        "outputs": output_devices,
        "recommended": {
            "mic_id": best_mic_id,
            "virtual_mic_id": virtual_output_id,
            "virtual_input_id": virtual_input_id,
            "meeting_device_id": virtual_input_id,
            "headphones_id": best_headphone_id,
        },
        "platform": sys.platform,
        "system_audio": {
            "recommended_backend": "screencapturekit" if sys.platform == "darwin" else "wasapi" if sys.platform == "win32" else "loopback",
            "native_available": sys.platform in {"darwin", "win32"},
        },
    }
