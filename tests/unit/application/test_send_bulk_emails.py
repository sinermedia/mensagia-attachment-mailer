from datetime import datetime
from unittest.mock import MagicMock, call, patch
import pytest
from src.domain.entities.contact import Contact
from src.domain.entities.extra_field import ExtraField
from src.application.use_cases.send_bulk_emails import SendBulkEmailsUseCase


# Fixed reference datetime used in all tests to make scheduling deterministic
FIXED_NOW = datetime(2024, 1, 15, 14, 23, 0)


@pytest.fixture
def contact_repo():
    """Mock ContactRepository for use case tests."""
    return MagicMock()


@pytest.fixture
def email_sender():
    """Mock EmailSender for use case tests."""
    return MagicMock()


@pytest.fixture
def use_case(contact_repo, email_sender):
    """SendBulkEmailsUseCase instance wired with mock dependencies."""
    return SendBulkEmailsUseCase(contact_repo, email_sender)


@pytest.fixture
def extra_field():
    """ExtraField whose name matches the key used by make_contact()."""
    return ExtraField(id=1, name="attachment_url")


def make_contact(contact_id, email, attachment_url=None):
    """Build a Contact with an optional attachment_url extra field.

    Args:
        contact_id: Numeric ID for the contact.
        email: Email address string; pass an empty string to simulate missing email.
        attachment_url: Value to store in the 'attachment_url' extra field.
            Pass None to simulate a contact without an attachment.

    Returns:
        A Contact instance with the given attributes.
    """
    extra = {"attachment_url": attachment_url} if attachment_url else {}
    return Contact(id=contact_id, name=f"Contact {contact_id}", email=email, extra_fields=extra)


class TestSendBulkEmailsUseCase:
    """Tests for SendBulkEmailsUseCase.execute().

    Each test verifies one specific aspect of the use-case logic (eligibility
    filtering, message construction, dry-run behaviour, error handling, etc.)
    in isolation using mock dependencies so no real HTTP calls are made.
    """

    @pytest.fixture(autouse=True)
    def mock_sleep(self):
        """Patch time.sleep so tests do not actually pause between sends."""
        with patch("src.application.use_cases.send_bulk_emails.time.sleep") as m:
            yield m

    def test_sends_one_email_per_eligible_contact(self, use_case, contact_repo, email_sender, extra_field):
        """One email is sent for each contact that has both email and attachment."""
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
        """Contacts with an empty email address are moved to the skipped list."""
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
        """Contacts without an attachment URL value are moved to the skipped list."""
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
        """The use case always queries contacts with in_mail_blacklist=False."""
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
        """The EmailMessage passed to the sender contains all fields from the call arguments."""
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
        """Each successive email is scheduled strictly later than the previous one."""
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

    def test_dry_run_does_not_call_sender(self, use_case, contact_repo, email_sender, extra_field):
        """In dry-run mode the email sender is never called but sent count is correct."""
        contacts = [make_contact(1, "a@test.com", "https://example.com/a.pdf")]
        contact_repo.get_by_group.return_value = contacts

        result = use_case.execute(
            from_email="sender@test.com",
            group_id=10,
            subject="Test",
            template_id=5,
            extra_field=extra_field,
            certified=0,
            now=FIXED_NOW,
            dry_run=True,
        )

        email_sender.send.assert_not_called()
        assert len(result.sent) == 1

    def test_dry_run_still_validates_attachment_url(self, use_case, contact_repo, email_sender, extra_field):
        """Even in dry-run mode an inaccessible attachment moves the contact to errors."""
        contacts = [make_contact(1, "a@test.com", "https://example.com/a.pdf")]
        contact_repo.get_by_group.return_value = contacts

        checker = MagicMock()
        checker.is_accessible.return_value = False

        result = use_case.execute(
            from_email="sender@test.com",
            group_id=10,
            subject="Test",
            template_id=5,
            extra_field=extra_field,
            certified=0,
            now=FIXED_NOW,
            dry_run=True,
            attachment_checker=checker,
        )

        email_sender.send.assert_not_called()
        assert len(result.errors) == 1
        assert len(result.sent) == 0

    def test_relative_attachment_url_resolved_with_base_url(self, use_case, contact_repo, email_sender, extra_field):
        """A relative attachment value is combined with the base URL before sending."""
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

    def test_inaccessible_attachment_discards_contact(self, use_case, contact_repo, email_sender, extra_field):
        """A contact whose attachment is not reachable is added to errors; others proceed."""
        contacts = [
            make_contact(1, "a@test.com", "https://example.com/ok.pdf"),
            make_contact(2, "b@test.com", "https://example.com/missing.pdf"),
        ]
        contact_repo.get_by_group.return_value = contacts
        email_sender.send.return_value = {"data": {"id": 1}}

        checker = MagicMock()
        checker.is_accessible.side_effect = [True, False]

        result = use_case.execute(
            from_email="sender@test.com",
            group_id=10,
            subject="Test",
            template_id=5,
            extra_field=extra_field,
            certified=0,
            now=FIXED_NOW,
            attachment_checker=checker,
        )

        assert len(result.sent) == 1
        assert len(result.errors) == 1

    def test_no_checker_skips_url_validation(self, use_case, contact_repo, email_sender, extra_field):
        """When attachment_checker is None, no accessibility check is performed."""
        contacts = [make_contact(1, "a@test.com", "https://example.com/a.pdf")]
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
            attachment_checker=None,
        )

        assert len(result.sent) == 1

    def test_relative_url_without_base_url_adds_to_errors(self, use_case, contact_repo, email_sender, extra_field):
        """A relative attachment value without a base URL causes an error for that contact."""
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
        """When the group has no contacts all result lists are empty."""
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

    def test_sleep_called_once_per_eligible_contact(self, use_case, contact_repo, email_sender, extra_field, mock_sleep):
        """time.sleep(1) is called once per eligible contact to rate-limit API sends."""
        contacts = [
            make_contact(1, "a@test.com", "https://example.com/a.pdf"),
            make_contact(2, "b@test.com", "https://example.com/b.pdf"),
            make_contact(3, "c@test.com", "https://example.com/c.pdf"),
        ]
        contact_repo.get_by_group.return_value = contacts
        email_sender.send.return_value = {}

        use_case.execute(
            from_email="sender@test.com",
            group_id=10,
            subject="Test",
            template_id=5,
            extra_field=extra_field,
            certified=0,
            now=FIXED_NOW,
        )

        assert mock_sleep.call_count == 3
        mock_sleep.assert_called_with(1)

    def test_no_sleep_in_dry_run(self, use_case, contact_repo, email_sender, extra_field, mock_sleep):
        """time.sleep is not called when dry_run=True because no real API request is made."""
        contacts = [
            make_contact(1, "a@test.com", "https://example.com/a.pdf"),
            make_contact(2, "b@test.com", "https://example.com/b.pdf"),
        ]
        contact_repo.get_by_group.return_value = contacts

        use_case.execute(
            from_email="sender@test.com",
            group_id=10,
            subject="Test",
            template_id=5,
            extra_field=extra_field,
            certified=0,
            now=FIXED_NOW,
            dry_run=True,
        )

        mock_sleep.assert_not_called()


class TestSendBulkEmailsUseCaseWithLogger:
    """Tests that the use case calls the logger on real sends and stays silent on dry-run."""

    @pytest.fixture(autouse=True)
    def mock_sleep(self):
        """Patch time.sleep so tests do not actually pause between sends."""
        with patch("src.application.use_cases.send_bulk_emails.time.sleep") as m:
            yield m

    def test_log_start_called_once_on_real_send(self, use_case, contact_repo, email_sender, extra_field):
        """log_start() is called exactly once when a logger is provided and dry_run is False."""
        contact_repo.get_by_group.return_value = [make_contact(1, "a@test.com", "https://example.com/a.pdf")]
        email_sender.send.return_value = {}
        logger = MagicMock()

        use_case.execute(
            from_email="sender@test.com", group_id=10, subject="Test",
            template_id=5, extra_field=extra_field, certified=0,
            now=FIXED_NOW, logger=logger,
        )

        logger.log_start.assert_called_once()

    def test_log_ok_called_for_each_sent_contact(self, use_case, contact_repo, email_sender, extra_field):
        """log_ok() is called once per successfully sent contact."""
        contact_repo.get_by_group.return_value = [
            make_contact(1, "a@test.com", "https://example.com/a.pdf"),
            make_contact(2, "b@test.com", "https://example.com/b.pdf"),
        ]
        email_sender.send.return_value = {}
        logger = MagicMock()

        use_case.execute(
            from_email="sender@test.com", group_id=10, subject="Test",
            template_id=5, extra_field=extra_field, certified=0,
            now=FIXED_NOW, logger=logger,
        )

        assert logger.log_ok.call_count == 2

    def test_log_skip_called_for_contacts_without_email_or_attachment(self, use_case, contact_repo, email_sender, extra_field):
        """log_skip() is called for every contact excluded before sending."""
        contact_repo.get_by_group.return_value = [
            make_contact(1, "", "https://example.com/a.pdf"),
            make_contact(2, "b@test.com", None),
            make_contact(3, "c@test.com", "https://example.com/c.pdf"),
        ]
        email_sender.send.return_value = {}
        logger = MagicMock()

        use_case.execute(
            from_email="sender@test.com", group_id=10, subject="Test",
            template_id=5, extra_field=extra_field, certified=0,
            now=FIXED_NOW, logger=logger,
        )

        assert logger.log_skip.call_count == 2

    def test_log_skip_reason_no_email(self, use_case, contact_repo, email_sender, extra_field):
        """log_skip() receives reason='no_email' for a contact with an empty email."""
        contact_repo.get_by_group.return_value = [make_contact(1, "", "https://example.com/a.pdf")]
        logger = MagicMock()

        use_case.execute(
            from_email="sender@test.com", group_id=10, subject="Test",
            template_id=5, extra_field=extra_field, certified=0,
            now=FIXED_NOW, logger=logger,
        )

        reason = logger.log_skip.call_args[0][1]
        assert reason == "no_email"

    def test_log_skip_reason_no_attachment(self, use_case, contact_repo, email_sender, extra_field):
        """log_skip() receives reason='no_attachment' for a contact with no attachment value."""
        contact_repo.get_by_group.return_value = [make_contact(1, "a@test.com", None)]
        logger = MagicMock()

        use_case.execute(
            from_email="sender@test.com", group_id=10, subject="Test",
            template_id=5, extra_field=extra_field, certified=0,
            now=FIXED_NOW, logger=logger,
        )

        reason = logger.log_skip.call_args[0][1]
        assert reason == "no_attachment"

    def test_log_error_called_when_send_raises(self, use_case, contact_repo, email_sender, extra_field):
        """log_error() is called when the email sender raises an exception."""
        contact_repo.get_by_group.return_value = [make_contact(1, "a@test.com", "https://example.com/a.pdf")]
        email_sender.send.side_effect = Exception("API error")
        logger = MagicMock()

        use_case.execute(
            from_email="sender@test.com", group_id=10, subject="Test",
            template_id=5, extra_field=extra_field, certified=0,
            now=FIXED_NOW, logger=logger,
        )

        logger.log_error.assert_called_once()

    def test_log_done_called_with_correct_counts(self, use_case, contact_repo, email_sender, extra_field):
        """log_done() is called once with the final sent/skipped/error counts."""
        contact_repo.get_by_group.return_value = [make_contact(1, "a@test.com", "https://example.com/a.pdf")]
        email_sender.send.return_value = {}
        logger = MagicMock()

        use_case.execute(
            from_email="sender@test.com", group_id=10, subject="Test",
            template_id=5, extra_field=extra_field, certified=0,
            now=FIXED_NOW, logger=logger,
        )

        logger.log_done.assert_called_once_with(1, 0, 0)

    def test_no_logging_when_dry_run_is_true(self, use_case, contact_repo, email_sender, extra_field):
        """No logger methods are called at all when dry_run=True."""
        contact_repo.get_by_group.return_value = [make_contact(1, "a@test.com", "https://example.com/a.pdf")]
        logger = MagicMock()

        use_case.execute(
            from_email="sender@test.com", group_id=10, subject="Test",
            template_id=5, extra_field=extra_field, certified=0,
            now=FIXED_NOW, dry_run=True, logger=logger,
        )

        logger.log_start.assert_not_called()
        logger.log_ok.assert_not_called()
        logger.log_skip.assert_not_called()
        logger.log_error.assert_not_called()
        logger.log_done.assert_not_called()

    def test_no_error_when_logger_is_none(self, use_case, contact_repo, email_sender, extra_field):
        """The use case runs without error and returns correct results when logger=None."""
        contact_repo.get_by_group.return_value = [make_contact(1, "a@test.com", "https://example.com/a.pdf")]
        email_sender.send.return_value = {}

        result = use_case.execute(
            from_email="sender@test.com", group_id=10, subject="Test",
            template_id=5, extra_field=extra_field, certified=0,
            now=FIXED_NOW,
        )

        assert len(result.sent) == 1
