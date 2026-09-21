# U.S. amateur-radio testing plan

Research checked 2026-09-20 (local). User confirmed **USA, Amateur Extra**.
This is an engineering plan based on the published rules, not an FCC determination
about a completed transmitter. Recheck the current rules and chosen frequency before
RF testing. A first supervised identified voice/tone test is recorded in the
[desktop bring-up notes](desktop-radio-bringup.md), along with a subsequent supervised
4-FSK message transmit attempt. A later acoustic recording yielded the exact message
after offline equalization; see [experiment 0003](experiments/0003-acoustic-equalization.md).
This engineering update does not refresh the dated regulatory research below.

## A new decoder is not automatically a prohibited code

The relevant prohibition concerns encoding intended to conceal meaning. It does not
say every listener must already own a compatible decoder. [§97.113(a)(4)](https://www.law.cornell.edu/cfr/text/47/97.113)

Two provisions matter: §97.309(a)(4) permits publicly documented techniques carrying
specified codes; §97.309(b) permits unspecified codes where authorized, with no
concealment purpose and with international restrictions. The latter also allows FCC
directions to stop, restrict, or retain recoverable records. Publishing source is
not a universal statutory prerequisite under (b), nor does publication alone make
any emission legal. Our engineering choice is to publish the specification and
decoder anyway. [§97.309](https://www.law.cornell.edu/cfr/text/47/97.309)

Do not assume that wrapping arbitrary binary data in a homegrown frame establishes
the specified-code route simply because one test payload is readable text. For the
initial FM work, design around the expressly permitted unspecified-code route on an
appropriate VHF/UHF channel. HF needs a separate review before testing.

## Band, emission, and operating conditions

| Issue | Relevant rule and implication |
| --- | --- |
| License privileges | Extra includes the relevant VHF/UHF privileges; it does not waive technical or operating rules. [§97.301](https://www.law.cornell.edu/cfr/text/47/97.301) |
| 2 m | Data is authorized at 144.1–148 MHz, with §97.307(f)(2), (5), (8). Pick a locally suitable simplex/data channel within that range, not a frequency just because it is in-band. [§97.305(c)](https://www.law.cornell.edu/cfr/text/47/97.305) |
| 70 cm | Data is authorized, subject to §97.307(f)(6), (8) and geographic/sharing restrictions. Keep the first partner exchange domestic. [§97.305](https://www.law.cornell.edu/cfr/text/47/97.305), [§97.303](https://www.law.cornell.edu/cfr/text/47/97.303) |
| Technical limits | Current text retains the 19.6-kilobaud/20-kHz provisions in (f)(5), and 56-kilobaud/100-kHz provisions in (f)(6). Those are not targets: necessary bandwidth, applicable phone-bandwidth restrictions, spurious emissions and interference rules also apply. Audio tone span does not establish RF occupied bandwidth. [§97.307](https://www.law.cornell.edu/cfr/text/47/97.307) |
| Supervision | Use locally controlled, attended tests with immediate PTT cancellation. Avoid unattended operation in the initial plan. [§97.109](https://www.law.cornell.edu/cfr/text/47/97.109) |
| Channel/power | Cooperate with other users, respect emergency traffic, and use the minimum necessary power. [§97.101](https://www.law.cornell.edu/cfr/text/47/97.101), [§97.313(a)](https://www.law.cornell.edu/cfr/text/47/97.313) |

The rule permitting brief experimental test emissions is not a blanket exemption
for ongoing data operation. Brief station-adjustment transmissions are also
authorized; extended unattended beaconing is outside this plan.
[§97.305(b)](https://www.law.cornell.edu/cfr/text/47/97.305),
[§97.111(b)](https://www.law.cornell.edu/cfr/text/47/97.111)

Local band plans and coordination help select a channel; distinguish those operating
recommendations from the FCC allocation/technical rules. The operator selected
146.580 MHz for the initial local trials; this is recorded test configuration, not
a universal default or approval for future locations/conditions. Avoid calling
channels, repeater inputs/outputs, satellite segments,
and active channels. Other-radio-service use needs separate authorization; an amateur
license is not blanket authority for GMRS, commercial, or other service experiments.

## Identification independent of our packets

Use ordinary English FM voice identification on a channel authorizing phone: each
transmitting station identifies at the end of its communication and at least every
ten minutes during it. For initial testing, also identify and briefly announce the
test before starting. The additional opening announcement is our practice, not a
substitute for the required end/periodic ID. [§97.119(a),(b)(2)](https://www.law.cornell.edu/cfr/text/47/97.119)

A callsign field carried only inside FLASH is not our station-identification
mechanism. Do not assume audio tones representing Morse through an FM transmitter
automatically satisfy the rule's CW identification provision; voice is straightforward
for this setup. Software must leave time for ID and must not continue unattended past
an identification deadline. The modem has no automatic ID scheduler. The optional
[desktop bring-up tool](desktop-radio-bringup.md) now supports supervised PTT and
playback of a prepared voice-ID clip; it does not verify identification content.

## Staged test procedure

1. **Offline samples and electrical audio loopback.** Start with generated/captured
   WAV files and, later, suitable line-level audio connections between interfaces.
   Radios remain unkeyed. Validate routing, packet recovery, levels, interruptions,
   and timing independently of RF.
2. **Controlled RF bench link.** Start one direction at a time: transmitter →
   properly rated 50-ohm load/coupler → additional attenuation/protection → receiver.
   Confirm the actual RF power, component power ratings, impedance, coupling loss,
   and receiver input limits before connection. **Never directly connect two antenna
   ports.** The reverse direction needs a separately validated path or a fixture
   rated for transmission from either end; do not accidentally transmit into a
   receive-only measurement branch. Shield the path and check leakage. A dummy load
   reduces radiation; it is not a blanket legal exemption.
3. **Short, supervised local simplex exchanges.** Both stations have the same
   published profile and decoder. Confirm the channel is clear, identify/announce,
   send a small known packet, stop, decode and compare. Increase burst size only after
   levels, RF spectrum, turnaround, and PTT release have been checked. End with voice ID.
4. **Partner trials.** Share version, channel, scheduled window, power, abort procedure,
   payload definition, and logging format in advance. Use ordinary communications
   outside the modem to coordinate failures. Do not begin with repeater/gateway integration.

For the bench fixture, determine attenuation from actual transmit power and a chosen
safe receive level, including margin and leakage. This document intentionally does
not prescribe a cable/attenuator bill of materials without those measurements. RF
spectrum/deviation and out-of-channel emissions must be measured at the transmitter;
an FFT of a generated WAV cannot certify them. See [hardware measurements](hardware.md).

## Public test package and logs

Before the first antenna-connected trial, publish a tagged, immutable package with:

- Complete sample rate, tones, symbol mapping, framing/CRC, training, and any future
  coding/interleaving/whitening parameters; clearly identify the experimental version.
- Buildable decoder, exact commands, known input payloads, and TX/RX example WAVs.
- Plaintext test messages initially. For longer tests, use a published deterministic
  sequence with its algorithm/seed; never conceal a payload or use secret keys.
- The tested source revision and a short page explaining the experiment and how to decode.

The GitHub repository was verified public in this session, but these new files are
local and uncommitted. A public repository does not expose unpublished working-tree
changes. No publication was performed. Select the software license before releasing
the package; source visibility and a license granting reuse are different matters.

Keep original payloads, source/profile revision, WAVs/hashes, UTC and monotonic timing,
radio/interface settings, TX power, chosen channel, station IDs, ID times, and failures.
These logs are our reproducibility practice; the rule's special recordkeeping direction
for unspecified codes applies when the FCC requires it. Don't describe routine project
logs as a universal FCC logging requirement.

## Before changing scope

Revisit the legal/technical analysis before HF, cross-border links, spread spectrum,
automatic operation, encryption/authentication design, or another radio service. If
the final emission/code classification is ambiguous, obtain a qualified amateur-radio
regulatory interpretation (and FCC clarification if necessary) with the actual spec
and proposed operating parameters. A novel name alone does not require a separate
experimental authorization; operating outside Part 97's permissions is a different issue.

## Source freshness

The official eCFR section URLs returned access errors in this session. The research
used Cornell LII's current republication of the CFR text, including January 2026
amendments where shown. The 2023 proposal to relax additional VHF/UHF limits must not
be mistaken for an effective final rule. Check the official current text again at
test time: [eCFR Part 97](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-D/part-97).
