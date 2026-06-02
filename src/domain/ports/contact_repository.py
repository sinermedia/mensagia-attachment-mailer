from abc import ABC, abstractmethod
from src.domain.entities.contact import Contact


class ContactRepository(ABC):
    """Port that defines how to retrieve contacts belonging to an agenda group.

    This abstract class belongs to the domain layer and specifies the
    contract that any data source adapter must fulfil. The concrete
    implementation lives in the infrastructure layer, keeping the domain
    independent of the Mensagia API or any other storage mechanism.
    """

    @abstractmethod
    def get_by_group(self, group_id: int, in_mail_blacklist: bool = False) -> list[Contact]:
        """Retrieve all contacts that belong to the given agenda group.

        Args:
            group_id: Numeric identifier of the agenda group to query.
            in_mail_blacklist: When True, also returns contacts that are on
                the email blacklist. Defaults to False to exclude them and
                avoid sending to unsubscribed addresses.

        Returns:
            A list of Contact instances belonging to the specified group.
            Returns an empty list if the group has no contacts.
        """
        pass
