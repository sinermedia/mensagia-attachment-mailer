from abc import ABC, abstractmethod
from src.domain.entities.email_address import EmailAddress


class EmailAddressRepository(ABC):
    @abstractmethod
    def get_all(self) -> list[EmailAddress]:
        pass
