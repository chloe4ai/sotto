import numpy as np
import pytest

from sotto.recorder import SAMPLE_RATE, Recorder, _resample


def test_resample_noop_at_target_rate():
    audio = np.random.rand(1600).astype(np.float32)
    assert _resample(audio, SAMPLE_RATE, SAMPLE_RATE) is audio


def test_resample_empty():
    audio = np.zeros(0, dtype=np.float32)
    assert len(_resample(audio, 48_000, SAMPLE_RATE)) == 0


def test_resample_48k_to_16k():
    one_second = np.random.rand(48_000).astype(np.float32)
    out = _resample(one_second, 48_000, SAMPLE_RATE)
    assert out.dtype == np.float32
    assert len(out) == SAMPLE_RATE


def test_resample_preserves_signal_shape():
    # A slow sine wave should survive resampling nearly unchanged.
    t = np.linspace(0, 1, 44_100, endpoint=False)
    sine = np.sin(2 * np.pi * 5 * t).astype(np.float32)
    out = _resample(sine, 44_100, SAMPLE_RATE)
    expected = np.sin(2 * np.pi * 5 * np.linspace(0, 1, len(out), endpoint=False))
    assert np.abs(out - expected).max() < 0.01


class _BrokenStream:
    def __init__(self):
        self.closed = False

    def stop(self):
        raise RuntimeError("device vanished")

    def abort(self, ignore_errors=True):
        pass

    def close(self, ignore_errors=True):
        self.closed = True


def test_reset_recovers_from_a_failed_stop():
    rec = Recorder()
    stream = _BrokenStream()
    rec._stream = stream
    rec._frames = [np.zeros((160, 1), dtype=np.float32)]

    with pytest.raises(RuntimeError):
        rec.stop()
    assert rec.recording  # the half-open stream would block the next take

    rec.reset()
    assert not rec.recording
    assert stream.closed
    assert len(rec.stop()) == 0  # nothing stale left behind
