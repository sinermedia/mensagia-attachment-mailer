from src.domain.entities.agenda import Agenda, AgendaPage
from src.domain.ports.agenda_repository import AgendaRepository
from src.infrastructure.api.mensagia_client import MensagiaClient


class MensagiaAgendaRepository(AgendaRepository):
    """Implements AgendaRepository by fetching data from the Mensagia API.

    This adapter translates raw API response dictionaries into domain Agenda
    objects, shielding the rest of the application from the API response
    structure. It lives in the infrastructure layer and depends on
    MensagiaClient for all HTTP communication.
    """

    def __init__(self, client: MensagiaClient):
        """Initialise the repository with a configured API client.

        Args:
            client: Authenticated MensagiaClient instance used to make
                API calls.
        """
        self.client = client

    def search(self, name: str = "", page: int = 1, per_page: int = 10) -> AgendaPage:
        """Retrieve one page of agendas from the Mensagia account.

        Args:
            name: Partial name to filter by. An empty string applies no filter.
            page: 1-based page number to retrieve.
            per_page: Maximum number of agendas to return in the page.

        Returns:
            An AgendaPage with the mapped Agenda objects and the total number
            of matches reported by the API.

        Raises:
            MensagiaAPIError: If the API call fails.
        """
        raw = self.client.get_agendas_page(name=name, page=page, per_page=per_page)

        # Map each raw API dict to a domain Agenda, using 0 as a safe default
        # for total_users when the field is absent from the response
        agendas = [
            Agenda(
                id=item["id"],
                name=item["name"],
                total_users=item.get("total_users", 0),
            )
            for item in raw.get("data", [])
        ]

        # Prefer the API's own match count; fall back to the page size so a
        # response without pagination metadata still yields a coherent page
        total = raw.get("meta", {}).get("pagination", {}).get("total", len(agendas))

        return AgendaPage(agendas=agendas, total=total)
