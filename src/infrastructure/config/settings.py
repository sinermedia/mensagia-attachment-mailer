import os
from pathlib import Path
from dotenv import load_dotenv


def load_api_token() -> str | None:
    """Load the Mensagia API token from environment variables or a .env file.

    Reads the MENSAGIA_API_TOKEN environment variable after loading any
    available .env file. Returns None when the variable is not set, which
    causes the application to prompt the user for the token at startup.

    Returns:
        The API token string, or None if not configured.
    """
    _load_env_files()
    return os.environ.get("MENSAGIA_API_TOKEN")


def load_language() -> str | None:
    """Load the UI language code from environment variables or a .env file.

    Reads the MENSAGIA_LANGUAGE environment variable. When set, the
    application uses this language instead of auto-detecting from the OS
    locale or prompting the user. Accepted values: 'es', 'ca', 'gl', 'eu', 'en'.

    Returns:
        A two-letter language code string, or None if not configured.
    """
    _load_env_files()
    return os.environ.get("MENSAGIA_LANGUAGE") or None


def load_attachment_base_url() -> str | None:
    """Load the base URL for relative attachment paths from environment variables.

    Reads the MENSAGIA_ATTACHMENT_BASE_URL environment variable. When set,
    this URL is prepended to any relative attachment value stored in a
    contact's extra field (e.g. a filename like 'contract_42.pdf' becomes
    'https://cdn.example.com/docs/contract_42.pdf').

    Returns:
        The base URL string, or None if not configured.
    """
    _load_env_files()
    return os.environ.get("MENSAGIA_ATTACHMENT_BASE_URL") or None


def load_show_ids() -> bool:
    """Load the flag that controls whether internal IDs are shown in the UI.

    Reads the MENSAGIA_SHOW_IDS environment variable. When True, the UI
    displays the Mensagia numeric IDs next to templates, senders, groups,
    and extra fields — useful for debugging but distracting for end users.

    Returns:
        True if MENSAGIA_SHOW_IDS is set to 'true' (case-insensitive);
        False in all other cases including when the variable is absent.
    """
    _load_env_files()
    return os.environ.get("MENSAGIA_SHOW_IDS", "false").strip().lower() == "true"


def _load_env_files():
    """Locate and load the nearest .env file without overriding existing env vars.

    Searches a list of candidate paths in priority order and loads the first
    one found. Using override=False means that variables already set in the
    process environment (e.g. by the OS or a CI system) take precedence over
    the .env file. This function is called at the start of every public
    loader so that the first call triggers the file load and subsequent calls
    are effectively no-ops because dotenv skips already-set variables.

    Candidate locations checked in order:
    1. Next to the .exe (PyInstaller bundle, by executable directory).
    2. Next to the .exe (PyInstaller bundle, by argv[0]).
    3. Current working directory ('.env').
    4. Repository root (four parent directories up from this file).
    """
    candidates = [
        Path(".env"),
        Path(__file__).parent.parent.parent.parent / ".env",
    ]

    # When running as a PyInstaller bundle the working directory may differ
    # from the executable location, so add paths relative to the bundle
    if hasattr(os, "_MEIPASS"):
        candidates.insert(0, Path(os.path.dirname(os.path.abspath(__file__))) / ".env")
        exe_dir = Path(os.path.dirname(os.path.abspath(os.sys.argv[0])))
        candidates.insert(0, exe_dir / ".env")

    # Load the first .env file found; skip missing files silently
    for path in candidates:
        if path.exists():
            load_dotenv(path, override=False)
            return
