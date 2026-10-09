from abc import ABC, abstractmethod

from src.domain.entities.recipient import Recipient


class RecipientSource(ABC):
    """Port that defines where the recipients of a bulk send come from.

    Each implementation reads one kind of source (an agenda group, a
    file...) and returns its data as Recipient objects, so the bulk send
    and the interfaces never depend on the source. Implementations decide
    which recipients cannot be sent and why, since that depends on what
    the source can hold.
    """

    @property
    @abstractmethod
    def identity(self) -> str:
        """Identify this source within a campaign.

        Returns:
            A text that is the same whenever the user picks the same source
            again, so an interrupted send can be resumed.
        """

    @property
    @abstractmethod
    def attachment_field(self) -> str:
        """Name the field that holds each recipient's attachment.

        Returns:
            The name of the extra field or column chosen for the attachment.
        """

    @property
    @abstractmethod
    def log_label(self) -> str:
        """Describe this source in the opening line of the log.

        Returns:
            One or more 'name=value' pairs separated by spaces.
        """

    @abstractmethod
    def get_recipients(self) -> list[Recipient]:
        """Read every recipient of the source, sendable or not.

        Returns:
            The recipients in source order. Those that cannot be sent carry
            the reason in skip_reason.
        """
