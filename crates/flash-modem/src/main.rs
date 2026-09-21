use flash_modem::streaming::StreamingDecoder;
use flash_modem::{MAX_PAYLOAD, MAX_SAMPLES, Profile, demodulate, frame, modulate};
use std::io::{self, Read, Write};

fn run() -> Result<bool, String> {
    let args: Vec<_> = std::env::args().collect();
    if !(args.len() == 3 || (args.len() == 4 && args[1] == "decode-stream"))
        || !["encode", "decode", "decode-stream", "frame"].contains(&args[1].as_str())
    {
        return Err("usage: flash-modem <encode|decode|decode-stream|frame> <fsk2|fsk4> [stream-chunk-samples]\nstdin/stdout: payload bytes or mono 48000 Hz f32le audio; decode exit 2 = no frame".into());
    }
    let profile = Profile::from_name(&args[2]).ok_or("unknown profile")?;
    let limit = if args[1].starts_with("decode") {
        MAX_SAMPLES * 4
    } else {
        MAX_PAYLOAD
    };
    let mut input = Vec::new();
    io::stdin()
        .take((limit + 1) as u64)
        .read_to_end(&mut input)
        .map_err(|e| e.to_string())?;
    if input.len() > limit {
        return Err("input exceeds experiment size limit".into());
    }
    let output = match args[1].as_str() {
        "frame" => frame(&input, profile)?,
        "encode" => modulate(&input, profile)?
            .iter()
            .flat_map(|v| v.to_le_bytes())
            .collect(),
        "decode" | "decode-stream" => {
            if !input.len().is_multiple_of(4) {
                return Err("f32le input must contain complete 4-byte samples".into());
            }
            let samples: Vec<_> = input
                .chunks_exact(4)
                .map(|b| f32::from_le_bytes(b.try_into().unwrap()))
                .collect();
            let decoded = if args[1] == "decode-stream" {
                let chunk: usize = args
                    .get(3)
                    .map_or(Ok(127), |v| v.parse())
                    .map_err(|_| "invalid chunk size")?;
                if chunk == 0 {
                    return Err("chunk size must be positive".into());
                }
                let mut decoder = StreamingDecoder::new(profile);
                let mut first = None;
                for block in samples.chunks(chunk) {
                    let events = decoder.push(block)?;
                    if first.is_none() {
                        first = events.into_iter().next().map(|e| e.payload);
                    }
                }
                first
            } else {
                demodulate(&samples, profile)?
            };
            match decoded {
                Some(payload) => payload,
                None => return Ok(false),
            }
        }
        _ => unreachable!(),
    };
    io::stdout().write_all(&output).map_err(|e| e.to_string())?;
    Ok(true)
}

fn main() {
    match run() {
        Ok(true) => (),
        Ok(false) => std::process::exit(2),
        Err(error) => {
            eprintln!("{error}");
            std::process::exit(1);
        }
    }
}
