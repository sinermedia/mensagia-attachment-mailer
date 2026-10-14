import requests
from requests.exceptions import RequestException, Timeout
from src.domain.ports.attachment_checker import AttachmentChecker


# Seconds to wait for the server on each request of a check
TIMEOUT_SECONDS = 10


class HttpAttachmentChecker(AttachmentChecker):
    """Verifies attachment accessibility by making real HTTP requests.

    Uses an HTTP HEAD request as the primary check because it is faster
    (no body download). Some servers do not support HEAD and return 405
    (Method Not Allowed); in that case the checker falls back to a
    streaming GET request to confirm the file exists without downloading
    the entire content.

    A check that runs out of time is repeated once, since a server that
    is slow for a moment says nothing about the file. All network errors
    (timeout, DNS failure, SSL error, etc.) are otherwise treated as
    inaccessible, so the calling code never has to handle exceptions from
    this class.
    """

    def is_accessible(self, url: str) -> bool:
        """Check whether the resource at the given URL can be downloaded.

        Makes the check once and, only if it timed out, a second time. An
        error status (404, 403...) is never retried: the file is missing or
        not public, and asking again does not change that.

        Args:
            url: Fully qualified URL of the file to verify.

        Returns:
            True if the resource returns HTTP 200; False for any other
            status code or if a network exception occurs, including a
            second timeout.
        """
        try:
            try:
                return self._check(url)
            except Timeout:
                # A single retry: a file that really is unreachable would
                # otherwise hold the send for another full timeout each time
                return self._check(url)
        except RequestException:
            # Any network-level error means the attachment is not accessible
            return False

    def _check(self, url: str) -> bool:
        """Make a single check of the URL, letting network errors through.

        Sends an HTTP HEAD request first. If the server responds with 405
        (Method Not Allowed) falls back to a streaming GET request to
        confirm reachability without downloading the full content.

        Args:
            url: Fully qualified URL of the file to verify.

        Returns:
            True if the resource returns HTTP 200, False otherwise.

        Raises:
            requests.exceptions.RequestException: When the request fails,
                such as Timeout when the server takes too long to answer.
        """
        # HEAD is preferred because it avoids downloading the file body
        response = requests.head(url, timeout=TIMEOUT_SECONDS, allow_redirects=True)

        if response.status_code == 405:
            # Server does not support HEAD — fall back to a streaming GET
            # to avoid downloading the full file while still confirming
            # that the resource exists
            with requests.get(url, timeout=TIMEOUT_SECONDS, allow_redirects=True, stream=True) as r:
                return r.status_code == 200

        return response.status_code == 200
