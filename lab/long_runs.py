"""Experiment 0002 adversarial follow-up: long runs without symbol transitions."""

import hashlib
import json
from pathlib import Path

import numpy as np

from .channel import Channel
from .modem import PROFILES, build, decode, encode
from .__main__ import source_hashes


def run():
    build()
    observations = []
    for profile in PROFILES:
        for byte in (0, 255):
            payload = bytes([byte]) * 1024
            tx = encode(payload, profile)
            for ppm in (-2000, 2000):
                rx, metadata = Channel(clock_ppm=ppm).apply(tx, 18, np.random.default_rng(90))
                result = decode(rx, profile, "stream")
                if result is not None and result != payload:
                    raise RuntimeError("CRC-valid wrong payload")
                observations.append({"profile": profile, "receiver": "stream", "payload_bytes": 1024,
                                     "repeated_byte": byte, "clock_ppm": ppm, "seed": 90,
                                     "success": result == payload, "payload_sha256": hashlib.sha256(payload).hexdigest(), **metadata})
    output = Path("artifacts/timing/long-runs.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"experiment": "0002-followup", "source_sha256": source_hashes(),
                                  "observations": observations}, indent=2) + "\n")
    print(f"{sum(r['success'] for r in observations)}/{len(observations)} long-run stress packets decoded; see {output}")


if __name__ == "__main__":
    run()
