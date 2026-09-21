import unittest

import numpy as np
from scipy import signal

from lab.modem import decode, reference_audio
from lab.recording import equalize_public_sync


class RecordingTests(unittest.TestCase):
    @staticmethod
    def distorted(payload, phase=0):
        # A strong delayed, inverted copy creates a frequency-selective path.
        impulse = np.r_[1.0, np.zeros(23), -0.95]
        tx = reference_audio(payload, "fsk4", initial_phase=phase)
        return -0.13 * np.pad(signal.lfilter(impulse, [1], tx), (719, 1000))

    def test_unrelated_payloads_recovered_through_selective_channel(self):
        for seed, phase in ((11, 0), (12, 0.77), (13, 1.71)):
            payload = np.random.default_rng(seed).bytes(256)
            rx = self.distorted(payload, phase)
            equalized, _, _ = equalize_public_sync(rx)
            self.assertEqual(decode(equalized, "fsk4"), payload)
            if seed == 11:
                self.assertIsNone(decode(rx, "fsk4"))
                self.assertEqual(decode(equalized, "fsk4", "stream"), payload)

    def test_filter_training_is_independent_of_payload(self):
        fits = []
        for seed in (21, 22):
            rx = self.distorted(np.random.default_rng(seed).bytes(256))
            _, weights, report = equalize_public_sync(rx)
            fits.append((weights, report))
        np.testing.assert_allclose(fits[0][0], fits[1][0], rtol=0, atol=1e-12)
        self.assertEqual(fits[0][1]["candidate_frame_origin_seconds"],
                         fits[1][1]["candidate_frame_origin_seconds"])
        self.assertFalse(fits[0][1]["expected_payload_used"])

    def test_payload_damage_still_rejected(self):
        rx = self.distorted(np.random.default_rng(11).bytes(256))
        rx[15000:18000] = 0  # Well after the training prefix, inside the payload.
        equalized, _, _ = equalize_public_sync(rx)
        for receiver in ("fixed", "stream"):
            self.assertIsNone(decode(equalized, "fsk4", receiver))

    def test_invalid_and_empty_signal_rejected(self):
        for samples in (np.zeros(100), np.zeros(10000), np.full(10000, np.nan)):
            with self.assertRaises(ValueError):
                equalize_public_sync(samples)


if __name__ == "__main__":
    unittest.main()
