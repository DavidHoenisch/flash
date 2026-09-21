import argparse
import csv
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import subprocess
import sys
import time

import numpy as np
import scipy
from scipy.io import wavfile

from .channel import CHANNELS, SAMPLE_RATE
from .modem import BINARY, PROFILES, ROOT, build, decode, encode


def wilson(successes, trials):
    """95% Wilson score interval (descriptive; no precision guarantee)."""
    z = 1.959963984540054
    p = successes / trials
    d = 1 + z * z / trials
    center = (p + z * z / (2 * trials)) / d
    half = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / d
    return max(0, center - half), min(1, center + half)


def smoke():
    build()
    output = ROOT / "artifacts" / "smoke"
    output.mkdir(parents=True, exist_ok=True)
    for index, profile in enumerate(PROFILES):
        payload = b"FLASH offline experiment 0001\n" + bytes(range(256))
        tx = encode(payload, profile)
        rx, metadata = CHANNELS["voice"].apply(tx, 18, np.random.default_rng(20260920 + index))
        actual = decode(rx, profile)
        if actual != payload:
            raise RuntimeError(f"{profile}: smoke payload mismatch")
        wavfile.write(output / f"{profile}-tx.wav", SAMPLE_RATE, tx)
        wavfile.write(output / f"{profile}-rx.wav", SAMPLE_RATE, rx)
        (output / f"{profile}.json").write_text(json.dumps(metadata, indent=2) + "\n")
        print(f"{profile}: {len(payload)} bytes recovered through synthetic voice filter + noise; {len(tx) / SAMPLE_RATE:.3f}s TX")
    print(f"WAV fixtures: {output}")


def source_hashes():
    paths = [ROOT / "Cargo.lock", ROOT / "uv.lock", ROOT / "rust-toolchain.toml"]
    paths += sorted((ROOT / "crates").rglob("*.rs"))
    paths += sorted((ROOT / "lab").glob("*.py"))
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def sweep(args):
    build()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    rows, summaries = [], []
    for profile_index, profile in enumerate(PROFILES):
        for channel_name in args.channels:
            channel_index = list(CHANNELS).index(channel_name)
            channel = CHANNELS[channel_name]
            for snr_index, snr in enumerate(args.snr):
                successes, airtime, decode_seconds = 0, 0.0, []
                for trial in range(args.trials):
                    # Payload and impairment seeds independent of loop ordering/profiles.
                    payload_rng = np.random.default_rng(np.random.SeedSequence([args.seed, trial, 0]))
                    payload = payload_rng.bytes(args.payload_bytes)
                    rng = np.random.default_rng(np.random.SeedSequence([args.seed, channel_index, snr_index, trial, 1]))
                    tx = encode(payload, profile)
                    rx, metadata = channel.apply(tx, snr, rng)
                    start = time.perf_counter()
                    received = decode(rx, profile)
                    elapsed = time.perf_counter() - start
                    if received is not None and received != payload:
                        raise RuntimeError("CRC-valid but incorrect payload: stop and investigate")
                    success = received == payload
                    successes += success
                    duration = len(tx) / SAMPLE_RATE
                    airtime += duration
                    decode_seconds.append(elapsed)
                    rows.append({"profile": profile, "channel": channel_name, "snr_3k_db": snr, "trial": trial,
                                 "success": success, "payload_bytes": len(payload), "tx_seconds": duration,
                                 "decode_process_seconds": elapsed, **metadata})
                lo, hi = wilson(successes, args.trials)
                summaries.append({"profile": profile, "channel": channel_name, "snr_3k_db": snr,
                                  "successes": successes, "trials": args.trials,
                                  "per": 1 - successes / args.trials,
                                  "per_ci95_low": 1 - hi, "per_ci95_high": 1 - lo,
                                  "payload_bps_per_tx_airtime": successes * args.payload_bytes * 8 / airtime,
                                  "decode_process_p50_seconds": float(np.median(decode_seconds))})
                print(f"{profile:4} {channel_name:10} SNR3k={snr:5g}: {successes:3}/{args.trials} received", flush=True)
    manifest = {
        "schema_version": 1, "experiment": "0001", "created_utc": datetime.now(timezone.utc).isoformat(),
        "command": sys.argv, "seed": args.seed, "trials_per_cell": args.trials,
        "payload_bytes": args.payload_bytes, "snr_3k_db": args.snr,
        "channels": [asdict(CHANNELS[c]) for c in args.channels],
        "sample_rate": SAMPLE_RATE, "platform": platform.platform(), "python": sys.version,
        "numpy": np.__version__, "scipy": scipy.__version__,
        "rustc": subprocess.check_output(["rustc", "--version"], text=True).strip(),
        "source_sha256": source_hashes(), "binary_sha256": hashlib.sha256(BINARY.read_bytes()).hexdigest(),
        "snr_definition": "TX active mean power / noise power in 3000Hz; white noise injected after audio impairments; not RF SNR or Eb/N0",
        "rate_definition": "successfully decoded payload bits / total TX waveform seconds, including failed attempts; excludes PTT, ACK, retries, and session time",
        "receiver": "offline fixed-phase exhaustive search, exact sync + header/body CRC, supplied profile, unknown packet offset and payload",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (output / "trials.json").write_text(json.dumps(rows, indent=2) + "\n")
    with (output / "summary.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)
    plot(summaries, output)
    print(f"Results: {output}")


def plot(rows, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.7), layout="constrained")
    for profile in PROFILES:
        for channel in dict.fromkeys(r["channel"] for r in rows):
            data = sorted([r for r in rows if r["profile"] == profile and r["channel"] == channel], key=lambda r: r["snr_3k_db"])
            x = [r["snr_3k_db"] for r in data]
            y = np.array([r["per"] for r in data])
            bounds = np.array([[r["per_ci95_low"] for r in data], [r["per_ci95_high"] for r in data]])
            axes[0].errorbar(x, y, yerr=np.maximum(0, [y - bounds[0], bounds[1] - y]), marker="o", capsize=2, label=f"{profile} / {channel}")
            axes[1].plot(x, [r["payload_bps_per_tx_airtime"] for r in data], marker="o", label=f"{profile} / {channel}")
    axes[0].set(ylabel="Packet error rate (95% Wilson interval)", ylim=(-0.04, 1.04))
    axes[1].set(ylabel="Delivered payload bits / TX waveform second", ylim=(0, 1250))
    for ax in axes:
        ax.set_xlabel("Nominal audio SNR in 3000 Hz (dB), referenced to TX")
        ax.grid(alpha=0.2)
    axes[0].legend(fontsize=8)
    fig.suptitle("FLASH experiment 0001 · uncoded FSK · synthetic audio only")
    fig.savefig(output / "curves.png", dpi=160)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="FLASH offline modem lab (no radio access)")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("smoke")
    sweep_parser = commands.add_parser("sweep")
    sweep_parser.add_argument("--trials", type=int, default=40)
    sweep_parser.add_argument("--payload-bytes", type=int, default=256)
    sweep_parser.add_argument("--seed", type=int, default=20260920)
    sweep_parser.add_argument("--snr", type=float, nargs="+", default=[-6, -3, 0, 3, 6, 9, 12, 18])
    sweep_parser.add_argument("--channels", nargs="+", choices=CHANNELS, default=["awgn", "voice"])
    sweep_parser.add_argument("--output", type=Path, default=Path("artifacts/baseline"))
    args = parser.parse_args()
    if args.command == "smoke":
        smoke()
    else:
        if not 1 <= args.payload_bytes <= 1024 or args.trials < 1 or args.seed < 0 or not all(math.isfinite(v) for v in args.snr):
            parser.error("need 1..1024 payload bytes, positive trials, nonnegative seed, and finite SNR")
        sweep(args)


if __name__ == "__main__":
    main()

