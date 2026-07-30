import numpy as np

from sotto.recorder import SAMPLE_RATE, _resample


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
