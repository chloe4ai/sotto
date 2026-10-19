"""Turn raw transcription into text you'd actually send.

Two tiers:
  local — fast regex cleanup, fully offline: filler words, stutters, spacing.
  ai    — Claude rewrites the transcript like Typeless does: applies
          mid-sentence self-corrections, formats lists, fixes punctuation.
          Used only when an ANTHROPIC_API_KEY is available and enabled.
"""

import os
import re
import sys

from .config import Config

# Conservative filler list: only tokens that are essentially never meaningful.
_EN_FILLERS = r"\b(?:um+|uh+|uhm+|erm*|hmm+)\b[,，]?\s*"
_ZH_FILLERS = r"(?:嗯+|呃+|唔+)[，,]?\s*"

_AI_SYSTEM_PROMPT = """\
You clean up dictated speech into polished written text. Rules:
- Remove filler words and false starts.
- If the speaker corrects themselves ("meet at 3, no wait, at 4"), keep only the final version.
- If the speaker dictates a list or steps, format them as a list.
- Fix punctuation and capitalization. Keep the speaker's language(s) — do not translate.
- Preserve meaning and tone. Do not add content, do not answer questions in the text.
- Output ONLY the cleaned text, nothing else."""

# Output budget for the AI tier. A 300 s take can run to a few thousand
# characters, and CJK text costs roughly a token per character, so scale with
# the input instead of using a flat limit that silently cuts long takes off.
_MIN_OUTPUT_TOKENS = 1024
_MAX_OUTPUT_TOKENS = 8192


def _output_budget(text: str) -> int:
    return min(_MAX_OUTPUT_TOKENS, max(_MIN_OUTPUT_TOKENS, 3 * len(text)))


def local_polish(text: str) -> str:
    """Offline cleanup. Deliberately conservative — never changes meaning."""
    text = re.sub(_EN_FILLERS, "", text, flags=re.IGNORECASE)
    text = re.sub(_ZH_FILLERS, "", text)
    # Collapse immediate word repeats: "the the" -> "the"
    text = re.sub(r"\b(\w+)(\s+\1\b)+", r"\1", text, flags=re.IGNORECASE)
    text = re.sub(r"\s{2,}", " ", text).strip()
    text = re.sub(r"\s+([,.!?;:，。！？；：])", r"\1", text)
    if text and text[0].isalpha():
        text = text[0].upper() + text[1:]
    return text


class Polisher:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._client = None

    def _ai_available(self) -> bool:
        return bool(os.environ.get("ANTHROPIC_API_KEY"))

    @property
    def active_mode(self) -> str:
        mode = self._config.polish
        if mode == "auto":
            return "ai" if self._ai_available() else "local"
        return mode

    def polish(self, text: str) -> str:
        if not text:
            return text
        mode = self.active_mode
        if mode == "off":
            return text
        if mode == "ai":
            try:
                return self._ai_polish(text)
            except Exception as exc:
                # Never lose the user's words, but say why AI polish was skipped.
                print(
                    f"Sotto: AI polish failed ({type(exc).__name__}: {exc}); "
                    "using local cleanup instead.",
                    file=sys.stderr,
                )
                return local_polish(text)
        return local_polish(text)

    def _ai_polish(self, text: str) -> str:
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic()
        response = self._client.messages.create(
            model=self._config.ai_model,
            max_tokens=_output_budget(text),
            system=_AI_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": text}],
        )
        if response.stop_reason == "max_tokens":
            # A truncated rewrite would drop the end of what was said.
            print(
                "Sotto: AI polish hit the output limit; using local cleanup "
                "instead so nothing is cut off.",
                file=sys.stderr,
            )
            return local_polish(text)
        cleaned = response.content[0].text.strip()
        return cleaned or local_polish(text)
