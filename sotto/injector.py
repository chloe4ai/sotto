"""Insert text into the frontmost app: clipboard swap + paste keystroke.

macOS pastes with ⌘V via the NSPasteboard; Windows pastes with Ctrl+V via
pyperclip. Either way the previous clipboard is restored shortly after.
"""

import sys
import threading
import time

from pynput.keyboard import Controller, Key

from .config import Config

if sys.platform == "darwin":
    from AppKit import NSPasteboard, NSPasteboardTypeString

_PASTE_MODIFIER = Key.cmd if sys.platform == "darwin" else Key.ctrl


class Injector:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._keyboard = Controller()

    def _read_clipboard(self) -> str | None:
        if sys.platform == "darwin":
            pb = NSPasteboard.generalPasteboard()
            return pb.stringForType_(NSPasteboardTypeString)
        import pyperclip

        return pyperclip.paste()

    def _write_clipboard(self, text: str) -> None:
        if sys.platform == "darwin":
            pb = NSPasteboard.generalPasteboard()
            pb.clearContents()
            pb.setString_forType_(text, NSPasteboardTypeString)
        else:
            import pyperclip

            pyperclip.copy(text)

    def insert(self, text: str) -> None:
        previous = self._read_clipboard()
        self._write_clipboard(text)
        # Small delay so the clipboard change is visible to the target app.
        time.sleep(0.05)
        with self._keyboard.pressed(_PASTE_MODIFIER):
            self._keyboard.press("v")
            self._keyboard.release("v")

        if previous is not None:
            delay = self._config.clipboard_restore_delay

            def restore() -> None:
                time.sleep(delay)
                # Only restore if nothing else has claimed the clipboard.
                if self._read_clipboard() == text:
                    self._write_clipboard(previous)

            threading.Thread(target=restore, daemon=True).start()
