from unittest.mock import MagicMock

from src.domain.entities.contact import Contact
from src.domain.entities.recipient import Recipient
from src.infrastructure.recipients.agenda_recipient_source import AgendaRecipientSource


def make_source(contacts: list, group_id: int = 10) -> AgendaRecipientSource:
    """Build a source over a repository mock returning *contacts* for any group."""
    repository = MagicMock()
    repository.get_by_group.return_value = contacts
    return AgendaRecipientSource(repository, group_id, "attachment_url")


class TestAgendaRecipientSource:
    """Covers reading the contacts of an agenda group as recipients."""

    def test_queries_the_group_without_blacklisted_contacts(self):
        """The group's contacts are requested excluding the email blacklist."""
        source = make_source([], group_id=42)
        source.get_recipients()
        source.contact_repository.get_by_group.assert_called_once_with(42, in_mail_blacklist=False)

    def test_maps_a_contact_to_a_recipient(self):
        """A contact becomes a recipient keyed by its ID, with its email, name and attachment value."""
        contact = Contact(id=7, name="Ana", email="ana@test.com", extra_fields={"attachment_url": "a.pdf"})
        assert make_source([contact]).get_recipients() == [
            Recipient(key="7", email="ana@test.com", attachment="a.pdf", name="Ana")
        ]

    def test_contact_without_email_is_skipped(self):
        """A contact without an email address carries the no_email reason."""
        contact = Contact(id=1, name="A", email="", extra_fields={"attachment_url": "a.pdf"})
        assert make_source([contact]).get_recipients()[0].skip_reason == "no_email"

    def test_contact_without_attachment_is_skipped(self):
        """A contact whose attachment field is missing or empty carries the no_attachment reason."""
        contacts = [
            Contact(id=1, name="A", email="a@test.com", extra_fields={}),
            Contact(id=2, name="B", email="b@test.com", extra_fields={"attachment_url": ""}),
        ]
        reasons = [r.skip_reason for r in make_source(contacts).get_recipients()]
        assert reasons == ["no_attachment", "no_attachment"]

    def test_identity_is_the_group_id(self):
        """The source is identified in a campaign by the group ID, as in earlier versions."""
        assert make_source([], group_id=42).identity == "42"

    def test_attachment_field_is_the_chosen_extra_field(self):
        """The attachment field is the name of the extra field chosen by the user."""
        assert make_source([]).attachment_field == "attachment_url"

    def test_log_fields_name_the_group(self):
        """The log describes the source by its group ID."""
        assert make_source([], group_id=42).log_fields == {"group_id": "42"}
