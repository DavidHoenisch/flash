# Experiment 0003 — recovering the first acoustic radio packet

Status: the lower-volume recording yields the complete 406-byte Declaration
paragraph after offline equalization. Both existing Rust receivers accept it,
including header and body CRCs. The original recording still fails. No new RF
transmission, wire-format change, or Rust receiver change was needed.

## Evidence and diagnosis

The operator recorded the FTM-200D speaker after transmitting the existing
identified `fsk4` clip through Digirig and the FT-65R on operator-set 146.580 MHz.
The two supplied recordings are 48 kHz stereo AAC. The second followed a request
to lower receive speaker volume; other physical conditions were not instrumented.
This is an acoustic radio-path demonstration, not a calibrated wired test.

| Recording | Raw fixed / streaming | Equalized fixed / streaming |
| --- | --- | --- |
| `Voice 260920_222133.m4a` | No valid packet / no valid packet | No valid packet / no valid packet |
| `Voice 260920_222820.m4a` | No valid packet / no valid packet | Exact 406 bytes / exact 406 bytes |

Accepted payload SHA-256:
`0e948931f853d6a087339383663faa8794f8b657c8da85c9f7149effbac7d15b`.
The expected text was compared **after** decoding. It was not an equalizer input.
Both outputs match the [fixture](../../fixtures/messages/declaration-opening.txt)
without its terminal newline. Reports include source recording hashes:
[original](results/acoustic/original.json), [lower volume](results/acoustic/low-volume.json).

Exploratory alignment against the known complete frame found approximately 57.5%
and 90.6% matching symbol decisions, respectively, with errors in the sync word
in both recordings. These are aided diagnostics, not blind receiver performance
or unbiased BER estimates. Raw decoders require exact sync before CRC validation.

A 2,048-tap linear path model fitted using the first 1.46 seconds of known modem
audio explained about 91.4% and 96.8% of signal energy in the respective later
validation intervals (`1 - residual_energy / observed_energy`, omitting the first
2,048 validation samples). That supports investigating repeatable filtering and
ringing. The model uses known message samples and is **not** the decoding filter.
It does not identify physical echoes or isolate the radio, speaker, room, microphone,
recorder processing, or AAC contribution. Its large endpoint taps are not reliable
physical-path measurements. [Saved diagnostics](results/acoustic/linear-path.json).

Simple channel selection, bandpass filtering, shorter/longer tone windows and
per-tone percentile normalization did not produce a valid packet in the probes.
Changing receive volume alone also did not yield a raw decode. The successful
intervention was a short inverse filter before the existing tone detectors.

## Public-sync equalizer

`lab.recording.equalize_public_sync` accepts only received samples. It builds a
reference from the protocol's fixed 16-byte preamble and four-byte sync. Neither
the header, payload length, nor payload text enters this reference.

1. Find one peak in energy-normalized correlation with the 16-symbol sync waveform,
   allowing either polarity. Commit to that candidate before CRC checks.
2. Fit an 80-tap inverse FIR with ridge penalty
   `1e-5 * trace(X.T @ X) / 80`. The targets are 1,120 samples entirely inside
   the sync interval. The centered receive windows also stay inside that interval.
3. Apply that fixed filter to the recording. This is offline processing with
   lookahead and a full-recording sync search, not the streaming receiver design.
4. Feed unmodified Rust decoders overlapping ten-second windows. They recover
   header/length themselves and require both CRCs. Compare accepted bytes with
   the fixture only afterward.

The first tried 80-tap, `1e-5` setting recovered the second recording. Exploratory
80/160/320/640-tap and `1e-5`/`1e-3`/`1e-1` fits did not recover the first recording.
This is a development result on two captures, not an independently held-out radio
qualification. The reusable command fixes the parameters at 80 taps and `1e-5`.

## Reproduce

FFmpeg must be available on PATH. The command below reads a recording and writes
analysis artifacts; it never opens a serial port or audio device.

```sh
make decode-recording RECORDING="/path/to/Voice 260920_222820.m4a"
# Equivalent, with an explicit output directory:
uv run --locked python -m lab.recording "/path/to/Voice 260920_222820.m4a" \
  --equalize --output artifacts/radio/recording-analysis
```

The output contains converted audio, filter coefficients, equalized audio,
CRC-accepted `.bin` payloads and `report.json`. Omitting `--equalize` runs the
unmodified receivers only. Generated recordings remain local under ignored
`artifacts/`; the recordings themselves are not included in the repository.
The historical source snapshot and hashes are in
[results/acoustic/manifest.json](results/acoustic/manifest.json).
The exploratory diagnostic scripts alongside it assume the original artifact
filenames and repository working directory; run them with `PYTHONPATH=.`.

## Regression checks and limits

Four new tests cover unrelated random payloads and carrier phases, a synthetic
selective path, identical filter weights when only payload changes, rejection
of payload damage, and invalid/silent input. All 19 Python tests pass.

The paired [90-trial sweep](results/acoustic/sweep.json) uses 256-byte seeded random
payloads, random initial phase and sample delay; each received array is tested raw
and equalized by both receivers (360 decoder checks):

| Channel / nominal audio SNR3k | Raw fixed / streaming | Equalized fixed / streaming |
| --- | ---: | ---: |
| AWGN, each of no noise / 18 / 9 dB | 10/10 / 10/10 | 10/10 / 10/10 |
| 300–3000 Hz voice filter, each of no noise / 18 / 9 dB | 10/10 / 10/10 | 10/10 / 10/10 |
| Delayed inverted copy, no noise | 3/10 / 0/10 | 9/10 / 5/10 |
| Delayed inverted copy, each of 18 / 9 dB | 0/10 / 0/10 | 0/10 / 0/10 |

The selective path is `h[0]=1, h[24]=-0.95` at 48 kHz. For these cells the existing
noise helper references signal power after that FIR; it is not a calibrated RF
SNR and should not be compared as a shared link budget with the other channels.
Reproduce with `uv run --locked python -m lab.equalizer_sweep`.

Short-sync equalization is not universally successful and can amplify noise near
channel nulls. It assumes nominal tone frequencies and symbol rate and selects
only one candidate. Clock drift, multiple packets, stronger noise, and changing
channels need further work. The original recording remains an unresolved failure.

Design implication: evaluate a deliberately diverse public training sequence and
regularized equalization alongside timing recovery, then test unseen recordings.
Retain raw decoding as a fallback/reference. Do not promote this offline helper
into the wire specification or claim reliable file transfer or VARA performance.
