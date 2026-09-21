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
