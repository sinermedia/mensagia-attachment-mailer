from abc import ABC, abstractmethod
from src.domain.entities.extra_field import ExtraField


class ExtraFieldRepository(ABC):
    """Port that defines how to retrieve custom extra field definitions.

    This abstract class belongs to the domain layer and specifies the
    contract that any data source adapter must fulfil. The concrete
    implementation lives in the infrastructure layer, keeping the domain
    independent of the Mensagia API or any other storage mechanism.
    """

    @abstractmethod
    def get_all(self) -> list[ExtraField]:
        """Retrieve all extra field definitions registered in the account.

        Returns:
            A list of ExtraField instances. Returns an empty list if no
            extra fields have been defined for the account.
        """
        pass
