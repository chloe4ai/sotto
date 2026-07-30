"""macOS permission checks.

pynput needs the running process (your terminal, when launched with `uv run`)
to be trusted for Accessibility — otherwise the hotkey listener starts but
never receives events, which looks like "nothing happens when I hold the key".
"""

import subprocess

ACCESSIBILITY_PANE = (
    "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
)
MICROPHONE_PANE = (
    "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone"
)


def accessibility_trusted(prompt: bool = False) -> bool:
    """Whether this process may monitor input. With prompt=True, macOS also
    shows its own dialog and adds the app to the Accessibility list."""
    try:
        if prompt:
            from ApplicationServices import (
                AXIsProcessTrustedWithOptions,
                kAXTrustedCheckOptionPrompt,
            )

            return bool(
                AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: True})
            )
        from ApplicationServices import AXIsProcessTrusted

        return bool(AXIsProcessTrusted())
    except Exception:
        return True  # if the check itself is unavailable, don't block the app


def open_accessibility_settings() -> None:
    subprocess.run(["open", ACCESSIBILITY_PANE], check=False)


def open_microphone_settings() -> None:
    subprocess.run(["open", MICROPHONE_PANE], check=False)


def microphone_ok() -> tuple[bool, str]:
    """Try to open the default input device for a moment."""
    try:
        import sounddevice as sd

        with sd.InputStream(samplerate=16_000, channels=1, dtype="float32"):
            pass
        return True, "microphone accessible"
    except Exception as exc:
        return False, str(exc)
