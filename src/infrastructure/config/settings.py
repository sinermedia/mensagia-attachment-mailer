import os
from pathlib import Path
from dotenv import load_dotenv


def load_api_token() -> str | None:
    _load_env_files()
    return os.environ.get("MENSAGIA_API_TOKEN")


def load_language() -> str | None:
    _load_env_files()
    return os.environ.get("MENSAGIA_LANGUAGE") or None


def load_attachment_base_url() -> str | None:
    _load_env_files()
    return os.environ.get("MENSAGIA_ATTACHMENT_BASE_URL") or None


def load_show_ids() -> bool:
    _load_env_files()
    return os.environ.get("MENSAGIA_SHOW_IDS", "false").strip().lower() == "true"


def _load_env_files():
    candidates = [
        Path(".env"),
        Path(__file__).parent.parent.parent.parent / ".env",
    ]
    # When running as PyInstaller bundle, also check next to the .exe
    if hasattr(os, "_MEIPASS"):
        candidates.insert(0, Path(os.path.dirname(os.path.abspath(__file__))) / ".env")
        exe_dir = Path(os.path.dirname(os.path.abspath(os.sys.argv[0])))
        candidates.insert(0, exe_dir / ".env")

    for path in candidates:
        if path.exists():
            load_dotenv(path, override=False)
            return
