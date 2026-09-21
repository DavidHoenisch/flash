# FLASH specification — draft 0.1

Status: working draft, 2026-09-20 (America/Los_Angeles). This is a design and
implementation contract under development, not a released interoperability standard.
**Document revision 0.1 is distinct from the existing on-air experiment version `00`.**

FLASH is an openly specified radio data modem intended to run locally on phones
and desktops. Initial work targets half-duplex FM through ordinary radio audio
interfaces. Rust supplies the portable core; Python supports independent references,
simulation and fast experiments. The first useful application is reliable point-to-point
messages and files between an Android station and a desktop station.

## Read the draft

| Document | Defines |
| --- | --- |
| [Requirements](requirements.md) | Scope, functional requirements, success metrics and evidence |
| [Experimental wire format](experimental-wire-v0.md) | Exact existing version-0 bytes, samples and acceptance rules |
| [Link and platform behavior](link-and-platform.md) | Proposed reliability semantics, component boundaries and audio/PTT lifecycle |
| [Validation and open decisions](validation-plan.md) | Next experiments, decision gates and conditions for freezing a supported profile |

## What is established, and what is provisional?

**Established direction:** FM first; Android and Linux as intended platforms;
Galaxy S25 Ultra → Digirig Mobile → FT-65R as the reference endpoint; Rust preferred,
with justified C/C++ dependencies permitted; near-VARA practical performance as the
MVP goal, exceeding it later. Today's host experiments run on macOS. FTM-200D and
another operator provide additional test options. HF with the X6100 is later work.

**Implemented experimental contract:** the two uncoded FSK profiles and version-0
frame in the wire document. These are reproducible baselines. They are not selected
as the first supported production waveform and contain no reliable-link protocol.

**Draft requirements:** statements labeled with requirement IDs describe intended
behavior. Their evidence/status is explicit; publication here does not assert they
are implemented or fully qualified. “Must” specifies required behavior within the
stated scope. “Proposed” and “TBD” identify decisions that remain revisable.

**Receiver choices:** fixed timing, streaming timing, and offline equalization are
implementations, not mandatory wire algorithms. A compatible receiver can use a
different algorithm if it observes the same frame acceptance rules.

## Evidence supporting this draft

- [Experiment 0001](../experiments/0001-fsk-baseline.md) supplies independent byte/sample
  vectors and basic noise/filter measurements.
- [Experiment 0002](../experiments/0002-streaming-timing.md) demonstrates streaming
  clock tracking for random payloads, and failure on long constant runs with drift.
- [Experiment 0003](../experiments/0003-acoustic-equalization.md) recovers all 406 bytes
  from one of two operator-supplied radio-speaker recordings after public-sync
  equalization. Both Rust receivers accept both CRCs. The other recording still fails.

This is evidence for feasibility and specific failure modes. It does not establish
reliable bidirectional transfer, Android operation, occupied RF bandwidth, or VARA
performance. The two acoustic recordings are development data, not an unseen test set.

## Change and compatibility rules

The wire document becomes the reference for the existing experimental contract;
experiment notes retain historical methods and results. If source and spec disagree,
record and resolve the discrepancy before claiming conformance.

A change to tones, symbol mapping, framing, training, coding or CRC coverage must
have a distinct experimental wire identity and new vectors before use in shared
tests. Do not silently redefine version `00`, profile `01` or `02`. The allocation
scheme for future identities and production negotiation remains decision D04.
Receiver-only improvements keep the existing wire identity when they accept the
same frames. A document edit alone does not change transmitted bytes.

Draft updates should cite evidence, update implementation status and affected
requirements, and explain compatibility effects. Freezing a supported profile
requires the gates in the validation plan; drafting this specification does not.
Software/spec licensing and the distribution package remain open (D08). This task
creates local documentation; it does not publish a release.
