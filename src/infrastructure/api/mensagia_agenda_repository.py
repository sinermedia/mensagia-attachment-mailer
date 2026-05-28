from src.domain.entities.agenda import Agenda
from src.domain.ports.agenda_repository import AgendaRepository
from src.infrastructure.api.mensagia_client import MensagiaClient


class MensagiaAgendaRepository(AgendaRepository):
    def __init__(self, client: MensagiaClient):
        self.client = client

    def get_all(self) -> list[Agenda]:
        raw = self.client.get_agendas()
        return [
            Agenda(
                id=item["id"],
                name=item["name"],
                total_users=item.get("total_users", 0),
            )
            for item in raw
        ]
