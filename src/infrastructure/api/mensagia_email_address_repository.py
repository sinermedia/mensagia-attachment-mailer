from src.domain.entities.email_address import EmailAddress
from src.domain.ports.email_address_repository import EmailAddressRepository
from src.infrastructure.api.mensagia_client import MensagiaClient


class MensagiaEmailAddressRepository(EmailAddressRepository):
    """Implements EmailAddressRepository by fetching data from the Mensagia API.

    This adapter translates raw API response dictionaries into domain
    EmailAddress objects, shielding the rest of the application from the
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

    def get_all(self) -> list[EmailAddress]:
        """Retrieve all verified sender addresses and map them to domain objects.

        Fetches raw sender address data via the client and converts each API
        dictionary into an EmailAddress domain entity. The field that stores
        the email string is not consistent across all Mensagia API versions
        (sometimes 'email', sometimes 'address'), so both keys are tried.

        Returns:
            A list of EmailAddress objects. Returns an empty list if no
            sender addresses have been registered.

        Raises:
            MensagiaAPIError: If the API call fails.
        """
        raw = self.client.get_email_addresses()

        # The Mensagia API has used both 'email' and 'address' as the field
        # name for the actual address string depending on the API version,
        # so we try 'email' first and fall back to 'address'
        return [
            EmailAddress(
                id=item["id"],
                email=item.get("email", item.get("address", "")),
                name=item.get("name", ""),
            )
            for item in raw
        ]
