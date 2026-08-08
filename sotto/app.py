"""Menu bar app: wires hotkey → recorder → transcriber → polisher → injector."""

import subprocess
import sys
import threading

import rumps

from .config import DEFAULT_HOTKEYS, Config, is_modifier
from .dictionary import Dictionary
from .hotkey import (  # re-exported: labels live with the key handling
    PressToToggle,
    hotkey_label,
    hotkey_summary,
    language_label,
    resolve_key,
)
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
        # Presses arrive on the pynput listener thread; keep start/stop atomic.
        self._toggle_lock = threading.RLock()
        self._active_language: str | None = None
        self._auto_stop: threading.Timer | None = None

        self.hotkeys = self._valid_hotkeys()
        self.status_item = rumps.MenuItem(hotkey_summary(self.hotkeys))
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
        self.hotkey = PressToToggle(self.hotkeys, self.on_hotkey)
        self.hotkey.start()
        self._check_permissions()

    def _valid_hotkeys(self) -> dict:
        """Drop anything pynput can't resolve, and any modifier — in toggle
        mode a stray modifier tap would start recording without you noticing."""
        valid = {}
        for key, language in (self.config.hotkeys or {}).items():
            try:
                resolve_key(key)
            except ValueError:
                print(f"Sotto: unknown hotkey {key!r} in config, ignoring it.",
                      file=sys.stderr)
                continue
            if is_modifier(key):
                print(
                    f"Sotto: {key!r} is a modifier and can't be a toggle key "
                    "(it would fire while you type), ignoring it.",
                    file=sys.stderr,
                )
                continue
            valid[key] = language or "auto"
        if not valid:
            print(
                "Sotto: no usable dictation keys in config, falling back to "
                f"{', '.join(DEFAULT_HOTKEYS)}.",
                file=sys.stderr,
            )
            return dict(DEFAULT_HOTKEYS)
        return valid

    def _check_permissions(self) -> None:
        """Without Accessibility trust the hotkey listener runs but never
        receives events — the #1 'nothing happens' failure. Tell the user."""
        if accessibility_trusted(prompt=True):
            return
        self.status_item.title = "⚠️ Grant Accessibility permission"
        clicked = rumps.alert(
            title="Sotto needs the Accessibility permission",
            message=(
                "Without it, pressing the dictation key does nothing.\n\n"
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

    def on_hotkey(self, key_name: str) -> None:
        """One press starts dictation, the next one ends it. Pressing the other
        language's key while recording just ends the take in progress."""
        with self._toggle_lock:
            if self.recorder.recording:
                self._stop_dictation()
            elif not self._busy:  # still transcribing the previous take
                self._start_dictation(self.hotkeys.get(key_name, "auto"))

    def _start_dictation(self, language: str) -> None:
        try:
            self.recorder.start()
        except Exception as exc:  # no mic permission, device busy, ...
            self._mic_failed(exc)
            return
        self._active_language = language
        self.title = "🔴"
        self.hud.listening(language_label(language))
        self._arm_auto_stop()

    def _stop_dictation(self) -> None:
        self._cancel_auto_stop()
        audio = self.recorder.stop()
        language, self._active_language = self._active_language, None
        self.title = "🎙"
        if len(audio) < SAMPLE_RATE * self.config.min_duration:
            self.hud.hide()
            return
        if self.transcriber.ready:
            self.hud.processing()
        else:  # first run: model still downloading/loading
            self.hud.loading_model()
        self._busy = True
        threading.Thread(
            target=self._process, args=(audio, language), daemon=True
        ).start()

    def _arm_auto_stop(self) -> None:
        """Nothing holds the key down any more, so cap how long a take can run
        and transcribe what we have rather than recording into the void."""
        self._cancel_auto_stop()
        if self.config.max_duration <= 0:
            return
        self._auto_stop = threading.Timer(
            self.config.max_duration, self._auto_stop_fired
        )
        self._auto_stop.daemon = True
        self._auto_stop.start()

    def _cancel_auto_stop(self) -> None:
        if self._auto_stop is not None:
            self._auto_stop.cancel()
            self._auto_stop = None

    def _auto_stop_fired(self) -> None:
        with self._toggle_lock:
            if self.recorder.recording:
                print(
                    f"Sotto: stopped after {self.config.max_duration:.0f}s "
                    "(max_duration) — transcribing what was recorded.",
                    file=sys.stderr,
                )
                self._stop_dictation()

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

    def _process(self, audio, language: str | None = None) -> None:
        try:
            text = self.transcriber.transcribe(audio, language=language)
            text = self.polisher.polish(text)
            if text:
                self.injector.insert(text)
            self.hud.hide()
        except Exception as exc:
            self._report_error("Dictation failed", str(exc))
        finally:
            self._busy = False
