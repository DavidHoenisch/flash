"""Offline fsk4 recording analysis; experimental public-sync equalization.

No radio or PTT access. The equalizer never receives an expected payload.
"""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from scipy import linalg, signal
from scipy.io import wavfile

from .channel import SAMPLE_RATE
from .modem import build, decode, reference_audio


def equalize_public_sync(samples):
    """Fit an 80-tap offline inverse filter using only the fixed sync waveform.

    Acquisition selects one normalized-correlation peak before attempting CRCs.
    This assumes nominal clock/carrier rates and a locally stable linear path.
    It is an experiment, not a streaming or general multipath receiver.
    """
    rx = np.asarray(samples, dtype=np.float64)
    if rx.ndim != 1 or not np.isfinite(rx).all() or len(rx) < 6400:
        raise ValueError("need finite mono samples covering the public frame prefix")
    # 16 preamble bytes + 4 sync bytes, four 80-sample symbols per byte.
    # No header or payload samples are part of this reference.
    prefix = reference_audio(b"", "fsk4")[:6400].astype(np.float64)
    sync = prefix[5120:]
    corr = signal.correlate(rx, sync, mode="valid", method="fft")
    cumulative = np.r_[0.0, np.cumsum(rx * rx)]
    energy = np.maximum(cumulative[len(sync):] - cumulative[:-len(sync)], 0)
    score = np.abs(corr) / np.sqrt(np.maximum(energy, 1e-10) * np.sum(sync * sync))
    # The complete prefix and the centered receive window must be present.
    taps, delay, ridge = 80, 40, 1e-5
    score[:5120 + delay] = -1
    last_sync = len(rx) - len(sync) - delay
    score[last_sync + 1:] = -1
    peak = int(np.argmax(score))
    origin = peak - 5120
    if score[peak] <= 0 or origin < delay or origin + len(prefix) + delay > len(rx):
        raise ValueError("no usable public-sync candidate")
    windows = np.lib.stride_tricks.sliding_window_view(
        rx[origin - delay:origin + len(prefix) + delay], taps
    )
    # Targets and every contributing receive sample stay inside the sync interval.
    lo, hi = 5120 + taps, 6400 - taps
    design = windows[lo:hi]
    target = prefix[lo:hi]
    gram = design.T @ design
    penalty = np.trace(gram) / taps * ridge
    if penalty <= 0:
        raise ValueError("sync candidate has no energy")
    weights = linalg.solve(gram + np.eye(taps) * penalty, design.T @ target, assume_a="pos")
    equalized = signal.correlate(rx, weights, mode="valid", method="fft").astype(np.float32)
    report = {
        "method": "public-sync inverse FIR, fixed 80 taps and ridge 1e-5",
        "candidate_frame_origin_seconds": origin / SAMPLE_RATE,
        "sync_correlation": float(score[peak]),
        "training_target_sample_range_in_frame": [lo, hi],
        "training_receive_sample_range_in_recording": [origin + lo - delay, origin + hi - delay + taps - 1],
        "training_samples": hi - lo,
        "expected_payload_used": False,
        "filter_taps": taps,
        "ridge": ridge,
    }
    return equalized, weights, report


def decode_windows(samples, output, label):
    """Use overlapping windows to respect the Rust CLI's ten-second limit."""
    results = []
    for start in range(0, len(samples), 5 * SAMPLE_RATE):
        clip = samples[start:start + 10 * SAMPLE_RATE]
        for receiver in ("fixed", "stream"):
            payload = decode(clip, "fsk4", receiver)
            item = {"processing": label, "receiver": receiver, "start_seconds": start / SAMPLE_RATE,
                    "decoded_bytes": None if payload is None else len(payload)}
            if payload is not None:
                name = f"{label}-{receiver}-{start // SAMPLE_RATE}.bin"
                (output / name).write_bytes(payload)
                item.update(payload_file=name, payload_sha256=hashlib.sha256(payload).hexdigest())
            results.append(item)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recording", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--equalize", action="store_true", help="try experimental public-sync equalization")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    wav = args.output / "converted.wav"
    if args.recording.resolve() == wav.resolve():
        parser.error("source must differ from the generated converted.wav")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(args.recording),
                    "-ar", str(SAMPLE_RATE), "-c:a", "pcm_f32le", str(wav)], check=True)
    rate, samples = wavfile.read(wav)
    if samples.ndim == 2:
        samples = samples.mean(axis=1)
    if rate != SAMPLE_RATE or not np.isfinite(samples).all():
        raise ValueError("conversion did not produce finite 48 kHz audio")
    build()
    report = {"source": str(args.recording.resolve()),
              "source_sha256": hashlib.sha256(args.recording.read_bytes()).hexdigest(),
              "duration_seconds": len(samples) / rate,
              "conversion": "FFmpeg to 48 kHz float WAV, arithmetic-mean channel mix",
              "results": decode_windows(samples, args.output, "raw")}
    if args.equalize:
        try:
            equalized, weights, fit = equalize_public_sync(samples)
        except ValueError as error:
            report["equalizer_error"] = str(error)
        else:
            report["equalizer"] = fit
            np.save(args.output / "equalizer.npy", weights)
            wavfile.write(args.output / "equalized.wav", rate, equalized)
            report["results"].extend(decode_windows(equalized, args.output, "equalized"))
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    accepted = [r for r in report["results"] if r["decoded_bytes"] is not None]
    print(json.dumps({"report": str(args.output / "report.json"), "accepted": accepted}, indent=2))


if __name__ == "__main__":
    main()
