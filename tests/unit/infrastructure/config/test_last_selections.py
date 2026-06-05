import json
from unittest.mock import patch
from src.infrastructure.config.last_selections import load_last_selections, save_last_selections


def test_load_returns_empty_dict_when_file_missing(tmp_path):
    """Returns an empty dict when last_selections.json does not exist yet (first run)."""
    f = tmp_path / "last_selections.json"
    with patch("src.infrastructure.config.last_selections._selections_path", return_value=f):
        assert load_last_selections() == {}


def test_load_returns_saved_data(tmp_path):
    """Returns the correct data when last_selections.json exists and is valid JSON."""
    f = tmp_path / "last_selections.json"
    f.write_text(json.dumps({"template_id": "42", "certified": 1}), encoding="utf-8")
    with patch("src.infrastructure.config.last_selections._selections_path", return_value=f):
        data = load_last_selections()
    assert data["template_id"] == "42"
    assert data["certified"] == 1


def test_load_returns_empty_dict_on_invalid_json(tmp_path):
    """Returns an empty dict instead of raising when the file contains invalid JSON."""
    f = tmp_path / "last_selections.json"
    f.write_text("not valid json", encoding="utf-8")
    with patch("src.infrastructure.config.last_selections._selections_path", return_value=f):
        assert load_last_selections() == {}


def test_save_writes_all_fields(tmp_path):
    """All provided fields are persisted to the JSON file."""
    f = tmp_path / "last_selections.json"
    payload = {"template_id": "1", "sender_id": "2", "agenda_id": "3", "field_id": "4", "certified": 0}
    with patch("src.infrastructure.config.last_selections._selections_path", return_value=f):
        save_last_selections(payload)
    data = json.loads(f.read_text(encoding="utf-8"))
    assert data == payload


def test_save_overwrites_previous(tmp_path):
    """A second save replaces the previous file content completely."""
    f = tmp_path / "last_selections.json"
    with patch("src.infrastructure.config.last_selections._selections_path", return_value=f):
        save_last_selections({"template_id": "1"})
        save_last_selections({"template_id": "99"})
    assert json.loads(f.read_text())["template_id"] == "99"


def test_save_is_silent_on_write_error(tmp_path):
    """A write error (e.g. missing directory) does not raise an exception."""
    bad_path = tmp_path / "nonexistent_dir" / "last_selections.json"
    with patch("src.infrastructure.config.last_selections._selections_path", return_value=bad_path):
        save_last_selections({"template_id": "1"})  # must not raise
