import sys
from pathlib import Path

import pytest

from src.infrastructure.config import app_paths
from src.infrastructure.config.app_paths import MACOS_DATA_DIR_NAME, user_data_dir


# Repository root, four levels above the module under test
REPO_ROOT = Path(app_paths.__file__).parents[3]


@pytest.fixture
def frozen(monkeypatch, tmp_path):
    """Simulate a PyInstaller bundle whose executable lives in tmp_path/bin."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "bin" / "mensagia-mailer-gui"))
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")


class TestUserDataDir:
    """Location of the user's files (.env, logs, selections, send progress) per platform."""

    def test_development_mode_uses_repository_root(self, monkeypatch):
        """Running from source returns the repository root on any platform."""
        monkeypatch.delattr(sys, "frozen", raising=False)
        monkeypatch.setattr(sys, "platform", "darwin")
        assert user_data_dir() == REPO_ROOT

    def test_frozen_on_windows_uses_executable_directory(self, frozen, monkeypatch, tmp_path):
        """A bundled Windows executable keeps its files next to the .exe."""
        monkeypatch.setattr(sys, "platform", "win32")
        assert user_data_dir() == tmp_path / "bin"

    def test_frozen_on_linux_uses_executable_directory(self, frozen, monkeypatch, tmp_path):
        """Platforms other than macOS keep the next-to-the-executable behaviour."""
        monkeypatch.setattr(sys, "platform", "linux")
        assert user_data_dir() == tmp_path / "bin"

    def test_frozen_on_macos_uses_visible_folder_in_home(self, frozen, monkeypatch, tmp_path):
        """A bundled macOS app uses a visible folder in the user's home directory."""
        monkeypatch.setattr(sys, "platform", "darwin")
        assert user_data_dir() == tmp_path / "home" / MACOS_DATA_DIR_NAME

    def test_macos_folder_name_is_user_friendly(self):
        """The macOS folder name is the readable one shown to the user in Finder."""
        assert MACOS_DATA_DIR_NAME == "Mensagia Mailer"

    def test_does_not_create_the_directory(self, frozen, monkeypatch, tmp_path):
        """Resolving the location never touches the filesystem; writers create it on demand."""
        monkeypatch.setattr(sys, "platform", "darwin")
        assert not user_data_dir().exists()
