import sounddevice as sd
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

    perssua_id = None
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

        # Check if virtual device (Perssua / BlackHole)
        is_perssua = "perssua" in name.lower() or "blackhole" in name.lower()
        if is_perssua and out_ch > 0:
            virtual_devices.append(item)
            if perssua_id is None:
                perssua_id = i

        if in_ch > 0:
            meeting_devices.append(item)
            if not is_perssua:
                input_devices.append(item)
                # Prefer external mic or default mic
                if "externo" in name.lower() or i == default_in:
                    if best_mic_id is None or "externo" in name.lower():
                        best_mic_id = i

        if out_ch > 0 and not is_perssua:
            output_devices.append(item)
            if "fone" in name.lower() or "headphone" in name.lower() or i == default_out:
                if best_headphone_id is None or "fone" in name.lower():
                    best_headphone_id = i

    if best_mic_id is None and input_devices:
        best_mic_id = input_devices[0]["id"]

    if best_headphone_id is None and output_devices:
        best_headphone_id = output_devices[0]["id"]

    # Fallback for virtual device if Perssua isn't named explicitly
    if perssua_id is None and virtual_devices:
        perssua_id = virtual_devices[0]["id"]

    return {
        "inputs": input_devices,
        "meeting_inputs": meeting_devices,
        "virtual_outputs": virtual_devices,
        "outputs": output_devices,
        "recommended": {
            "mic_id": best_mic_id,
            "virtual_mic_id": perssua_id,
            "meeting_device_id": perssua_id or best_mic_id,
            "headphones_id": best_headphone_id,
        },
    }
