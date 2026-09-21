import subprocess
import unittest

from lab.radio import keyed_play


class FakePort:
    def __init__(self, fail_open=False):
        self.is_open = False
        self.rts = True
        self.dtr = True
        self.fail_open = fail_open
        self.closed = False

    def open(self):
        assert not self.rts and not self.dtr
        if self.fail_open:
            raise OSError("cannot open")
        self.is_open = True

    def close(self):
        assert not self.rts
        self.closed = True
        self.is_open = False


class RadioTests(unittest.TestCase):
    def test_ptt_cleanup_success_timeout_and_worker_error(self):
        for failure in (None, subprocess.TimeoutExpired("audio", 5), subprocess.CalledProcessError(1, "audio"), KeyboardInterrupt()):
            port = FakePort()
            def worker(command, **kwargs):
                self.assertTrue(port.rts)
                self.assertEqual(kwargs["timeout"], 5)
                if failure is not None:
                    raise failure
                return subprocess.CompletedProcess(command, 0, stdout='{}')
            if failure is None:
                self.assertEqual(keyed_play(port, ["audio"], 2, sleep=lambda _: None, run=worker), '{}')
            else:
                with self.assertRaises(type(failure)):
                    keyed_play(port, ["audio"], 2, sleep=lambda _: None, run=worker)
            self.assertFalse(port.rts)
            self.assertTrue(port.closed)

    def test_invalid_duration_and_failed_open_never_key(self):
        port = FakePort()
        with self.assertRaises(ValueError):
            keyed_play(port, [], 9)
        self.assertFalse(port.is_open)
        port = FakePort(fail_open=True)
        with self.assertRaises(OSError):
            keyed_play(port, [], 1)
        self.assertFalse(port.rts)


if __name__ == "__main__":
    unittest.main()
