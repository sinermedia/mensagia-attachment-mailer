import json
from pathlib import Path

from src.infrastructure.config.app_paths import user_data_dir


# Name of the JSON file that persists the user's last UI selections
_FILE = "last_selections.json"


def _selections_path() -> Path:
    """Return the absolute path to the last_selections.json file.

    The file lives in the shared user data directory: next to the .exe on
    Windows, in ~/Mensagia Mailer on macOS, or at the repository root when
    running from source (see user_data_dir).

    Returns:
        Path object pointing to the last_selections.json file.
    """
    return user_data_dir() / _FILE


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
    # The user data directory may not exist yet: on macOS it is a folder in
    # the home directory that nothing creates before the first save
    try:
        path = _selections_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        # Silently ignore write failures — preference persistence is best-effort
        pass
