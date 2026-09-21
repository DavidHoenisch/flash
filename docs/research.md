# Research register

Primary sources checked 2026-09-20. This is a shortlist, not a dependency adoption
decision. Pin source revisions, configurations, build flags, and licenses before
benchmarking or linking any candidate. Today's Rust prototype has no third-party
Rust/C dependencies; Python's numerical dependencies are in `uv.lock`.

## Hardware and baseline

| Source | Observed fact | Consequence |
| --- | --- | --- |
| [Digirig Mobile](https://digirig.net/product/digirig-mobile/) | CM108 audio, CP2102 serial, RTS PTT; current listing is a later revision | Separate audio and serial adapters; do not infer user's revision from current listing |
| [Digirig revision notes](https://digirig.net/digirig-mobile-rev-1-9/) | Independent audio-socket PTT starts at rev 1.6 | Verify hardware before asserting wiring |
| [VARA author's site](https://rosmodem.wordpress.com/) | Lists VARA FM v4.4.0 at time of review | Record installed version and operating mode when benchmarking; no downloaded/observed benchmark yet |
| [Yaesu FTM-200DR/DE manual](https://yaesu.com/Files/DFDF4D53-1B78-7375-E6C7A6E4B192BE13/FTM-200DR_DE_OM_ENG_EH061M200_2208O-CS.pdf) | Distinct front firmware DATA and rear external-equipment DATA connections | Confirm variant, connector, and audio path; see hardware plan |

## Implementation candidates

| Candidate | What the upstream source offers | Evaluation still needed |
| --- | --- | --- |
| [Codec2 data API](https://github.com/drowe67/codec2/blob/main/README_data.md) | Raw FSK and OFDM data; configurable FSK_LDPC; caller handles frame loss and segmentation | First external comparator: tone plan, code/frame lengths, tracking, CPU, Android C build, exact dependency licenses |
| [liquid-dsp](https://github.com/jgaeddert/liquid-dsp) | C modulation, framing, equalization, filtering, synchronization, OFDM | Useful higher-rate prototype blocks; benchmark real-audio modem integration and native build cost. Upstream describes MIT licensing and optional FFTW/libfec dependencies; inspect chosen build. |
| [RustFFT](https://github.com/ejmahler/RustFFT) | Rust FFT implementation including architecture acceleration | ARM64 performance if FFT-based PHY requires it |
| [Rubato](https://github.com/HEnquist/rubato) | Rust resampling with adjustable ratios | Streaming sample-clock tracking, buffer sizes, delay, and allocations |
| [Labrador-LDPC](https://github.com/adamgreig/labrador-ldpc) | Rust implementations of selected LDPC codes | Appropriate short-block codes, soft metrics, throughput/error performance; not a drop-in arbitrary-code engine |
| [CPAL](https://github.com/RustAudio/cpal) | Cross-platform Rust audio with Android and desktop support | Device routing, simultaneous USB paths, lifecycle, callback behavior on the S25 Ultra |
| [Oboe](https://github.com/google/oboe) | Android C++ audio abstraction with device workarounds | USB routing and capture/playback lifecycle on the actual phone; compare adapter complexity against CPAL |
| [USB Serial for Android](https://github.com/mik3y/usb-serial-for-android) | Android USB serial drivers including CP210x and control-line support | Digirig RTS behavior, permissions, disconnects, simultaneous audio access |

Our inference: Rust is a reasonable owner of the link/session API and new modem code.
C offers more integrated existing modem components than an FFT or resampler alone.
The efficient next comparison is therefore the present Rust baseline against a pinned
Codec2 FSK_LDPC build, followed by a higher-rate modem candidate if measurements support
it. Library availability does not establish target-device performance.

## Questions the literature cannot answer for this station

- Usable FT-65R-to-FTM-200D end-to-end audio passband and distortion at actual gains.
- S25 Ultra USB audio/serial concurrency, routing stability, and power consumption.
- Practical turnaround cost and best burst length in both directions.
- Whether FSK plus coding gets close enough to the requested throughput, or a more
  spectrally efficient mode is necessary.
- The agreed comparable VARA payload rate and completion-rate target.

These require measurements. No RF/audio captures, Android results, Codec2 results,
or VARA benchmark numbers are claimed in the initial experiment.
