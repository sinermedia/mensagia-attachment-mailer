from src.domain.entities.email_template import EmailTemplate
from src.domain.ports.email_template_repository import EmailTemplateRepository
from src.infrastructure.api.mensagia_client import MensagiaClient


class MensagiaEmailTemplateRepository(EmailTemplateRepository):
    def __init__(self, client: MensagiaClient):
        self.client = client

    def get_all(self) -> list[EmailTemplate]:
        raw = self.client.get_email_templates()
        return [
            EmailTemplate(
                id=item["id"],
                name=item.get("name", item.get("title", f"Template {item['id']}")),
            )
            for item in raw
        ]
