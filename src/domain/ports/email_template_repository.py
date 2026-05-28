from abc import ABC, abstractmethod
from src.domain.entities.email_template import EmailTemplate


class EmailTemplateRepository(ABC):
    @abstractmethod
    def get_all(self) -> list[EmailTemplate]:
        pass
