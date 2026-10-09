import threading
from unittest.mock import patch
import pytest
from src.infrastructure.http.github_release_checker import RELEASES_PAGE_URL
from src.infrastructure.ui import update_notice
from src.infrastructure.ui.console import console_app
from src.infrastructure.ui.i18n import set_language
from src.infrastructure.ui.update_notice import start_update_check, update_notice_text


@pytest.fixture(autouse=True)
def _english_ui():
    """Pin the UI language so assertions on the notice text are deterministic."""
    set_language("en")


def _run_check(enabled: bool, current: str, latest: str | None) -> list[str]:
    """Run the start-up check to the end and collect what it reports.

    Args:
        enabled: Value of the MENSAGIA_CHECK_UPDATES setting.
        current: Version the running application reports.
        latest: Latest release GitHub reports.

    Returns:
        The versions handed to the on_found callback.
    """
    found = []
    with patch.object(update_notice, "load_check_updates", return_value=enabled), \
            patch.object(update_notice, "current_version", return_value=current), \
            patch.object(update_notice.GitHubReleaseChecker, "latest_version", return_value=latest):
        check = start_update_check(found.append)
        if check:
            check.join(5)
    return found


class TestStartUpdateCheck:
    """Covers the background check for a new version when the app starts."""

    def test_reports_a_newer_release(self):
        """Hands the newer release to the callback."""
        assert _run_check(True, "v1.4.0", "v1.5.0") == ["v1.5.0"]

    def test_stays_quiet_when_up_to_date(self):
        """Does not call the callback when the running version is the latest one."""
        assert _run_check(True, "v1.4.0", "v1.4.0") == []

    def test_stays_quiet_when_github_does_not_answer(self):
        """Does not call the callback when the latest release cannot be found out."""
        assert _run_check(True, "v1.4.0", None) == []

    def test_stays_quiet_for_a_development_version(self):
        """Does not report anything when running from the source code."""
        assert _run_check(True, "dev", "v1.5.0") == []

    def test_does_nothing_when_turned_off(self):
        """Starts no check at all when MENSAGIA_CHECK_UPDATES is false."""
        with patch.object(update_notice, "load_check_updates", return_value=False), \
                patch.object(update_notice.GitHubReleaseChecker, "latest_version") as fake_latest:
            assert start_update_check(lambda version: None) is None
        fake_latest.assert_not_called()

    def test_runs_in_the_background(self):
        """Returns at once while GitHub is still being asked, so start-up is never delayed."""
        answer = threading.Event()

        def _slow_latest(_self):
            answer.wait(5)
            return "v1.5.0"

        found = []
        with patch.object(update_notice, "load_check_updates", return_value=True), \
                patch.object(update_notice, "current_version", return_value="v1.4.0"), \
                patch.object(update_notice.GitHubReleaseChecker, "latest_version", _slow_latest):
            check = start_update_check(found.append)
            assert check.is_alive() and found == []
            answer.set()
            check.join(5)
        assert found == ["v1.5.0"]


class TestUpdateNoticeText:
    """Covers the wording of the notice."""

    def test_names_the_version_and_the_download_page(self):
        """Names the new version and links to the latest release page."""
        text = update_notice_text("v1.5.0")
        assert "v1.5.0" in text
        assert text.endswith(RELEASES_PAGE_URL)

    def test_the_download_page_is_the_latest_release(self):
        """Links to the page of the latest release of the repository."""
        assert RELEASES_PAGE_URL == "https://github.com/sinermedia/mensagia-attachment-mailer/releases/latest"


class TestConsoleUpdateNotice:
    """Covers the console line shown before asking for the subject."""

    @staticmethod
    def _finished_check() -> threading.Thread:
        """Return a check thread that has already finished."""
        thread = threading.Thread(target=lambda: None)
        thread.start()
        thread.join()
        return thread

    def test_prints_the_notice_when_a_release_was_found(self, capsys):
        """Prints one line with the new version and the download page."""
        console_app._show_update_notice(self._finished_check(), ["v1.5.0"])
        assert update_notice_text("v1.5.0") in capsys.readouterr().out

    def test_prints_nothing_when_up_to_date(self, capsys):
        """Prints nothing when no newer release was found."""
        console_app._show_update_notice(self._finished_check(), [])
        assert capsys.readouterr().out == ""

    def test_prints_nothing_when_the_check_is_off(self, capsys):
        """Prints nothing when no check was started."""
        console_app._show_update_notice(None, [])
        assert capsys.readouterr().out == ""

    def test_does_not_wait_longer_than_the_timeout(self, capsys):
        """Gives up on a check still running after the wait, printing nothing."""
        stop = threading.Event()
        check = threading.Thread(target=stop.wait, daemon=True)
        check.start()
        with patch.object(console_app, "UPDATE_WAIT_SECONDS", 0.05):
            console_app._show_update_notice(check, [])
        stop.set()
        assert capsys.readouterr().out == ""
