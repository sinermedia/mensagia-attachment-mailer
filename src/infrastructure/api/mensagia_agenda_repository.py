from src.domain.entities.agenda import Agenda
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

    def get_all(self) -> list[Agenda]:
        """Retrieve all agendas from the Mensagia account and map them to domain objects.

        Fetches raw agenda data via the client (handling pagination
        automatically) and converts each API dictionary into an Agenda
        domain entity.

        Returns:
            A list of Agenda objects. Returns an empty list if the account
            has no agendas.

        Raises:
            MensagiaAPIError: If the API call fails.
        """
        raw = self.client.get_agendas()

        # Map each raw API dict to a domain Agenda, using 0 as a safe default
        # for total_users when the field is absent from the response
        return [
            Agenda(
                id=item["id"],
                name=item["name"],
                total_users=item.get("total_users", 0),
            )
            for item in raw
        ]
