from abc import ABC, abstractmethod
from src.domain.entities.agenda import Agenda


class AgendaRepository(ABC):
    """Port that defines how to retrieve agenda (contact group) data.

    This abstract class belongs to the domain layer and specifies the
    contract that any data source adapter must fulfil. The concrete
    implementation lives in the infrastructure layer, keeping the domain
    independent of the Mensagia API or any other storage mechanism.
    """

    @abstractmethod
    def get_all(self) -> list[Agenda]:
        """Retrieve all agendas available in the account.

        Returns:
            A list of Agenda instances. Returns an empty list if no
            agendas exist or none are accessible with the current token.
        """
        pass
