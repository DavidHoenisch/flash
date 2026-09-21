# FLASH

An experimental, open radio data modem: native phone operation, a portable Rust core,
and a protocol we can implement independently from a written specification.
FLASH is the working project name. FM comes first; HF comes later.

**Current state:** Rust FSK prototypes with fixed and streaming timing receivers,
a Python channel/measurement lab, and a supervised desktop audio/PTT adapter. An
identified test through Digirig and FT-65R was recorded from an FTM-200D speaker;
offline public-sync equalization recovered the complete 406-byte message with both
packet CRCs passing. No Android app, reliable link, or demonstrated VARA-level
performance yet. The experiment's framing is not
the eventual protocol. Project licensing is still an open decision; no release
license has been selected.

## Start here

- [Specification draft 0.1](docs/spec/README.md): requirements, exact experimental wire
  format, proposed link/platform behavior, and evidence needed to settle open decisions.
- [Design and decisions](docs/design.md): scope, architecture, milestones, open questions.
- [Experiment 0001](docs/experiments/0001-fsk-baseline.md): exact waveform/framing,
  measurement definitions, reproduction commands, and limitations.
- [First results](docs/experiments/0001-results.md): measured findings and next decisions.
- [Streaming timing experiment](docs/experiments/0002-streaming-timing.md): clock recovery,
  longer packets, paired receiver comparisons, and the long-constant-run failure.
- [First acoustic packet recovery](docs/experiments/0003-acoustic-equalization.md):
  recording diagnosis, experimental equalization, and reproducible decoding.
- [Hardware plan](docs/hardware.md): S25 Ultra / Digirig / FT-65R, FTM-200D, and a second operator.
- [U.S. radio test plan](docs/radio-testing-us.md): novel digital codes, identification,
  publication, controlled bench testing, and supervised on-air trials.
- [Desktop radio bring-up](docs/desktop-radio-bringup.md): optional device discovery,
  receive capture, and an explicitly executed, supervised PTT/audio test.
- [Research](docs/research.md): primary sources and dependency evaluation.

## Run the lab

Requires Rust via rustup and Python/uv. Rust is pinned by `rust-toolchain.toml`;
Python is pinned by `.python-version`. Dependencies are locked. The simulation
commands below run offline against sample buffers. The separate optional `lab.radio`
commands access hardware; only `transmit --execute` keys the radio. See its bring-up guide.

```sh
uv sync --locked
cargo build --release --locked
uv run --locked python -m lab smoke
uv run --locked python -m lab sweep --trials 40 --output artifacts/baseline
uv run --locked python -m lab.timing --trials 20 --output artifacts/timing
uv run --locked python -m lab.long_runs
```

Equivalent mise tasks: `mise run setup`, `mise run smoke`, `mise run sweep`,
and `mise run check`. Run `mise install` if its pinned tools are missing.
The first run may download dependencies; subsequent simulation runs need no network.

The smoke run produces TX/RX WAV files. Sweeps produce a manifest with source hashes,
per-trial JSON, summary CSV, and plots. Generated runs live in ignored `artifacts/`;
reviewed evidence lives under `docs/experiments/results/`.

```sh
cargo fmt --check
cargo clippy --all-targets --locked -- -D warnings
cargo test --locked
cargo build --release --locked
uv run --locked python -m unittest discover -s tests -v
```

The Rust CLI also accepts binary payloads and raw audio on stdin/stdout:

```sh
printf 'hello radio' | target/release/flash-modem encode fsk4 > artifacts/hello.f32
target/release/flash-modem decode fsk4 < artifacts/hello.f32
```

Create `artifacts/` first if you have not run the lab. Audio is mono, 48 kHz,
little-endian float32. `frame` emits wire bytes instead of samples. `decode` returns
exit status 0 for a valid payload, 2 for no packet, and 1 for an input/tool error.
Capture limit: ten seconds; payload limit: 1024 bytes.
Use `decode-stream fsk4` to exercise streaming timing recovery, optionally followed
by a chunk size in samples. The library accepts successive buffers; this CLI still
reads an offline capture and outputs the first valid payload.

## Working method

Start an experiment with a question and falsifiable success criteria. Preserve its
seed, source hashes, parameters, raw outcomes, and limitations. Promote a result to
a design decision only after independent vectors and, where relevant, radio captures
support it. Keep speculation explicitly marked as proposed. Use Python for experiments
and Rust for the shared implementation; add native dependencies when a measured
benefit justifies them.
