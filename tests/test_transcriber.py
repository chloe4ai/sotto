"""The per-key language has to reach Whisper — that's the whole point of
having one key per language."""

import numpy as np

from sotto.config import Config
from sotto.dictionary import Dictionary
from sotto.transcriber import Transcriber


class _Segment:
    def __init__(self, text):
        self.text = text


class _FakeModel:
    def __init__(self):
        self.calls = []

    def transcribe(self, audio, **kwargs):
        self.calls.append(kwargs)
        return [_Segment("hello")], None


def _transcriber(**config_kwargs):
    t = Transcriber(Config(**config_kwargs), Dictionary())
    t._model = _FakeModel()
    return t


def test_hotkey_language_is_passed_through():
    t = _transcriber()
    assert t.transcribe(np.zeros(10, dtype=np.float32), language="zh") == "hello"
    assert t._model.calls[0]["language"] == "zh"


def test_auto_means_let_whisper_detect():
    t = _transcriber()
    t.transcribe(np.zeros(10, dtype=np.float32), language="auto")
    assert t._model.calls[0]["language"] is None


def test_falls_back_to_configured_language():
    t = _transcriber(language="ja")
    t.transcribe(np.zeros(10, dtype=np.float32))
    assert t._model.calls[0]["language"] == "ja"


def test_task_still_honoured():
    t = _transcriber(task="translate")
    t.transcribe(np.zeros(10, dtype=np.float32), language="zh")
    assert t._model.calls[0]["task"] == "translate"
