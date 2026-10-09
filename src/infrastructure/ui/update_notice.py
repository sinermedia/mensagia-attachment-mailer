import threading
from collections.abc import Callable

from src.application.use_cases.check_for_update import CheckForUpdateUseCase
from src.infrastructure.config.app_version import current_version
from src.infrastructure.config.settings import load_check_updates
from src.infrastructure.http.github_release_checker import RELEASES_PAGE_URL, GitHubReleaseChecker
from src.infrastructure.ui.i18n import t


def start_update_check(on_found: Callable[[str], None]) -> threading.Thread | None:
    """Start looking for a newer release in the background.

    The settings are read here, on the calling thread, so the .env file is
    never loaded from two threads at once. GitHub is then asked from a daemon
    thread, which never delays start-up and never keeps the app open.

    Args:
        on_found: Called with the newer version when there is one. It runs
            on the background thread, so a GUI must hand the update over to
            its main thread.

    Returns:
        The thread doing the check, or None when the check is turned off
        with MENSAGIA_CHECK_UPDATES=false.
    """
    if not load_check_updates():
        return None
    version = current_version()

    def _check():
        """Background thread: ask for the latest release and report a newer one."""
        newer = CheckForUpdateUseCase(GitHubReleaseChecker()).execute(version)
        if newer:
            on_found(newer)

    thread = threading.Thread(target=_check, daemon=True)
    thread.start()
    return thread


def update_notice_text(version: str) -> str:
    """Build the one-line notice of a new version, with the download page.

    Args:
        version: The newer version found.

    Returns:
        The translated notice followed by the download page address.
    """
    return f"{t('update_available', version=version)} {RELEASES_PAGE_URL}"
