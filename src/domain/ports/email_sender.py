from abc import ABC, abstractmethod
from src.domain.entities.email_message import EmailMessage


class EmailSender(ABC):
    @abstractmethod
    def send(self, message: EmailMessage) -> dict:
        pass
