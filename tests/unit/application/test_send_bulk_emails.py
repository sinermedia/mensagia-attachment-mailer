from datetime import datetime
from unittest.mock import MagicMock, call
import pytest
from src.domain.entities.contact import Contact
from src.domain.entities.extra_field import ExtraField
from src.application.use_cases.send_bulk_emails import SendBulkEmailsUseCase


FIXED_NOW = datetime(2024, 1, 15, 14, 23, 0)


@pytest.fixture
def contact_repo():
    return MagicMock()


@pytest.fixture
def email_sender():
    return MagicMock()


@pytest.fixture
def use_case(contact_repo, email_sender):
    return SendBulkEmailsUseCase(contact_repo, email_sender)


@pytest.fixture
def extra_field():
    return ExtraField(id=1, name="attachment_url")


def make_contact(contact_id, email, attachment_url=None):
    extra = {"attachment_url": attachment_url} if attachment_url else {}
    return Contact(id=contact_id, name=f"Contact {contact_id}", email=email, extra_fields=extra)


class TestSendBulkEmailsUseCase:
    def test_sends_one_email_per_eligible_contact(self, use_case, contact_repo, email_sender, extra_field):
        contacts = [
            make_contact(1, "a@test.com", "https://example.com/a.pdf"),
            make_contact(2, "b@test.com", "https://example.com/b.pdf"),
        ]
        contact_repo.get_by_group.return_value = contacts
        email_sender.send.return_value = {"data": {"id": 1}}

        result = use_case.execute(
            from_email="sender@test.com",
            group_id=10,
            subject="Test",
            template_id=5,
            extra_field=extra_field,
            certified=0,
            now=FIXED_NOW,
        )

        assert email_sender.send.call_count == 2
        assert len(result.sent) == 2
        assert len(result.skipped) == 0

    def test_skips_contacts_without_email(self, use_case, contact_repo, email_sender, extra_field):
        contacts = [
            make_contact(1, "", "https://example.com/a.pdf"),
            make_contact(2, "b@test.com", "https://example.com/b.pdf"),
        ]
        contact_repo.get_by_group.return_value = contacts

        result = use_case.execute(
            from_email="sender@test.com",
            group_id=10,
            subject="Test",
            template_id=5,
            extra_field=extra_field,
            certified=0,
            now=FIXED_NOW,
        )

        assert email_sender.send.call_count == 1
        assert len(result.skipped) == 1

    def test_skips_contacts_without_attachment_url(self, use_case, contact_repo, email_sender, extra_field):
        contacts = [
            make_contact(1, "a@test.com", None),
            make_contact(2, "b@test.com", "https://example.com/b.pdf"),
        ]
        contact_repo.get_by_group.return_value = contacts

        result = use_case.execute(
            from_email="sender@test.com",
            group_id=10,
            subject="Test",
            template_id=5,
            extra_field=extra_field,
            certified=0,
            now=FIXED_NOW,
        )

        assert email_sender.send.call_count == 1
        assert len(result.skipped) == 1

    def test_queries_contacts_without_blacklist(self, use_case, contact_repo, email_sender, extra_field):
        contact_repo.get_by_group.return_value = []

        use_case.execute(
            from_email="sender@test.com",
            group_id=42,
            subject="Test",
            template_id=5,
            extra_field=extra_field,
            certified=0,
            now=FIXED_NOW,
        )

        contact_repo.get_by_group.assert_called_once_with(42, in_mail_blacklist=False)

    def test_email_message_has_correct_fields(self, use_case, contact_repo, email_sender, extra_field):
        contacts = [make_contact(1, "a@test.com", "https://example.com/a.pdf")]
        contact_repo.get_by_group.return_value = contacts
        email_sender.send.return_value = {"data": {"id": 1}}

        use_case.execute(
            from_email="sender@test.com",
            group_id=10,
            subject="Hello",
            template_id=7,
            extra_field=extra_field,
            certified=1,
            now=FIXED_NOW,
        )

        sent_message = email_sender.send.call_args[0][0]
        assert sent_message.from_email == "sender@test.com"
        assert sent_message.to_email == "a@test.com"
        assert sent_message.subject == "Hello"
        assert sent_message.template_id == 7
        assert sent_message.attachments == ["https://example.com/a.pdf"]
        assert sent_message.certified == 1

    def test_start_dates_are_staggered(self, use_case, contact_repo, email_sender, extra_field):
        contacts = [
            make_contact(1, "a@test.com", "https://example.com/a.pdf"),
            make_contact(2, "b@test.com", "https://example.com/b.pdf"),
            make_contact(3, "c@test.com", "https://example.com/c.pdf"),
        ]
        contact_repo.get_by_group.return_value = contacts
        email_sender.send.return_value = {"data": {"id": 1}}

        use_case.execute(
            from_email="sender@test.com",
            group_id=10,
            subject="Test",
            template_id=5,
            extra_field=extra_field,
            certified=0,
            now=FIXED_NOW,
        )

        calls = email_sender.send.call_args_list
        dates = [c[0][0].start_date for c in calls]
        assert dates[1] > dates[0]
        assert dates[2] > dates[1]

    def test_relative_attachment_url_resolved_with_base_url(self, use_case, contact_repo, email_sender, extra_field):
        contacts = [make_contact(1, "a@test.com", "file.pdf")]
        contact_repo.get_by_group.return_value = contacts
        email_sender.send.return_value = {"data": {"id": 1}}

        use_case.execute(
            from_email="sender@test.com",
            group_id=10,
            subject="Test",
            template_id=5,
            extra_field=extra_field,
            certified=0,
            now=FIXED_NOW,
            attachment_base_url="https://example.com/files",
        )

        sent_message = email_sender.send.call_args[0][0]
        assert sent_message.attachments == ["https://example.com/files/file.pdf"]

    def test_relative_url_without_base_url_adds_to_errors(self, use_case, contact_repo, email_sender, extra_field):
        contacts = [make_contact(1, "a@test.com", "file.pdf")]
        contact_repo.get_by_group.return_value = contacts

        result = use_case.execute(
            from_email="sender@test.com",
            group_id=10,
            subject="Test",
            template_id=5,
            extra_field=extra_field,
            certified=0,
            now=FIXED_NOW,
        )

        assert len(result.errors) == 1
        assert len(result.sent) == 0

    def test_returns_empty_result_when_no_contacts(self, use_case, contact_repo, email_sender, extra_field):
        contact_repo.get_by_group.return_value = []

        result = use_case.execute(
            from_email="sender@test.com",
            group_id=10,
            subject="Test",
            template_id=5,
            extra_field=extra_field,
            certified=0,
            now=FIXED_NOW,
        )

        assert email_sender.send.call_count == 0
        assert len(result.sent) == 0
        assert len(result.skipped) == 0
