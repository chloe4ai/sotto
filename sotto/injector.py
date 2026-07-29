"""Insert text into the frontmost app: clipboard swap + Cmd+V, then restore."""

import threading
import time

from AppKit import NSPasteboard, NSPasteboardTypeString
from pynput.keyboard import Controller, Key

from .config import Config


class Injector:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._keyboard = Controller()

    def _read_clipboard(self) -> str | None:
        pb = NSPasteboard.generalPasteboard()
        return pb.stringForType_(NSPasteboardTypeString)

    def _write_clipboard(self, text: str) -> None:
        pb = NSPasteboard.generalPasteboard()
        pb.clearContents()
        pb.setString_forType_(text, NSPasteboardTypeString)

    def insert(self, text: str) -> None:
        previous = self._read_clipboard()
        self._write_clipboard(text)
        # Small delay so the pasteboard change is visible to the target app.
        time.sleep(0.05)
        with self._keyboard.pressed(Key.cmd):
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
