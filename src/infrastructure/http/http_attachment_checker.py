import requests
from requests.exceptions import RequestException
from src.domain.ports.attachment_checker import AttachmentChecker


class HttpAttachmentChecker(AttachmentChecker):
    """Verifies attachment accessibility by making real HTTP requests.

    Uses an HTTP HEAD request as the primary check because it is faster
    (no body download). Some servers do not support HEAD and return 405
    (Method Not Allowed); in that case the checker falls back to a
    streaming GET request to confirm the file exists without downloading
    the entire content.

    All network errors (timeout, DNS failure, SSL error, etc.) are
    treated as inaccessible, so the calling code never has to handle
    exceptions from this class.
    """

    def is_accessible(self, url: str) -> bool:
        """Check whether the resource at the given URL can be downloaded.

        Sends an HTTP HEAD request first. If the server responds with 405
        (Method Not Allowed) falls back to a streaming GET request to
        confirm reachability without downloading the full content. Any
        network exception is caught and treated as False.

        Args:
            url: Fully qualified URL of the file to verify.

        Returns:
            True if the resource returns HTTP 200; False for any other
            status code or if a network exception occurs.
        """
        try:
            # HEAD is preferred because it avoids downloading the file body
            response = requests.head(url, timeout=10, allow_redirects=True)

            if response.status_code == 405:
                # Server does not support HEAD — fall back to a streaming GET
                # to avoid downloading the full file while still confirming
                # that the resource exists
                with requests.get(url, timeout=10, allow_redirects=True, stream=True) as r:
                    return r.status_code == 200

            return response.status_code == 200

        except RequestException:
            # Any network-level error means the attachment is not accessible
            return False
