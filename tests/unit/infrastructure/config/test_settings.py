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


from src.infrastructure.config.settings import _load_env_files


class TestEnvFileLocation:
    """Which .env file is loaded, depending on the user data directory and the working directory."""

    @staticmethod
    def _load_marker(user_dir, cwd, monkeypatch):
        """Load the .env files with the given user data dir and cwd, and return the marker value."""
        monkeypatch.setattr("src.infrastructure.config.settings.user_data_dir", lambda: user_dir)
        monkeypatch.chdir(cwd)
        env = {k: v for k, v in os.environ.items() if k != "MENSAGIA_TEST_MARKER"}
        with patch.dict(os.environ, env, clear=True):
            _load_env_files()
            return os.environ.get("MENSAGIA_TEST_MARKER")

    def test_loads_env_from_user_data_dir(self, tmp_path, monkeypatch):
        """The .env in the user data directory is found even when the working directory is elsewhere."""
        user_dir, cwd = tmp_path / "user", tmp_path / "cwd"
        user_dir.mkdir()
        cwd.mkdir()
        (user_dir / ".env").write_text("MENSAGIA_TEST_MARKER=user\n", encoding="utf-8")
        assert self._load_marker(user_dir, cwd, monkeypatch) == "user"

    def test_falls_back_to_working_directory(self, tmp_path, monkeypatch):
        """A .env in the working directory is used when the user data directory has none."""
        user_dir, cwd = tmp_path / "user", tmp_path / "cwd"
        user_dir.mkdir()
        cwd.mkdir()
        (cwd / ".env").write_text("MENSAGIA_TEST_MARKER=cwd\n", encoding="utf-8")
        assert self._load_marker(user_dir, cwd, monkeypatch) == "cwd"

    def test_user_data_dir_takes_precedence_over_working_directory(self, tmp_path, monkeypatch):
        """When both exist, the .env in the user data directory wins."""
        user_dir, cwd = tmp_path / "user", tmp_path / "cwd"
        user_dir.mkdir()
        cwd.mkdir()
        (user_dir / ".env").write_text("MENSAGIA_TEST_MARKER=user\n", encoding="utf-8")
        (cwd / ".env").write_text("MENSAGIA_TEST_MARKER=cwd\n", encoding="utf-8")
        assert self._load_marker(user_dir, cwd, monkeypatch) == "user"

    def test_missing_user_data_dir_is_not_an_error(self, tmp_path, monkeypatch):
        """A user data directory that does not exist yet (first run on macOS) is skipped silently."""
        cwd = tmp_path / "cwd"
        cwd.mkdir()
        assert self._load_marker(tmp_path / "missing", cwd, monkeypatch) is None


from src.infrastructure.config.settings import load_app_version_override, load_check_updates


class TestUpdateSettings:
    """Covers the .env settings of the new version notice."""

    @staticmethod
    def _load(loader, variables: dict):
        """Call *loader* with only the given notice variables in the environment."""
        env = {k: v for k, v in os.environ.items() if k not in ("MENSAGIA_CHECK_UPDATES", "MENSAGIA_APP_VERSION")}
        env.update(variables)
        with patch("src.infrastructure.config.settings._load_env_files"):
            with patch.dict(os.environ, env, clear=True):
                return loader()

    def test_checks_for_updates_by_default(self):
        """Checks for a new version when MENSAGIA_CHECK_UPDATES is absent."""
        assert self._load(load_check_updates, {}) is True

    def test_false_turns_the_check_off(self):
        """Does not check for a new version when MENSAGIA_CHECK_UPDATES is false, in any case."""
        assert self._load(load_check_updates, {"MENSAGIA_CHECK_UPDATES": " False "}) is False

    def test_any_other_value_keeps_the_check(self):
        """Keeps checking for any value other than false."""
        assert self._load(load_check_updates, {"MENSAGIA_CHECK_UPDATES": "true"}) is True

    def test_no_version_override_by_default(self):
        """Returns None when MENSAGIA_APP_VERSION is absent."""
        assert self._load(load_app_version_override, {}) is None

    def test_reads_the_version_override(self):
        """Returns MENSAGIA_APP_VERSION without surrounding spaces."""
        assert self._load(load_app_version_override, {"MENSAGIA_APP_VERSION": " v1.3.0 "}) == "v1.3.0"

    def test_an_empty_override_is_none(self):
        """Treats an empty MENSAGIA_APP_VERSION as not set."""
        assert self._load(load_app_version_override, {"MENSAGIA_APP_VERSION": ""}) is None
