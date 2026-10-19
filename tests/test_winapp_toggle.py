"""The Windows tray app's toggle has to survive a failing recorder too: an
exception escaping into pynput stops the listener and every key goes dead."""

import importlib
import importlib.util
import sys
import threading
from types import SimpleNamespace

import numpy as np
import pytest

from sotto.config import Config
from sotto.recorder import SAMPLE_RATE

# pystray and Pillow are Windows-only dependencies. Elsewhere, stand-ins are
# enough to import the module: these tests never touch the tray or the HUD.
_STUBS = {
    "pystray": SimpleNamespace(Icon=object, Menu=object, MenuItem=object),
    "PIL": SimpleNamespace(Image=SimpleNamespace(Image=object), ImageDraw=object),
}


@pytest.fixture
def winapp(monkeypatch):
    missing = [name for name in _STUBS if importlib.util.find_spec(name) is None]
    for name in missing:
        monkeypatch.setitem(sys.modules, name, _STUBS[name])
    if missing:
        monkeypatch.delitem(sys.modules, "sotto.winapp", raising=False)
    module = importlib.import_module("sotto.winapp")
    yield module
    if missing:  # don't leak a module built on stand-ins to other tests
        sys.modules.pop("sotto.winapp", None)


class _FakeRecorder:
    def __init__(self):
        self.recording = False
        self.starts = 0

    def start(self):
        self.starts += 1
        self.recording = True

    def stop(self):
        self.recording = False
        return np.zeros(SAMPLE_RATE, dtype=np.float32)

    def reset(self):
        self.recording = False


class _FakeHud:
    def __init__(self):
        self.errors = []

    def listening(self, language=None):
        pass

    def error(self, text, seconds=4.0):
        self.errors.append(text)

    def hide(self):
        pass


def _app(winapp):
    app = winapp.WinApp.__new__(winapp.WinApp)  # skip tray/HUD/model setup
    app.config = Config()
    app.hotkeys = {"f13": "zh", "f15": "en"}
    app.recorder = _FakeRecorder()
    app.hud = _FakeHud()
    app._busy = False
    app._toggle_lock = threading.RLock()
    app._active_language = None
    app._auto_stop = None
    app._idle_icon, app._recording_icon = "idle", "recording"
    app.icon = SimpleNamespace(icon="idle")
    return app


def test_recorder_failing_on_stop_does_not_escape_the_callback(winapp, capsys):
    app = _app(winapp)
    app.on_hotkey("f13")
    assert app.icon.icon == "recording"

    def broken_stop():
        raise RuntimeError("PortAudio: device unavailable")

    app.recorder.stop = broken_stop
    app.on_hotkey("f13")  # must not raise

    assert not app.recorder.recording
    assert not app._busy
    assert app._auto_stop is None
    assert app.icon.icon == "idle"
    assert app.hud.errors == ["Dictation key failed — see log"]
    assert "device unavailable" in capsys.readouterr().err

    del app.recorder.stop
    app.on_hotkey("f15")
    assert app.recorder.recording and app.recorder.starts == 2
