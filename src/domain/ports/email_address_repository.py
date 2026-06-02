from abc import ABC, abstractmethod
from src.domain.entities.email_address import EmailAddress


class EmailAddressRepository(ABC):
    """Port that defines how to retrieve verified sender email addresses.

    This abstract class belongs to the domain layer and specifies the
    contract that any data source adapter must fulfil. The concrete
    implementation lives in the infrastructure layer, keeping the domain
    independent of the Mensagia API or any other storage mechanism.
    """

    @abstractmethod
    def get_all(self) -> list[EmailAddress]:
        """Retrieve all verified sender addresses registered in the account.

        Returns:
            A list of EmailAddress instances. Returns an empty list if no
            sender addresses have been registered or verified.
        """
        pass
