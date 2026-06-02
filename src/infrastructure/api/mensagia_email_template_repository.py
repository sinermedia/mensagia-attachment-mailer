from src.domain.entities.email_template import EmailTemplate
from src.domain.ports.email_template_repository import EmailTemplateRepository
from src.infrastructure.api.mensagia_client import MensagiaClient


class MensagiaEmailTemplateRepository(EmailTemplateRepository):
    """Implements EmailTemplateRepository by fetching data from the Mensagia API.

    This adapter translates raw API response dictionaries into domain
    EmailTemplate objects, shielding the rest of the application from the
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

    def get_all(self) -> list[EmailTemplate]:
        """Retrieve all email templates and map them to domain objects.

        Fetches raw template data via the client and converts each API
        dictionary into an EmailTemplate domain entity. The display name
        field varies across Mensagia API versions ('name' vs 'title'), so
        both keys are tried and a numeric fallback is used as a last resort.

        Returns:
            A list of EmailTemplate objects. Returns an empty list if no
            templates exist in the account.

        Raises:
            MensagiaAPIError: If the API call fails.
        """
        raw = self.client.get_email_templates()

        # 'name' is the standard field; 'title' was used in earlier API
        # versions. Fall back to a numeric label if neither is present
        return [
            EmailTemplate(
                id=item["id"],
                name=item.get("name", item.get("title", f"Template {item['id']}")),
            )
            for item in raw
        ]
