"""Floating capsule HUD — the little pill that shows Sotto is listening.

A borderless, non-activating NSPanel pinned above all windows at the bottom
center of the screen. It never steals focus from the app you're dictating into.
All AppKit calls are marshalled onto the main thread.
"""

import threading

import objc
from AppKit import (
    NSColor,
    NSFont,
    NSMakeRect,
    NSObject,
    NSPanel,
    NSScreen,
    NSStatusWindowLevel,
    NSTextField,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowStyleMaskBorderless,
    NSWindowStyleMaskNonactivatingPanel,
)

_WIDTH, _HEIGHT, _MARGIN_BOTTOM = 220.0, 36.0, 80.0


class _HudBridge(NSObject):
    """Runs HUD mutations on the AppKit main thread."""

    def init(self):
        self = objc.super(_HudBridge, self).init()
        if self is None:
            return None
        self.panel = None
        return self

    def _ensurePanel(self):
        if self.panel is not None:
            return
        main_screen = NSScreen.mainScreen() or (NSScreen.screens() or [None])[0]
        if main_screen is None:  # headless — nothing to draw on
            return
        screen = main_screen.frame()
        x = (screen.size.width - _WIDTH) / 2
        rect = NSMakeRect(x, _MARGIN_BOTTOM, _WIDTH, _HEIGHT)
        style = NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel
        panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, style, 2, False
        )
        panel.setLevel_(NSStatusWindowLevel)
        panel.setOpaque_(False)
        panel.setBackgroundColor_(NSColor.clearColor())
        panel.setCollectionBehavior_(NSWindowCollectionBehaviorCanJoinAllSpaces)
        panel.setIgnoresMouseEvents_(True)

        content = panel.contentView()
        content.setWantsLayer_(True)
        layer = content.layer()
        layer.setCornerRadius_(_HEIGHT / 2)
        layer.setBackgroundColor_(
            NSColor.colorWithCalibratedWhite_alpha_(0.08, 0.92).CGColor()
        )

        label = NSTextField.alloc().initWithFrame_(
            NSMakeRect(0, (_HEIGHT - 20) / 2, _WIDTH, 20)
        )
        label.setBezeled_(False)
        label.setDrawsBackground_(False)
        label.setEditable_(False)
        label.setSelectable_(False)
        label.setAlignment_(1)  # center
        label.setFont_(NSFont.systemFontOfSize_(13))
        label.setTextColor_(NSColor.whiteColor())
        content.addSubview_(label)

        self.panel = panel
        self.label = label

    def showText_(self, text):
        self._ensurePanel()
        if self.panel is None:
            return
        self.label.setStringValue_(text)
        # Grow the capsule to fit longer messages (e.g. errors).
        self.label.sizeToFit()
        width = max(_WIDTH, self.label.frame().size.width + 44)
        screen = (NSScreen.mainScreen() or NSScreen.screens()[0]).frame()
        x = (screen.size.width - width) / 2
        self.panel.setFrame_display_(
            NSMakeRect(x, _MARGIN_BOTTOM, width, _HEIGHT), True
        )
        self.label.setFrame_(NSMakeRect(0, (_HEIGHT - 20) / 2, width, 20))
        self.panel.orderFrontRegardless()

    def hide_(self, _):
        if self.panel is not None:
            self.panel.orderOut_(None)


class Hud:
    def __init__(self) -> None:
        self._bridge = _HudBridge.alloc().init()
        self._hide_timer: threading.Timer | None = None

    def _show(self, text: str) -> None:
        if self._hide_timer is not None:
            self._hide_timer.cancel()
            self._hide_timer = None
        self._bridge.performSelectorOnMainThread_withObject_waitUntilDone_(
            b"showText:", text, False
        )

    def listening(self) -> None:
        self._show("🔴  Listening…")

    def processing(self) -> None:
        self._show("✨  Polishing…")

    def loading_model(self) -> None:
        self._show("⏳  Loading model…")

    def error(self, text: str, seconds: float = 4.0) -> None:
        """Show an error in the capsule, then auto-hide. This is the fallback
        channel when macOS notifications are unavailable or muted."""
        self._show(f"⚠️  {text}")
        self._hide_timer = threading.Timer(seconds, self.hide)
        self._hide_timer.daemon = True
        self._hide_timer.start()

    def hide(self) -> None:
        if self._hide_timer is not None:
            self._hide_timer.cancel()
            self._hide_timer = None
        self._bridge.performSelectorOnMainThread_withObject_waitUntilDone_(
            b"hide:", None, False
        )
