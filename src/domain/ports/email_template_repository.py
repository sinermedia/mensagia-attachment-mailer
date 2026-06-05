from abc import ABC, abstractmethod
from src.domain.entities.email_template import EmailTemplate


class EmailTemplateRepository(ABC):
    """Port that defines how to retrieve email templates.

    This abstract class belongs to the domain layer and specifies the
    contract that any data source adapter must fulfil. The concrete
    implementation lives in the infrastructure layer, keeping the domain
    independent of the Mensagia API or any other storage mechanism.
    """

    @abstractmethod
    def get_all(self) -> list[EmailTemplate]:
        """Retrieve all email templates available in the account.

        Returns:
            A list of EmailTemplate instances. Returns an empty list if no
            templates have been created in the Mensagia account.
        """
        pass
