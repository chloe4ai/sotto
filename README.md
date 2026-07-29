# 🎙 Sotto

> *sotto voce* — in a soft voice.
> **Speak softly, never type.** 轻声一说，文字即成。

Sotto is a privacy-first AI voice dictation tool for macOS. Hold a key, speak
naturally in any app — Sotto transcribes **on your device**, cleans up the
filler words, and drops polished text right where your cursor is.

Inspired by [Typeless](https://www.typeless.com/), but with a different set of
values: **local-first, transparent, free**.

|                    | Sotto                          | Typeless        |
| ------------------ | ------------------------------ | --------------- |
| Speech recognition | 🏠 On-device (Whisper)         | ☁️ Cloud only    |
| Works offline      | ✅                             | ❌              |
| AI cleanup         | Optional (local rules / Claude)| Always cloud    |
| Mixed 中文/English  | ✅ auto-detected               | ✅              |
| Price              | Free, MIT licensed             | $144/year       |
| Permissions        | Mic + Accessibility only       | Screen, camera… |

## How it works

```
hold ⌥ ──▶ 🎤 record ──▶ 🏠 Whisper (local) ──▶ ✨ polish ──▶ ⌘V insert
```

1. **Hold the right Option key** (configurable) and speak — a floating capsule
   shows Sotto is listening.
2. **Release.** Audio is transcribed locally with
   [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — it never
   leaves your Mac.
3. The transcript is **polished**: filler words (um, uh, 嗯, 呃) removed,
   stutters collapsed, punctuation fixed. With an `ANTHROPIC_API_KEY` set,
   Claude additionally applies your mid-sentence self-corrections and formats
   lists — like Typeless, but opt-in.
4. Text is **pasted into whatever app you're in** and your old clipboard is
   restored.

## Install

Requires macOS and [uv](https://docs.astral.sh/uv/) (`brew install uv`).

```bash
git clone https://github.com/chloe-us/sotto.git
cd sotto
uv sync                 # add --extra ai for Claude polishing
uv run sotto
```

First run downloads the Whisper `base` model (~150 MB) and macOS will prompt
for two permissions:

- **Microphone** — to hear you.
- **Accessibility / Input Monitoring** — to detect the hotkey and paste text.
  (System Settings → Privacy & Security. Grant it to your terminal app.)

That's the whole permission surface. No screen recording, no camera, no cloud.

## Use

- Put your cursor in any text field — Mail, Slack, WeChat, your editor, a
  ChatGPT/Claude prompt box.
- Hold **right ⌥**, say what you want, release.
- 🎙 in the menu bar: switch Whisper model size, polish mode, edit your
  personal dictionary.

### Polish modes

| Mode    | What happens                                                    |
| ------- | --------------------------------------------------------------- |
| `auto`  | Claude if `ANTHROPIC_API_KEY` is set, otherwise local rules     |
| `ai`    | Always Claude (self-corrections, list formatting, tone)         |
| `local` | Offline regex cleanup only — nothing ever leaves your machine   |
| `off`   | Raw Whisper output                                              |

### Personal dictionary

`~/.sotto/dictionary.txt` — one term per line to bias recognition, or a
correction rule:

```
Kubernetes
cloudy tan -> Chloe Tan
```

### Config

`~/.sotto/config.json` — hotkey, model size (`tiny`…`large-v3`), language
(`auto` handles mixed 中英), polish mode.

## Debugging

Transcribe a file without the menu bar app:

```bash
uv run sotto --file some_audio.wav
```

Run tests:

```bash
uv run --extra dev pytest
```

## Roadmap

- [ ] Speak-to-edit: select text, speak an instruction ("make this shorter")
- [ ] Context awareness: adapt tone to the frontmost app
- [ ] Real-time translation mode
- [ ] Windows/Linux support

## License

MIT
