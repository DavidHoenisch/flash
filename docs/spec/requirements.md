# Requirements and performance contract

Part of [FLASH draft 0.1](README.md). “Required” below means a draft requirement for
the intended product, not a claim about today's implementation.

## Scope

| ID | Requirement | Current evidence / completion condition |
| --- | --- | --- |
| R01 | Modem processing must run locally on the endpoint, without an Internet service in the sample or link path. | Offline Rust/Python prototypes exist; native Android operation remains to demonstrate. |
| R02 | The first supported radio profile must work through measured FM audio paths, including the FT-65R/Digirig reference endpoint. | One acoustic message recovered; gain, bandwidth, both directions and usable operating envelope remain unqualified. |
| R03 | The core must support Android and Linux adapters; protocol behavior must not depend on desktop-only libraries. | Rust core has no platform I/O. Current device bring-up is macOS only. |
| R04 | PHY and link processing must be separable from UI, USB/audio discovery, device permissions and operating policy. | PHY separation exists; link core and stable adapter API remain to implement. |
| R05 | Another implementation must be able to reproduce transmitted frames from public definitions and vectors, without secret parameters. | Version-0 byte/sample reference and vectors exist; future profiles need equivalent coverage. |

The Galaxy S25 Ultra, Digirig Mobile and FT-65R are the intended reference endpoint.
The FTM-200D speaker recording is a useful exploratory receive path. Its acoustic
success does not substitute for a wired reference or simultaneous bidirectional
interfaces. Exact hardware revisions, cable details and OS/audio routes belong in
capture records rather than universal protocol constants.

Initial exclusions: HF profiles, multi-hop routing, repeater/gateway integration,
Winlink/VARA wire compatibility, unattended operation and confidentiality features.
Checksums do not provide authentication. Requirements for authentication and other
operating services need a separate design. Existing KISS TNC transport support would
be an adapter feature, not evidence it can generate FLASH waveforms.

## Data and reliability

| ID | Requirement | Current evidence / completion condition |
| --- | --- | --- |
| R06 | The transport must preserve arbitrary payload bytes and distinguish accepted data, corruption, unsupported format and incomplete reception. | Version-0 codec accepts bounded byte payloads with two CRCs. CLI exposes no-frame versus invalid-input outcomes; detailed receive events remain draft. |
| R07 | Reliable mode must acknowledge accepted data, retry within explicit limits, suppress duplicates in a live session, and report completion, failure or cancellation. | Not implemented; simulator and two-radio gates E06/E07. |
| R08 | File transfer must bound fragmentation/reassembly resources, verify the complete object and expose it as complete only after verification. | Not implemented. Maximum object size, hash algorithm and storage policy are D05. |
| R09 | Negotiation must reject incompatible peers and agree on a mutually supported profile before relying on optional features. | Not implemented; experiment version 0 requires an externally selected profile. D04 defines negotiation and identity. |
| R10 | Corrupt or unauthenticated peer input must not cause unbounded allocations, retries, airtime or file-system writes chosen by the peer. | Codec length bounds exist; link/storage limits and negative tests remain to implement. No authenticated peer mechanism exists. |

“Delivered” means accepted by the receiving application under its stated storage
policy. “Sender complete” additionally requires the protocol's final confirmation.
If the receiver accepts an object but every final confirmation is lost, the sender
may time out with delivery unconfirmed; it must not assert the object was never
received. Duplicate handling across process restarts is not yet promised (D05).

## Platform and operation

| ID | Requirement | Current evidence / completion condition |
| --- | --- | --- |
| R11 | Audio and PTT must use explicit device routing, bounded queues and finite transmission deadlines. | Desktop test adapter selects devices and limits clips; sustained adapters and queue/latency bounds remain to qualify. |
| R12 | Transmission must account for key-up, audio drain, tail and return-to-receive; cancellation/error must stop output and attempt to release PTT. | Desktop software cleanup is tested. Physical timing, disconnect behavior and hardware watchdog coverage remain unverified. |
| R13 | The station must support attended control, identification scheduling and cancellation independently of decoding custom packets. | Prepared spoken-ID clips work in supervised tests. Scheduling and long-transfer integration remain to implement. |
| R14 | Discontinuities, underruns, route changes and device removal must be observable and must not be reported as successful packet/transfer completion. | Partial desktop checks exist; adapter fault matrix is E07. |
| R15 | Shared-core link state machines must use injected monotonic time and produce bounded actions/events that can be replayed in simulation. | Not implemented. Verify identical logical outcomes under equivalent simulated and adapter events. |

Operating policy is separate from the byte protocol. Frequency, power, permitted
emission and identification settings are station configuration, not constants inferred
from a profile name. The dated [U.S. test research](../radio-testing-us.md) and
[hardware plan](../hardware.md) provide context; this draft does not certify regulatory
compliance or prescribe a universal test frequency.

## Measurement and acceptance

**R16 — practical performance:** the MVP goal is to approach VARA FM's delivered
throughput and reliability on comparable hardware. Exceeding it is a later objective.
There is no agreed percentage or numeric minimum yet. The earlier 80% suggestion is
not an acceptance requirement. D07 must set thresholds before qualification trials.

**R17 — reproducibility:** every qualification result must identify source/build,
wire profile, payload definition, device/configuration, capture format, preprocessing,
timing, failures, trial count and uncertainty. Unknown settings must remain unknown,
not be filled with presumed defaults. Keep original captures and hashes; preserve
development versus held-out labels. Never supply expected payload bytes to a receiver
being evaluated. Compare accepted output afterward, and record any wrong acceptance
as a correctness failure, not ordinary packet loss.

| Metric | Definition / reporting rule |
| --- | --- |
| Payload goodput | Unique successfully delivered application bytes divided by elapsed transfer time, including setup, identification overhead, contention, PTT, ACKs and retries; state measurement boundaries. |
| Aggregate goodput | Total unique delivered bytes across the trial set divided by total elapsed trial time, including failures and timeouts. Do not sum only successful durations. |
| Completion rate | Completed transfers / attempted transfers, alongside payload size, conditions and uncertainty. Report sender-confirmed completion separately from receiver acceptance. |
| Packet error rate | Failed packet attempts / packet attempts for a defined receiver/profile/condition, with trial counts and intervals. |
| Latency | Submission to receiver delivery and submission to sender confirmation, with median/p95 where sample size supports them; label success-conditioned statistics and show timeout counts. |
| Resource cost | Sustained target-device CPU, memory, audio overruns and energy under stated RX/TX workloads. Subprocess wall time is not core DSP CPU cost. |
| Spectrum | Measured occupied audio/RF spectrum and deviation under stated settings; tone span and generated-WAV FFT alone do not qualify RF emissions. |

VARA comparisons must record the version, license/rate restrictions, Narrow/Wide
setting, audio path, power, payload set and retry budget. Benchmark the same conditions
and disclose differences that cannot be matched. Version-0 raw 1200 bit/s and payload
bits per waveform second are not application goodput claims.
