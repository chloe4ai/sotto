"""Global hold-to-talk hotkey via pynput (needs Input Monitoring permission)."""

from typing import Callable

from pynput import keyboard


def resolve_key(name: str):
    """Map a config name like 'alt_r' or 'f13' to a pynput key object."""
    try:
        return getattr(keyboard.Key, name)
    except AttributeError:
        if len(name) == 1:
            return keyboard.KeyCode.from_char(name)
        raise ValueError(f"Unknown hotkey: {name!r}")


class HoldToTalk:
    """Calls on_press when the hotkey goes down, on_release when it comes up."""

    def __init__(self, key_name: str, on_press: Callable, on_release: Callable):
        self._key = resolve_key(key_name)
        self._on_press = on_press
        self._on_release = on_release
        self._down = False
        self._listener: keyboard.Listener | None = None

    def start(self) -> None:
        self._listener = keyboard.Listener(
            on_press=self._handle_press, on_release=self._handle_release
        )
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None

    def _matches(self, key) -> bool:
        return key == self._key

    def _handle_press(self, key) -> None:
        if self._matches(key) and not self._down:
            self._down = True  # macOS auto-repeats key-down events; fire once
            self._on_press()

    def _handle_release(self, key) -> None:
        if self._matches(key) and self._down:
            self._down = False
            self._on_release()
