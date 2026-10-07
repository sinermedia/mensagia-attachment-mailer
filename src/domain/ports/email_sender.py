from abc import ABC, abstractmethod
from src.domain.entities.email_message import EmailMessage


class EmailSendError(Exception):
    """Base class for failures reported by an EmailSender adapter.

    Subclasses tell the caller what is known about the fate of the email,
    which decides whether it is safe to retry and whether the user must be
    warned about a possible duplicate.
    """


class EmailRejectedError(EmailSendError):
    """The delivery service answered and refused the email.

    Nothing was scheduled, and retrying with the same data would fail again.
    """


class EmailNotSentError(EmailSendError):
    """The request never got processed by the delivery service.

    Nothing was scheduled (e.g. the connection could not be opened, or the
    service asked to slow down), so the email can safely be retried.
    """


class EmailSendUncertainError(EmailSendError):
    """The request may have been processed but no reliable answer arrived.

    The email may or may not have been scheduled (e.g. a response timeout
    after the request was sent). Retrying may create a duplicate, so the
    user must be told which recipient and slot to check.
    """


class EmailSender(ABC):
    """Port that defines how to dispatch an email message.

    This abstract class belongs to the domain layer and specifies the
    contract that any sending adapter must fulfil. The concrete
    implementation lives in the infrastructure layer, keeping the domain
    independent of the Mensagia API or any other delivery mechanism.
    """

    @abstractmethod
    def send(self, message: EmailMessage) -> dict:
        """Send a single email message.

        Args:
            message: The EmailMessage instance containing all the data
                needed to schedule and deliver the email.

        Returns:
            A dictionary with the raw API response. The exact structure
            depends on the concrete implementation, but typically contains
            the assigned message ID and delivery status.

        Raises:
            EmailRejectedError: The service refused the email.
            EmailNotSentError: The request was not processed; safe to retry.
            EmailSendUncertainError: The outcome is unknown; the email may
                have been scheduled.
        """
        pass
