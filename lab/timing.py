"""Experiment 0002: paired fixed/offline versus streaming timing receiver trials."""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys

import numpy as np
import scipy

from .channel import Channel, SAMPLE_RATE
from .modem import BINARY, PROFILES, build, decode, encode
from .__main__ import source_hashes, wilson


def run(args):
    build()
    args.output.mkdir(parents=True, exist_ok=True)
    rows, summary = [], []
    cells = [("clock", length, ppm, "awgn", 18) for length in (64, 256, 1024)
             for ppm in (-2000, -1000, -500, 0, 500, 1000, 2000)]
    cells += [("noise", 256, 0, channel, snr) for channel in ("awgn", "voice")
              for snr in (3, 6, 9, 12, 18)]
    for profile in PROFILES:
        for cell, (suite, length, ppm, channel_name, snr) in enumerate(cells):
            channel = Channel(channel_name, bandpass_hz=(300, 3000) if channel_name == "voice" else None, clock_ppm=ppm)
            counts = dict.fromkeys(("fixed", "stream"), 0)
            for trial in range(args.trials):
                payload = np.random.default_rng(np.random.SeedSequence([args.seed, length, trial, 0])).bytes(length)
                tx = encode(payload, profile)
                rx, metadata = channel.apply(tx, snr, np.random.default_rng(np.random.SeedSequence([args.seed, cell, trial, 1])))
                for receiver in counts:
                    result = decode(rx, profile, receiver)
                    if result is not None and result != payload:
                        raise RuntimeError("CRC-valid wrong payload")
                    success = result == payload
                    counts[receiver] += success
                    rows.append({"suite": suite, "profile": profile, "receiver": receiver,
                                 "payload_bytes": length, "clock_ppm": ppm, "channel": channel_name,
                                 "snr_3k_db": snr, "trial": trial, "cell_index": cell,
                                 "success": success, "tx_seconds": len(tx) / SAMPLE_RATE,
                                 "payload_sha256": hashlib.sha256(payload).hexdigest(), **metadata})
            for receiver, successes in counts.items():
                low, high = wilson(successes, args.trials)
                summary.append({"suite": suite, "profile": profile, "receiver": receiver,
                                "payload_bytes": length, "clock_ppm": ppm, "channel": channel_name,
                                "snr_3k_db": snr, "successes": successes, "trials": args.trials,
                                "per": 1 - successes / args.trials, "per_ci95_low": 1 - high,
                                "per_ci95_high": 1 - low})
            print(f"{suite:5} {profile} {length:4}B {ppm:+5}ppm {channel_name:5} {snr:2}dB: fixed {counts['fixed']}/{args.trials}; stream {counts['stream']}/{args.trials}", flush=True)
    manifest = {"experiment": "0002", "created_utc": datetime.now(timezone.utc).isoformat(),
                "command": sys.argv, "seed": args.seed, "trials_per_cell": args.trials,
                "cells": cells, "python": sys.version, "platform": platform.platform(),
                "numpy": np.__version__, "scipy": scipy.__version__, "source_sha256": source_hashes(),
                "binary_sha256": hashlib.sha256(BINARY.read_bytes()).hexdigest(),
                "sample_rate": SAMPLE_RATE, "stream_chunk_samples": 127,
                "snr_definition": "TX active mean power / white-noise power in 3000Hz, noise added after channel impairments",
                "comparison": "Both receivers consume identical captured samples; no payload/offset/ppm supplied to receivers. Profiles supplied. Paired cells across profiles; independent trials within each cell."}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (args.output / "trials.json").write_text(json.dumps(rows, indent=2) + "\n")
    with (args.output / "summary.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=summary[0])
        writer.writeheader()
        writer.writerows(summary)
    plot(summary, args.output)
    print(f"Saved {len(rows)} receiver attempts: {args.output}")


def plot(rows, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    for suite, panels in [("clock", (64, 256, 1024)), ("noise", ("awgn", "voice"))]:
        fig, axes = plt.subplots(1, len(panels), figsize=(5 * len(panels), 4.5), sharey=True, layout="constrained")
        for ax, panel in zip(axes, panels):
            for profile, color in zip(PROFILES, ("#20639b", "#bc4b22")):
                for receiver, style in [("fixed", "--"), ("stream", "-")]:
                    data = [r for r in rows if r["suite"] == suite and r["profile"] == profile and r["receiver"] == receiver
                            and (r["payload_bytes"] == panel if suite == "clock" else r["channel"] == panel)]
                    x = [r["clock_ppm"] if suite == "clock" else r["snr_3k_db"] for r in data]
                    y = np.array([r["per"] for r in data])
                    error = np.maximum(0, [y - np.array([r["per_ci95_low"] for r in data]), np.array([r["per_ci95_high"] for r in data]) - y])
                    ax.errorbar(x, y, yerr=error, color=color, linestyle=style, marker="o" if receiver == "stream" else "x", capsize=2, label=f"{profile} / {receiver}")
            ax.set(title=f"{panel} bytes · nominal SNR3k 18 dB" if suite == "clock" else f"{panel} · 256 bytes · 0 ppm",
                   xlabel="Clock stretch (ppm)" if suite == "clock" else "Nominal audio SNR3k (dB)", ylim=(-0.04, 1.04))
            ax.grid(alpha=0.2)
        axes[0].set_ylabel("Packet error rate (95% Wilson interval)")
        axes[0].legend(fontsize=8)
        fig.suptitle("FLASH 0002 · fixed timing vs streaming tracking · synthetic audio")
        fig.savefig(output / f"{suite}.png", dpi=160)
        plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20260921)
    parser.add_argument("--output", type=Path, default=Path("artifacts/timing"))
    args = parser.parse_args()
    if args.trials < 1 or args.seed < 0:
        parser.error("positive trials and nonnegative seed required")
    run(args)

