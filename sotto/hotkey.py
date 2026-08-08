"""Global press-to-toggle hotkeys via pynput (needs Input Monitoring permission).

Dictation is a toggle, not a hold: press a registered key once to start, press
it again to stop. Several keys can be registered at once — the callback gets
the key's name back, which is how the app picks a language per key.
"""

from typing import Callable, Iterable

from pynput import keyboard

_KEY_LABELS = {
    "alt_r": "right ⌥",
    "alt_l": "left ⌥",
    "alt": "⌥",
    "cmd_r": "right ⌘",
    "cmd_l": "left ⌘",
    "cmd": "⌘",
    "ctrl_r": "right ⌃",
    "ctrl_l": "left ⌃",
    "ctrl": "⌃",
    "shift_r": "right ⇧",
    "shift_l": "left ⇧",
    "shift": "⇧",
}

_LANGUAGE_LABELS = {
    "auto": "auto-detect",
    "zh": "中文",
    "en": "English",
    "ja": "日本語",
    "ko": "한국어",
    "es": "Español",
    "fr": "Français",
    "de": "Deutsch",
}


def hotkey_label(name: str) -> str:
    return _KEY_LABELS.get(name, name.upper() if name.startswith("f") else name)


def language_label(code: str) -> str:
    return _LANGUAGE_LABELS.get(code, code.upper())


def hotkey_summary(hotkeys: dict) -> str:
    """e.g. 'Press F13 for 中文 · F15 for English'."""
    parts = [
        f"{hotkey_label(key)} for {language_label(lang)}"
        for key, lang in hotkeys.items()
    ]
    return "Press " + " · ".join(parts)


def resolve_key(name: str):
    """Map a config name like 'alt_r' or 'f13' to a pynput key object."""
    try:
        return getattr(keyboard.Key, name)
    except AttributeError:
        if len(name) == 1:
            return keyboard.KeyCode.from_char(name)
        raise ValueError(f"Unknown hotkey: {name!r}")


class PressToToggle:
    """Calls on_toggle(key_name) once per press of any registered key.

    macOS repeats key-down events while a key stays down, so a key has to come
    back up before it can toggle again — holding it counts as a single press.
    """

    def __init__(self, key_names: Iterable[str], on_toggle: Callable[[str], None]):
        # A list, not a dict: pynput hands back Key/KeyCode variants that
        # compare equal without necessarily hashing equal, so we scan with ==.
        self._keys = [(resolve_key(name), name) for name in key_names]
        if not self._keys:
            raise ValueError("PressToToggle needs at least one key")
        self._on_toggle = on_toggle
        self._down: set[str] = set()
        self._listener: keyboard.Listener | None = None

    @property
    def key_names(self) -> list[str]:
        return [name for _key, name in self._keys]

    def start(self) -> None:
        self._listener = keyboard.Listener(
            on_press=self._handle_press, on_release=self._handle_release
        )
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        self._down.clear()

    def _name_for(self, key) -> str | None:
        for candidate, name in self._keys:
            if key == candidate:
                return name
        return None

    def _handle_press(self, key) -> None:
        name = self._name_for(key)
        if name is None or name in self._down:
            return  # not ours, or an auto-repeat while the key is still down
        self._down.add(name)
        self._on_toggle(name)

    def _handle_release(self, key) -> None:
        name = self._name_for(key)
        if name is not None:
            self._down.discard(name)
