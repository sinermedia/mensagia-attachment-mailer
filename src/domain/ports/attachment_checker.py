from abc import ABC, abstractmethod


class AttachmentChecker(ABC):
    """Port that defines how to verify that an attachment URL is reachable.

    Before scheduling an email with a personalised attachment, the application
    checks that the file is publicly accessible so contacts do not receive
    emails with broken links. This abstract class belongs to the domain layer
    and keeps the domain decoupled from the HTTP library used for the check.
    """

    @abstractmethod
    def is_accessible(self, url: str) -> bool:
        """Check whether the resource at the given URL can be downloaded.

        Args:
            url: Fully qualified URL of the file to verify.

        Returns:
            True if the resource is reachable and returns a successful HTTP
            status code; False if the request fails for any reason (network
            error, 404, 403, timeout, etc.).
        """
        pass
