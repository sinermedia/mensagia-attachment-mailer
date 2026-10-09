from src.domain.entities.recipient import Recipient
from src.domain.ports.contact_repository import ContactRepository
from src.domain.ports.recipient_source import RecipientSource


class AgendaRecipientSource(RecipientSource):
    """Reads the contacts of an agenda group as recipients.

    Every contact is returned, including those that cannot be sent: a
    contact needs an email address and a value in the chosen extra field.
    Contacts on the global email blacklist are left out by the query, as
    they cannot receive email at all.

    Attributes:
        contact_repository: Port used to fetch the group's contacts.
        group_id: ID of the agenda group.
        field_name: Name of the extra field holding the attachment value.
    """

    def __init__(self, contact_repository: ContactRepository, group_id: int, field_name: str):
        """Initialise the source for one group and attachment field.

        Args:
            contact_repository: Port used to fetch the group's contacts.
            group_id: ID of the agenda group.
            field_name: Name of the extra field holding the attachment value.
        """
        self.contact_repository = contact_repository
        self.group_id = group_id
        self.field_name = field_name

    @property
    def identity(self) -> str:
        """Identify the group within a campaign.

        Returns:
            The group ID, the value earlier versions used, so their
            interrupted sends can still be resumed.
        """
        return str(self.group_id)

    @property
    def attachment_field(self) -> str:
        """Name the extra field that holds each contact's attachment.

        Returns:
            The name of the chosen extra field.
        """
        return self.field_name

    @property
    def log_fields(self) -> dict[str, str]:
        """Describe the group in the opening line of the log.

        Returns:
            The group ID under 'group_id'.
        """
        return {"group_id": str(self.group_id)}

    def get_recipients(self) -> list[Recipient]:
        """Fetch the group's contacts and turn each one into a recipient.

        Returns:
            One recipient per contact, keyed by the contact ID. Those without
            an email address or attachment value carry the reason.
        """
        # The API returns subscribed and unsubscribed contacts alike, as
        # subscription status is not exposed: only the blacklist is excluded
        contacts = self.contact_repository.get_by_group(self.group_id, in_mail_blacklist=False)

        recipients = []
        for contact in contacts:
            attachment = contact.extra_fields.get(self.field_name) or ""
            if not contact.email:
                reason = "no_email"
            elif not attachment:
                reason = "no_attachment"
            else:
                reason = None
            recipients.append(Recipient(
                key=str(contact.id), email=contact.email, attachment=attachment,
                name=contact.name, skip_reason=reason,
            ))
        return recipients
