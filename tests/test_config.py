import json

import sotto.config as config_mod
from sotto.config import DEFAULT_HOTKEYS, Config, is_modifier


def test_defaults():
    c = Config()
    assert c.hotkeys == {"f13": "zh", "f15": "en"}
    assert c.model == "base"
    assert c.polish == "auto"
    assert c.task == "transcribe"


def test_default_hotkeys_are_not_shared_between_instances():
    Config().hotkeys["f16"] = "ja"
    assert Config().hotkeys == DEFAULT_HOTKEYS


def test_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(config_mod, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(config_mod, "CONFIG_PATH", tmp_path / "config.json")
    c = Config(
        model="small",
        polish="local",
        task="translate",
        hotkeys={"f13": "zh", "f14": "ja"},
    )
    c.save()
    loaded = Config.load()
    assert loaded.model == "small"
    assert loaded.polish == "local"
    assert loaded.task == "translate"
    assert loaded.hotkeys == {"f13": "zh", "f14": "ja"}


def test_bad_config_falls_back_to_defaults(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    path.write_text("{not json")
    monkeypatch.setattr(config_mod, "CONFIG_PATH", path)
    assert Config.load().model == "base"


def test_unknown_keys_preserved(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"model": "tiny", "future_option": 1}))
    monkeypatch.setattr(config_mod, "CONFIG_PATH", path)
    c = Config.load()
    assert c.model == "tiny"
    assert c.extra == {"future_option": 1}


def test_legacy_modifier_hotkey_is_dropped(tmp_path, monkeypatch):
    """Holding right ⌥ was fine; toggling on it would fire while typing."""
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"hotkey": "alt_r", "model": "tiny"}))
    monkeypatch.setattr(config_mod, "CONFIG_PATH", path)
    c = Config.load()
    assert c.hotkeys == DEFAULT_HOTKEYS
    assert "hotkey" not in c.extra


def test_legacy_plain_hotkey_is_kept_as_a_toggle(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"hotkey": "f18", "language": "zh"}))
    monkeypatch.setattr(config_mod, "CONFIG_PATH", path)
    c = Config.load()
    assert c.hotkeys == {"f13": "zh", "f15": "en", "f18": "zh"}


def test_explicit_hotkeys_win_over_legacy(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"hotkey": "f18", "hotkeys": {"f13": "zh"}}))
    monkeypatch.setattr(config_mod, "CONFIG_PATH", path)
    assert Config.load().hotkeys == {"f13": "zh"}


def test_is_modifier():
    assert is_modifier("alt_r")
    assert is_modifier("cmd")
    assert not is_modifier("f13")
    assert not is_modifier("v")
