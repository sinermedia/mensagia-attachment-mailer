from abc import ABC, abstractmethod
from src.domain.entities.agenda import AgendaPage


class AgendaRepository(ABC):
    """Port that defines how to retrieve agenda (contact group) data.

    This abstract class belongs to the domain layer and specifies the
    contract that any data source adapter must fulfil. The concrete
    implementation lives in the infrastructure layer, keeping the domain
    independent of the Mensagia API or any other storage mechanism.
    """

    @abstractmethod
    def search(self, name: str = "", page: int = 1, per_page: int = 10) -> AgendaPage:
        """Retrieve a single page of agendas, optionally filtered by name.

        Deliberately page-based rather than returning every agenda: accounts
        with thousands of groups made a full listing unusable, both because
        of the time spent walking every API page and because of the number
        of widgets the interface then had to render.

        Args:
            name: Partial name to filter by. An empty string returns the
                first agendas of the account without any filter.
            page: 1-based page number to retrieve.
            per_page: Maximum number of agendas to return in the page.

        Returns:
            An AgendaPage with the agendas of the requested page and the
            total number of matches across all pages.
        """
        pass
