import os
from unittest.mock import patch
from src.infrastructure.config.settings import load_language


def test_load_language_returns_none_when_not_set():
    with patch("src.infrastructure.config.settings._load_env_files"):
        env = {k: v for k, v in os.environ.items() if k != "MENSAGIA_LANGUAGE"}
        with patch.dict(os.environ, env, clear=True):
            assert load_language() is None


def test_load_language_returns_value_when_set():
    with patch("src.infrastructure.config.settings._load_env_files"):
        with patch.dict(os.environ, {"MENSAGIA_LANGUAGE": "ca"}):
            assert load_language() == "ca"


def test_load_language_returns_value_for_any_language_code():
    for code in ("es", "ca", "gl", "eu", "en"):
        with patch("src.infrastructure.config.settings._load_env_files"):
            with patch.dict(os.environ, {"MENSAGIA_LANGUAGE": code}):
                assert load_language() == code


from src.infrastructure.config.settings import load_attachment_base_url


def test_load_attachment_base_url_returns_none_when_not_set():
    with patch("src.infrastructure.config.settings._load_env_files"):
        env = {k: v for k, v in os.environ.items() if k != "MENSAGIA_ATTACHMENT_BASE_URL"}
        with patch.dict(os.environ, env, clear=True):
            assert load_attachment_base_url() is None


def test_load_attachment_base_url_returns_value_when_set():
    with patch("src.infrastructure.config.settings._load_env_files"):
        with patch.dict(os.environ, {"MENSAGIA_ATTACHMENT_BASE_URL": "https://example.com/files"}):
            assert load_attachment_base_url() == "https://example.com/files"
