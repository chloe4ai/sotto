#!/usr/bin/env bash
# Build Sotto.app and a drag-to-install DMG. Run on macOS with uv installed.
#
#   bash packaging/build_dmg.sh
#
# Output: dist/Sotto-<version>-macos-<arch>.dmg
set -euo pipefail
cd "$(dirname "$0")/.."

VERSION=$(sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml | head -1)
ARCH=$(uname -m)
VENV="${SOTTO_BUILD_VENV:-/tmp/sotto-build-venv}"
# Build entirely outside the repo: iCloud-synced folders (Desktop/Documents)
# keep re-adding extended attributes mid-build, which breaks codesign.
OUT="${SOTTO_BUILD_OUT:-/tmp/sotto-build}"

# A clean venv keeps dev dependencies out of the bundle.
uv venv "$VENV" --python 3.12 --clear
uv pip install --python "$VENV/bin/python" . pyinstaller

"$VENV/bin/pyinstaller" --noconfirm --clean --windowed --name Sotto \
    --osx-bundle-identifier com.chloetan.sotto \
    --distpath "$OUT/dist" --workpath "$OUT/work" --specpath "$OUT" \
    --collect-all faster_whisper \
    --collect-all ctranslate2 \
    --collect-all onnxruntime \
    --collect-all av \
    --collect-all tokenizers \
    --collect-all sounddevice \
    packaging/pyi_entry.py

APP="$OUT/dist/Sotto.app"
PLIST="$APP/Contents/Info.plist"
# Menu-bar-only app: no Dock icon, no app switcher entry.
/usr/libexec/PlistBuddy -c "Add :LSUIElement bool true" "$PLIST" 2>/dev/null || true
/usr/libexec/PlistBuddy -c \
    "Add :NSMicrophoneUsageDescription string Sotto records your voice while you hold the hotkey and transcribes it on this Mac." \
    "$PLIST" 2>/dev/null || true
# Re-sign (ad-hoc) after the plist edit so the bundle stays launchable.
xattr -cr "$APP"
codesign --force --deep -s - "$APP"

rm -rf "$OUT/dmg"
mkdir "$OUT/dmg"
cp -R "$APP" "$OUT/dmg/"
ln -s /Applications "$OUT/dmg/Applications"
hdiutil create -volname "Sotto" -srcfolder "$OUT/dmg" -ov -format UDZO \
    "$OUT/Sotto-$VERSION-macos-$ARCH.dmg"
echo "Built $OUT/Sotto-$VERSION-macos-$ARCH.dmg"
