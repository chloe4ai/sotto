"""Menu bar app: wires hotkey → recorder → transcriber → polisher → injector."""

import subprocess
import threading

import rumps

from .config import Config
from .dictionary import Dictionary
from .hotkey import HoldToTalk
from .hud import Hud
from .injector import Injector
from .polisher import Polisher
from .recorder import SAMPLE_RATE, Recorder
from .transcriber import Transcriber

MODELS = ["tiny", "base", "small", "medium", "large-v3"]
POLISH_MODES = ["auto", "ai", "local", "off"]


class SottoApp(rumps.App):
    def __init__(self) -> None:
        super().__init__("Sotto", title="🎙", quit_button="Quit Sotto")
        self.config = Config.load()
        self.dictionary = Dictionary()
        self.recorder = Recorder()
        self.transcriber = Transcriber(self.config, self.dictionary)
        self.polisher = Polisher(self.config)
        self.injector = Injector(self.config)
        self.hud = Hud()
        self._busy = False

        self.status_item = rumps.MenuItem(f"Hold ⌥ (right) to speak")
        self.status_item.set_callback(None)
        self.menu = [
            self.status_item,
            None,
            self._build_model_menu(),
            self._build_polish_menu(),
            rumps.MenuItem("Edit Dictionary…", callback=self.open_dictionary),
            None,
        ]

        self.transcriber.preload()
        self.hotkey = HoldToTalk(
            self.config.hotkey, self.on_hotkey_down, self.on_hotkey_up
        )
        self.hotkey.start()

    # ----- menus -----

    def _build_model_menu(self) -> rumps.MenuItem:
        menu = rumps.MenuItem("Model")
        for name in MODELS:
            item = rumps.MenuItem(name, callback=self.set_model)
            item.state = name == self.config.model
            menu.add(item)
        return menu

    def _build_polish_menu(self) -> rumps.MenuItem:
        menu = rumps.MenuItem("Polish")
        for name in POLISH_MODES:
            item = rumps.MenuItem(name, callback=self.set_polish)
            item.state = name == self.config.polish
            menu.add(item)
        return menu

    def set_model(self, sender: rumps.MenuItem) -> None:
        self.config.model = sender.title
        self.config.save()
        for item in self.menu["Model"].values():
            item.state = item.title == sender.title
        # Force a reload with the new size on next use.
        self.transcriber._model = None
        self.transcriber.preload()

    def set_polish(self, sender: rumps.MenuItem) -> None:
        self.config.polish = sender.title
        self.config.save()
        for item in self.menu["Polish"].values():
            item.state = item.title == sender.title

    def open_dictionary(self, _sender) -> None:
        path = self.dictionary.ensure_file()
        subprocess.run(["open", "-t", str(path)], check=False)

    # ----- dictation flow -----

    def on_hotkey_down(self) -> None:
        if self._busy:
            return
        try:
            self.recorder.start()
        except Exception as exc:  # no mic permission, device busy, ...
            rumps.notification("Sotto", "Could not access microphone", str(exc))
            return
        self.title = "🔴"
        self.hud.listening()

    def on_hotkey_up(self) -> None:
        if not self.recorder.recording:
            return
        audio = self.recorder.stop()
        self.title = "🎙"
        if len(audio) < SAMPLE_RATE * self.config.min_duration:
            self.hud.hide()
            return
        self.hud.processing()
        self._busy = True
        threading.Thread(target=self._process, args=(audio,), daemon=True).start()

    def _process(self, audio) -> None:
        try:
            text = self.transcriber.transcribe(audio)
            text = self.polisher.polish(text)
            if text:
                self.injector.insert(text)
        except Exception as exc:
            rumps.notification("Sotto", "Dictation failed", str(exc))
        finally:
            self._busy = False
            self.hud.hide()
