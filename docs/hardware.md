# Hardware characterization plan

Initial desktop bring-up is now complete: the Mac captured audio from Digirig, and
an identified voice/tone transmission through the FT-65R was heard on the FTM-200D.
See [desktop bring-up](desktop-radio-bringup.md). This is not an over-radio modem decode
or a measured passband/deviation test. The simulation lab remains device-free.

For U.S. operation under the user's Amateur Extra license, follow the separate
[novel-mode and radio test plan](radio-testing-us.md), including independent voice ID,
published test materials, and a validated attenuated RF bench path before field trials.

## Known equipment

| Endpoint | Confirmed | Still to establish |
| --- | --- | --- |
| A | Galaxy S25 Ultra, Digirig Mobile, Yaesu FT-65R | Android version, Digirig revision, cable, USB routing, gain and timing |
| B (local) | Yaesu FTM-200D | Exact variant, computer, audio/PTT interface and cable |
| B (remote) | Another operator can help test | Radio/interface, host OS, repeatable test conditions |
| Later HF | Xiegu X6100, 20 m | Second HF station and suitable captures |

Digirig documents a CM108 audio codec and CP2102 serial interface, with RTS controlling
PTT. Audio-socket PTT independent of CAT starts at revision 1.6; verify the actual unit.
See [product](https://digirig.net/product/digirig-mobile/),
[revision notes](https://digirig.net/digirig-mobile-rev-1-9/), and
[FT-65R cable](https://digirig.net/product/yaesu-ft65r-cable-for-digirig-mobile/).

The [FTM-200DR/DE operating manual](https://yaesu.com/Files/DFDF4D53-1B78-7375-E6C7A6E4B192BE13/FTM-200DR_DE_OM_ENG_EH061M200_2208O-CS.pdf)
distinguishes a front DATA connector used for firmware updates from a rear DATA
connector for external equipment (printed page 15). Do not infer generic USB audio
support or connector pinout from the word DATA. Verify the user's exact radio variant
and the relevant manual before selecting cables or data settings. The
[FT-65R manufacturer page](https://yaesu.com/product-detail.aspx?CatName=VHF%2FUHF+Handhelds&Model=FT-65R)
links its manuals.

Having two radios enables local testing, but exchanging bytes also requires an
audio path at both ends. One Digirig can be moved between endpoints for separate
characterization runs; a simultaneous bidirectional link requires an interface
at each station. A partner's existing interface may provide that without a purchase.

## Measurement sequence

1. Inventory device IDs, supported sample rates, gain settings, cable wiring, radio
   firmware, FM width/deviation setting, and squelch. Record exact routing rather than
   trusting the host's default microphone/speaker.
2. Verify receive capture and explicit playback routing before transmitter control.
   On the phone, verify USB host permissions and simultaneous audio/serial access.
3. Verify bounded RTS/PTT assertion, audio-drain detection, release on every error,
   and recovery after USB unplug/replug. Log monotonic timestamps and underruns.
4. Through an appropriately attenuated test path or coordinated radio link, record
   stepped tones/sweeps at several audio levels. Capture both directions independently.
   Measure useful passband, frequency-dependent gain/delay, clipping, and harmonic
   distortion. Keep the original samples; do not normalize away gain information.
5. Transmit bursts with varying lead time; measure PTT-to-audio, squelch opening,
   lost leading samples, tail truncation, and return-to-receive delay. Use a sustained
   known waveform to estimate relative sample-clock error.
6. Replay captured test signals through candidate decoders. Then test actual packets
   over both radios. Acoustic speaker-to-microphone tests are a separate exploratory
   condition, not a substitute for the wired reference audio path.
7. On Android: run sustained RX/TX cycles, screen lock/background operation, permission
   refusal, device removal, route changes, and low-battery/thermal conditions. Record
   actual CPU/energy, not desktop estimates.

## Capture record

For each original WAV, store SHA-256, UTC timestamp, sample format/rate, channel,
station/host/radio/interface IDs, software revisions, cable identity, TX power,
frequency, radio mode/width, gain settings, squelch, test payload/hash, and impairment
or path description. Keep RX and transmitted reference audio plus timing logs.
Unknown fields should be null, not invented defaults. Keep personally identifying
station/location information out of public fixtures unless intentionally included.

The first useful evidence set is: a clean bidirectional capture, a level sweep that
crosses the distortion knee, burst-start/tail captures, and a long clock measurement.
Those data determine the next waveform experiment and practical PTT timing budget.
