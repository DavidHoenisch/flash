# Desktop Digirig bring-up

The optional `radio` dependencies add actual audio-device and RTS access. The offline
modem and simulation commands remain device-free. Use only in an attended station
with a chosen clear channel and an appropriate identification plan.

```sh
uv sync --extra radio --locked
uv run --extra radio --locked python -m lab.radio devices
uv run --extra radio --locked python -m lab.radio receive --seconds 3
```

`devices` enumerates without opening serial ports. `receive` records only the explicitly
named `USB PnP Sound Device`; it does not touch serial/PTT. It reports input RMS, peak,
and overflows. Capturing samples verifies host capture, not successful radio decoding.

## First test

Prepare a mono 48-kHz WAV of at most eight seconds with intelligible English callsign
identification and a short test signal. Prefer voice/tone for initial PTT/audio bring-up;
modem testing is a subsequent step. A generated WAV is not automatically published
and does not establish RF bandwidth, deviation, or reception quality.

```sh
uv run --extra radio --locked python -m lab.radio transmit artifacts/radio/kj7lym-test.wav \
  --device 'USB PnP Sound Device' --port /dev/cu.usbserial-2120 \
  --frequency-mhz 146.580 --gain 0.2
```

This invocation validates the file, CP210x identity, and selected audio output path,
but leaves the serial port unopened. **Adding `--execute` keys PTT and transmits once.**
The frequency argument is metadata only: this adapter neither tunes the FT-65R nor
verifies its TX frequency, power, offset, or physical PTT state. Validate the current
radio settings yourself. The example path refers to the locally prepared ID/tone
clip, not a file distributed in the repository.

The parent process owns serial RTS, configuring RTS and DTR inactive before opening.
It asserts RTS, waits 300 ms, then starts a separate audio process. Audio is duplicated
to both device output channels, with an explicit device selection. The child drains
queued audio; the parent adds 200 ms tail time and releases RTS. The child's timeout
is waveform duration plus three seconds. The parent's `finally` releases RTS and
closes serial on completion, worker error, timeout, or interruption. Driver-level
opening glitches and a host crash/hang are not eliminated by this software timeout;
this is not a hardware watchdog. The operator must remain able to stop the transmitter.

Logs are saved under ignored `artifacts/radio/`. A successful process result confirms
software playback/release operations, not an RF reception. Ask the receiving operator
whether speech/tone was heard, whether it sounded distorted, and whether transmission
stopped. Do not increase gain or repeat automatically without that observation.

## Discovery in this session

The Mac enumerated a C-Media USB PnP audio device (one input, two outputs, 48 kHz)
and a Silicon Labs CP2102N interface. `/dev/cu.usbserial-2120` and
`/dev/cu.SLAB_USBtoUART` identified as aliases of the same unit. Use only one; re-enumerate
after reconnecting, because device names/indices can change.

A three-second input capture completed without overflow. The operator initially
reported 144.650 MHz; the [Idaho ARES band-plan page](https://www.idahoares.info/idaho_band_plan_2meters.php)
places that frequency among repeater inputs and lists 146.580 MHz for simplex.
The proposed first test therefore uses 146.580 MHz after the operator confirms both
radios are tuned with no offset, low TX power, and a clear channel. This is operating
coordination, not a claim that a voluntary band plan changes FCC frequency privileges.
See the [U.S. testing plan](radio-testing-us.md) for regulatory context.

## First live result — 2026-09-21 UTC

The operator confirmed both radios had been moved to 146.580 MHz. A three-second
Digirig input capture had RMS 0.0001603, peak 0.0007935, and no input overflow. This
indicated quiet captured audio, not a calibrated RF channel-occupancy measurement.

One 5.6457-second clip was transmitted at software gain 0.2: spoken callsign, a
half-second 1000-Hz tone, and the spoken callsign again. The child audio process
completed without reported output underflow; the parent released RTS and closed
the serial port. The operator confirmed hearing the callsign and tone on the FTM-200D and that
TX stopped. Precise TX-stop timing was not measured.

This establishes a working host audio/PTT-to-radio path with audible RF reception.
It does not establish modem packet recovery, calibrated deviation, audio bandwidth,
bit error rate, or phone support. There were no automatic repeat transmissions.

Original local evidence is under ignored `artifacts/radio/`: `test-plan.json`,
`kj7lym-test.wav`, `receive-146580-before.wav`, and `tx-146580-first.json`. The next
hardware milestone needs received audio fed into a decoder—ideally a second wired
interface, or an explicitly labeled acoustic capture of the FTM-200D speaker for
an early experiment.

## First modem message attempt — 2026-09-21 04:54 UTC

At the operator's request, the opening body paragraph of the Declaration of
Independence was encoded as 406 ASCII bytes in a `fsk4` frame. The modem waveform
lasts 2.92 seconds at 1200 raw bit/s. Spoken callsign IDs before and after bring the
complete clip to 7.9657 seconds, within the existing eight-second limit. Both local
decoders recovered the exact payload from the complete gain-scaled clip.

A three-second receive capture was quiet (RMS 0.0001386; no overflow). One playback
was executed through the same Digirig/serial path on the operator-reported 146.580 MHz
at gain 0.2. Software playback, PTT release and port closure completed successfully.
The operator subsequently confirmed hearing the modem signal between the callsigns
on the FTM-200D. Audible RF reception is confirmed; over-radio packet decoding is
not yet verified, so this is not a successful data-transfer claim.

The public-domain [message fixture](../fixtures/messages/declaration-opening.txt)
has [source attribution](../fixtures/messages/README.md). Local evidence under
`artifacts/radio/` includes `declaration-opening-plan.json`,
`declaration-opening-fsk4.wav`, `declaration-opening-payload.txt`,
`receive-before-declaration.wav`, and `tx-declaration-opening.json`.

## First submitted acoustic recording — 2026-09-21

The operator supplied `Voice 260920_222133.m4a` after replaying the Declaration
test. It contains 18.2613 seconds of stereo, 48 kHz AAC audio. The waveform and
spectrogram show the two spoken-ID intervals surrounding the modem burst.

Neither existing Rust receiver returned a CRC-valid frame. Initial testing used
FFmpeg conversion to mono 48 kHz float WAV and overlapping ten-second windows
(five-second stride) to respect the CLI input limit. Follow-up attempts used the
10.0–14.2-second interval with left, right, and averaged channels, each unfiltered
or with a fourth-order 600–3200 Hz or 1200–3500 Hz Butterworth bandpass. Both fixed
and streaming receivers failed all these attempts. No recovered payload is claimed.

This recording is useful real-path failure evidence, but it does not isolate
radio distortion, speaker/room effects, recorder processing, or receiver limitations.
An exploratory known-message alignment was also saved; it is not a successful
decode or a reliable bit-error-rate measurement. A subsequent controlled test
should compare recording levels and a short known tone sequence before drawing
conclusions about the waveform.

Local, ignored evidence is under `artifacts/radio/`: `received-declaration.wav`,
`received-declaration-stereo.wav`, `received-declaration-spectrum.png`,
`received-declaration-decode.json` (including the source SHA-256), and
`received-declaration-followup.json`. Analysis did not key PTT or transmit.

## Lower-volume acoustic recording — 2026-09-21

The next supplied recording, `Voice 260920_222820.m4a`, followed the request to
reduce FTM-200D speaker volume. It contains 16.4693 seconds of stereo 48 kHz AAC.
Both spoken-ID intervals and the intervening modem burst are visible.

The existing fixed and streaming decoders returned no CRC-valid frame across
36 attempts: left, right, or arithmetic-mean mono channels; raw or fourth-order
600–3200 Hz Butterworth bandpass; ten-second windows starting at 0, 5, or 10 seconds
(the last window ends with the recording). Expected text was used only to check
decoder output, not to supply missing data. No payload was recovered.

Using the same arithmetic-mean stereo mix for both recordings, whole-recording
peak decreased from 0.8353 to 0.5584. RMS over representative 2.3-second interior
modem intervals decreased by about 1.63 dB. These intervals are not symbol-aligned
and recorder gain processing is unknown; this is a recording-level comparison,
not a calibrated measurement of speaker output or proof of clipping in the first
recording. Reducing volume did not resolve decoding failure.

Local evidence under `artifacts/radio/` includes
`received-declaration-low-volume-stereo.wav`,
`received-declaration-low-volume-decode.json` (source SHA-256 and every attempt),
`received-declaration-low-volume-spectrum.png`, and
`recording-volume-comparison.json`. No RF transmission was performed during analysis.

## Offline recovery follow-up — 2026-09-21

The [equalization investigation](experiments/0003-acoustic-equalization.md) subsequently
recovered the exact 406-byte message from the lower-volume recording with both
Rust receivers and both CRCs passing. The inverse filter was trained only on the
public sync waveform, without the expected message. The original recording still
fails. Earlier raw-decoder failures above remain accurate; this result adds an
experimental offline preprocessing step. No additional transmission was needed.
