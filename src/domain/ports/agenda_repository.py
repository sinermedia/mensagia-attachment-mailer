from abc import ABC, abstractmethod
from src.domain.entities.agenda import Agenda


class AgendaRepository(ABC):
    @abstractmethod
    def get_all(self) -> list[Agenda]:
        pass
