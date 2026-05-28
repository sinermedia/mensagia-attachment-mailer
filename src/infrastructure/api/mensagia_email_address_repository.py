from src.domain.entities.email_address import EmailAddress
from src.domain.ports.email_address_repository import EmailAddressRepository
from src.infrastructure.api.mensagia_client import MensagiaClient


class MensagiaEmailAddressRepository(EmailAddressRepository):
    def __init__(self, client: MensagiaClient):
        self.client = client

    def get_all(self) -> list[EmailAddress]:
        raw = self.client.get_email_addresses()
        return [
            EmailAddress(
                id=item["id"],
                email=item.get("email", item.get("address", "")),
                name=item.get("name", ""),
            )
            for item in raw
        ]
