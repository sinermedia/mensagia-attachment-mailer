from src.domain.app_version import is_newer, parse_version
from src.domain.ports.release_checker import ReleaseChecker


class CheckForUpdateUseCase:
    """Finds out whether a newer release than the running one is available.

    The application is handed over to clients without any record of who uses
    it, so it tells them itself when a new version is published. It only
    reports the version; downloading it is left to the user.

    Attributes:
        release_checker: Port used to find out the latest published release.
    """

    def __init__(self, release_checker: ReleaseChecker):
        """Initialise the use case with the port that knows the releases.

        Args:
            release_checker: Port used to find out the latest published release.
        """
        self.release_checker = release_checker

    def execute(self, current_version: str) -> str | None:
        """Return the latest release when it is newer than *current_version*.

        Args:
            current_version: Version of the running application, such as
                'v1.4.0', or 'dev' when it does not know its version.

        Returns:
            The newer release version, or None when the running version is
            up to date, the latest release cannot be found out, or the
            running version is not a release.
        """
        # A development version cannot be compared with any release, so the
        # releases are not even asked for
        if parse_version(current_version) is None:
            return None

        latest = self.release_checker.latest_version()
        return latest if is_newer(latest, current_version) else None
