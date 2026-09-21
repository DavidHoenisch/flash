"""Subprocess boundary for the Rust modem and an independent framing oracle."""

from pathlib import Path
import subprocess
import zlib

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BINARY = ROOT / "target" / "release" / "flash-modem"
PROFILES = ("fsk2", "fsk4")


def build():
    subprocess.run(["cargo", "build", "--release", "--locked"], cwd=ROOT, check=True)


def invoke(command, profile, data):
    result = subprocess.run([str(BINARY), command, profile], input=data, capture_output=True, timeout=30)
    if result.returncode == 2 and command in ("decode", "decode-stream"):
        return None
    if result.returncode != 0:
        raise RuntimeError(f"modem {command} failed: {result.stderr.decode(errors='replace')}")
    return result.stdout


def encode(payload, profile):
    return np.frombuffer(invoke("encode", profile, payload), dtype="<f4").copy()


def decode(samples, profile, receiver="fixed"):
    command = {"fixed": "decode", "stream": "decode-stream"}[receiver]
    return invoke(command, profile, np.asarray(samples, dtype="<f4").tobytes())


def reference_frame(payload, profile):
    if len(payload) > 1024:
        raise ValueError("payload exceeds 1024 bytes")
    header = bytes([0, PROFILES.index(profile) + 1]) + len(payload).to_bytes(2, "big")
    crc = lambda data: zlib.crc32(data).to_bytes(4, "big")
    return b"\x55" * 16 + bytes.fromhex("d391c5a7") + header + crc(header) + payload + crc(header + payload)


def reference_audio(payload, profile, initial_phase=0.0):
    """Independent vectorized TX to catch shared Rust TX/RX mistakes."""
    bits = np.unpackbits(np.frombuffer(reference_frame(payload, profile), dtype=np.uint8))
    if profile == "fsk2":
        tones, symbols, sps = np.array([1200, 2400]), bits, 40
    else:
        tones, symbols, sps = np.array([900, 1500, 2100, 2700]), bits[::2] * 2 + bits[1::2], 80
    increments = np.repeat(2 * np.pi * tones[symbols] / 48_000, sps)
    phase = initial_phase + np.concatenate(([0], np.cumsum(increments[:-1])))
    return (0.7 * np.sin(phase)).astype("<f4")
