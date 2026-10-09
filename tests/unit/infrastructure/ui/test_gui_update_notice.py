from unittest.mock import patch
import pytest
from src.infrastructure.http.github_release_checker import RELEASES_PAGE_URL
from src.infrastructure.ui.i18n import set_language, t
# Reuse the event-loop helper and the Tk availability skip
from tests.unit.infrastructure.ui.test_gui_group_selection import _wait_until, pytestmark  # noqa: F401


def _make_app(tmp_path, monkeypatch, found: str | None):
    """Create a hidden App window whose start-up check reports *found*.

    Args:
        tmp_path: Empty data folder for the window.
        monkeypatch: Pytest monkeypatch fixture.
        found: Newer version the check reports, or None for no notice.

    Returns:
        The App instance, sitting on the token step.
    """
    for module in ("config.last_selections", "config.settings", "logging.send_logger",
                   "persistence.json_send_registry"):
        monkeypatch.setattr(f"src.infrastructure.{module}.user_data_dir", lambda: tmp_path)

    def _fake_check(on_found):
        """Report *found* straight away, as a finished background check would."""
        if found:
            on_found(found)
        return None

    monkeypatch.setattr("src.infrastructure.ui.gui.gui_app.start_update_check", _fake_check)
    set_language("en")
    from src.infrastructure.ui.gui.gui_app import App
    window = App()
    window.withdraw()
    return window


@pytest.fixture
def app_with_update(tmp_path, monkeypatch):
    """Yield a window whose start-up check found v1.5.0, destroyed afterwards."""
    window = _make_app(tmp_path, monkeypatch, "v1.5.0")
    yield window
    window.destroy()


@pytest.fixture
def app_up_to_date(tmp_path, monkeypatch):
    """Yield a window whose start-up check found nothing, destroyed afterwards."""
    window = _make_app(tmp_path, monkeypatch, None)
    yield window
    window.destroy()


class TestGuiUpdateNotice:
    """Covers the small new version notice at the bottom of the token step."""

    def test_shows_the_new_version(self, app_with_update):
        """Shows the new version on the token step once the check reports it."""
        expected = t("update_available", version="v1.5.0")
        assert _wait_until(app_with_update, lambda: app_with_update._update_label.cget("text") == expected)
        assert app_with_update._update_link.cget("text") == RELEASES_PAGE_URL
        assert app_with_update._update_label.winfo_manager() == "pack"

    def test_shows_nothing_when_up_to_date(self, app_up_to_date):
        """Leaves the notice out of the token step when there is no newer version."""
        app_up_to_date.update()
        assert app_up_to_date._update_label.winfo_manager() == ""
        assert app_up_to_date._update_link.winfo_manager() == ""

    def test_keeps_the_notice_after_changing_the_language(self, app_with_update):
        """Shows the notice again, translated, after the UI is rebuilt in another language."""
        assert _wait_until(app_with_update, lambda: app_with_update._update_label.cget("text") != "")
        app_with_update._lang_var.set("es")
        app_with_update._on_language_change()
        app_with_update.update()
        assert app_with_update._update_label.cget("text") == t("update_available", version="v1.5.0")
        assert app_with_update._update_label.winfo_manager() == "pack"
        set_language("en")

    def test_the_link_opens_the_download_page(self, app_with_update):
        """Opens the latest release page in the browser when the link is clicked."""
        with patch("src.infrastructure.ui.gui.gui_app.webbrowser.open") as fake_open:
            app_with_update._open_releases_page()
        fake_open.assert_called_once_with(RELEASES_PAGE_URL)
