Press a key, speak, press it again — one key per language.

## What's new in {{VERSION}}

- **Press-to-toggle dictation.** Press a dictation key once to start, again to stop. No more holding a key through a long thought; holding it counts as a single press.
- **One key per language.** F13 → 中文, F15 → English by default (`hotkeys` in `~/.sotto/config.json`). The language is passed to Whisper instead of auto-detected, so it can't drift mid-sentence, and the capsule shows which language is recording.
- **Safer edges.** A forgotten stop press is capped at `max_duration` (300 s) and transcribed; modifier keys are rejected as dictation keys; the old `hotkey` setting migrates automatically.

Both the macOS and Windows builds include these changes.

## Downloads

| File | Platform | Notes |
| --- | --- | --- |
| `Sotto-{{VERSION}}-macos-arm64.dmg` | macOS (Apple Silicon) | Drag to Applications. Not notarized — see the README for the **Open Anyway** steps on first launch. |
| `Sotto.exe` | Windows 10/11 (beta) | Portable single file. SmartScreen: More info → Run anyway. First start unpacks for ~20–30 s. |
| `*.sha256` | — | SHA-256 of each installer: `shasum -a 256 -c <file>.sha256` (macOS), `Get-FileHash Sotto.exe` (Windows). |

See the [README](https://github.com/chloe4ai/sotto#install) for install steps and permissions setup.

**Notes**
- Speech recognition runs fully on device. The first dictation downloads the Whisper model (~150 MB), which needs internet once.
- The macOS app is ad-hoc signed only, and the Windows build is not code-signed (no paid developer certificates), hence the security prompts on first launch. The checksums let you confirm the download is the file CI built.
- Both installers are built by GitHub Actions from the tagged commit.
