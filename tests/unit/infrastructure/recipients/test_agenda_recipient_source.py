from datetime import date
from unittest.mock import MagicMock

import pytest

from src.domain.date_input import DateFormat
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

    def test_without_a_date_field_there_is_no_send_date(self):
        """Outside the contact date mode recipients carry no send date."""
        contact = Contact(id=1, name="A", email="a@x.com", extra_fields={"attachment_url": "a.pdf"})
        source = make_source([contact])
        assert source.get_recipients()[0].send_date is None
        assert source.date_field is None


def make_dated_source(contacts: list) -> AgendaRecipientSource:
    """Build a source that reads the send day from the 'Fecha' field, as dd/mm/yyyy."""
    repository = MagicMock()
    repository.get_by_group.return_value = contacts
    return AgendaRecipientSource(repository, 10, "attachment_url", "Fecha", DateFormat.DMY_SLASH)


def dated_contact(value) -> Contact:
    """Build a sendable contact whose 'Fecha' field holds *value* (None leaves it out)."""
    fields = {"attachment_url": "a.pdf"}
    if value is not None:
        fields["Fecha"] = value
    return Contact(id=1, name="A", email="a@x.com", extra_fields=fields)


class TestAgendaRecipientSourceSendDate:
    """Covers reading the send day of each contact from a custom field."""

    def test_reads_the_send_date_in_the_chosen_format(self):
        """The field is read with the chosen format."""
        [recipient] = make_dated_source([dated_contact("5/11/26")]).get_recipients()
        assert (recipient.send_date, recipient.skip_reason) == (date(2026, 11, 5), None)

    @pytest.mark.parametrize("value, reason", [
        (None, "no_send_date"),
        ("", "no_send_date"),
        ("2026-11-05", "invalid_send_date"),
        ("05/11/2026 10:00", "send_date_has_time"),
    ])
    def test_unusable_send_dates_are_skipped(self, value, reason):
        """A missing, unreadable or timed value skips the contact with its reason."""
        assert make_dated_source([dated_contact(value)]).get_recipients()[0].skip_reason == reason

    def test_missing_email_is_reported_before_the_date(self):
        """A contact without an email is skipped for that, whatever its date."""
        contact = Contact(id=1, name="A", email="", extra_fields={"attachment_url": "a.pdf"})
        assert make_dated_source([contact]).get_recipients()[0].skip_reason == "no_email"

    def test_date_field_and_log(self):
        """The source names its date field, and the log shows it with its format."""
        source = make_dated_source([])
        assert source.date_field == "Fecha"
        assert source.log_fields == {"group_id": "10", "date_field": "Fecha", "date_format": "dd/mm/yyyy"}


from src.domain.subject_fields import SubjectTemplate


def make_subject_source(contacts: list, subject: str) -> AgendaRecipientSource:
    """Build a source whose subject is bound to the fields 'num factura' and 'cliente'."""
    repository = MagicMock()
    repository.get_by_group.return_value = contacts
    template = SubjectTemplate.bind(subject, ["attachment_url", "num factura", "cliente"])
    return AgendaRecipientSource(repository, 10, "attachment_url", subject=template)


def subject_contact(**fields) -> Contact:
    """Build a sendable contact with the given extra fields besides its attachment."""
    return Contact(id=1, name="Ana", email="ana@test.com", extra_fields={"attachment_url": "a.pdf", **fields})


class TestAgendaRecipientSourceSubject:
    """Covers the subject of each contact built from its custom fields."""

    def test_builds_the_subject_of_each_contact(self):
        """Fills the subject with the contact's custom field values."""
        contact = subject_contact(**{"num factura": "123", "cliente": "ACME"})
        [recipient] = make_subject_source([contact], "Factura #num_factura# - #cliente#").get_recipients()
        assert recipient.subject == "Factura 123 - ACME"
        assert recipient.skip_reason is None

    def test_a_subject_without_fields_is_the_same_for_everyone(self):
        """Gives every contact the subject as written when it has no fields."""
        [recipient] = make_subject_source([subject_contact()], "Tu factura").get_recipients()
        assert recipient.subject == "Tu factura"

    @pytest.mark.parametrize("value", [None, "", "   "])
    def test_an_empty_value_skips_the_contact(self, value):
        """Skips a contact whose subject field is empty, naming the field."""
        [recipient] = make_subject_source([subject_contact(cliente=value)], "#cliente#").get_recipients()
        assert (recipient.skip_reason, recipient.skip_detail, recipient.subject) == ("empty_subject_field", "cliente", None)

    def test_a_missing_field_skips_the_contact(self):
        """Skips a contact that does not have the subject field at all."""
        [recipient] = make_subject_source([subject_contact()], "#cliente#").get_recipients()
        assert recipient.skip_reason == "empty_subject_field"

    def test_other_reasons_come_first(self):
        """Reports a missing attachment before an empty subject field."""
        contact = Contact(id=1, name="A", email="a@test.com", extra_fields={})
        [recipient] = make_subject_source([contact], "#cliente#").get_recipients()
        assert (recipient.skip_reason, recipient.skip_detail) == ("no_attachment", None)

    def test_numeric_values_are_written_as_text(self):
        """Writes a numeric field value as text."""
        [recipient] = make_subject_source([subject_contact(cliente=42)], "#cliente#").get_recipients()
        assert recipient.subject == "42"

    def test_without_a_template_there_is_no_subject(self):
        """Leaves the subject to the send when the source was given no template."""
        [recipient] = make_source([subject_contact()]).get_recipients()
        assert recipient.subject is None
