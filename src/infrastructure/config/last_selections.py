import json
import sys
from pathlib import Path

_FILE = "last_selections.json"


def _selections_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / _FILE
    return Path(__file__).parents[3] / _FILE


def load_last_selections() -> dict:
    path = _selections_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_last_selections(data: dict) -> None:
    try:
        _selections_path().write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
