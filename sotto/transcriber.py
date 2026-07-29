"""Local speech-to-text with faster-whisper. Everything stays on device."""

import threading

import numpy as np

from .config import Config
from .dictionary import Dictionary


class Transcriber:
    """Lazy wrapper around a faster-whisper model.

    The model (~150 MB for `base`) is downloaded on first use and cached in
    ~/.cache/huggingface. Loading takes a few seconds, so we do it once in a
    background thread at startup.
    """

    def __init__(self, config: Config, dictionary: Dictionary) -> None:
        self._config = config
        self._dictionary = dictionary
        self._model = None
        self._model_lock = threading.Lock()

    @property
    def ready(self) -> bool:
        return self._model is not None

    def preload(self) -> None:
        threading.Thread(target=self._preload_quietly, daemon=True).start()

    def _preload_quietly(self) -> None:
        try:
            self._ensure_model()
        except Exception:
            # No network on first run, most likely. transcribe() will retry
            # and surface the error where the user can see it.
            pass

    def reset(self) -> None:
        """Drop the loaded model (e.g. after the user picks a new size)."""
        with self._model_lock:
            self._model = None

    def _ensure_model(self):
        with self._model_lock:
            if self._model is None:
                from faster_whisper import WhisperModel

                self._model = WhisperModel(
                    self._config.model, device="cpu", compute_type="int8"
                )
            return self._model

    def transcribe(self, audio: np.ndarray) -> str:
        model = self._ensure_model()
        language = None if self._config.language == "auto" else self._config.language
        # Feeding custom terms as the initial prompt biases Whisper toward
        # spelling them correctly (names, jargon, product terms).
        hint = self._dictionary.prompt_hint()
        segments, _info = model.transcribe(
            audio,
            language=language,
            vad_filter=True,
            initial_prompt=hint or None,
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        return self._dictionary.apply(text)
