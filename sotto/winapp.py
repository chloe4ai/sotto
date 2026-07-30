"""Windows system-tray app: the macOS menu bar experience, ported.

pystray provides the tray icon and menu, a dedicated-thread tkinter window
plays the role of the floating HUD capsule, and pasting happens with Ctrl+V.
"""

import os
import queue
import sys
import threading

import pystray
from PIL import Image, ImageDraw

from .config import Config
from .dictionary import Dictionary
from .hotkey import HoldToTalk, resolve_key
from .injector import Injector
from .polisher import Polisher
from .recorder import SAMPLE_RATE, Recorder
from .transcriber import Transcriber

# Keep in sync with sotto/app.py (macOS), which owns the canonical lists.
MODELS = ["tiny", "base", "small", "medium", "large-v3"]
POLISH_MODES = ["auto", "ai", "local", "off"]


def _tray_image(color: str) -> Image.Image:
    """A simple filled-circle mic dot; tray icons are 16-32 px, keep it bold."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((8, 8, 56, 56), fill=color)
    draw.ellipse((24, 18, 40, 40), fill="white")
    draw.rectangle((30, 40, 34, 50), fill="white")
    return img


class TkHud(threading.Thread):
    """Floating status pill at the bottom of the screen.

    tkinter is not thread-safe, so one dedicated thread owns the widget and
    everyone else talks to it through a queue.
    """

    def __init__(self) -> None:
        super().__init__(daemon=True, name="sotto-hud")
        self._queue: queue.Queue = queue.Queue()
        self.start()

    def run(self) -> None:
        try:
            import tkinter as tk

            self._root = tk.Tk()
            self._root.withdraw()
            self._root.overrideredirect(True)
            self._root.attributes("-topmost", True)
            try:
                self._root.attributes("-alpha", 0.92)
            except tk.TclError:
                pass
            self._label = tk.Label(
                self._root,
                text="",
                font=("Segoe UI", 11),
                fg="white",
                bg="#101014",
                padx=18,
                pady=8,
            )
            self._label.pack()
            self._poll()
            self._root.mainloop()
        except Exception:
            # No display / broken Tk — run headless, states just aren't shown.
            self._queue = None

    def _poll(self) -> None:
        try:
            while True:
                msg = self._queue.get_nowait()
                if msg is None:
                    self._root.withdraw()
                else:
                    self._label.config(text=msg)
                    self._root.update_idletasks()
                    w = self._root.winfo_reqwidth()
                    h = self._root.winfo_reqheight()
                    sw = self._root.winfo_screenwidth()
                    sh = self._root.winfo_screenheight()
                    self._root.geometry(f"+{(sw - w) // 2}+{sh - h - 80}")
                    self._root.deiconify()
        except queue.Empty:
            pass
        self._root.after(80, self._poll)

    def _put(self, msg) -> None:
        if self._queue is not None:
            self._queue.put(msg)

    def listening(self) -> None:
        self._put("🔴  Listening…")

    def processing(self) -> None:
        self._put("✨  Polishing…")

    def loading_model(self) -> None:
        self._put("⏳  Loading model…")

    def error(self, text: str, seconds: float = 4.0) -> None:
        self._put(f"⚠️  {text}")
        threading.Timer(seconds, self.hide).start()

    def hide(self) -> None:
        self._put(None)


class WinApp:
    def __init__(self) -> None:
        self.config = Config.load()
        self.dictionary = Dictionary()
        self.recorder = Recorder()
        self.transcriber = Transcriber(self.config, self.dictionary)
        self.polisher = Polisher(self.config)
        self.injector = Injector(self.config)
        self.hud = TkHud()
        self._busy = False

        self._idle_icon = _tray_image("#4a3d8f")
        self._recording_icon = _tray_image("#e03131")

        hotkey_name = self._valid_hotkey_name()
        self.hotkey = HoldToTalk(
            hotkey_name, self.on_hotkey_down, self.on_hotkey_up
        )
        self.icon = pystray.Icon(
            "Sotto",
            self._idle_icon,
            "Sotto — hold right Alt and speak",
            menu=self._build_menu(hotkey_name),
        )

    def _valid_hotkey_name(self) -> str:
        try:
            resolve_key(self.config.hotkey)
            return self.config.hotkey
        except ValueError:
            print(
                f"Unknown hotkey {self.config.hotkey!r} in config, "
                "falling back to alt_r (right Alt).",
                file=sys.stderr,
            )
            return "alt_r"

    # ----- menu -----

    def _build_menu(self, hotkey_name: str) -> pystray.Menu:
        key_hint = "right Alt" if hotkey_name == "alt_r" else hotkey_name
        return pystray.Menu(
            pystray.MenuItem(f"Hold {key_hint} to speak", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Model",
                pystray.Menu(
                    *[
                        pystray.MenuItem(
                            name,
                            self._set_model(name),
                            checked=lambda item, n=name: self.config.model == n,
                            radio=True,
                        )
                        for name in MODELS
                    ]
                ),
            ),
            pystray.MenuItem(
                "Polish",
                pystray.Menu(
                    *[
                        pystray.MenuItem(
                            name,
                            self._set_polish(name),
                            checked=lambda item, n=name: self.config.polish == n,
                            radio=True,
                        )
                        for name in POLISH_MODES
                    ]
                ),
            ),
            pystray.MenuItem(
                "Translate to English",
                self._toggle_translate,
                checked=lambda item: self.config.task == "translate",
            ),
            pystray.MenuItem("Edit Dictionary…", self._open_dictionary),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit Sotto", self._quit),
        )

    def _set_model(self, name: str):
        def apply(icon, item) -> None:
            self.config.model = name
            self.config.save()
            self.transcriber.reset()
            self.transcriber.preload()

        return apply

    def _set_polish(self, name: str):
        def apply(icon, item) -> None:
            self.config.polish = name
            self.config.save()

        return apply

    def _toggle_translate(self, icon, item) -> None:
        translating = self.config.task != "translate"
        self.config.task = "translate" if translating else "transcribe"
        self.config.save()

    def _open_dictionary(self, icon, item) -> None:
        os.startfile(self.dictionary.ensure_file())  # noqa: attribute exists on Windows

    def _quit(self, icon, item) -> None:
        self.hotkey.stop()
        icon.stop()

    # ----- dictation flow -----

    def on_hotkey_down(self) -> None:
        if self._busy:
            return
        try:
            self.recorder.start()
        except Exception as exc:  # no mic, device busy, ...
            self.hud.error(f"Microphone unavailable: {exc}")
            return
        self.icon.icon = self._recording_icon
        self.hud.listening()

    def on_hotkey_up(self) -> None:
        if not self.recorder.recording:
            return
        audio = self.recorder.stop()
        self.icon.icon = self._idle_icon
        if len(audio) < SAMPLE_RATE * self.config.min_duration:
            self.hud.hide()
            return
        if self.transcriber.ready:
            self.hud.processing()
        else:  # first run: model still downloading/loading
            self.hud.loading_model()
        self._busy = True
        threading.Thread(target=self._process, args=(audio,), daemon=True).start()

    def _process(self, audio) -> None:
        try:
            text = self.transcriber.transcribe(audio)
            text = self.polisher.polish(text)
            if text:
                self.injector.insert(text)
            self.hud.hide()
        except Exception as exc:
            print(f"Sotto: dictation failed: {exc}", file=sys.stderr)
            self.hud.error("Dictation failed — see log")
        finally:
            self._busy = False

    def run(self) -> None:
        self.transcriber.preload()
        self.hotkey.start()
        self.icon.run()
