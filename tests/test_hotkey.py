import pytest

from sotto.hotkey import resolve_key


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
    from sotto.app import hotkey_label

    assert hotkey_label("alt_r") == "right ⌥"
    assert hotkey_label("f13") == "F13"
    assert hotkey_label("cmd_r") == "right ⌘"
