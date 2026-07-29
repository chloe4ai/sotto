"""Entry point.

    sotto                     run the menu bar app
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
    args = parser.parse_args()

    if args.file:
        _transcribe_file(args.file, raw=args.raw)
        return

    if sys.platform != "darwin":
        sys.exit("Sotto currently supports macOS only.")

    from .app import SottoApp

    SottoApp().run()


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


if __name__ == "__main__":
    main()
