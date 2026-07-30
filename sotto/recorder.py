"""Microphone capture. Delivers 16 kHz mono float32, which is what Whisper
expects. Devices that refuse a 16 kHz stream (some Bluetooth headsets and
webcams) are recorded at their native rate and resampled on stop."""

import threading

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16_000


def _resample(audio: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    if src_rate == dst_rate or len(audio) == 0:
        return audio
    n = int(round(len(audio) * dst_rate / src_rate))
    x_src = np.linspace(0.0, 1.0, num=len(audio), endpoint=False)
    x_dst = np.linspace(0.0, 1.0, num=n, endpoint=False)
    return np.interp(x_dst, x_src, audio).astype(np.float32)


class Recorder:
    def __init__(self) -> None:
        self._frames: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._rate = SAMPLE_RATE
        self._lock = threading.Lock()

    @property
    def recording(self) -> bool:
        return self._stream is not None

    def start(self) -> None:
        with self._lock:
            if self._stream is not None:
                return
            self._frames = []
            self._stream, self._rate = self._open_stream()
            self._stream.start()

    def _open_stream(self) -> tuple[sd.InputStream, int]:
        try:
            return self._stream_at(SAMPLE_RATE), SAMPLE_RATE
        except sd.PortAudioError:
            # The device may simply not support 16 kHz. Retry at its native
            # rate; if that fails too (usually missing mic permission or no
            # input device), let the original-style error propagate.
            device_rate = int(
                sd.query_devices(kind="input")["default_samplerate"]
            )
            if device_rate == SAMPLE_RATE:
                raise
            return self._stream_at(device_rate), device_rate

    def _stream_at(self, rate: int) -> sd.InputStream:
        return sd.InputStream(
            samplerate=rate,
            channels=1,
            dtype="float32",
            callback=self._on_audio,
        )

    def _on_audio(self, indata, frames, time, status) -> None:
        self._frames.append(indata.copy())

    def stop(self) -> np.ndarray:
        """Stop capturing and return the audio as 16 kHz 1-D float32."""
        with self._lock:
            if self._stream is None:
                return np.zeros(0, dtype=np.float32)
            self._stream.stop()
            self._stream.close()
            self._stream = None
            if not self._frames:
                return np.zeros(0, dtype=np.float32)
            audio = np.concatenate(self._frames)[:, 0]
            self._frames = []
            return _resample(audio, self._rate, SAMPLE_RATE)
