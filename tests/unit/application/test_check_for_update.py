from unittest.mock import MagicMock
from src.application.use_cases.check_for_update import CheckForUpdateUseCase


def _use_case(latest: str | None) -> tuple[CheckForUpdateUseCase, MagicMock]:
    """Build the use case over a release checker that reports *latest*.

    Args:
        latest: Version the fake checker returns as the latest release.

    Returns:
        The use case and the fake checker, to inspect its calls.
    """
    checker = MagicMock()
    checker.latest_version.return_value = latest
    return CheckForUpdateUseCase(checker), checker


class TestCheckForUpdate:
    """Covers finding out whether a newer release than the running one has been published."""

    def test_returns_a_newer_release(self):
        """Returns the latest release when it is newer than the running version."""
        use_case, _ = _use_case("v1.5.0")
        assert use_case.execute("v1.4.0") == "v1.5.0"

    def test_returns_none_when_up_to_date(self):
        """Returns None when the running version is the latest release."""
        use_case, _ = _use_case("v1.4.0")
        assert use_case.execute("v1.4.0") is None

    def test_returns_none_when_the_release_is_older(self):
        """Returns None when the running version is newer than the latest release."""
        use_case, _ = _use_case("v1.3.1")
        assert use_case.execute("v1.4.0") is None

    def test_returns_none_when_the_latest_release_is_unknown(self):
        """Returns None when the latest release could not be found out."""
        use_case, _ = _use_case(None)
        assert use_case.execute("v1.4.0") is None

    def test_does_not_ask_for_a_development_version(self):
        """Does not query the releases at all when running a development version."""
        use_case, checker = _use_case("v1.5.0")
        assert use_case.execute("dev") is None
        checker.latest_version.assert_not_called()
