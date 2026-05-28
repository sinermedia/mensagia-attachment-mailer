from abc import ABC, abstractmethod
from src.domain.entities.extra_field import ExtraField


class ExtraFieldRepository(ABC):
    @abstractmethod
    def get_all(self) -> list[ExtraField]:
        pass
