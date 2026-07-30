"""Menu bar app: wires hotkey → recorder → transcriber → polisher → injector."""

import subprocess
import sys
import threading

import rumps

from .config import Config
from .dictionary import Dictionary
from .hotkey import HoldToTalk, resolve_key
from .hud import Hud
from .injector import Injector
from .permissions import (
    accessibility_trusted,
    open_accessibility_settings,
    open_microphone_settings,
)
from .polisher import Polisher
from .recorder import SAMPLE_RATE, Recorder
from .transcriber import Transcriber

MODELS = ["tiny", "base", "small", "medium", "large-v3"]
POLISH_MODES = ["auto", "ai", "local", "off"]

_KEY_LABELS = {
    "alt_r": "right ⌥",
    "alt_l": "left ⌥",
    "alt": "⌥",
    "cmd_r": "right ⌘",
    "cmd_l": "left ⌘",
    "cmd": "⌘",
    "ctrl_r": "right ⌃",
    "ctrl_l": "left ⌃",
    "ctrl": "⌃",
    "shift_r": "right ⇧",
    "shift_l": "left ⇧",
    "shift": "⇧",
}


def hotkey_label(name: str) -> str:
    return _KEY_LABELS.get(name, name.upper() if name.startswith("f") else name)


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
        self._mic_help_shown = False

        hotkey_name = self._valid_hotkey_name()
        self.status_item = rumps.MenuItem(
            f"Hold {hotkey_label(hotkey_name)} to speak"
        )
        self.status_item.set_callback(None)
        self.translate_item = rumps.MenuItem(
            "Translate to English", callback=self.toggle_translate
        )
        self.translate_item.state = self.config.task == "translate"
        self.menu = [
            self.status_item,
            None,
            self._build_model_menu(),
            self._build_polish_menu(),
            self.translate_item,
            rumps.MenuItem("Edit Dictionary…", callback=self.open_dictionary),
            None,
        ]

        self.transcriber.preload()
        self.hotkey = HoldToTalk(
            hotkey_name, self.on_hotkey_down, self.on_hotkey_up
        )
        self.hotkey.start()
        self._check_permissions()

    def _valid_hotkey_name(self) -> str:
        try:
            resolve_key(self.config.hotkey)
            return self.config.hotkey
        except ValueError:
            print(
                f"Unknown hotkey {self.config.hotkey!r} in config, "
                "falling back to alt_r (right Option).",
                file=sys.stderr,
            )
            return "alt_r"

    def _check_permissions(self) -> None:
        """Without Accessibility trust the hotkey listener runs but never
        receives events — the #1 'nothing happens' failure. Tell the user."""
        if accessibility_trusted(prompt=True):
            return
        self.status_item.title = "⚠️ Grant Accessibility permission"
        clicked = rumps.alert(
            title="Sotto needs the Accessibility permission",
            message=(
                "Without it, holding the hotkey does nothing.\n\n"
                "In System Settings → Privacy & Security → Accessibility, "
                "enable the app you launched sotto from (e.g. Terminal), "
                "then quit and rerun sotto.\n\n"
                "If dictation still doesn't trigger, also enable it under "
                "Input Monitoring."
            ),
            ok="Open System Settings",
            cancel="Later",
        )
        if clicked == 1:
            open_accessibility_settings()

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
        self.transcriber.reset()
        self.transcriber.preload()

    def set_polish(self, sender: rumps.MenuItem) -> None:
        self.config.polish = sender.title
        self.config.save()
        for item in self.menu["Polish"].values():
            item.state = item.title == sender.title

    def toggle_translate(self, sender: rumps.MenuItem) -> None:
        translating = not sender.state
        sender.state = translating
        self.config.task = "translate" if translating else "transcribe"
        self.config.save()

    def open_dictionary(self, _sender) -> None:
        path = self.dictionary.ensure_file()
        subprocess.run(["open", "-t", str(path)], check=False)

    # ----- errors -----

    def _report_error(self, title: str, detail: str) -> None:
        """Notifications can be unavailable (unbundled Python) or muted, so
        always show the error in the HUD too and log it to the terminal."""
        print(f"Sotto: {title}: {detail}", file=sys.stderr)
        self.hud.error(title)
        try:
            rumps.notification("Sotto", title, detail)
        except Exception:
            pass

    # ----- dictation flow -----

    def on_hotkey_down(self) -> None:
        if self._busy:
            return
        try:
            self.recorder.start()
        except Exception as exc:  # no mic permission, device busy, ...
            self._mic_failed(exc)
            return
        self.title = "🔴"
        self.hud.listening()

    def _mic_failed(self, exc: Exception) -> None:
        self._report_error(
            "Microphone blocked — check System Settings",
            f"{exc} — enable the app you launched sotto from under "
            "System Settings → Privacy & Security → Microphone, then "
            "quit and rerun sotto. (`sotto --doctor` verifies this.)",
        )
        # Take the user straight to the right pane, once per run. This runs
        # on the hotkey listener thread, where a modal alert isn't safe.
        if not self._mic_help_shown:
            self._mic_help_shown = True
            open_microphone_settings()

    def on_hotkey_up(self) -> None:
        if not self.recorder.recording:
            return
        audio = self.recorder.stop()
        self.title = "🎙"
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
            self._report_error("Dictation failed", str(exc))
        finally:
            self._busy = False
