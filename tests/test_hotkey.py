import pytest

from sotto.hotkey import (
    PressToToggle,
    hotkey_label,
    hotkey_summary,
    language_label,
    resolve_key,
)


def test_resolve_named_key():
    from pynput import keyboard

    assert resolve_key("alt_r") == keyboard.Key.alt_r
    assert resolve_key("f13") == keyboard.Key.f13


def test_resolve_single_char():
    from pynput import keyboard

    assert resolve_key("v") == keyboard.KeyCode.from_char("v")


def test_resolve_unknown_raises():
    with pytest.raises(ValueError):
        resolve_key("not_a_key")


def test_hotkey_labels():
    assert hotkey_label("alt_r") == "right ⌥"
    assert hotkey_label("f13") == "F13"
    assert hotkey_label("cmd_r") == "right ⌘"


def test_language_labels():
    assert language_label("zh") == "中文"
    assert language_label("en") == "English"
    assert language_label("auto") == "auto-detect"
    assert language_label("pt") == "PT"  # unknown codes still read sensibly


def test_hotkey_summary():
    assert (
        hotkey_summary({"f13": "zh", "f15": "en"})
        == "Press F13 for 中文 · F15 for English"
    )


def _toggler(*names):
    fired = []
    toggle = PressToToggle(names, fired.append)
    return toggle, fired


def test_press_toggles_without_holding():
    toggle, fired = _toggler("f13")
    key = resolve_key("f13")

    toggle._handle_press(key)  # start
    toggle._handle_release(key)
    toggle._handle_press(key)  # stop
    toggle._handle_release(key)

    assert fired == ["f13", "f13"]


def test_key_repeat_while_held_fires_once():
    toggle, fired = _toggler("f13")
    key = resolve_key("f13")

    toggle._handle_press(key)
    toggle._handle_press(key)  # macOS auto-repeat
    toggle._handle_press(key)

    assert fired == ["f13"]


def test_each_key_reports_itself():
    toggle, fired = _toggler("f13", "f15")

    toggle._handle_press(resolve_key("f15"))
    toggle._handle_release(resolve_key("f15"))
    toggle._handle_press(resolve_key("f13"))

    assert fired == ["f15", "f13"]


def test_other_keys_ignored():
    toggle, fired = _toggler("f13")

    toggle._handle_press(resolve_key("f14"))
    toggle._handle_press(resolve_key("a"))

    assert fired == []


def test_requires_at_least_one_key():
    with pytest.raises(ValueError):
        PressToToggle([], lambda name: None)
