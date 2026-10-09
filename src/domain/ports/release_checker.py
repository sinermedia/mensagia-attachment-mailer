from abc import ABC, abstractmethod


class ReleaseChecker(ABC):
    """Port that defines how to find out the latest published release.

    The application tells the user when a newer version than the running one
    has been published. This abstract class keeps that decision independent
    of where the releases are published and how they are fetched.
    """

    @abstractmethod
    def latest_version(self) -> str | None:
        """Return the version of the latest published release.

        Implementations must never raise: being unable to find out the latest
        release is not an error for the user, who simply gets no notice.

        Returns:
            The release version, such as 'v1.5.0', or None when it cannot be
            found out (no connection, no answer in time, unreadable answer).
        """
        pass
