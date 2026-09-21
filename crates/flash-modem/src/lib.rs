//! Experimental offline audio modem. See docs/experiments/0001-fsk-baseline.md.
//! No platform I/O, clock tracking, FEC, ARQ, or production protocol promises.

use std::f64::consts::TAU;

pub mod streaming;

pub const SAMPLE_RATE: usize = 48_000;
pub const MAX_PAYLOAD: usize = 1024;
pub const MAX_SAMPLES: usize = SAMPLE_RATE * 10;
pub const SYNC: [u8; 4] = [0xd3, 0x91, 0xc5, 0xa7];
pub const PREAMBLE_BYTES: usize = 16;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Profile {
    Fsk2,
    Fsk4,
}

impl Profile {
    pub fn from_name(name: &str) -> Option<Self> {
        match name {
            "fsk2" => Some(Self::Fsk2),
            "fsk4" => Some(Self::Fsk4),
            _ => None,
        }
    }

    pub fn id(self) -> u8 {
        match self {
            Self::Fsk2 => 1,
            Self::Fsk4 => 2,
        }
    }

    pub fn bits_per_symbol(self) -> usize {
        match self {
            Self::Fsk2 => 1,
            Self::Fsk4 => 2,
        }
    }

    pub fn samples_per_symbol(self) -> usize {
        40 * self.bits_per_symbol()
    }

    pub fn tones(self) -> &'static [usize] {
        match self {
            Self::Fsk2 => &[1200, 2400],
            Self::Fsk4 => &[900, 1500, 2100, 2700],
        }
    }
}

/// CRC-32/ISO-HDLC (check value for "123456789": 0xcbf43926).
pub fn crc32(bytes: &[u8]) -> u32 {
    let mut crc = !0u32;
    for &byte in bytes {
        crc ^= u32::from(byte);
        for _ in 0..8 {
            crc = (crc >> 1) ^ (0xedb8_8320 & 0u32.wrapping_sub(crc & 1));
        }
    }
    !crc
}

/// Preamble | sync | version, profile, BE length | header CRC | payload | body CRC.
/// Both CRCs are BE on the wire; body CRC covers header fields AND payload.
pub fn frame(payload: &[u8], profile: Profile) -> Result<Vec<u8>, &'static str> {
    if payload.len() > MAX_PAYLOAD {
        return Err("payload exceeds 1024 bytes");
    }
    let len = (payload.len() as u16).to_be_bytes();
    let header = [0, profile.id(), len[0], len[1]];
    let mut output = vec![0x55; PREAMBLE_BYTES];
    output.extend(SYNC);
    output.extend(header);
    output.extend(crc32(&header).to_be_bytes());
    output.extend(payload);
    let mut protected = header.to_vec();
    protected.extend(payload);
    output.extend(crc32(&protected).to_be_bytes());
    Ok(output)
}

pub fn modulate(payload: &[u8], profile: Profile) -> Result<Vec<f32>, &'static str> {
    let bytes = frame(payload, profile)?;
    let bits = profile.bits_per_symbol();
    let sps = profile.samples_per_symbol();
    let mut phase = 0.0;
    let mut samples = Vec::with_capacity(bytes.len() * 8 / bits * sps);
    for byte in bytes {
        for shift in (0..8).step_by(bits).rev() {
            let tone = ((byte >> shift) & ((1 << bits) - 1)) as usize;
            let step = TAU * profile.tones()[tone] as f64 / SAMPLE_RATE as f64;
            for _ in 0..sps {
                samples.push((0.7 * f64::sin(phase)) as f32);
                phase = (phase + step) % TAU;
            }
        }
    }
    Ok(samples)
}

fn gcd(mut a: usize, mut b: usize) -> usize {
    while b != 0 {
        (a, b) = (b, a % b);
    }
    a
}

/// Noncoherent rectangular matched filters at every possible sample offset.
/// Sliding quadrature sums keep the offline search linear in recording length.
fn decisions(samples: &[f32], profile: Profile) -> Vec<u8> {
    let window = profile.samples_per_symbol();
    let count = samples.len() + 1 - window;
    let mut best = vec![0.0f64; count];
    let mut symbols = vec![0; count];
    for (tone_index, &frequency) in profile.tones().iter().enumerate() {
        let period = SAMPLE_RATE / gcd(SAMPLE_RATE, frequency);
        let oscillator: Vec<_> = (0..period)
            .map(|i| (TAU * frequency as f64 * i as f64 / SAMPLE_RATE as f64).sin_cos())
            .collect();
        let (mut re, mut im) = (0.0, 0.0);
        for (i, &sample) in samples.iter().enumerate() {
            let (sin, cos) = oscillator[i % period];
            re += f64::from(sample) * cos;
            im += f64::from(sample) * sin;
            if i >= window {
                let old = i - window;
                let (sin, cos) = oscillator[old % period];
                re -= f64::from(samples[old]) * cos;
                im -= f64::from(samples[old]) * sin;
            }
            if i + 1 >= window {
                let start = i + 1 - window;
                let power = re * re + im * im;
                if power > best[start] {
                    best[start] = power;
                    symbols[start] = tone_index as u8;
                }
            }
        }
    }
    symbols
}

fn unpack(bits: &[u8]) -> Vec<u8> {
    bits.chunks_exact(8)
        .map(|byte| byte.iter().fold(0, |acc, bit| (acc << 1) | bit))
        .collect()
}

fn parse_body(bits: &[u8], profile: Profile) -> Option<Vec<u8>> {
    if bits.len() < 96 {
        return None;
    }
    let header = unpack(&bits[..64]);
    if header[0] != 0 || header[1] != profile.id() {
        return None;
    }
    if crc32(&header[..4]).to_be_bytes() != header[4..8] {
        return None;
    }
    let length = u16::from_be_bytes([header[2], header[3]]) as usize;
    if length > MAX_PAYLOAD || bits.len() < (12 + length) * 8 {
        return None;
    }
    let body = unpack(&bits[64..(12 + length) * 8]);
    let mut protected = header[..4].to_vec();
    protected.extend(&body[..length]);
    (crc32(&protected).to_be_bytes() == body[length..]).then(|| body[..length].to_vec())
}

/// Decode the first valid candidate in an offline capture of at most 10 seconds.
/// Only the profile is supplied: no known payload, frame offset, or length.
/// Exhaustively tries fixed symbol phases, requiring exact sync and both CRCs.
/// This is a reference detector, not a streaming timing-recovery algorithm.
pub fn demodulate(samples: &[f32], profile: Profile) -> Result<Option<Vec<u8>>, &'static str> {
    if samples.len() > MAX_SAMPLES {
        return Err("capture exceeds 10 seconds");
    }
    if samples.iter().any(|v| !v.is_finite()) {
        return Err("capture contains non-finite samples");
    }
    let sps = profile.samples_per_symbol();
    if samples.len() < sps {
        return Ok(None);
    }
    let symbols = decisions(samples, profile);
    let sync = u32::from_be_bytes(SYNC);
    for offset in 0..sps.min(symbols.len()) {
        let mut bits = Vec::with_capacity(samples.len() / 40);
        for &symbol in symbols[offset..].iter().step_by(sps) {
            for shift in (0..profile.bits_per_symbol()).rev() {
                bits.push((symbol >> shift) & 1);
            }
        }
        let mut word = 0u32;
        for (i, &bit) in bits.iter().enumerate() {
            word = (word << 1) | u32::from(bit);
            if i >= 31
                && word == sync
                && let Some(payload) = parse_body(&bits[i + 1..], profile)
            {
                return Ok(Some(payload));
            }
        }
    }
    Ok(None)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn standard_crc_check_and_payload_limit() {
        assert_eq!(crc32(b"123456789"), 0xcbf4_3926);
        assert_eq!(crc32(b""), 0);
        assert!(frame(&vec![0; MAX_PAYLOAD + 1], Profile::Fsk2).is_err());
    }

    #[test]
    fn acquisition_with_unknown_delay_gain_polarity_and_trailing_audio() {
        for profile in [Profile::Fsk2, Profile::Fsk4] {
            let payload: Vec<_> = (0..=255).collect();
            let tx = modulate(&payload, profile).unwrap();
            let mut rx = vec![0.0; 719];
            rx.extend(tx.iter().map(|v| -v * 0.13));
            rx.extend(vec![0.0; 701]);
            assert_eq!(demodulate(&rx, profile), Ok(Some(payload)));
        }
    }

    #[test]
    fn empty_and_maximum_payloads() {
        for profile in [Profile::Fsk2, Profile::Fsk4] {
            for payload in [vec![], vec![0xa6; MAX_PAYLOAD]] {
                let tx = modulate(&payload, profile).unwrap();
                assert_eq!(demodulate(&tx, profile), Ok(Some(payload)));
            }
        }
    }

    #[test]
    fn rejects_corrupt_header_and_payload() {
        let bytes = frame(b"hello", Profile::Fsk2).unwrap();
        let body = &bytes[PREAMBLE_BYTES + SYNC.len()..];
        let to_bits = |bytes: &[u8]| -> Vec<u8> {
            bytes
                .iter()
                .flat_map(|byte| (0..8).rev().map(move |i| (byte >> i) & 1))
                .collect()
        };
        assert_eq!(
            parse_body(&to_bits(body), Profile::Fsk2),
            Some(b"hello".to_vec())
        );
        for index in 0..body.len() {
            let mut corrupt = body.to_vec();
            corrupt[index] ^= 1;
            assert_eq!(parse_body(&to_bits(&corrupt), Profile::Fsk2), None);
        }
    }

    #[test]
    fn silence_truncation_and_invalid_samples_do_not_decode() {
        assert_eq!(demodulate(&vec![0.0; 4800], Profile::Fsk2), Ok(None));
        let tx = modulate(b"hello", Profile::Fsk2).unwrap();
        assert_eq!(demodulate(&tx[..tx.len() - 400], Profile::Fsk2), Ok(None));
        assert!(demodulate(&[f32::NAN], Profile::Fsk2).is_err());
        assert!(demodulate(&vec![0.0; MAX_SAMPLES + 1], Profile::Fsk2).is_err());
    }
}
