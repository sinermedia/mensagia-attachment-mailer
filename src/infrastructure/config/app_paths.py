import sys
from pathlib import Path


# Folder created in the user's home directory to hold the app's files on macOS.
# Kept readable because non-technical users must find it in Finder to drop
# their .env file in and to look at the send logs.
MACOS_DATA_DIR_NAME = "Mensagia Mailer"


def user_data_dir() -> Path:
    """Return the directory that holds the user's files for this application.

    The .env file, the logs/ folder, last_selections.json and
    send_progress.json all live in this directory. Its location depends on
    how the application is running:
    - Development (plain Python): the repository root, so the files are easy
      to inspect while working on the code.
    - Bundled with PyInstaller on macOS: ~/Mensagia Mailer. Next to the
      executable is not usable there, because inside a .app bundle that is
      the hidden Contents/MacOS folder, often read-only when the app is
      installed in /Applications.
    - Bundled with PyInstaller elsewhere (Windows): next to the executable,
      so the files survive app updates and sit beside the .exe the user ran.

    The directory is not created here; code that writes into it creates it
    on demand, so merely resolving the location has no side effects.

    Returns:
        Absolute Path of the user data directory.
    """
    # sys.frozen is set by PyInstaller; anything else is a source checkout
    if not getattr(sys, "frozen", False):
        return Path(__file__).parents[3]

    # A visible folder in the home directory, found by path rather than via
    # the working directory, which is / when an app is opened from Finder
    if sys.platform == "darwin":
        return Path.home() / MACOS_DATA_DIR_NAME

    return Path(sys.executable).parent
