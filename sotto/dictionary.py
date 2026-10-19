"""Personal dictionary: custom terms Whisper should get right.

~/.sotto/dictionary.txt, one entry per line:

    Kubernetes                # a term to bias recognition toward
    cloudy tan -> Chloe Tan   # a correction applied after transcription

Lines starting with # are comments.
"""

import re
from pathlib import Path

from .config import DICTIONARY_PATH


class Dictionary:
    def __init__(self, path: Path = DICTIONARY_PATH) -> None:
        self._path = path
        self.terms: list[str] = []
        self.corrections: list[tuple[str, str]] = []
        self.reload()

    def reload(self) -> None:
        self.terms = []
        self.corrections = []
        if not self._path.exists():
            return
        for line in self._path.read_text(encoding="utf-8").splitlines():
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            if "->" in line:
                wrong, right = (part.strip() for part in line.split("->", 1))
                if wrong and right:
                    self.corrections.append((wrong, right))
            else:
                self.terms.append(line)

    def prompt_hint(self) -> str:
        """Vocabulary hint fed to Whisper as the initial prompt."""
        vocab = self.terms + [right for _, right in self.corrections]
        return ", ".join(vocab[:40])

    def apply(self, text: str) -> str:
        for wrong, right in self.corrections:
            # A function replacement is inserted verbatim; a string one would
            # treat backslashes in `right` as escapes (\n, \1, ...).
            text = re.sub(
                re.escape(wrong),
                lambda _m, right=right: right,
                text,
                flags=re.IGNORECASE,
            )
        return text

    def ensure_file(self) -> Path:
        if not self._path.exists():
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                "# Sotto personal dictionary\n"
                "# One term per line, or a correction: wrong -> right\n",
                encoding="utf-8",
            )
        return self._path
