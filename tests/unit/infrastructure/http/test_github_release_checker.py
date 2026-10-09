from unittest.mock import MagicMock, patch
import pytest
from requests.exceptions import ConnectionError, Timeout
from src.infrastructure.http.github_release_checker import LATEST_RELEASE_API_URL, GitHubReleaseChecker


def _response(status_code: int = 200, payload=None, json_error: Exception | None = None) -> MagicMock:
    """Build a fake HTTP response.

    Args:
        status_code: HTTP status of the response.
        payload: Value returned by json().
        json_error: Exception raised by json() instead, if any.

    Returns:
        A MagicMock that behaves like a requests response.
    """
    response = MagicMock(status_code=status_code)
    if json_error:
        response.json.side_effect = json_error
    else:
        response.json.return_value = payload
    return response


class TestGitHubReleaseChecker:
    """Covers asking GitHub for the latest published release without ever failing."""

    def test_returns_the_tag_of_the_latest_release(self):
        """Returns the tag name of the latest release."""
        with patch("requests.get", return_value=_response(payload={"tag_name": "v1.5.0"})):
            assert GitHubReleaseChecker().latest_version() == "v1.5.0"

    def test_asks_the_latest_release_endpoint_with_a_short_timeout(self):
        """Queries the latest release of the repository and waits 3 seconds at most."""
        with patch("requests.get", return_value=_response(payload={"tag_name": "v1.5.0"})) as fake_get:
            GitHubReleaseChecker().latest_version()

        assert fake_get.call_args[0][0] == LATEST_RELEASE_API_URL
        assert fake_get.call_args[1]["timeout"] == 3

    def test_the_endpoint_is_the_repository_latest_release(self):
        """Points at the latest release of the public repository."""
        assert LATEST_RELEASE_API_URL == (
            "https://api.github.com/repos/sinermedia/mensagia-attachment-mailer/releases/latest"
        )

    @pytest.mark.parametrize("error", [ConnectionError(), Timeout()])
    def test_returns_none_on_a_network_error(self, error):
        """Returns None when there is no connection or GitHub does not answer in time."""
        with patch("requests.get", side_effect=error):
            assert GitHubReleaseChecker().latest_version() is None

    @pytest.mark.parametrize("status_code", [403, 404, 500])
    def test_returns_none_on_an_error_status(self, status_code):
        """Returns None when GitHub answers with an error, such as a rate limit."""
        with patch("requests.get", return_value=_response(status_code, {"message": "error"})):
            assert GitHubReleaseChecker().latest_version() is None

    def test_returns_none_when_the_body_is_not_json(self):
        """Returns None when the answer cannot be read as JSON."""
        with patch("requests.get", return_value=_response(json_error=ValueError("not json"))):
            assert GitHubReleaseChecker().latest_version() is None

    @pytest.mark.parametrize("payload", [{}, {"tag_name": 15}, ["v1.5.0"], None])
    def test_returns_none_when_there_is_no_tag(self, payload):
        """Returns None when the answer does not hold a tag name."""
        with patch("requests.get", return_value=_response(payload=payload)):
            assert GitHubReleaseChecker().latest_version() is None
