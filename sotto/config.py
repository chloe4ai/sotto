"""User configuration, stored at ~/.sotto/config.json."""

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("SOTTO_HOME", Path.home() / ".sotto"))
CONFIG_PATH = CONFIG_DIR / "config.json"
DICTIONARY_PATH = CONFIG_DIR / "dictionary.txt"

# One key per dictation language. Press once to start, again to stop.
DEFAULT_HOTKEYS = {"f13": "zh", "f15": "en"}

# Modifiers are fine to hold but terrible to toggle: a stray tap while typing
# would silently start recording. They are rejected as dictation keys.
_MODIFIER_PREFIXES = ("alt", "cmd", "ctrl", "shift")


def is_modifier(key_name: str) -> bool:
    return key_name.split("_")[0] in _MODIFIER_PREFIXES


@dataclass
class Config:
    # Dictation keys: {pynput key name: language}. Press the key once to start
    # dictating in that language, press it again to stop. Language is a Whisper
    # code ("zh", "en", "ja", …) or "auto" to let Whisper detect it.
    hotkeys: dict = field(default_factory=lambda: dict(DEFAULT_HOTKEYS))
    # Whisper model size: tiny, base, small, medium, large-v3
    model: str = "base"
    # Fallback language when a hotkey says "auto" or none applies (--file).
    # "auto" lets Whisper detect it (works for mixed zh/en speech).
    language: str = "auto"
    # "transcribe" keeps the spoken language; "translate" uses Whisper's
    # built-in translation task to output English no matter what you speak.
    task: str = "transcribe"
    # "auto" = use Claude if ANTHROPIC_API_KEY is set, else local cleanup.
    # "ai" = always Claude, "local" = never call the network, "off" = raw text.
    polish: str = "auto"
    # Claude model used for polishing when AI polish is active.
    ai_model: str = "claude-haiku-4-5-20251001"
    # Seconds to wait after pasting before restoring the previous clipboard.
    clipboard_restore_delay: float = 0.6
    # Recordings shorter than this are ignored (accidental taps).
    min_duration: float = 0.3
    # Safety net for toggle mode: stop and transcribe by yourself after this
    # long, so a forgotten "stop" press can't record (and buffer) forever.
    max_duration: float = 300.0
    extra: dict = field(default_factory=dict)

    @classmethod
    def load(cls) -> "Config":
        if CONFIG_PATH.exists():
            try:
                data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                data = _migrate(data)
                known = {f for f in cls.__dataclass_fields__}
                kwargs = {k: v for k, v in data.items() if k in known}
                kwargs["extra"] = {k: v for k, v in data.items() if k not in known}
                return cls(**kwargs)
            except (json.JSONDecodeError, TypeError, AttributeError):
                pass  # fall through to defaults; never crash on a bad config
        return cls()

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = asdict(self)
        data.update(data.pop("extra"))
        CONFIG_PATH.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )


def _migrate(data: dict) -> dict:
    """Upgrade a pre-toggle config (single `hotkey` you had to hold)."""
    legacy = data.pop("hotkey", None)
    if not isinstance(legacy, str) or "hotkeys" in data:
        return data
    hotkeys = dict(DEFAULT_HOTKEYS)
    if is_modifier(legacy):
        print(
            f"Sotto: dictation is now press-to-toggle, so the old hold key "
            f"{legacy!r} was dropped (a modifier tap would start recording by "
            f"accident). Using {', '.join(hotkeys)} instead — see "
            f"{CONFIG_PATH}.",
            file=sys.stderr,
        )
    else:
        # Keep the user's muscle memory: same key, now a toggle, auto-detect.
        hotkeys.setdefault(legacy, data.get("language", "auto"))
    data["hotkeys"] = hotkeys
    return data
