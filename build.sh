#!/usr/bin/env bash
# Build the macOS executables of Mensagia Attachment Mailer.
#
# macOS counterpart of build.bat. PyInstaller cannot cross-compile, so this
# script must run on a Mac; the resulting binaries only work on the same
# processor family (Apple Silicon or Intel) as the machine that built them.
#
# Output, in dist/ (<arch> is apple-silicon or intel, detected automatically):
#   mensagia-mailer-gui-macos-<arch>.zip      graphical app (.app bundle)
#   mensagia-mailer-console-macos-<arch>.zip  console executable
set -euo pipefail

# Always work from the repository root, wherever the script is called from
cd "$(dirname "$0")"

echo "================================================"
echo " Building Mensagia Attachment Mailer (macOS)"
echo "================================================"

# Use the project's virtual environment when there is one (local builds);
# CI runners provide Python directly, without a .venv
if [ -f .venv/bin/activate ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi
PYTHON="${PYTHON:-python3}"

# Name the zips after the processor family, because an Apple Silicon build
# does not run on an Intel Mac and users must pick the right download
case "$(uname -m)" in
    arm64)  ARCH="apple-silicon" ;;
    x86_64) ARCH="intel" ;;
    *)      echo "ERROR: unsupported architecture $(uname -m)"; exit 1 ;;
esac
echo "Architecture: $ARCH"

# Install/update dependencies
echo "Installing dependencies..."
"$PYTHON" -m pip install -r requirements-dev.txt -q

# Clean previous builds
rm -rf dist build mensagia-mailer-gui.spec mensagia-mailer-console.spec

# Generate the .icns icon from the PNG with the native macOS tools, so no
# binary icon file has to be kept in the repository. The iconset needs every
# standard size; sips scales the source image to each of them
ICONSET="build/icon.iconset"
mkdir -p "$ICONSET"
for size in 16 32 128 256 512; do
    sips -z "$size" "$size" assets/icon.png --out "$ICONSET/icon_${size}x${size}.png" >/dev/null
    double=$((size * 2))
    sips -z "$double" "$double" assets/icon.png --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o build/icon.icns

# Build the GUI as a .app bundle. --onedir rather than --onefile: PyInstaller
# deprecates one-file .app bundles on macOS
echo
echo "Building GUI version..."
"$PYTHON" -m PyInstaller \
    --onedir \
    --windowed \
    --noconfirm \
    --name "mensagia-mailer-gui" \
    --icon build/icon.icns \
    --hidden-import customtkinter \
    --hidden-import PIL \
    --collect-all customtkinter \
    main_gui.py

# Build the console version as a single executable, like on Windows
echo
echo "Building console version..."
"$PYTHON" -m PyInstaller \
    --onefile \
    --console \
    --noconfirm \
    --name "mensagia-mailer-console" \
    main.py

# Zip both for distribution. ditto keeps the symlinks and permissions inside
# the .app bundle and the console binary's executable bit, which a plain zip
# can lose, leaving an app that refuses to start
echo
echo "Packaging..."
GUI_ZIP="mensagia-mailer-gui-macos-$ARCH.zip"
CONSOLE_ZIP="mensagia-mailer-console-macos-$ARCH.zip"
ditto -c -k --keepParent dist/mensagia-mailer-gui.app "dist/$GUI_ZIP"
ditto -c -k --keepParent dist/mensagia-mailer-console "dist/$CONSOLE_ZIP"

echo
echo "================================================"
echo " Build complete!"
echo " Files in: dist/"
echo "   $GUI_ZIP      (graphical mode)"
echo "   $CONSOLE_ZIP  (console mode)"
echo
echo " IMPORTANT: Place a .env file in the folder"
echo " 'Mensagia Mailer' inside your home folder"
echo " with your API token:"
echo "   MENSAGIA_API_TOKEN=your_token_here"
echo "================================================"
