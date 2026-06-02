from src.domain.entities.contact import Contact
from src.domain.ports.contact_repository import ContactRepository
from src.infrastructure.api.mensagia_client import MensagiaClient


class MensagiaContactRepository(ContactRepository):
    """Implements ContactRepository by fetching data from the Mensagia API.

    This adapter translates raw API response dictionaries into domain Contact
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

    def get_by_group(self, group_id: int, in_mail_blacklist: bool = False) -> list[Contact]:
        """Retrieve contacts from the given agenda group and map them to domain objects.

        Fetches raw contact data via the client (handling pagination
        automatically) and converts each API dictionary into a Contact
        domain entity. Missing or null values from the API are normalised
        to safe defaults (empty string for email and name, empty dict for
        extra_fields) so the rest of the application never receives None.

        Args:
            group_id: Numeric ID of the agenda group to query.
            in_mail_blacklist: When False (default) excludes contacts that
                are on the global email blacklist. The blacklist is separate
                from agenda subscription: the API returns all contacts in
                the group regardless of their subscription status.

        Returns:
            A list of Contact objects. Returns an empty list if the group
            has no contacts.

        Raises:
            MensagiaAPIError: If the API call fails.
        """
        raw = self.client.get_contacts(group_id, in_mail_blacklist)

        # Map each raw API dict to a domain Contact, normalising nulls to
        # empty strings/dicts so downstream code never has to guard against None
        return [
            Contact(
                id=item["id"],
                name=item.get("name", ""),
                email=item.get("email", "") or "",
                extra_fields=item.get("extra_fields", {}) or {},
            )
            for item in raw
        ]
