from abc import ABC, abstractmethod


class AttachmentChecker(ABC):
    @abstractmethod
    def is_accessible(self, url: str) -> bool:
        pass
