import os
from unittest.mock import patch
from src.infrastructure.config.settings import load_language


def test_load_language_returns_none_when_not_set():
    """Returns None when MENSAGIA_LANGUAGE is absent from the environment."""
    with patch("src.infrastructure.config.settings._load_env_files"):
        env = {k: v for k, v in os.environ.items() if k != "MENSAGIA_LANGUAGE"}
        with patch.dict(os.environ, env, clear=True):
            assert load_language() is None


def test_load_language_returns_value_when_set():
    """Returns the configured language code when MENSAGIA_LANGUAGE is set."""
    with patch("src.infrastructure.config.settings._load_env_files"):
        with patch.dict(os.environ, {"MENSAGIA_LANGUAGE": "ca"}):
            assert load_language() == "ca"


def test_load_language_returns_value_for_any_language_code():
    """Returns the correct code for every supported language."""
    for code in ("es", "ca", "gl", "eu", "en"):
        with patch("src.infrastructure.config.settings._load_env_files"):
            with patch.dict(os.environ, {"MENSAGIA_LANGUAGE": code}):
                assert load_language() == code


from src.infrastructure.config.settings import load_attachment_base_url, load_show_ids


def test_load_attachment_base_url_returns_none_when_not_set():
    """Returns None when MENSAGIA_ATTACHMENT_BASE_URL is absent from the environment."""
    with patch("src.infrastructure.config.settings._load_env_files"):
        env = {k: v for k, v in os.environ.items() if k != "MENSAGIA_ATTACHMENT_BASE_URL"}
        with patch.dict(os.environ, env, clear=True):
            assert load_attachment_base_url() is None


def test_load_attachment_base_url_returns_value_when_set():
    """Returns the configured URL when MENSAGIA_ATTACHMENT_BASE_URL is set."""
    with patch("src.infrastructure.config.settings._load_env_files"):
        with patch.dict(os.environ, {"MENSAGIA_ATTACHMENT_BASE_URL": "https://example.com/files"}):
            assert load_attachment_base_url() == "https://example.com/files"


def test_load_show_ids_returns_false_by_default():
    """Returns False when MENSAGIA_SHOW_IDS is absent from the environment."""
    with patch("src.infrastructure.config.settings._load_env_files"):
        env = {k: v for k, v in os.environ.items() if k != "MENSAGIA_SHOW_IDS"}
        with patch.dict(os.environ, env, clear=True):
            assert load_show_ids() is False


def test_load_show_ids_returns_false_when_set_to_false():
    """Returns False when MENSAGIA_SHOW_IDS is explicitly 'false'."""
    with patch("src.infrastructure.config.settings._load_env_files"):
        with patch.dict(os.environ, {"MENSAGIA_SHOW_IDS": "false"}):
            assert load_show_ids() is False


def test_load_show_ids_returns_true_when_set_to_true():
    """Returns True when MENSAGIA_SHOW_IDS is set to 'true'."""
    with patch("src.infrastructure.config.settings._load_env_files"):
        with patch.dict(os.environ, {"MENSAGIA_SHOW_IDS": "true"}):
            assert load_show_ids() is True
