"""Small paired regression experiment for offline public-sync equalization."""

import argparse
import json
from pathlib import Path

import numpy as np
from scipy import signal

from .channel import Channel
from .modem import build, decode, reference_audio
from .recording import equalize_public_sync


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("artifacts/equalizer-sweep"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    build()
    trials, summary = [], []
    for channel in ("awgn", "voice", "delayed-inverted-copy"):
        for snr in (None, 18, 9):
            counts = dict(raw_fixed=0, raw_stream=0, equalized_fixed=0, equalized_stream=0)
            for trial in range(10):
                rng = np.random.default_rng(20260921 + trial)
                payload = rng.bytes(256)
                phase = rng.uniform(0, 2 * np.pi)
                tx = reference_audio(payload, "fsk4", initial_phase=phase)
                if channel == "delayed-inverted-copy":
                    tx = signal.lfilter(np.r_[1.0, np.zeros(23), -0.95], [1], tx)
                model = Channel(channel, bandpass_hz=(300, 3000) if channel == "voice" else None)
                rx, metadata = model.apply(tx, snr, rng)
                try:
                    equalized, _, _ = equalize_public_sync(rx)
                except ValueError:
                    equalized = None
                result = dict(channel=channel, snr_3k_db=snr, trial=trial, phase=phase, channel_metadata=metadata)
                for label, audio in (("raw", rx), ("equalized", equalized)):
                    for receiver in ("fixed", "stream"):
                        key = f"{label}_{receiver}"
                        result[key] = audio is not None and decode(audio, "fsk4", receiver) == payload
                        counts[key] += int(result[key])
                trials.append(result)
            cell = dict(channel=channel, snr_3k_db=snr, trials=10, **counts)
            summary.append(cell)
            print(json.dumps(cell), flush=True)
    (args.output / "results.json").write_text(json.dumps({
        "seed_base": 20260921, "payload_bytes": 256,
        "note": "For delayed-inverted-copy, SNR is referenced to audio after that FIR; other cells follow Channel's TX reference.",
        "summary": summary, "trials": trials,
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
