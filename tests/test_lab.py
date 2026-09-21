import unittest
import json

import numpy as np

from lab.channel import CHANNELS, Channel, SAMPLE_RATE
from lab.modem import PROFILES, ROOT, decode, encode, invoke, reference_audio, reference_frame
from lab.__main__ import wilson


class ModemTests(unittest.TestCase):
    def test_saved_wire_vectors(self):
        fixture = json.loads((ROOT / "docs/experiments/results/0001-vectors.json").read_text())
        for vector in fixture["vectors"]:
            payload = bytes.fromhex(vector["payload_hex"])
            expected = bytes.fromhex(vector["frame_hex"])
            self.assertEqual(reference_frame(payload, vector["profile"]), expected)
            self.assertEqual(invoke("frame", vector["profile"], payload), expected)

    def test_independent_wire_and_sample_vectors(self):
        for profile in PROFILES:
            for payload in [b"", b"123456789", bytes(range(256))]:
                self.assertEqual(invoke("frame", profile, payload), reference_frame(payload, profile))
                np.testing.assert_allclose(encode(payload, profile), reference_audio(payload, profile), atol=2e-6)

    def test_independent_transmitter_random_phase_and_symbol_offset(self):
        rng = np.random.default_rng(7)
        for profile in PROFILES:
            for _ in range(5):
                payload = rng.bytes(64)
                tx = reference_audio(payload, profile, initial_phase=rng.uniform(0, 2 * np.pi))
                rx, _ = CHANNELS["awgn"].apply(tx, 18, rng)
                self.assertEqual(decode(rx, profile), payload)

    def test_noise_only_false_positives_and_wrong_profile(self):
        rng = np.random.default_rng(11)
        for profile in PROFILES:
            for _ in range(5):
                self.assertIsNone(decode(rng.normal(0, 1, SAMPLE_RATE // 2), profile))
        self.assertIsNone(decode(encode(b"wrong profile", "fsk2"), "fsk4"))

    def test_known_audio_conditions(self):
        for profile in PROFILES:
            payload = bytes(range(256))
            tx = encode(payload, profile)
            for channel in ["voice", "clip", "clock+100", "clock-100", "erase50"]:
                rx, _ = CHANNELS[channel].apply(tx, None, np.random.default_rng(8))
                self.assertEqual(decode(rx, profile), payload, (profile, channel))
            rx, _ = CHANNELS["erase150"].apply(tx, None, np.random.default_rng(8))
            self.assertIsNone(decode(rx, profile))

    def test_invalid_cli_input_is_an_error_not_packet_loss(self):
        with self.assertRaises(RuntimeError):
            invoke("decode", "fsk2", b"x")
        with self.assertRaises(RuntimeError):
            decode(np.array([np.nan]), "fsk2")
        with self.assertRaises(RuntimeError):
            encode(bytes(1025), "fsk2")


class ChannelTests(unittest.TestCase):
    def test_snr_noise_scaling_and_repeatability(self):
        tx = np.sin(2 * np.pi * 1200 * np.arange(SAMPLE_RATE * 2) / SAMPLE_RATE)
        rx, metadata = Channel().apply(tx, 0, np.random.default_rng(33))
        again, _ = Channel().apply(tx, 0, np.random.default_rng(33))
        np.testing.assert_array_equal(rx, again)
        clean = np.pad(tx, (metadata["delay_samples"], SAMPLE_RATE // 10))
        variance = np.mean((rx - clean) ** 2)
        self.assertAlmostEqual(variance / metadata["noise_variance"], 1, delta=0.02)
        self.assertAlmostEqual(metadata["noise_variance"], 4.0, places=8)

    def test_clock_direction_and_length(self):
        tx = np.ones(SAMPLE_RATE)
        for ppm in [-1000, 1000]:
            rx, metadata = Channel(clock_ppm=ppm).apply(tx, None, np.random.default_rng(2))
            expected = SAMPLE_RATE + ppm * SAMPLE_RATE // 1_000_000 + metadata["delay_samples"] + SAMPLE_RATE // 10
            self.assertEqual(len(rx), expected)

    def test_wilson_does_not_claim_certainty_at_endpoints(self):
        self.assertGreater(wilson(0, 40)[1], 0.08)
        self.assertLess(wilson(40, 40)[0], 0.92)


if __name__ == "__main__":
    unittest.main()
