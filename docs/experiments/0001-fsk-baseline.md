# Experiment 0001 — uncoded audio FSK baseline

Status: implemented research fixture, **not a production PHY or link spec**.

## Questions

Can a small Rust modem recover arbitrary framed bytes from noisy audio with an
unknown packet start? Do equal-bit-rate 2-FSK and 4-FSK respond differently to a
synthetic audio filter and sample-clock mismatch? Can Python independently verify
the wire format and waveform, and preserve reproducible evidence?

Pass criteria for the lab: exact independent framing/sample agreement; clean-channel
recovery; unknown delay/phase, polarity and gain tolerance; corrupt frames and noise
rejected; explicit loss curves and clock failure modes. There is no requirement to
approach VARA in this experiment.

## Signal definition

| Parameter | `fsk2` | `fsk4` |
| --- | --- | --- |
| Experiment profile ID | 1 | 2 |
| Sample rate | 48000 Hz | 48000 Hz |
| Symbols/s | 1200 | 600 |
| Bits/s before framing | 1200 | 1200 |
| Samples/symbol | 40 | 80 |
| Tone mapping | 0 → 1200, 1 → 2400 Hz | 00 → 900, 01 → 1500, 10 → 2100, 11 → 2700 Hz |

Bytes transmit most-significant bit first; 4-FSK groups consecutive bit pairs,
high bit first (natural binary mapping). Phase starts at zero and is continuous:
emit `0.7*sin(phase)`, then increment by `2*pi*f/48000` per sample. No pulse shaping,
whitening, FEC, interleaving, ramps, or amplitude leveling. These are custom FSK
profiles, not Bell 202/AX.25 or an implementation of another modem's wire protocol.

Tone spacing is one symbol rate; the rectangular-window tone correlators are
orthogonal over an aligned symbol. Equal payload, rate, and amplitude make a useful
controlled comparison, but do not imply equal occupied spectrum. Abrupt tone changes
and burst edges have sidelobes. The full occupied audio/RF bandwidth remains unmeasured.

## Exact experimental frame

| Field | Size | Encoding |
| --- | --- | --- |
| Preamble | 16 bytes | `55` repeated |
| Sync | 4 bytes | `d3 91 c5 a7` |
| Version | 1 byte | `00` (experiment) |
| Profile | 1 byte | `01` or `02` |
| Payload length | 2 bytes | unsigned big-endian; 0..1024 |
| Header CRC | 4 bytes | CRC of version, profile, length; big-endian |
| Payload | length bytes | arbitrary bytes |
| Body CRC | 4 bytes | CRC of version, profile, length, then payload; big-endian |

Both CRCs use CRC-32/ISO-HDLC: polynomial `0x04c11db7`, reflected algorithm polynomial
`0xedb88320`, initial value and final XOR `0xffffffff`, reflected input/output.
Check: ASCII `123456789` → `0xcbf43926`. No CRC residue convention is required because
the computed value is compared directly. Header CRC is error detection, not correction.
Unknown versions/profiles, oversize lengths, truncation, or CRC failure are rejected.

Overhead is 32 bytes. For a 256-byte payload, transmission lasts 1.92 seconds and
the error-free payload rate per waveform second is 1066.67 bit/s. Empty payloads
are valid for codec conformance; the throughput sweep requires nonempty payloads.

The checked-in [vectors](results/0001-vectors.json) give exact wire bytes. Tests also
compare every emitted sample against an independent vectorized Python transmitter
and Python/zlib framing. Floating-point samples use a numerical tolerance; wire bytes
are exact.

## Receiver and limitations

The receiver takes a supplied profile and at most ten seconds of f32 audio. It computes
sliding quadrature tone energy over one symbol, hard-selects the strongest tone, and
tries each integer sample phase for a fixed symbol clock. It scans decoded bits for
exact sync, checks the header before using its length, and returns the first candidate
in search order passing both CRCs. It is not guaranteed to return the earliest packet
in time when a capture contains multiple packets. No known payload, start offset,
length, or SNR enters the decoder.

This is an **offline exhaustive fixed-phase search**. CRC validation selects among
timing hypotheses. It is more permissive than committing to one acquisition phase
in a real-time receiver; its curve must not be presented as streaming performance.
The preamble is transmitted but not used for clock/frequency estimation or detection.
Exact sync is fragile to bit errors. No frequency estimation, clock tracking, AGC,
equalizer, soft decisions, FEC, ARQ, or streaming buffer handling is implemented.
Noise-only rejection tests are smoke evidence, not an operational false-alarm bound.

## Synthetic channel

`lab/channel.py` applies causal fourth-order Butterworth bandpass filtering (if set),
then optional clipping, polyphase clock resampling, leading-sample erasure, an unknown
0..249.98 ms leading delay and 100 ms trailing padding, then white Gaussian noise.
Bandpass cases preserve a 10 ms filter tail. Positive clock ppm stretches the capture,
lengthens symbols, and lowers received tone frequencies; the receiver gets no correction.

Default channels are `awgn` and `voice` (300–3000 Hz). `tight` uses 500–2400 Hz;
`clip` limits samples to ±0.25; clock cases are ±100, ±500 and +1000 ppm; `erase50`
and `erase150` mute the first 50/150 ms. Erasures happen before noise and do not
model a complete squelch state machine. None is a measured model of the user's radios.

Noise variance is `Ptx * (48000 / (2*3000)) * 10^(-SNR3k/10)`, with `Ptx` the average
power of the complete active TX waveform before impairments (no leading/trailing
silence). Noise is white over the full sampled band, so the variance is eight times
the noise power in a 3000-Hz band. This is **nominal audio SNR referenced to TX**,
not post-filter received SNR, RF carrier-to-noise, full-Nyquist sample SNR, or Eb/N0.
Filter/clip attenuation is not renormalized away. FM threshold effects, colored
receiver noise, interference, RF fading/capture, and actual pre/de-emphasis are absent.

## Reproduce

```sh
uv run --locked python -m lab smoke
uv run --locked python -m lab sweep --trials 40 --output artifacts/baseline
uv run --locked python -m lab sweep --trials 20 --snr 18 --channels clock+100 clock-100 clock+500 clock-500 clock+1000 erase50 erase150 --output artifacts/stress
```

Default seed: 20260920. Each cell uses seeded random 256-byte payloads (uncompressed)
and unknown packet delays. Payloads are paired across profiles/channel conditions;
impairment streams are paired across profiles. Noise/delay seeds depend on SNR list
position, so retain the exact SNR array as well as the seed to reproduce a run.
There is no claim of independence between different cells; per-cell intervals describe
the independent trials within that cell.

Outputs: manifest with parameters/tool versions/source and binary hashes, per-trial
JSON, CSV summary, and plot. Wrong CRC-valid payloads and tool crashes abort the sweep;
only an ordinary no-frame result is counted as packet loss.

Metrics: packet error rate with 95% Wilson intervals, delivered payload bits divided
by all attempted TX waveform seconds, and median decode subprocess wall time. The
last metric includes process startup; it is not DSP CPU time or phone performance.
Rate excludes connection time, PTT/ACKs/retries and is **not link goodput**. At 40/40
successes the uncertainty still allows roughly 8.8% packet error; small sweeps are
exploratory. More trials are required to qualify high reliability.

## Next experiment

Use the measured clock/packet-length limit to prioritize streaming timing recovery,
then compare against a pinned Codec2 FSK_LDPC modem. Obtain radio captures before
choosing tone placement or interpreting these simulations as hardware performance.
