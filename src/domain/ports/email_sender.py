from abc import ABC, abstractmethod
from src.domain.entities.email_message import EmailMessage


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
            Any exception raised by the concrete adapter if the delivery
            attempt fails (network error, API error, etc.).
        """
        pass
