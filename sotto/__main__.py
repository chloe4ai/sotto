"""Entry point.

    sotto                     run the menu bar app
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

    if sys.platform != "darwin":
        sys.exit("Sotto currently supports macOS only.")

    if args.doctor:
        sys.exit(_doctor())

    from .app import SottoApp

    SottoApp().run()


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
    from .permissions import accessibility_trusted, microphone_ok

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

    check(
        accessibility_trusted(),
        "Accessibility permission (hotkey + paste)",
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
        print("Everything looks good. Run `sotto` and hold the hotkey to speak.")
    return 1 if failures else 0


if __name__ == "__main__":
    main()
