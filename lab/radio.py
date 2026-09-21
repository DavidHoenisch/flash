"""Supervised desktop Digirig bring-up. Only `transmit --execute` asserts PTT."""

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import subprocess
import sys
import time

import numpy as np
from scipy.io import wavfile

from .channel import SAMPLE_RATE


def audio_device(name):
    import sounddevice as sd
    matches = [(i, d) for i, d in enumerate(sd.query_devices()) if d["name"] == name]
    if len(matches) != 1:
        raise ValueError(f"need exactly one audio device named {name!r}; run devices")
    return matches[0]


def load_audio(path, gain=1.0):
    rate, audio = wavfile.read(path)
    if rate != SAMPLE_RATE or audio.ndim != 1 or not 0 < len(audio) <= 8 * SAMPLE_RATE:
        raise ValueError("test WAV must be mono 48000 Hz, nonempty, at most 8 seconds")
    if audio.dtype == np.int16:
        audio = audio.astype(np.float32) / 32768
    elif not np.issubdtype(audio.dtype, np.floating):
        raise ValueError("test WAV must be int16 or floating point")
    audio = np.asarray(audio, dtype=np.float32) * gain
    if not math.isfinite(gain) or not 0 < gain <= 1 or not np.isfinite(audio).all() or np.max(np.abs(audio)) > 0.5:
        raise ValueError("need finite audio, 0 < gain <= 1, and output peak <= 0.5")
    return audio


def validate_port(device):
    from serial.tools import list_ports
    found = [p for p in list_ports.comports() if p.device == device and p.vid == 0x10c4 and p.pid == 0xea60]
    if len(found) != 1:
        raise ValueError("selected port must identify as a Silicon Labs CP210x (10c4:ea60)")


def keyed_play(port, worker, duration, *, sleep=time.sleep, run=subprocess.run):
    """Parent owns PTT; blocking audio runs in a child with a deadline.

    Configure inactive control lines before opening. Driver-level opening glitches
    cannot be ruled out. This is a software timeout, not a hardware PTT watchdog.
    """
    if not 0 < duration <= 8:
        raise ValueError("test duration must be 0..8 seconds")
    port.rts = False
    port.dtr = False
    try:
        port.open()
        port.rts = False
        port.rts = True
        sleep(0.3)
        # Child uses only audio. run() kills/waits for it on timeout; parent unkeys.
        result = run(worker, check=True, capture_output=True, text=True, timeout=duration + 3)
        sleep(0.2)
        return result.stdout
    finally:
        if port.is_open:
            try:
                port.rts = False
            finally:
                port.close()


def play(args):
    import sounddevice as sd
    audio = load_audio(args.wav, args.gain)
    index, info = audio_device(args.device)
    channels = min(2, info["max_output_channels"])
    if channels < 1:
        raise ValueError("selected device has no output")
    output = np.repeat(audio[:, None], channels, axis=1)
    with sd.OutputStream(device=index, samplerate=SAMPLE_RATE, channels=channels, dtype="float32", latency="high") as stream:
        underflow = stream.write(output)
        stream.stop()  # Drain queued samples before the parent releases PTT.
    if underflow:
        raise RuntimeError("audio output underflow during test")
    print(json.dumps({"audio_playback_completed": True, "device": args.device, "seconds": len(audio) / SAMPLE_RATE}))


def transmit(args):
    import serial
    import sounddevice as sd
    audio = load_audio(args.wav, args.gain)
    index, info = audio_device(args.device)
    channels = min(2, info["max_output_channels"])
    if channels < 1:
        raise ValueError("selected device has no output")
    validate_port(args.port)
    # Open/close the intended audio device with PTT untouched before attempting RF.
    with sd.OutputStream(device=index, samplerate=SAMPLE_RATE, channels=channels, dtype="float32"):
        pass
    report = {"utc": datetime.now(timezone.utc).isoformat(), "device": args.device, "port": args.port,
              "frequency_mhz_operator_reported": args.frequency_mhz, "seconds": len(audio) / SAMPLE_RATE,
              "gain": args.gain, "execute": args.execute, "ptt_assertion_requested": False,
              "note": "Radio tuning, RF output and physical PTT state are not read back by this adapter."}
    print(json.dumps(report), flush=True)
    if not args.execute:
        return
    port = serial.Serial(port=None, baudrate=9600, timeout=0.5, write_timeout=0.5, rtscts=False, dsrdtr=False, exclusive=True)
    port.port = args.port
    worker = [sys.executable, "-m", "lab.radio", "_play", str(args.wav.resolve()), "--device", args.device, "--gain", str(args.gain)]
    try:
        report["ptt_assertion_requested"] = True
        report["playback"] = json.loads(keyed_play(port, worker, len(audio) / SAMPLE_RATE))
        report["result"] = "playback finished; software PTT release and serial close completed"
    except BaseException as error:
        report["result"] = f"failed: {type(error).__name__}: {error}"
        raise
    finally:
        args.log.parent.mkdir(parents=True, exist_ok=True)
        args.log.write_text(json.dumps(report, indent=2) + "\n")


def receive(args):
    import sounddevice as sd
    if not math.isfinite(args.seconds) or not 0 < args.seconds <= 10:
        raise ValueError("capture duration must be 0..10 seconds")
    index, info = audio_device(args.device)
    if info["max_input_channels"] < 1:
        raise ValueError("selected device has no input")
    with sd.InputStream(device=index, samplerate=SAMPLE_RATE, channels=1, dtype="float32") as stream:
        audio, overflow = stream.read(round(args.seconds * SAMPLE_RATE))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(args.output, SAMPLE_RATE, audio[:, 0])
    print(json.dumps({"file": str(args.output), "input_device": args.device, "seconds": len(audio) / SAMPLE_RATE,
                      "rms": float(np.sqrt(np.mean(audio * audio))), "peak": float(np.max(np.abs(audio))),
                      "input_overflow": overflow, "ptt_accessed": False}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("devices")
    rx = commands.add_parser("receive")
    rx.add_argument("--device", default="USB PnP Sound Device")
    rx.add_argument("--seconds", type=float, default=3)
    rx.add_argument("--output", type=Path, default=Path("artifacts/radio/rx.wav"))
    for name in ("transmit", "_play"):
        tx = commands.add_parser(name)
        tx.add_argument("wav", type=Path)
        tx.add_argument("--device", required=True)
        tx.add_argument("--gain", type=float, default=0.2)
        if name == "transmit":
            tx.add_argument("--port", required=True)
            tx.add_argument("--frequency-mhz", type=float, required=True, help="metadata only; does not tune the radio")
            tx.add_argument("--execute", action="store_true", help="assert PTT and transmit once")
            tx.add_argument("--log", type=Path, default=Path("artifacts/radio/tx-log.json"))
    args = parser.parse_args()
    if args.command == "devices":
        import sounddevice as sd
        from serial.tools import list_ports
        print(json.dumps({"audio": list(sd.query_devices()), "serial": [{"port": p.device, "description": p.description,
              "vid": p.vid, "pid": p.pid} for p in list_ports.comports()]}, indent=2))
    elif args.command == "receive":
        receive(args)
    elif args.command == "_play":
        play(args)
    else:
        transmit(args)


if __name__ == "__main__":
    main()
