from src.domain.date_input import DateFormat, read_send_date
from src.domain.entities.recipient import Recipient
from src.domain.ports.contact_repository import ContactRepository
from src.domain.ports.recipient_source import RecipientSource
from src.domain.subject_fields import SubjectTemplate


class AgendaRecipientSource(RecipientSource):
    """Reads the contacts of an agenda group as recipients.

    Every contact is returned, including those that cannot be sent: a
    contact needs an email address and a value in the chosen extra field,
    in the contact date start mode, a usable send day in the chosen date
    field and, when the subject takes text from the custom fields, a value
    in each of them. Contacts on the global email blacklist are left out by the
    query, as they cannot receive email at all.

    Attributes:
        contact_repository: Port used to fetch the group's contacts.
        group_id: ID of the agenda group.
        field_name: Name of the extra field holding the attachment value.
        date_field_name: Name of the extra field holding the send day, or
            None outside the contact date start mode.
        date_format: Format of the send days, or None.
        subject: Subject bound to the account's custom fields, or None to
            leave the subject to the send.
    """

    def __init__(self, contact_repository: ContactRepository, group_id: int, field_name: str,
                 date_field_name: str | None = None, date_format: DateFormat | None = None,
                 subject: SubjectTemplate | None = None):
        """Initialise the source for one group and attachment field.

        Args:
            contact_repository: Port used to fetch the group's contacts.
            group_id: ID of the agenda group.
            field_name: Name of the extra field holding the attachment value.
            date_field_name: Name of the extra field holding the send day,
                in the contact date start mode.
            date_format: Format of the send days, required with a date field.
            subject: Subject bound to the account's custom fields; each
                contact gets it with its own values.
        """
        self.contact_repository = contact_repository
        self.group_id = group_id
        self.field_name = field_name
        self.date_field_name = date_field_name
        self.date_format = date_format
        self.subject = subject

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
    def date_field(self) -> str | None:
        """Name the extra field that holds each contact's send day.

        Returns:
            The name of the chosen date field, or None.
        """
        return self.date_field_name

    @property
    def log_fields(self) -> dict[str, str]:
        """Describe the group in the opening line of the log.

        Returns:
            The group ID under 'group_id' and, in the contact date mode,
            the date field and its format.
        """
        fields = {"group_id": str(self.group_id)}
        if self.date_field_name is not None:
            fields["date_field"] = self.date_field_name
            fields["date_format"] = self.date_format.value
        return fields

    def get_recipients(self) -> list[Recipient]:
        """Fetch the group's contacts and turn each one into a recipient.

        Returns:
            One recipient per contact, keyed by the contact ID, with its
            final subject. Those without an email address, an attachment
            value, a usable send day (contact date mode) or a value in a
            subject field carry the reason.
        """
        # The API returns subscribed and unsubscribed contacts alike, as
        # subscription status is not exposed: only the blacklist is excluded
        contacts = self.contact_repository.get_by_group(self.group_id, in_mail_blacklist=False)

        recipients = []
        for contact in contacts:
            attachment = contact.extra_fields.get(self.field_name) or ""

            # The send day is read even when another reason skips the
            # contact, but the first reason found is the one reported
            send_date, date_reason = None, None
            if self.date_field_name is not None:
                value = str(contact.extra_fields.get(self.date_field_name) or "")
                send_date, date_reason = read_send_date(value, self.date_format)

            # The values are written as text, so a numeric field still fits
            subject, empty_field = None, None
            if self.subject is not None:
                values = {name: "" if value is None else str(value) for name, value in contact.extra_fields.items()}
                subject, empty_field = self.subject.render(values)

            if not contact.email:
                reason = "no_email"
            elif not attachment:
                reason = "no_attachment"
            elif date_reason:
                reason = date_reason
            elif empty_field:
                reason = "empty_subject_field"
            else:
                reason = None
            recipients.append(Recipient(
                key=str(contact.id), email=contact.email, attachment=attachment,
                name=contact.name, skip_reason=reason, send_date=send_date,
                subject=subject if reason is None else None,
                skip_detail=empty_field if reason == "empty_subject_field" else None,
            ))
        return recipients
