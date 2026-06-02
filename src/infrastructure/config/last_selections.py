import json
import sys
from pathlib import Path


# Name of the JSON file that persists the user's last UI selections
_FILE = "last_selections.json"


def _selections_path() -> Path:
    """Return the absolute path to the last_selections.json file.

    The file location depends on whether the application is running as a
    plain Python script or as a PyInstaller-packaged executable:
    - Frozen (PyInstaller): next to the .exe so it survives app updates.
    - Development: at the repository root (three levels above this file)
      so it is convenient to inspect and is not buried inside the package.

    Returns:
        Path object pointing to the last_selections.json file.
    """
    # sys.frozen is set by PyInstaller; use the executable's directory
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / _FILE
    # In development the repo root is four package levels above this file
    return Path(__file__).parents[3] / _FILE


def load_last_selections() -> dict:
    """Load the previously saved UI selections from disk.

    Reads and parses the last_selections.json file. Returns an empty dict
    if the file does not exist (first run) or if the content is not valid
    JSON (corrupted file). Errors are swallowed silently so that a corrupt
    file never prevents the application from starting.

    Returns:
        A dictionary with the saved selection keys and values, or an empty
        dict if the file is missing or unreadable.
    """
    path = _selections_path()

    # File is absent on first run — treat as if no selections were saved
    if not path.exists():
        return {}

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        # Corrupt or unreadable file — return a safe empty state
        return {}


def save_last_selections(data: dict) -> None:
    """Persist the current UI selections to disk for the next session.

    Writes the provided dictionary as pretty-printed JSON to the
    last_selections.json file. Write errors are silently ignored so that
    a read-only file system or permissions issue never causes the app to
    crash — the worst outcome is that preferences are not remembered.

    Args:
        data: Dictionary of selection keys and values to persist.
            Expected keys: 'template_id', 'sender_id', 'agenda_id',
            'field_id', 'certified'.
    """
    try:
        _selections_path().write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except Exception:
        # Silently ignore write failures — preference persistence is best-effort
        pass
