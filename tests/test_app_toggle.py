"""The toggle state machine: press once to start, press again to stop."""

import threading

import numpy as np
import pytest

from sotto.config import Config

rumps = pytest.importorskip("rumps")  # menu bar deps are macOS-only

from sotto.app import SottoApp  # noqa: E402
from sotto.recorder import SAMPLE_RATE  # noqa: E402


class _FakeRecorder:
    def __init__(self, fail=False):
        self.recording = False
        self.fail = fail
        self.starts = 0

    def start(self):
        if self.fail:
            raise RuntimeError("no microphone")
        self.starts += 1
        self.recording = True

    def stop(self):
        self.recording = False
        return np.zeros(SAMPLE_RATE, dtype=np.float32)  # one second

    def reset(self):
        self.recording = False


class _FakeHud:
    def __init__(self):
        self.shown = []

    def listening(self, language=None):
        self.shown.append(("listening", language))

    def processing(self):
        self.shown.append(("processing", None))

    def loading_model(self):
        self.shown.append(("loading", None))

    def error(self, text, seconds=4.0):
        self.shown.append(("error", text))

    def hide(self):
        self.shown.append(("hide", None))


class _TestApp(SottoApp):
    """Bypasses rumps/AppKit init; `title` shadows rumps' status-bar property."""

    title = None

    def __init__(self, hotkeys=None, mic_fails=False):
        self.config = Config()
        self.hotkeys = hotkeys or {"f13": "zh", "f15": "en"}
        self.recorder = _FakeRecorder(fail=mic_fails)
        self.hud = _FakeHud()
        self.transcriber = _Ready()
        self._busy = False
        self._mic_help_shown = True  # don't open System Settings in a test
        self._toggle_lock = threading.RLock()
        self._active_language = None
        self._auto_stop = None
        self.processed = []
        self.errors = []
        self._done = threading.Event()

    def _process(self, audio, language=None):
        # Runs on the worker thread _stop_dictation spawns.
        self.processed.append((len(audio), language))
        self._busy = False
        self._done.set()

    def wait_for_processing(self) -> None:
        assert self._done.wait(5), "transcription never ran"

    def _report_error(self, title, detail):
        self.errors.append(title)


class _Ready:
    ready = True


def _app(**kwargs):
    return _TestApp(**kwargs)


def test_first_press_starts_second_press_stops():
    app = _app()

    app.on_hotkey("f13")
    assert app.recorder.recording
    assert ("listening", "中文") in app.hud.shown

    app.on_hotkey("f13")
    assert not app.recorder.recording
    app.wait_for_processing()
    assert app.processed == [(SAMPLE_RATE, "zh")]


def test_each_key_dictates_its_own_language():
    app = _app()

    app.on_hotkey("f15")
    app.on_hotkey("f15")

    assert app.hud.shown[0] == ("listening", "English")
    app.wait_for_processing()
    assert app.processed == [(SAMPLE_RATE, "en")]


def test_other_language_key_ends_the_take_in_progress():
    app = _app()

    app.on_hotkey("f13")
    app.on_hotkey("f15")  # stops; the take stays in the language it started in

    assert not app.recorder.recording
    app.wait_for_processing()
    assert app.processed == [(SAMPLE_RATE, "zh")]


def test_press_while_transcribing_is_ignored():
    app = _app()
    app.on_hotkey("f13")
    app.on_hotkey("f13")
    app._busy = True  # transcription still running

    app.on_hotkey("f13")

    assert not app.recorder.recording
    assert app.recorder.starts == 1


def test_short_tap_is_discarded():
    app = _app()
    app.recorder.stop = lambda: np.zeros(10, dtype=np.float32)

    app.on_hotkey("f13")
    app.on_hotkey("f13")

    assert app.processed == []
    assert app.hud.shown[-1] == ("hide", None)


def test_unknown_key_falls_back_to_auto_detect():
    app = _app()

    app.on_hotkey("f19")
    app.on_hotkey("f19")

    app.wait_for_processing()
    assert app.processed == [(SAMPLE_RATE, "auto")]


def test_mic_failure_leaves_no_recording_armed():
    app = _app(mic_fails=True)

    app.on_hotkey("f13")

    assert not app.recorder.recording
    assert app._auto_stop is None
    assert app.errors  # user was told


def test_auto_stop_is_armed_while_recording_and_cancelled_after():
    app = _app()

    app.on_hotkey("f13")
    assert app._auto_stop is not None and app._auto_stop.is_alive()

    app.on_hotkey("f13")
    assert app._auto_stop is None


def test_auto_stop_transcribes_what_was_recorded():
    app = _app()
    app.config.max_duration = 0.05

    app.on_hotkey("f13")
    app._auto_stop.join(2)

    app.wait_for_processing()
    assert not app.recorder.recording
    assert app.processed == [(SAMPLE_RATE, "zh")]


def test_max_duration_zero_disables_the_safety_net():
    app = _app()
    app.config.max_duration = 0

    app.on_hotkey("f13")

    assert app._auto_stop is None
    assert app.recorder.recording


def test_recorder_failing_on_stop_does_not_escape_the_callback():
    """pynput kills its listener if a callback raises, so a failed stop must
    be reported and recovered from, never propagated."""
    app = _app()
    app.on_hotkey("f13")

    def broken_stop():
        raise RuntimeError("PortAudio: device unavailable")

    app.recorder.stop = broken_stop
    app.on_hotkey("f13")  # must not raise

    assert app.errors == ["Dictation key failed"]
    assert not app.recorder.recording
    assert not app._busy
    assert app._auto_stop is None
    assert app._active_language is None

    del app.recorder.stop  # the device is back
    app.on_hotkey("f15")
    assert app.recorder.recording
    assert app.recorder.starts == 2
