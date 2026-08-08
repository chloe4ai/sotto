"""Entry point.

    sotto                     run the menu bar / system tray app
    sotto --doctor            check permissions and setup, print what's wrong
    sotto --file audio.wav    transcribe + polish a file and print it (debug)
"""

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(prog="sotto", description=__doc__)
    parser.add_argument("--file", help="transcribe an audio file and exit")
    parser.add_argument(
        "--raw", action="store_true", help="with --file: skip polishing"
    )
    parser.add_argument(
        "--doctor", action="store_true", help="diagnose permissions and setup"
    )
    parser.add_argument("--version", action="version", version=_version())
    args = parser.parse_args()

    if args.file:
        _transcribe_file(args.file, raw=args.raw)
        return

    if args.doctor:
        sys.exit(_doctor())

    if sys.platform == "darwin":
        from .app import SottoApp

        SottoApp().run()
    elif sys.platform == "win32":
        from .winapp import WinApp

        WinApp().run()
    else:
        sys.exit("Sotto currently supports macOS and Windows.")


def _version() -> str:
    from . import __version__

    return f"sotto {__version__}"


def _transcribe_file(path: str, raw: bool = False) -> None:
    from .config import Config
    from .dictionary import Dictionary
    from .polisher import Polisher
    from .transcriber import Transcriber

    config = Config.load()
    transcriber = Transcriber(config, Dictionary())
    text = transcriber.transcribe(path)  # faster-whisper accepts paths too
    if not raw:
        text = Polisher(config).polish(text)
    print(text)


def _doctor() -> int:
    """Print a checklist of everything Sotto needs. Returns an exit code."""
    import os

    from .config import CONFIG_PATH, Config

    config = Config.load()
    failures = 0

    def check(ok: bool, label: str, fix: str = "") -> None:
        nonlocal failures
        print(f"  {'✓' if ok else '✗'} {label}")
        if not ok:
            failures += 1
            if fix:
                print(f"      → {fix}")

    print("Sotto doctor\n")

    if sys.platform == "darwin":
        from .permissions import accessibility_trusted, microphone_ok

        check(
            accessibility_trusted(),
            "Accessibility permission (dictation keys + paste)",
            "System Settings → Privacy & Security → Accessibility: enable the app "
            "you launch sotto from (e.g. Terminal), then restart sotto. "
            "If it still fails, also enable it under Input Monitoring.",
        )

        mic_ok, mic_detail = microphone_ok()
        check(
            mic_ok,
            "Microphone" + ("" if mic_ok else f" ({mic_detail})"),
            "System Settings → Privacy & Security → Microphone: enable the app "
            "you launch sotto from.",
        )
    else:
        print("  • Permission checks are macOS-only — Windows needs no setup")

    model_dir = os.path.join(
        os.path.expanduser("~/.cache/huggingface/hub"),
        f"models--Systran--faster-whisper-{config.model}",
    )
    if os.path.isdir(model_dir):
        print(f"  ✓ Whisper model '{config.model}' downloaded")
    else:
        print(
            f"  • Whisper model '{config.model}' not downloaded yet — "
            "the first dictation will fetch it (network needed once)"
        )

    from .hotkey import hotkey_label, language_label

    keys = ", ".join(
        f"{hotkey_label(k)} → {language_label(v)}"
        for k, v in (config.hotkeys or {}).items()
    )
    print(f"  • Dictation keys (press once to start, again to stop): {keys}")
    if config.task == "translate":
        print(
            "      → 'Translate to English' is on, so every key outputs "
            "English regardless of the language you speak"
        )

    if os.environ.get("ANTHROPIC_API_KEY"):
        polish_note = "Claude AI polish available"
    else:
        polish_note = "local rules (no ANTHROPIC_API_KEY set — that's fine)"
    print(f"  • Polish mode '{config.polish}': {polish_note}")
    print(
        f"  • Config: {CONFIG_PATH}"
        + ("" if CONFIG_PATH.exists() else " (using defaults, not created yet)")
    )

    print()
    if failures:
        print(
            f"{failures} problem(s) found — fix the ✗ items above, "
            "then run `sotto --doctor` again."
        )
    else:
        print(
            "Everything looks good. Run `sotto`, press a dictation key, "
            "speak, and press it again."
        )
    return 1 if failures else 0


if __name__ == "__main__":
    main()
