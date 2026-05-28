from abc import ABC, abstractmethod
from src.domain.entities.contact import Contact


class ContactRepository(ABC):
    @abstractmethod
    def get_by_group(self, group_id: int, in_mail_blacklist: bool = False) -> list[Contact]:
        pass
