//! Experiment 0002: bounded streaming acquisition and decision-directed timing.
//! Shares experiment 0001's wire format; never searches using the expected payload.

use std::collections::VecDeque;

use crate::{MAX_PAYLOAD, Profile, SAMPLE_RATE, SYNC, crc32, gcd, parse_body, unpack};

#[derive(Clone, Copy, Default)]
struct Energy {
    power: [f64; 4],
    symbol: u8,
    confidence: f64,
}

struct ToneBank {
    oscillators: Vec<Vec<(f64, f64)>>,
    sums: Vec<(f64, f64)>,
    samples: VecDeque<f64>,
    window: usize,
    count: usize,
}

impl ToneBank {
    fn new(profile: Profile) -> Self {
        Self {
            oscillators: profile
                .tones()
                .iter()
                .map(|&f| {
                    (0..SAMPLE_RATE / gcd(SAMPLE_RATE, f))
                        .map(|i| {
                            (std::f64::consts::TAU * f as f64 * i as f64 / SAMPLE_RATE as f64)
                                .sin_cos()
                        })
                        .collect()
                })
                .collect(),
            sums: vec![(0.0, 0.0); profile.tones().len()],
            samples: VecDeque::with_capacity(profile.samples_per_symbol() + 1),
            window: profile.samples_per_symbol(),
            count: 0,
        }
    }

    fn push(&mut self, sample: f32) -> Option<Energy> {
        let old = if self.samples.len() == self.window {
            self.samples.pop_front()
        } else {
            None
        };
        self.samples.push_back(f64::from(sample));
        let mut result = Energy::default();
        for (tone, (osc, (re, im))) in self.oscillators.iter().zip(&mut self.sums).enumerate() {
            let (sin, cos) = osc[self.count % osc.len()];
            *re += f64::from(sample) * cos;
            *im += f64::from(sample) * sin;
            if let Some(old) = old {
                let (sin, cos) = osc[(self.count - self.window) % osc.len()];
                *re -= old * cos;
                *im -= old * sin;
            }
            result.power[tone] = *re * *re + *im * *im;
        }
        self.count += 1;
        if self.count < self.window {
            return None;
        }
        let mut best = 0.0;
        let mut second = 0.0;
        for (index, &power) in result.power[..self.sums.len()].iter().enumerate() {
            if power > best {
                second = best;
                best = power;
                result.symbol = index as u8;
            } else if power > second {
                second = power;
            }
        }
        result.confidence = (best - second) / (best + second + 1e-30);
        Some(result)
    }
}

struct Acquisition {
    until: usize,
    best_end: usize,
    score: f64,
}

struct Packet {
    next: f64,
    period: f64,
    bits: Vec<u8>,
    expected_bits: Option<usize>,
}

/// An event is emitted only after both header and body CRC verification.
#[derive(Debug, PartialEq)]
pub struct DecodedFrame {
    pub payload: Vec<u8>,
    /// Input samples consumed at emission, including synchronization lookahead.
    pub samples_seen: usize,
    /// Diagnostic loop estimate; not a calibrated oscillator measurement.
    pub timing_ppm: f64,
}

/// Incremental receiver with bounded internal history, independent of chunk sizes.
/// Commits to one sync phase and tracks symbol timing; does not use CRCs to choose
/// between timing hypotheses. There is no FEC, frequency tracker, or live audio I/O.
pub struct StreamingDecoder {
    profile: Profile,
    bank: ToneBank,
    history: VecDeque<Energy>,
    history_start: usize,
    history_limit: usize,
    words: Vec<u32>,
    acquisition: Option<Acquisition>,
    packet: Option<Packet>,
}

impl StreamingDecoder {
    pub fn new(profile: Profile) -> Self {
        let sps = profile.samples_per_symbol();
        let history_limit = (32 / profile.bits_per_symbol() + 4) * sps + 8;
        Self {
            profile,
            bank: ToneBank::new(profile),
            history: VecDeque::with_capacity(history_limit + 1),
            history_start: 0,
            history_limit,
            words: vec![0; sps],
            acquisition: None,
            packet: None,
        }
    }

    fn at(&self, start: usize) -> Energy {
        self.history[start - self.history_start]
    }

    fn power_at(&self, start: f64, tone: usize) -> f64 {
        let low = start.floor() as usize;
        let fraction = start - low as f64;
        self.at(low).power[tone] * (1.0 - fraction) + self.at(low + 1).power[tone] * fraction
    }

    /// Invalid chunks are rejected before any state changes; empty chunks are legal.
    pub fn push(&mut self, samples: &[f32]) -> Result<Vec<DecodedFrame>, &'static str> {
        if samples.iter().any(|s| !s.is_finite()) {
            return Err("capture contains non-finite samples");
        }
        let mut frames = Vec::new();
        for &sample in samples {
            let Some(energy) = self.bank.push(sample) else {
                continue;
            };
            let start = self.bank.count - self.profile.samples_per_symbol();
            self.history.push_back(energy);
            if self.history.len() > self.history_limit {
                self.history.pop_front();
                self.history_start += 1;
            }
            if self.packet.is_none() {
                self.search(start, energy);
            }
            if let Some(frame) = self.track(start) {
                frames.push(frame);
            }
        }
        Ok(frames)
    }

    fn search(&mut self, start: usize, energy: Energy) {
        let sps = self.profile.samples_per_symbol();
        let bps = self.profile.bits_per_symbol();
        let word = &mut self.words[start % sps];
        *word = (*word << bps) | u32::from(energy.symbol);
        let span = (32 / bps - 1) * sps;
        if start >= span && *word == u32::from_be_bytes(SYNC) {
            let score = (0..32 / bps)
                .map(|i| self.at(start - i * sps).confidence)
                .sum();
            if let Some(acquisition) = &mut self.acquisition {
                if score > acquisition.score {
                    acquisition.best_end = start;
                    acquisition.score = score;
                }
            } else {
                self.acquisition = Some(Acquisition {
                    until: start + sps,
                    best_end: start,
                    score,
                });
            }
        }
        if self.acquisition.as_ref().is_some_and(|a| start >= a.until) {
            let acquisition = self.acquisition.take().unwrap();
            self.packet = Some(Packet {
                next: (acquisition.best_end + sps) as f64,
                period: sps as f64,
                bits: Vec::with_capacity((MAX_PAYLOAD + 12) * 8),
                expected_bits: None,
            });
        }
    }

    fn reset_search(&mut self) {
        self.packet = None;
        self.acquisition = None;
        self.words.fill(0);
    }

    fn track(&mut self, available: usize) -> Option<DecodedFrame> {
        let nominal = self.profile.samples_per_symbol() as f64;
        let delta = nominal * 0.2;
        let packet = self.packet.as_ref()?;
        // One sample for interpolation. This finite lookahead is part of latency.
        if available < (packet.next + delta).floor() as usize + 1 {
            return None;
        }
        let symbol = self.at(packet.next.round() as usize).symbol;
        let early = self.power_at(packet.next - delta, symbol as usize);
        let late = self.power_at(packet.next + delta, symbol as usize);
        let error = (late - early) / (late + early + 1e-30);
        let packet = self.packet.as_mut().unwrap();
        // Second-order early/late loop, bounded to +/-5000 ppm. Experimental gains.
        packet.period =
            (packet.period + 0.0002 * nominal * error).clamp(nominal * 0.995, nominal * 1.005);
        packet.next += packet.period + 0.08 * nominal * error;
        for bit in (0..self.profile.bits_per_symbol()).rev() {
            packet.bits.push((symbol >> bit) & 1);
        }
        if packet.bits.len() == 64 {
            let header = unpack(&packet.bits);
            let length = u16::from_be_bytes([header[2], header[3]]) as usize;
            if header[0] != 0
                || header[1] != self.profile.id()
                || length > MAX_PAYLOAD
                || crc32(&header[..4]).to_be_bytes() != header[4..8]
            {
                self.reset_search();
                return None;
            }
            packet.expected_bits = Some((length + 12) * 8);
        }
        if packet.expected_bits == Some(packet.bits.len()) {
            let event = parse_body(&packet.bits, self.profile).map(|payload| DecodedFrame {
                payload,
                samples_seen: self.bank.count,
                timing_ppm: (packet.period / nominal - 1.0) * 1e6,
            });
            self.reset_search();
            return event;
        }
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::modulate;

    fn run(samples: &[f32], profile: Profile, chunk: usize) -> Vec<DecodedFrame> {
        let mut decoder = StreamingDecoder::new(profile);
        let mut events = Vec::new();
        for samples in samples.chunks(chunk) {
            events.extend(decoder.push(samples).unwrap());
            assert!(decoder.history.len() <= decoder.history_limit);
            assert!(decoder.bank.samples.len() <= profile.samples_per_symbol());
        }
        events
    }

    #[test]
    fn chunk_boundaries_do_not_change_events_and_multiple_packets_work() {
        for profile in [Profile::Fsk2, Profile::Fsk4] {
            let payloads = [b"first packet".to_vec(), (0..=255).collect()];
            let mut samples = vec![0.0; 319];
            for payload in &payloads {
                samples.extend(modulate(payload, profile).unwrap());
                samples.extend(vec![0.0; 1000]);
            }
            let reference = run(&samples, profile, 1);
            assert_eq!(
                reference
                    .iter()
                    .map(|e| e.payload.clone())
                    .collect::<Vec<_>>(),
                payloads
            );
            for chunk in [7, 127, 1024, samples.len()] {
                assert_eq!(run(&samples, profile, chunk), reference);
            }
        }
    }

    #[test]
    fn noise_silence_truncation_and_invalid_input() {
        let mut decoder = StreamingDecoder::new(Profile::Fsk4);
        assert!(decoder.push(&[]).unwrap().is_empty());
        assert!(decoder.push(&[f32::INFINITY]).is_err());
        assert_eq!(decoder.bank.count, 0);
        assert!(decoder.push(&vec![0.0; SAMPLE_RATE]).unwrap().is_empty());
        let tx = modulate(b"truncated", Profile::Fsk4).unwrap();
        assert!(run(&tx[..tx.len() - 400], Profile::Fsk4, 127).is_empty());
    }
}
