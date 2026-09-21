# Validation plan and decision register

Part of [FLASH draft 0.1](README.md). Plans below are proposed experiments, not
completed trials or statistically qualified operating limits. Existing tests and
recordings remain development evidence.

## Next experiments

**E04 — fixed receiver on unseen captures.** Freeze source, equalizer settings and
acquisition rules before collecting a new evaluation set. Use fresh random payloads,
readable messages, empty/short packets and long `00`/`ff` patterns; include the 1024-byte
codec limit offline and shorter RF clips that fit the configured ID/burst budget.
Keep expected bytes outside decoder inputs. Label clean wired, acoustic and simulated
paths separately. Start with the available acoustic setup; a second interface or
partner is needed for the wired reference and reverse direction.

Proposed pilot: at least 30 packet attempts per selected level/path condition, changing
one factor at a time and logging recording position, gain settings and unknowns.
Include silence/noise, damaged headers, truncated tails and leading-sample loss.
Evaluate raw fixed, raw streaming and frozen equalized paths on identical samples.
Report exact recovery, wrong acceptance, no frame, tool faults and processing cost.
Any tuning using evaluation results moves those captures into the development set;
use new captures for the next held-out evaluation. Pilot success is not a high-reliability
claim; qualification sample sizes follow D07's agreed error bound.

**E05 — training, timing and coding comparison.** Compare the current constant
preamble/public-sync equalizer with an explicitly defined diverse training candidate,
and compare uncoded FSK against a pinned FEC baseline and a justified higher-rate
candidate. Do not allocate or change wire identities until each candidate is defined
with vectors. Include random and constant payloads, mixed clock/filter/noise conditions,
bursty corruption, measured channel models and original-path captures when the waveform
matches. A saved FSK recording cannot directly test a different transmitted waveform:
use it to estimate a labeled channel model, then collect new captures for confirmation.

Measure total overhead, acquisition failure, packet loss, goodput, spectrum and compute
cost rather than raw bit rate alone. Hold out some channel captures from model fitting.
Sweep equalizer regularization and training lengths using development data, then freeze
them for evaluation. The 80-tap inverse filter is a baseline, not a mandatory answer.
Compare public whitening/line coding or periodic training against the observed long-run
clock-tracking failure. Record any noise amplification or raw-receiver regressions.

**E06 — reliable-link simulator.** Implement the proposed logical link with injected
time before depending on radio experiments. Exercise lost/corrupt data, lost and delayed
ACKs, duplicates, stale sessions, simultaneous starts, receiver rejection, restart,
file-integrity mismatch, cancellation and final-ACK loss. Assert bounded resources and
airtime requests, no premature completion, and no duplicate delivery within a live
session. Specify and test sequence wrap, identity reuse and retention once D04/D05 are
resolved. Model turnaround explicitly; do not assume instantaneous ACKs.

**E07 — two stations and target adapters.** Measure audio passband/gain, onset loss,
drain, tail, return-to-receive and relative clocks in both directions. Repeat fresh
message/file transfers with acknowledgments, induced loss and cancellation. Separate
simulator timing from physical observations. Exercise device disconnect, route change,
permission refusal and audio faults; verify observable PTT release and recovery.
On S25 Ultra/Android and Linux, measure sustained operation and target resource cost.
Current Mac-to-radio transmission and phone recording do not establish phone modem
execution. Hardware work requires an actual second transmit/receive interface or
partner station; document that dependency rather than assuming it is available.

## Open decisions

| ID | Decision | Evidence needed | Status |
| --- | --- | --- | --- |
| D01 | First supported waveform and operating rates | E04/E05/E07; measured paths, total overhead, spectrum and target compute | Open; version-0 FSK remains experimental. |
| D02 | Training/acquisition, equalization and clock strategy | E04/E05; unseen captures, clock plus filtering, constant runs, noise amplification | Open; public-sync inverse FIR is an offline prototype. |
| D03 | FEC, interleaving, whitening/line coding | E05; reliability/latency/overhead comparison and independent vectors | Open; none exists in version 0. |
| D04 | Discovery/control mode, versions, capabilities and session/block identities | E05/E06; rejection, collision and wrap/reuse behavior, interoperability vectors | Open; no new bytes/opcodes allocated. |
| D05 | Object limits, end-to-end hash, deduplication retention, persistence/resume | E06/E07; memory/storage bounds, crash and final-confirmation tests | Open; no restart exactly-once promise. |
| D06 | Turn-taking, retry/backoff/timers, buffers and audio backend/ABI | E06/E07; measured turnaround and platform fault behavior | Open; desktop helper constants are not production defaults. |
| D07 | MVP numeric acceptance and VARA comparison matrix | Comparable hardware measurements and agreement on thresholds before qualification | Open; no 80% requirement or throughput promise. |
| D08 | Source/spec licensing and distribution | Explicit license selection, dependency review and reproducible test package | Open; drafting docs does not publish a release. |

## Traceability and gates

| Requirement group | Verification / evidence | Remaining gate |
| --- | --- | --- |
| R01–R05: scope, portability, openness | Existing codec/oracle and vectors; E05/E07 | Buildable independent implementation and target adapters; resolve D08. |
| R06: payload/format integrity | Byte vectors, negative codec tests, both acoustic recordings | E04/E05 and additional false-accept/truncation conditions. |
| R07–R10: reliable transfer/resources | No link implementation yet | E06/E07 and resolved D04/D05. |
| R11–R15: platform/control | Desktop routing and software cleanup tests | E07 physical timing/fault evidence and deterministic link replay. |
| R16: practical performance | No comparable VARA run yet | D07 followed by a frozen, reproducible qualification run. |
| R17: evidence quality | Source hashes, seeded trials and capture reports | Preserve frozen evaluation sets, original data and failure accounting throughout. |

Freeze a **supported PHY profile** only after its exact wire definition and independent
vectors exist, its operating envelope is measured, its receiver is evaluated on unseen
conditions, and acquisition/noise/clock/spectrum/resource tradeoffs are documented.
Unresolved qualification thresholds cannot be treated as passed by default.

Freeze a **reliable link revision** only after all peer-visible fields, state transitions,
limits and timeouts are explicit; simulator negative cases pass; and two stations have
completed bidirectional message/file trials with integrity and failure behavior checked.
Freeze a **product/MVP release claim** only after target-platform requirements, operating
controls, distribution/license decisions and the agreed practical benchmark are met.

These gates do not prevent implementing draft components or continuing supervised
experiments. They prevent exploratory results being presented as completed qualification.

## Commands available today

```sh
# Offline checks; none of these commands transmits.
cargo test --locked
cargo build --release --locked
uv run --locked python -m unittest discover -s tests -v
uv run --locked python -m lab.timing --trials 20 --output artifacts/timing
uv run --locked python -m lab.long_runs
uv run --locked python -m lab.equalizer_sweep
make decode-recording RECORDING="/path/to/recording.m4a"
```

E04–E07 are planned work, not aliases for existing scripts. Live transmission uses
separate explicit commands described in the bring-up notes. Record actual test
settings and operator observations alongside software logs.
