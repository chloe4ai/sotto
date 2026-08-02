# 🎙 Sotto

[![CI](https://github.com/chloe4ai/sotto/actions/workflows/ci.yml/badge.svg)](https://github.com/chloe4ai/sotto/actions/workflows/ci.yml)

> *sotto voce* — in a soft voice.
> **Speak softly, never type.** 

Sotto is a privacy-first AI voice dictation tool for macOS and Windows. Hold a
key, speak naturally in any app — Sotto transcribes **on your device**, cleans
up the filler words, and drops polished text right where your cursor is.

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

### In four steps

> Illustrated walkthrough, drawn to match the real UI — run it yourself to see the real thing.

**1 — Launch it.** Sotto sits in your menu bar: pick a model, a polish mode, toggle translate, edit your dictionary.

<img src="docs/step1-menubar.svg" width="760" alt="Sotto in the macOS menu bar with its dropdown menu open">

**2 — Hold right ⌥ and just talk.** A floating capsule shows Sotto is listening — in any app, any text field.

<img src="docs/step2-hold-speak.svg" width="760" alt="Floating Listening capsule while dictating into a mail compose window">

**3 — Release. Sotto polishes.** Fillers dropped, self-corrections applied, punctuation fixed — on device, or via Claude if you opt in.

<img src="docs/step3-polish.svg" width="760" alt="Raw speech with filler words transformed into clean polished text">

**4 — Text appears where your cursor is.** Pasted into the frontmost app; your old clipboard is restored.

<img src="docs/step4-insert.svg" width="760" alt="Polished text inserted into a Slack message box, clipboard restored toast">


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

## Install — download, double-click, done

No terminal needed. Grab the file for your system from the
[**latest release**](https://github.com/chloe4ai/sotto/releases/latest):

### macOS (Apple Silicon) — `Sotto-x.y.z-macos-arm64.dmg`

1. Download the `.dmg` and double-click it.
2. Drag **Sotto** onto the **Applications** folder in the window that opens.
3. Open Sotto from Applications — the first time, **right-click the app →
   Open → Open**. (Sotto isn't notarized with Apple, so a plain double-click
   shows a warning. If macOS still refuses: System Settings → Privacy &
   Security → scroll down → **Open Anyway**.)
4. macOS asks for two permissions — allow both, they are the whole surface:
   **Microphone** (to hear you) and **Accessibility** (to detect the hotkey
   and paste text). After granting Accessibility, quit and reopen Sotto once.
5. Look for 🎙 in the menu bar. Put your cursor in any text field, hold
   **right ⌥**, speak, release.

> Intel Macs: no prebuilt DMG yet — use [install from source](#install-from-source-developers).

### Windows 10/11 — `Sotto.exe` (beta)

1. Download `Sotto.exe` and double-click it. Nothing to install — it's a
   portable app (first start takes ~20–30 s while it unpacks itself).
2. If SmartScreen shows "Windows protected your PC", click **More info →
   Run anyway** (Sotto is open source but not code-signed).
3. Find the round Sotto icon in the system tray (bottom-right). Put your
   cursor in any text field, hold **right Alt**, speak, release.
4. The first dictation downloads the speech model (~150 MB) — internet is
   needed that one time; everything runs on your PC afterwards.

Both builds are unsigned because there's no paid developer certificate behind
this project — that's what the security prompts are about, not malware. If in
doubt, read the code or build from source below.

## Install from source (developers)

Requires macOS 11+ (Apple Silicon or Intel) or Windows 10/11, and
[uv](https://docs.astral.sh/uv/) (`brew install uv`). Python is fetched
automatically if needed — any 3.11–3.14 works.

```bash
git clone https://github.com/chloe4ai/sotto.git
cd sotto
uv sync                 # add --extra ai for Claude polishing
uv run sotto
```

Or, without cloning:

```bash
uv tool install git+https://github.com/chloe4ai/sotto
sotto
```

First run downloads the Whisper `base` model (~150 MB, one-time; everything
runs offline after that) and macOS will prompt for two permissions:

- **Microphone** — to hear you.
- **Accessibility** — to detect the hotkey and paste text.

Grant both to **the app you launch sotto from** (Terminal, iTerm, etc.) in
System Settings → Privacy & Security, then **quit and rerun sotto** — macOS
only applies the permission to newly started processes. Sotto pops a reminder
at launch if the permission is missing.

That's the whole permission surface. No screen recording, no camera, no cloud.

Check your setup anytime:

```bash
uv run sotto --doctor
```

## Use

- Put your cursor in any text field — Mail, Slack, WeChat, your editor, a
  ChatGPT/Claude prompt box.
- Hold **right ⌥**, say what you want, release.
- 🎙 in the menu bar: switch Whisper model size, polish mode, translation,
  edit your personal dictionary.

### Translate as you speak

Toggle **Translate to English** in the menu bar (🎙) and Sotto outputs
English no matter what language you speak — 说中文，出英文. This uses
Whisper's built-in translation, so it works fully offline too. Translation
quality scales with model size: `base` is serviceable, `small` or `medium`
is noticeably better. (Whisper only translates *into* English.)

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
(`auto` handles mixed 中英), polish mode, task (`transcribe` or `translate`).

## Troubleshooting

**Nothing happens when I hold the key.** This is almost always the
Accessibility permission. Run `uv run sotto --doctor` — if it shows ✗, enable
your terminal app in System Settings → Privacy & Security → **Accessibility**
(and, on some macOS versions, **Input Monitoring** too), then quit and rerun
sotto. If you see `This process is not trusted!` in the terminal, it's the
same issue. Note: after your terminal app updates, macOS may silently revoke
the permission — toggle it off and on again.

**"Microphone blocked."** The Microphone permission belongs to the app you
launched sotto from (Terminal, iTerm, …), not to sotto itself. Enable that app
under System Settings → Privacy & Security → Microphone, then quit and rerun
sotto. Two gotchas:

- If you ever clicked **Don't Allow** on the mic prompt, macOS never asks
  again — you must flip the toggle manually, or re-trigger the prompt with
  `tccutil reset Microphone com.apple.Terminal` (adjust the bundle id for
  your terminal).
- If your input device is a Bluetooth headset or webcam, try again after
  selecting the built-in mic in System Settings → Sound → Input. (Sotto
  falls back to the device's native sample rate automatically.)

**First dictation is slow or fails offline.** The Whisper model downloads
from Hugging Face on first use (~150 MB for `base`). Stay online for that one
dictation; everything is local afterwards. The HUD shows "⏳ Loading model…"
while this happens.

**Text lands in the wrong app.** Sotto pastes into whatever app has focus
when you release the key. Click into the target text field before speaking.

**Pasting replaced my clipboard.** Sotto restores your previous clipboard
about half a second after pasting (text only — images are not restored).

## Debugging

Transcribe a file without the menu bar app:

```bash
uv run sotto --file some_audio.wav
```

Check permissions and setup:

```bash
uv run sotto --doctor
```

Run tests:

```bash
uv run --extra dev pytest
```

## Roadmap

- [x] Translation mode: speak any language, get English (Whisper translate)
- [ ] Speak-to-edit: select text, speak an instruction ("make this shorter")
- [ ] Context awareness: adapt tone to the frontmost app
- [ ] Translation into languages other than English (via AI polish)
- [x] Windows support (beta — system tray app + portable EXE)
- [ ] Linux support

## License

MIT
