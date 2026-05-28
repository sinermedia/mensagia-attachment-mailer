from src.domain.entities.extra_field import ExtraField
from src.domain.ports.extra_field_repository import ExtraFieldRepository
from src.infrastructure.api.mensagia_client import MensagiaClient


class MensagiaExtraFieldRepository(ExtraFieldRepository):
    def __init__(self, client: MensagiaClient):
        self.client = client

    def get_all(self) -> list[ExtraField]:
        raw = self.client.get_extra_fields()
        return [ExtraField(id=item["id"], name=item["name"]) for item in raw]
