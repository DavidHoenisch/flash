"""Explicit synthetic *audio* impairments, not an RF FM-channel simulator."""

from dataclasses import asdict, dataclass
from fractions import Fraction

import numpy as np
from scipy import signal

SAMPLE_RATE = 48_000


@dataclass(frozen=True)
class Channel:
    name: str = "awgn"
    bandpass_hz: tuple[float, float] | None = None
    clip_level: float | None = None
    clock_ppm: int = 0
    erase_start_ms: float = 0

    def apply(self, tx, snr_3k_db, rng):
        """SNR refers to TX active mean power and white noise in 3000 Hz.

        White noise spans 0..24000 Hz; variance = Ptx * Fs/(2*3000) / SNR.
        It is added AFTER filtering/clipping/resampling, including the silence.
        Positive ppm lengthens the recording (and lowers tones). No drift tracking.
        """
        tx = np.asarray(tx, dtype=np.float64)
        if not len(tx) or not np.isfinite(tx).all():
            raise ValueError("TX must be a nonempty finite signal")
        if abs(self.clock_ppm) > 10_000:
            raise ValueError("clock mismatch must be within +/-10000 ppm")
        if self.clip_level is not None and self.clip_level <= 0:
            raise ValueError("clip level must be positive")
        if self.erase_start_ms < 0:
            raise ValueError("erasure duration must be nonnegative")
        x = tx.copy()
        if self.bandpass_hz:
            sos = signal.butter(4, self.bandpass_hz, btype="bandpass", fs=SAMPLE_RATE, output="sos")
            # Causal filter; preserve a short tail rather than using zero-phase filtering.
            x = signal.sosfilt(sos, np.pad(x, (0, 480)))
        if self.clip_level:
            x = np.clip(x, -self.clip_level, self.clip_level)
        if self.clock_ppm:
            ratio = Fraction(1_000_000 + self.clock_ppm, 1_000_000)
            x = signal.resample_poly(x, ratio.numerator, ratio.denominator)
        erase = min(len(x), round(self.erase_start_ms * SAMPLE_RATE / 1000))
        x[:erase] = 0
        delay = int(rng.integers(0, SAMPLE_RATE // 4))
        rx = np.pad(x, (delay, SAMPLE_RATE // 10))
        tx_power = float(np.mean(tx * tx))
        noise_variance = 0.0 if snr_3k_db is None else tx_power * (SAMPLE_RATE / 6000) * 10 ** (-snr_3k_db / 10)
        rx += rng.normal(0, np.sqrt(noise_variance), len(rx))
        return rx.astype("<f4"), {
            **asdict(self),
            "delay_samples": delay,
            "noise_variance": noise_variance,
            "tx_active_power": tx_power,
            "nominal_snr_3k_db": snr_3k_db,
        }


CHANNELS = {
    "awgn": Channel(),
    "voice": Channel("voice", bandpass_hz=(300, 3000)),
    "tight": Channel("tight", bandpass_hz=(500, 2400)),
    "clip": Channel("clip", clip_level=0.25),
    "clock+100": Channel("clock+100", clock_ppm=100),
    "clock-100": Channel("clock-100", clock_ppm=-100),
    "clock+500": Channel("clock+500", clock_ppm=500),
    "clock-500": Channel("clock-500", clock_ppm=-500),
    "clock+1000": Channel("clock+1000", clock_ppm=1000),
    "erase50": Channel("erase50", erase_start_ms=50),
    "erase150": Channel("erase150", erase_start_ms=150),
}

