import requests
from requests.exceptions import RequestException
from src.domain.ports.release_checker import ReleaseChecker


# Public repository: the latest release can be read without a token. Drafts
# are never returned by this endpoint, so an unpublished release is not seen
LATEST_RELEASE_API_URL = "https://api.github.com/repos/sinermedia/mensagia-attachment-mailer/releases/latest"

# Page shown to the user to download the new version
RELEASES_PAGE_URL = "https://github.com/sinermedia/mensagia-attachment-mailer/releases/latest"

# Seconds to wait for GitHub; the check is a courtesy and must stay unnoticed
TIMEOUT_SECONDS = 3


class GitHubReleaseChecker(ReleaseChecker):
    """Finds out the latest release of the application published on GitHub.

    Asks the GitHub REST API for the latest release of the public repository
    and reads its tag. Every failure (no connection, timeout, error status
    such as the rate limit, unreadable answer) is turned into None, so the
    calling code never has to handle exceptions from this class.
    """

    def latest_version(self) -> str | None:
        """Return the tag of the latest published release.

        Returns:
            The tag name, such as 'v1.5.0', or None when GitHub cannot be
            reached in time or its answer does not hold a tag.
        """
        try:
            response = requests.get(
                LATEST_RELEASE_API_URL,
                headers={"Accept": "application/vnd.github+json"},
                timeout=TIMEOUT_SECONDS,
            )
            if response.status_code != 200:
                return None
            payload = response.json()
        except (RequestException, ValueError):
            # A network error or a body that is not JSON: no notice, no error
            return None

        # Only a text tag is a usable answer; anything else is ignored
        tag = payload.get("tag_name") if isinstance(payload, dict) else None
        return tag if isinstance(tag, str) else None
