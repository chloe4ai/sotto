"""User configuration, stored at ~/.sotto/config.json."""

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("SOTTO_HOME", Path.home() / ".sotto"))
CONFIG_PATH = CONFIG_DIR / "config.json"
DICTIONARY_PATH = CONFIG_DIR / "dictionary.txt"


@dataclass
class Config:
    # Key to hold while speaking. Any pynput key name: alt_r, cmd_r, f13 ...
    hotkey: str = "alt_r"
    # Whisper model size: tiny, base, small, medium, large-v3
    model: str = "base"
    # "auto" lets Whisper detect the language (works for mixed zh/en speech)
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
    extra: dict = field(default_factory=dict)

    @classmethod
    def load(cls) -> "Config":
        if CONFIG_PATH.exists():
            try:
                data = json.loads(CONFIG_PATH.read_text())
                known = {f for f in cls.__dataclass_fields__}
                kwargs = {k: v for k, v in data.items() if k in known}
                kwargs["extra"] = {k: v for k, v in data.items() if k not in known}
                return cls(**kwargs)
            except (json.JSONDecodeError, TypeError):
                pass  # fall through to defaults; never crash on a bad config
        return cls()

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = asdict(self)
        data.update(data.pop("extra"))
        CONFIG_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False))
