from src.domain.entities.extra_field import ExtraField
from src.domain.ports.extra_field_repository import ExtraFieldRepository
from src.infrastructure.api.mensagia_client import MensagiaClient


class MensagiaExtraFieldRepository(ExtraFieldRepository):
    """Implements ExtraFieldRepository by fetching data from the Mensagia API.

    This adapter translates raw API response dictionaries into domain
    ExtraField objects, shielding the rest of the application from the
    API response structure. It lives in the infrastructure layer and depends
    on MensagiaClient for all HTTP communication.
    """

    def __init__(self, client: MensagiaClient):
        """Initialise the repository with a configured API client.

        Args:
            client: Authenticated MensagiaClient instance used to make
                API calls.
        """
        self.client = client

    def get_all(self) -> list[ExtraField]:
        """Retrieve all extra field definitions and map them to domain objects.

        Fetches raw extra field data via the client and converts each API
        dictionary into an ExtraField domain entity.

        Returns:
            A list of ExtraField objects. Returns an empty list if no extra
            fields have been defined for the account.

        Raises:
            MensagiaAPIError: If the API call fails.
        """
        raw = self.client.get_extra_fields()

        # Both 'id' and 'name' are always present in the Mensagia response
        return [ExtraField(id=item["id"], name=item["name"]) for item in raw]
