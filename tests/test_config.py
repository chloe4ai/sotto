import json

import sotto.config as config_mod
from sotto.config import Config


def test_defaults():
    c = Config()
    assert c.hotkey == "alt_r"
    assert c.model == "base"
    assert c.polish == "auto"
    assert c.task == "transcribe"


def test_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(config_mod, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(config_mod, "CONFIG_PATH", tmp_path / "config.json")
    c = Config(model="small", polish="local", task="translate")
    c.save()
    loaded = Config.load()
    assert loaded.model == "small"
    assert loaded.polish == "local"
    assert loaded.task == "translate"


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
