import subprocess
import unittest

import numpy as np

from lab.channel import Channel, SAMPLE_RATE
from lab.modem import BINARY, PROFILES, decode, reference_audio


class StreamingTests(unittest.TestCase):
    def test_long_packets_clock_mismatch_and_unknown_carrier_phase(self):
        for profile in PROFILES:
            for ppm in (-2000, 0, 2000):
                payload = np.random.default_rng(31).bytes(1024)
                tx = reference_audio(payload, profile, initial_phase=1.71)
                rx, _ = Channel(clock_ppm=ppm).apply(tx, 18, np.random.default_rng(2))
                self.assertEqual(decode(rx, profile, "stream"), payload, (profile, ppm))

    def test_empty_constant_and_short_payloads(self):
        for profile in PROFILES:
            for payload in (b"", b"a", bytes(1024), b"\xff" * 1024):
                tx = reference_audio(payload, profile, initial_phase=0.77)
                # Receiver has a documented finite lookahead after the final symbol.
                self.assertEqual(decode(np.pad(tx, (193, 100)), profile, "stream"), payload)

    def test_noise_and_corruption_rejected_then_reacquisition(self):
        for profile in PROFILES:
            noise = np.random.default_rng(17).normal(0, 0.1, SAMPLE_RATE)
            self.assertIsNone(decode(noise, profile, "stream"))
            bad = reference_audio(b"damaged", profile)
            # Remove an interior payload byte, retaining total duration and header.
            bad[28 * 8 * 40:29 * 8 * 40] = 0
            good = reference_audio(b"next packet", profile)
            capture = np.concatenate([noise, bad, np.zeros(1000), good, np.zeros(100)])
            self.assertEqual(decode(capture, profile, "stream"), b"next packet")

    def test_capture_cli_chunk_invariance_and_invalid_chunk(self):
        tx = np.pad(reference_audio(b"chunks", "fsk4"), (13, 100)).tobytes()
        for chunk in (1, 17, 127, 1024):
            result = subprocess.run([str(BINARY), "decode-stream", "fsk4", str(chunk)], input=tx, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, b"chunks")
        result = subprocess.run([str(BINARY), "decode-stream", "fsk4", "0"], input=tx, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 1)


if __name__ == "__main__":
    unittest.main()
