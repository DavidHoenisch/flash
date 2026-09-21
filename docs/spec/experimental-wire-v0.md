# Experimental wire contract — version 0

Part of [FLASH draft 0.1](README.md). This document specifies the already implemented
uncoded experiment. It does not define discovery, addressing, acknowledgments or a
reliable link. Future supported profiles remain undecided.

## Audio and symbols

The reference sample representation is mono 48,000 samples/s. Raw CLI audio is IEEE
754 float32, little-endian. Device-level conversion and gain belong to the adapter.
The reference transmitter emits amplitude 0.7; that number is not an RF deviation
setting or a prescribed playback gain. Receive level and polarity may differ.

| Parameter | `fsk2` | `fsk4` |
| --- | --- | --- |
| Profile byte | `01` | `02` |
| Symbol rate | 1200 symbols/s | 600 symbols/s |
| Samples per symbol | 40 | 80 |
| Bits per symbol | 1 | 2 |
| Tone mapping | `0`: 1200 Hz; `1`: 2400 Hz | `00`: 900 Hz; `01`: 1500 Hz; `10`: 2100 Hz; `11`: 2700 Hz |
| Raw bit rate | 1200 bit/s | 1200 bit/s |

Every byte is serialized most-significant bit first. `fsk4` takes consecutive pairs
in that order and uses natural binary tone mapping. Both profiles modulate every
frame field, including preamble and sync, using the selected profile. A receiver must
be given the profile externally or search independently; the profile byte inside
the header is not an out-of-band discovery signal.

The reference phase starts at zero at the first preamble sample. For every sample,
emit `0.7 * sin(phase)`, then update `phase = (phase + 2*pi*f/48000) mod (2*pi)`.
There is no phase reset at symbol or byte boundaries. Absolute received phase is
not required to be zero. For reference-vector checks, sample comparisons use
`abs(actual-reference) <= 2e-6 + 1e-7*abs(reference)`, matching the current independent
sample tests; wire-byte comparisons are exact. This numerical test tolerance is not
a receiver gain, clock or carrier tolerance.

There is no FEC, interleaving, whitening, compression, pulse shaping, amplitude
ramp, or encryption in this contract. No guard silence or voice ID is encoded as
a frame field. Station test clips add those outside the frame. Abrupt transitions
and burst edges have spectral sidelobes; occupied RF bandwidth is unmeasured.

## Frame layout

Offsets are zero-based bytes before modulation. Let `L` be payload length.

| Offset | Bytes | Field | Required value / encoding |
| ---: | ---: | --- | --- |
| 0 | 16 | Preamble | `55` repeated 16 times |
| 16 | 4 | Sync | `d3 91 c5 a7` |
| 20 | 1 | Version | `00` |
| 21 | 1 | Profile | `01` or `02`, matching the modulation profile |
| 22 | 2 | Payload length | Unsigned big-endian, 0 through 1024 inclusive |
| 24 | 4 | Header CRC | CRC of bytes 20 through 23, stored big-endian |
| 28 | L | Payload | Arbitrary bytes, with no implicit terminator or text encoding |
| 28 + L | 4 | Body CRC | CRC of bytes 20 through 23 followed by payload, stored big-endian |

The body CRC excludes the preamble, sync and header CRC. Each CRC starts with a
fresh initial state. Total frame length is `L + 32` bytes. Empty payloads are valid.
The 4-FSK preamble is 64 identical `01` symbols at 1500 Hz; it is not a diverse
training sequence. The sync occupies 16 4-FSK symbols.

Both fields use CRC-32/ISO-HDLC: width 32, normal polynomial `04c11db7`, reflected
implementation polynomial `edb88320`, initial state `ffffffff`, reflected input/output,
final XOR `ffffffff`. ASCII `123456789` checks to `cbf43926`. Reflection in the CRC
algorithm does not change MSB-first byte serialization or big-endian CRC storage.
Check the computed integer directly against the stored value; no residue test is
required. CRCs detect corruption; they do not authenticate a transmitter.

## Acceptance and errors

A conforming accepted frame must have supported version and profile, a length in
range, all required bytes, and valid header and body CRCs. Validate the protected
header before trusting its length for allocation or body extraction. Unknown fields
must not be silently interpreted as this experiment. A failed or truncated frame
must not expose partial bytes as an accepted payload. CRC-valid output is still
compared with the test oracle when measuring correctness.

Transmitters must emit the complete preamble and sync. The existing receivers do
not require observing all preamble bytes to accept a frame. They acquire on exact
sync and require both CRCs; other receiver algorithms may use different acquisition
methods. More than one algorithm or timing candidate is allowed, but measurement
reports must disclose offline searches and CRC-based candidate selection.

There are no peer-visible reject codes, ACKs, sequence numbers, addresses or session
fields. Repeated frames are independent observations. Payload byte patterns must
not be treated as hidden control messages in an interoperability claim.

## Durations and implementation limits

At either profile, frame duration is `(L + 32) * 8 / 1200` seconds. This excludes
PTT lead/tail, voice ID, guard silence, contention and any future ACKs.

| Payload bytes | Frame bytes | Waveform duration |
| ---: | ---: | ---: |
| 0 | 32 | 0.213333… s |
| 256 | 288 | 1.92 s |
| 406 | 438 | 2.92 s |
| 1024 | 1056 | 7.04 s |

The current raw decoder CLI permits at most ten seconds of audio and returns only
one accepted payload. The fixed receiver's search order need not find the earliest
packet. The streaming library can emit multiple packet events; the CLI retains the
first emitted one. These are tool/API limits, not on-air fields.

CLI: `flash-modem <frame|encode|decode|decode-stream> <fsk2|fsk4>`.
`decode-stream` accepts an optional positive sample-chunk size. `frame` emits frame
bytes; `encode` emits raw audio; decoders emit payload bytes. Exit 0 means success,
2 means no accepted frame, and 1 means invalid input or another reported error.
An empty accepted payload produces no stdout bytes but still returns 0.

The current desktop transmit helper limits the **whole audio clip** to eight seconds,
including voice ID and silence. A maximum-length codec frame need not fit that helper
with IDs. Its 0.3-second lead, 0.2-second tail and software watchdog are test settings,
not mandatory protocol timing.

## Receiver implementations and conformance

The fixed detector exhaustively checks integer symbol phases. The streaming detector
tracks timing with bounded state and has finite lookahead. The optional Python
equalizer searches a whole recording and trains an inverse filter on public sync.
Neither its 80 taps nor its numerical regularizer is a wire requirement. No receiver
may use an expected test payload as an undisclosed decoding input.

[Exact byte vectors](../experiments/results/0001-vectors.json) cover both profiles,
empty payload, ASCII `123456789` and bytes `00` through `0f`. For example, the empty
`fsk4` frame is:

```text
55555555555555555555555555555555d391c5a70002000022c00b7222c00b72
```

Conformance requires matching vectors, bounded length handling, CRC/header rejection,
and independent sample-reference agreement; receiver qualification additionally
requires the validation matrix. Passing wire vectors alone says nothing about radio
reliability. Implemented references: [Rust codec](../../crates/flash-modem/src/lib.rs),
[Python oracle](../../lab/modem.py), and [codec tests](../../tests/test_lab.py).
