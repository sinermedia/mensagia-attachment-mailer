from src.domain.entities.contact import Contact
from src.domain.ports.contact_repository import ContactRepository
from src.infrastructure.api.mensagia_client import MensagiaClient


class MensagiaContactRepository(ContactRepository):
    def __init__(self, client: MensagiaClient):
        self.client = client

    def get_by_group(self, group_id: int, in_mail_blacklist: bool = False) -> list[Contact]:
        raw = self.client.get_contacts(group_id, in_mail_blacklist)
        return [
            Contact(
                id=item["id"],
                name=item.get("name", ""),
                email=item.get("email", "") or "",
                extra_fields=item.get("extra_fields", {}) or {},
            )
            for item in raw
        ]
