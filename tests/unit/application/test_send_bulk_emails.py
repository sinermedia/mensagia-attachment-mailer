from datetime import datetime, timedelta
from unittest.mock import MagicMock, call, patch
import pytest
from src.domain.entities.campaign import Campaign
from src.domain.entities.contact import Contact
from src.domain.entities.recipient import Recipient
from src.infrastructure.recipients.agenda_recipient_source import AgendaRecipientSource
from src.application.use_cases.send_bulk_emails import SendBulkEmailsUseCase
from src.domain.ports.email_sender import EmailNotSentError, EmailRejectedError, EmailSendUncertainError
from src.domain.scheduling import StartMode


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
def use_case(email_sender):
    """SendBulkEmailsUseCase instance wired with a mock sender."""
    return SendBulkEmailsUseCase(email_sender)


@pytest.fixture
def source(contact_repo):
    """Agenda source over the mock repository, with the attachment field used by make_contact()."""
    return AgendaRecipientSource(contact_repo, 10, "attachment_url")


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


def make_recipient(contact_id, email, attachment_url, skip_reason=None):
    """Build the Recipient the agenda source yields for the contact of make_contact().

    Args:
        contact_id: Numeric ID of the contact.
        email: Email address of the contact.
        attachment_url: Value of its 'attachment_url' extra field.
        skip_reason: Reason the source gives when it cannot be sent.

    Returns:
        A Recipient equal to the one read from that contact.
    """
    return Recipient(key=str(contact_id), email=email, attachment=attachment_url,
                     name=f"Contact {contact_id}", skip_reason=skip_reason)


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

    def test_sends_one_email_per_eligible_contact(self, use_case, contact_repo, email_sender, source):
        """One email is sent for each contact that has both email and attachment."""
        contacts = [
            make_contact(1, "a@test.com", "https://example.com/a.pdf"),
            make_contact(2, "b@test.com", "https://example.com/b.pdf"),
        ]
        contact_repo.get_by_group.return_value = contacts
        email_sender.send.return_value = {"data": {"id": 1}}

        result = use_case.execute(
            from_email="sender@test.com",
            subject="Test",
            template_id=5,
            recipient_source=source,
            certified=0,
            now=FIXED_NOW,
        )

        assert email_sender.send.call_count == 2
        assert len(result.sent) == 2
        assert len(result.skipped) == 0

    def test_skips_contacts_without_email(self, use_case, contact_repo, email_sender, source):
        """Contacts with an empty email address are moved to the skipped list."""
        contacts = [
            make_contact(1, "", "https://example.com/a.pdf"),
            make_contact(2, "b@test.com", "https://example.com/b.pdf"),
        ]
        contact_repo.get_by_group.return_value = contacts

        result = use_case.execute(
            from_email="sender@test.com",
            subject="Test",
            template_id=5,
            recipient_source=source,
            certified=0,
            now=FIXED_NOW,
        )

        assert email_sender.send.call_count == 1
        assert len(result.skipped) == 1

    def test_skips_contacts_without_attachment_url(self, use_case, contact_repo, email_sender, source):
        """Contacts without an attachment URL value are moved to the skipped list."""
        contacts = [
            make_contact(1, "a@test.com", None),
            make_contact(2, "b@test.com", "https://example.com/b.pdf"),
        ]
        contact_repo.get_by_group.return_value = contacts

        result = use_case.execute(
            from_email="sender@test.com",
            subject="Test",
            template_id=5,
            recipient_source=source,
            certified=0,
            now=FIXED_NOW,
        )

        assert email_sender.send.call_count == 1
        assert len(result.skipped) == 1

    def test_email_message_has_correct_fields(self, use_case, contact_repo, email_sender, source):
        """The EmailMessage passed to the sender contains all fields from the call arguments."""
        contacts = [make_contact(1, "a@test.com", "https://example.com/a.pdf")]
        contact_repo.get_by_group.return_value = contacts
        email_sender.send.return_value = {"data": {"id": 1}}

        use_case.execute(
            from_email="sender@test.com",
            subject="Hello",
            template_id=7,
            recipient_source=source,
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

    def test_start_dates_are_staggered(self, use_case, contact_repo, email_sender, source):
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
            subject="Test",
            template_id=5,
            recipient_source=source,
            certified=0,
            now=FIXED_NOW,
        )

        calls = email_sender.send.call_args_list
        dates = [c[0][0].start_date for c in calls]
        assert dates[1] > dates[0]
        assert dates[2] > dates[1]

    def test_dry_run_does_not_call_sender(self, use_case, contact_repo, email_sender, source):
        """In dry-run mode the email sender is never called but sent count is correct."""
        contacts = [make_contact(1, "a@test.com", "https://example.com/a.pdf")]
        contact_repo.get_by_group.return_value = contacts

        result = use_case.execute(
            from_email="sender@test.com",
            subject="Test",
            template_id=5,
            recipient_source=source,
            certified=0,
            now=FIXED_NOW,
            dry_run=True,
        )

        email_sender.send.assert_not_called()
        assert len(result.sent) == 1

    def test_dry_run_still_validates_attachment_url(self, use_case, contact_repo, email_sender, source):
        """Even in dry-run mode an inaccessible attachment moves the contact to errors."""
        contacts = [make_contact(1, "a@test.com", "https://example.com/a.pdf")]
        contact_repo.get_by_group.return_value = contacts

        checker = MagicMock()
        checker.is_accessible.return_value = False

        result = use_case.execute(
            from_email="sender@test.com",
            subject="Test",
            template_id=5,
            recipient_source=source,
            certified=0,
            now=FIXED_NOW,
            dry_run=True,
            attachment_checker=checker,
        )

        email_sender.send.assert_not_called()
        assert len(result.errors) == 1
        assert len(result.sent) == 0

    def test_relative_attachment_url_resolved_with_base_url(self, use_case, contact_repo, email_sender, source):
        """A relative attachment value is combined with the base URL before sending."""
        contacts = [make_contact(1, "a@test.com", "file.pdf")]
        contact_repo.get_by_group.return_value = contacts
        email_sender.send.return_value = {"data": {"id": 1}}

        use_case.execute(
            from_email="sender@test.com",
            subject="Test",
            template_id=5,
            recipient_source=source,
            certified=0,
            now=FIXED_NOW,
            attachment_base_url="https://example.com/files",
        )

        sent_message = email_sender.send.call_args[0][0]
        assert sent_message.attachments == ["https://example.com/files/file.pdf"]

    def test_inaccessible_attachment_discards_contact(self, use_case, contact_repo, email_sender, source):
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
            subject="Test",
            template_id=5,
            recipient_source=source,
            certified=0,
            now=FIXED_NOW,
            attachment_checker=checker,
        )

        assert len(result.sent) == 1
        assert len(result.errors) == 1

    def test_no_checker_skips_url_validation(self, use_case, contact_repo, email_sender, source):
        """When attachment_checker is None, no accessibility check is performed."""
        contacts = [make_contact(1, "a@test.com", "https://example.com/a.pdf")]
        contact_repo.get_by_group.return_value = contacts
        email_sender.send.return_value = {"data": {"id": 1}}

        result = use_case.execute(
            from_email="sender@test.com",
            subject="Test",
            template_id=5,
            recipient_source=source,
            certified=0,
            now=FIXED_NOW,
            attachment_checker=None,
        )

        assert len(result.sent) == 1

    def test_relative_url_without_base_url_adds_to_errors(self, use_case, contact_repo, email_sender, source):
        """A relative attachment value without a base URL causes an error for that contact."""
        contacts = [make_contact(1, "a@test.com", "file.pdf")]
        contact_repo.get_by_group.return_value = contacts

        result = use_case.execute(
            from_email="sender@test.com",
            subject="Test",
            template_id=5,
            recipient_source=source,
            certified=0,
            now=FIXED_NOW,
        )

        assert len(result.errors) == 1
        assert len(result.sent) == 0

    def test_returns_empty_result_when_no_contacts(self, use_case, contact_repo, email_sender, source):
        """When the group has no contacts all result lists are empty."""
        contact_repo.get_by_group.return_value = []

        result = use_case.execute(
            from_email="sender@test.com",
            subject="Test",
            template_id=5,
            recipient_source=source,
            certified=0,
            now=FIXED_NOW,
        )

        assert email_sender.send.call_count == 0
        assert len(result.sent) == 0
        assert len(result.skipped) == 0

    def test_sleep_called_once_per_eligible_contact(self, use_case, contact_repo, email_sender, source, mock_sleep):
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
            subject="Test",
            template_id=5,
            recipient_source=source,
            certified=0,
            now=FIXED_NOW,
        )

        assert mock_sleep.call_count == 3
        mock_sleep.assert_called_with(1)

    def test_no_sleep_in_dry_run(self, use_case, contact_repo, email_sender, source, mock_sleep):
        """time.sleep is not called when dry_run=True because no real API request is made."""
        contacts = [
            make_contact(1, "a@test.com", "https://example.com/a.pdf"),
            make_contact(2, "b@test.com", "https://example.com/b.pdf"),
        ]
        contact_repo.get_by_group.return_value = contacts

        use_case.execute(
            from_email="sender@test.com",
            subject="Test",
            template_id=5,
            recipient_source=source,
            certified=0,
            now=FIXED_NOW,
            dry_run=True,
        )

        mock_sleep.assert_not_called()


class TestSendBulkEmailsUseCaseWithLogger:
    """Tests that the use case calls the logger on real sends and dry runs alike."""

    @pytest.fixture(autouse=True)
    def mock_sleep(self):
        """Patch time.sleep so tests do not actually pause between sends."""
        with patch("src.application.use_cases.send_bulk_emails.time.sleep") as m:
            yield m

    def test_log_start_called_once_on_real_send(self, use_case, contact_repo, email_sender, source):
        """log_start() is called exactly once when a logger is provided and dry_run is False."""
        contact_repo.get_by_group.return_value = [make_contact(1, "a@test.com", "https://example.com/a.pdf")]
        email_sender.send.return_value = {}
        logger = MagicMock()

        use_case.execute(
            from_email="sender@test.com", subject="Test",
            template_id=5, recipient_source=source, certified=0,
            now=FIXED_NOW, logger=logger,
        )

        logger.log_start.assert_called_once()

    def test_log_ok_called_for_each_sent_contact(self, use_case, contact_repo, email_sender, source):
        """log_ok() is called once per successfully sent contact."""
        contact_repo.get_by_group.return_value = [
            make_contact(1, "a@test.com", "https://example.com/a.pdf"),
            make_contact(2, "b@test.com", "https://example.com/b.pdf"),
        ]
        email_sender.send.return_value = {}
        logger = MagicMock()

        use_case.execute(
            from_email="sender@test.com", subject="Test",
            template_id=5, recipient_source=source, certified=0,
            now=FIXED_NOW, logger=logger,
        )

        assert logger.log_ok.call_count == 2

    def test_log_skip_called_for_contacts_without_email_or_attachment(self, use_case, contact_repo, email_sender, source):
        """log_skip() is called for every contact excluded before sending."""
        contact_repo.get_by_group.return_value = [
            make_contact(1, "", "https://example.com/a.pdf"),
            make_contact(2, "b@test.com", None),
            make_contact(3, "c@test.com", "https://example.com/c.pdf"),
        ]
        email_sender.send.return_value = {}
        logger = MagicMock()

        use_case.execute(
            from_email="sender@test.com", subject="Test",
            template_id=5, recipient_source=source, certified=0,
            now=FIXED_NOW, logger=logger,
        )

        assert logger.log_skip.call_count == 2

    def test_log_skip_reason_no_email(self, use_case, contact_repo, email_sender, source):
        """log_skip() receives reason='no_email' for a contact with an empty email."""
        contact_repo.get_by_group.return_value = [make_contact(1, "", "https://example.com/a.pdf")]
        logger = MagicMock()

        use_case.execute(
            from_email="sender@test.com", subject="Test",
            template_id=5, recipient_source=source, certified=0,
            now=FIXED_NOW, logger=logger,
        )

        reason = logger.log_skip.call_args[0][1]
        assert reason == "no_email"

    def test_log_skip_reason_no_attachment(self, use_case, contact_repo, email_sender, source):
        """log_skip() receives reason='no_attachment' for a contact with no attachment value."""
        contact_repo.get_by_group.return_value = [make_contact(1, "a@test.com", None)]
        logger = MagicMock()

        use_case.execute(
            from_email="sender@test.com", subject="Test",
            template_id=5, recipient_source=source, certified=0,
            now=FIXED_NOW, logger=logger,
        )

        reason = logger.log_skip.call_args[0][1]
        assert reason == "no_attachment"

    def test_log_error_called_when_send_raises(self, use_case, contact_repo, email_sender, source):
        """log_error() is called when the email sender raises an exception."""
        contact_repo.get_by_group.return_value = [make_contact(1, "a@test.com", "https://example.com/a.pdf")]
        email_sender.send.side_effect = Exception("API error")
        logger = MagicMock()

        use_case.execute(
            from_email="sender@test.com", subject="Test",
            template_id=5, recipient_source=source, certified=0,
            now=FIXED_NOW, logger=logger,
        )

        logger.log_error.assert_called_once()

    def test_log_done_called_with_correct_counts(self, use_case, contact_repo, email_sender, source):
        """log_done() is called once with the final sent/skipped/error counts."""
        contact_repo.get_by_group.return_value = [make_contact(1, "a@test.com", "https://example.com/a.pdf")]
        email_sender.send.return_value = {}
        logger = MagicMock()

        use_case.execute(
            from_email="sender@test.com", subject="Test",
            template_id=5, recipient_source=source, certified=0,
            now=FIXED_NOW, logger=logger,
        )

        logger.log_done.assert_called_once_with(1, 0, 0)

    def test_dry_run_logs_like_a_real_send(self, use_case, contact_repo, email_sender, source):
        """A dry run writes the same start, ok, skip and done entries as a real send."""
        contact_repo.get_by_group.return_value = [
            make_contact(1, "a@test.com", "https://example.com/a.pdf"),
            make_contact(2, "", "https://example.com/b.pdf"),
        ]
        logger = MagicMock()

        use_case.execute(
            from_email="sender@test.com", subject="Test",
            template_id=5, recipient_source=source, certified=0,
            now=FIXED_NOW, dry_run=True, logger=logger,
        )

        logger.log_start.assert_called_once()
        logger.log_ok.assert_called_once_with(
            make_recipient(1, "a@test.com", "https://example.com/a.pdf"), "https://example.com/a.pdf"
        )
        logger.log_skip.assert_called_once_with(
            make_recipient(2, "", "https://example.com/b.pdf", "no_email"), "no_email"
        )
        logger.log_done.assert_called_once_with(1, 1, 0)

    def test_dry_run_logs_errors_found_while_preparing(self, use_case, contact_repo, email_sender, source):
        """A dry run logs a contact whose attachment cannot be resolved as an error."""
        contact_repo.get_by_group.return_value = [make_contact(1, "a@test.com", "relative.pdf")]
        logger = MagicMock()

        use_case.execute(
            from_email="sender@test.com", subject="Test",
            template_id=5, recipient_source=source, certified=0,
            now=FIXED_NOW, dry_run=True, logger=logger,
        )

        logger.log_error.assert_called_once()
        logger.log_done.assert_called_once_with(0, 0, 1)

    def test_dry_run_with_no_eligible_contacts_logs_every_skip(self, use_case, contact_repo, email_sender, source):
        """A dry run where no contact is eligible still logs each skipped contact with its reason."""
        contact_repo.get_by_group.return_value = [
            make_contact(1, "", "https://example.com/a.pdf"),
            make_contact(2, "b@test.com", None),
        ]
        logger = MagicMock()

        result = use_case.execute(
            from_email="sender@test.com", subject="Test",
            template_id=5, recipient_source=source, certified=0,
            now=FIXED_NOW, dry_run=True, logger=logger,
        )

        assert result.sent == []
        assert [c.args[1] for c in logger.log_skip.call_args_list] == ["no_email", "no_attachment"]
        logger.log_done.assert_called_once_with(0, 2, 0)

    def test_no_error_when_logger_is_none(self, use_case, contact_repo, email_sender, source):
        """The use case runs without error and returns correct results when logger=None."""
        contact_repo.get_by_group.return_value = [make_contact(1, "a@test.com", "https://example.com/a.pdf")]
        email_sender.send.return_value = {}

        result = use_case.execute(
            from_email="sender@test.com", subject="Test",
            template_id=5, recipient_source=source, certified=0,
            now=FIXED_NOW,
        )

        assert len(result.sent) == 1


class TestSendBulkEmailsUseCaseWithProgressCallback:
    """Tests that the use case reports per-contact progress via an optional callback."""

    @pytest.fixture(autouse=True)
    def mock_sleep(self):
        """Patch time.sleep so tests do not actually pause between sends."""
        with patch("src.application.use_cases.send_bulk_emails.time.sleep") as m:
            yield m

    def test_progress_callback_called_once_per_eligible_contact(self, use_case, contact_repo, email_sender, source):
        """progress_callback is invoked exactly once for each eligible contact processed."""
        contact_repo.get_by_group.return_value = [
            make_contact(1, "a@test.com", "https://example.com/a.pdf"),
            make_contact(2, "b@test.com", "https://example.com/b.pdf"),
            make_contact(3, "c@test.com", "https://example.com/c.pdf"),
        ]
        email_sender.send.return_value = {}
        progress_callback = MagicMock()

        use_case.execute(
            from_email="sender@test.com", subject="Test",
            template_id=5, recipient_source=source, certified=0,
            now=FIXED_NOW, progress_callback=progress_callback,
        )

        assert progress_callback.call_count == 3

    def test_progress_callback_receives_current_and_total(self, use_case, contact_repo, email_sender, source):
        """progress_callback receives the 1-indexed current position and the total eligible count."""
        contact_repo.get_by_group.return_value = [
            make_contact(1, "a@test.com", "https://example.com/a.pdf"),
            make_contact(2, "b@test.com", "https://example.com/b.pdf"),
        ]
        email_sender.send.return_value = {}
        progress_callback = MagicMock()

        use_case.execute(
            from_email="sender@test.com", subject="Test",
            template_id=5, recipient_source=source, certified=0,
            now=FIXED_NOW, progress_callback=progress_callback,
        )

        assert progress_callback.call_args_list == [call(1, 2), call(2, 2)]

    def test_progress_callback_called_for_errored_contacts(self, use_case, contact_repo, email_sender, source):
        """progress_callback fires even when a contact's send attempt raises an exception."""
        contact_repo.get_by_group.return_value = [make_contact(1, "a@test.com", "https://example.com/a.pdf")]
        email_sender.send.side_effect = Exception("API error")
        progress_callback = MagicMock()

        use_case.execute(
            from_email="sender@test.com", subject="Test",
            template_id=5, recipient_source=source, certified=0,
            now=FIXED_NOW, progress_callback=progress_callback,
        )

        progress_callback.assert_called_once_with(1, 1)

    def test_progress_callback_called_in_dry_run(self, use_case, contact_repo, email_sender, source):
        """progress_callback fires during a dry-run so the UI can still show progress."""
        contact_repo.get_by_group.return_value = [make_contact(1, "a@test.com", "https://example.com/a.pdf")]
        progress_callback = MagicMock()

        use_case.execute(
            from_email="sender@test.com", subject="Test",
            template_id=5, recipient_source=source, certified=0,
            now=FIXED_NOW, dry_run=True, progress_callback=progress_callback,
        )

        progress_callback.assert_called_once_with(1, 1)

    def test_no_error_when_progress_callback_is_none(self, use_case, contact_repo, email_sender, source):
        """The use case runs without error when progress_callback is not provided."""
        contact_repo.get_by_group.return_value = [make_contact(1, "a@test.com", "https://example.com/a.pdf")]
        email_sender.send.return_value = {}

        result = use_case.execute(
            from_email="sender@test.com", subject="Test",
            template_id=5, recipient_source=source, certified=0,
            now=FIXED_NOW,
        )

        assert len(result.sent) == 1


class TestSendBulkEmailsUseCaseWithSendRegistry:
    """Tests that the use case skips already-sent contacts and updates the registry."""

    @pytest.fixture(autouse=True)
    def mock_sleep(self):
        """Patch time.sleep so tests do not actually pause between sends."""
        with patch("src.application.use_cases.send_bulk_emails.time.sleep") as m:
            yield m

    @pytest.fixture
    def send_registry(self):
        """Mock SendRegistry with no prior sends recorded by default."""
        registry = MagicMock()
        registry.get_sent_keys.return_value = set()
        registry.get_last_start_date.return_value = None
        registry.get_uncertain_attempts.return_value = {}
        return registry

    def test_contact_already_marked_sent_is_not_sent_again(self, use_case, contact_repo, email_sender, source, send_registry):
        """A contact whose ID is already in the registry is excluded from the send loop."""
        contact_repo.get_by_group.return_value = [
            make_contact(1, "a@test.com", "https://example.com/a.pdf"),
            make_contact(2, "b@test.com", "https://example.com/b.pdf"),
        ]
        send_registry.get_sent_keys.return_value = {"1"}
        email_sender.send.return_value = {}

        result = use_case.execute(
            from_email="sender@test.com", subject="Test",
            template_id=5, recipient_source=source, certified=0,
            now=FIXED_NOW, send_registry=send_registry,
        )

        assert email_sender.send.call_count == 1
        assert email_sender.send.call_args[0][0].to_email == "b@test.com"
        assert len(result.sent) == 1

    def test_already_sent_contacts_are_reported_separately_from_skipped(self, use_case, contact_repo, email_sender, source, send_registry):
        """Contacts excluded because they were already sent land in already_sent, not skipped."""
        contact_repo.get_by_group.return_value = [
            make_contact(1, "a@test.com", "https://example.com/a.pdf"),
            make_contact(2, "b@test.com", "https://example.com/b.pdf"),
        ]
        send_registry.get_sent_keys.return_value = {"1"}
        email_sender.send.return_value = {}

        result = use_case.execute(
            from_email="sender@test.com", subject="Test",
            template_id=5, recipient_source=source, certified=0,
            now=FIXED_NOW, send_registry=send_registry,
        )

        assert [r.key for r in result.already_sent] == ["1"]
        assert result.skipped == []

    def test_registry_is_queried_with_campaign_parameters(self, use_case, contact_repo, email_sender, source, send_registry):
        """get_sent_keys() is called with the group, template, field name and subject."""
        contact_repo.get_by_group.return_value = []

        use_case.execute(
            from_email="sender@test.com", subject="Test",
            template_id=5, recipient_source=source, certified=0,
            now=FIXED_NOW, send_registry=send_registry,
        )

        send_registry.get_sent_keys.assert_called_once_with(Campaign("10", 5, "attachment_url", "Test"))

    def test_mark_sent_called_for_each_successful_send(self, use_case, contact_repo, email_sender, source, send_registry):
        """mark_sent() is called once per contact with its scheduled slot right after a successful send."""
        contact_repo.get_by_group.return_value = [make_contact(1, "a@test.com", "https://example.com/a.pdf")]
        email_sender.send.return_value = {}

        use_case.execute(
            from_email="sender@test.com", subject="Test",
            template_id=5, recipient_source=source, certified=0,
            now=FIXED_NOW, send_registry=send_registry,
        )

        send_registry.mark_sent.assert_called_once_with(Campaign("10", 5, "attachment_url", "Test"), "1", datetime(2024, 1, 15, 14, 40, 0))

    def test_mark_sent_not_called_when_send_fails(self, use_case, contact_repo, email_sender, source, send_registry):
        """mark_sent() is not called for a contact whose send attempt raised an exception."""
        contact_repo.get_by_group.return_value = [make_contact(1, "a@test.com", "https://example.com/a.pdf")]
        email_sender.send.side_effect = Exception("API error")

        use_case.execute(
            from_email="sender@test.com", subject="Test",
            template_id=5, recipient_source=source, certified=0,
            now=FIXED_NOW, send_registry=send_registry,
        )

        send_registry.mark_sent.assert_not_called()

    def test_mark_sent_not_called_in_dry_run(self, use_case, contact_repo, email_sender, source, send_registry):
        """No progress is persisted during a dry-run since no email is actually sent."""
        contact_repo.get_by_group.return_value = [make_contact(1, "a@test.com", "https://example.com/a.pdf")]

        use_case.execute(
            from_email="sender@test.com", subject="Test",
            template_id=5, recipient_source=source, certified=0,
            now=FIXED_NOW, dry_run=True, send_registry=send_registry,
        )

        send_registry.mark_sent.assert_not_called()

    def test_registry_filtering_still_applies_in_dry_run(self, use_case, contact_repo, email_sender, source, send_registry):
        """A dry-run preview still excludes contacts already sent in a previous real run."""
        contact_repo.get_by_group.return_value = [
            make_contact(1, "a@test.com", "https://example.com/a.pdf"),
            make_contact(2, "b@test.com", "https://example.com/b.pdf"),
        ]
        send_registry.get_sent_keys.return_value = {"1"}

        result = use_case.execute(
            from_email="sender@test.com", subject="Test",
            template_id=5, recipient_source=source, certified=0,
            now=FIXED_NOW, dry_run=True, send_registry=send_registry,
        )

        assert len(result.sent) == 1
        assert [r.key for r in result.already_sent] == ["1"]

    def test_clear_called_when_run_completes_with_no_errors(self, use_case, contact_repo, email_sender, source, send_registry):
        """clear() is called once the whole eligible batch was sent successfully."""
        contact_repo.get_by_group.return_value = [make_contact(1, "a@test.com", "https://example.com/a.pdf")]
        email_sender.send.return_value = {}

        use_case.execute(
            from_email="sender@test.com", subject="Test",
            template_id=5, recipient_source=source, certified=0,
            now=FIXED_NOW, send_registry=send_registry,
        )

        send_registry.clear.assert_called_once_with(Campaign("10", 5, "attachment_url", "Test"))

    def test_clear_not_called_when_there_are_errors(self, use_case, contact_repo, email_sender, source, send_registry):
        """clear() is not called if any contact failed, so a retry can pick up where it left off."""
        contact_repo.get_by_group.return_value = [
            make_contact(1, "a@test.com", "https://example.com/a.pdf"),
            make_contact(2, "b@test.com", "https://example.com/b.pdf"),
        ]
        email_sender.send.side_effect = [{}, EmailRejectedError("API error")]

        use_case.execute(
            from_email="sender@test.com", subject="Test",
            template_id=5, recipient_source=source, certified=0,
            now=FIXED_NOW, send_registry=send_registry,
        )

        send_registry.clear.assert_not_called()

    def test_clear_not_called_in_dry_run(self, use_case, contact_repo, email_sender, source, send_registry):
        """clear() is never called during a dry-run since nothing was actually sent."""
        contact_repo.get_by_group.return_value = [make_contact(1, "a@test.com", "https://example.com/a.pdf")]

        use_case.execute(
            from_email="sender@test.com", subject="Test",
            template_id=5, recipient_source=source, certified=0,
            now=FIXED_NOW, dry_run=True, send_registry=send_registry,
        )

        send_registry.clear.assert_not_called()

    def test_log_skip_called_with_already_sent_reason(self, use_case, contact_repo, email_sender, source, send_registry):
        """log_skip() records already-sent contacts with reason='already_sent'."""
        contact_repo.get_by_group.return_value = [make_contact(1, "a@test.com", "https://example.com/a.pdf")]
        send_registry.get_sent_keys.return_value = {"1"}
        logger = MagicMock()

        use_case.execute(
            from_email="sender@test.com", subject="Test",
            template_id=5, recipient_source=source, certified=0,
            now=FIXED_NOW, send_registry=send_registry, logger=logger,
        )

        logger.log_skip.assert_called_once_with(make_recipient(1, "a@test.com", "https://example.com/a.pdf"), "already_sent")

    def test_no_error_when_send_registry_is_none(self, use_case, contact_repo, email_sender, source):
        """The use case runs normally when send_registry is not provided (default behaviour)."""
        contact_repo.get_by_group.return_value = [make_contact(1, "a@test.com", "https://example.com/a.pdf")]
        email_sender.send.return_value = {}

        result = use_case.execute(
            from_email="sender@test.com", subject="Test",
            template_id=5, recipient_source=source, certified=0,
            now=FIXED_NOW,
        )

        assert len(result.sent) == 1
        assert result.already_sent == []


# First slot computed from FIXED_NOW (14:23) for a brand-new campaign
FIRST_SLOT = datetime(2024, 1, 15, 14, 40, 0)


def slot(n):
    """Return the n-th (0-indexed) 12-second slot after FIRST_SLOT."""
    return FIRST_SLOT + timedelta(seconds=12 * n)


def run(use_case, source, **kwargs):
    """Execute the use case with the standard campaign parameters used in this module."""
    return use_case.execute(
        from_email="sender@test.com", subject="Test",
        template_id=5, recipient_source=source, certified=0,
        now=FIXED_NOW, **kwargs,
    )


def sent_slots(email_sender):
    """Return the (recipient, start_date) pair of every call made to the sender, in order."""
    return [(c.args[0].to_email, c.args[0].start_date) for c in email_sender.send.call_args_list]


@pytest.fixture
def send_registry():
    """Mock SendRegistry with no prior state recorded."""
    registry = MagicMock()
    registry.get_sent_keys.return_value = set()
    registry.get_last_start_date.return_value = None
    registry.get_uncertain_attempts.return_value = {}
    return registry


@pytest.fixture
def one_contact(contact_repo):
    """A single eligible contact returned by the repository."""
    contact_repo.get_by_group.return_value = [make_contact(1, "a@test.com", "https://example.com/a.pdf")]


@pytest.fixture
def two_contacts(contact_repo):
    """Two eligible contacts returned by the repository."""
    contact_repo.get_by_group.return_value = [
        make_contact(1, "a@test.com", "https://example.com/a.pdf"),
        make_contact(2, "b@test.com", "https://example.com/b.pdf"),
    ]


class TestSendBulkEmailsUseCaseRetries:
    """Tests for the end-of-run retry of sends that got no answer from the API.

    Contacts whose request was not processed, or whose outcome is uncertain,
    are retried once after all other contacts, on new slots right after the
    last one of the run so the sending rhythm is kept. Rejections and
    pre-send failures are final and never retried.
    """

    @pytest.fixture(autouse=True)
    def mock_sleep(self):
        """Patch time.sleep so tests do not actually pause between sends."""
        with patch("src.application.use_cases.send_bulk_emails.time.sleep") as m:
            yield m

    @pytest.mark.parametrize("error", [EmailNotSentError("no connection"), EmailSendUncertainError("timeout")])
    def test_unanswered_send_is_retried_after_the_other_contacts(self, use_case, email_sender, source, two_contacts, error):
        """A send without answer is retried at the end on the slot after the last one of the run."""
        email_sender.send.side_effect = [error, {}, {}]

        run(use_case, source)

        assert sent_slots(email_sender) == [
            ("a@test.com", slot(0)),
            ("b@test.com", slot(1)),
            ("a@test.com", slot(2)),
        ]

    def test_successful_retry_counts_as_sent(self, use_case, email_sender, source, two_contacts):
        """A contact whose retry succeeds is reported as sent and not as an error."""
        email_sender.send.side_effect = [EmailNotSentError("no connection"), {}, {}]

        result = run(use_case, source)

        assert [item["recipient"].key for item in result.sent] == ["2", "1"]
        assert result.errors == []

    def test_failed_retry_is_reported_once_as_error(self, use_case, email_sender, source, two_contacts):
        """A contact whose retry fails again is retried only once and reported as one error."""
        email_sender.send.side_effect = [EmailNotSentError("no connection"), {}, EmailNotSentError("still down")]

        result = run(use_case, source)

        assert email_sender.send.call_count == 3
        assert len(result.errors) == 1
        assert result.errors[0]["recipient"].key == "1"
        assert result.errors[0]["error"] == "still down"

    def test_rejected_send_is_not_retried(self, use_case, email_sender, source, two_contacts):
        """A send refused by the API is a final error and is not retried."""
        email_sender.send.side_effect = [EmailRejectedError("invalid address"), {}]

        result = run(use_case, source)

        assert email_sender.send.call_count == 2
        assert [item["recipient"].key for item in result.errors] == ["1"]

    def test_unexpected_send_exception_is_treated_as_uncertain(self, use_case, email_sender, source, two_contacts):
        """An unknown exception from the sender is handled conservatively as an uncertain send."""
        email_sender.send.side_effect = [RuntimeError("boom"), {}, {}]

        result = run(use_case, source)

        assert email_sender.send.call_count == 3
        assert [u["recipient"].key for u in result.uncertain] == ["1"]

    def test_failure_before_sending_is_not_retried(self, use_case, contact_repo, email_sender, source):
        """A contact failing before any API call (e.g. unresolvable attachment) is not retried."""
        contact_repo.get_by_group.return_value = [make_contact(1, "a@test.com", "relative.pdf")]

        result = run(use_case, source)

        email_sender.send.assert_not_called()
        assert len(result.errors) == 1

    def test_sleep_before_every_attempt_including_retries(self, use_case, email_sender, source, two_contacts, mock_sleep):
        """The 1-second pause is applied before retries too, to respect the API rate limit."""
        email_sender.send.side_effect = [EmailNotSentError("no connection"), {}, {}]

        run(use_case, source)

        assert mock_sleep.call_count == 3

    def test_logger_records_only_the_final_outcome_of_a_retried_contact(self, use_case, email_sender, source, two_contacts):
        """A not-sent first attempt followed by a successful retry logs a single SEND_OK and no error."""
        email_sender.send.side_effect = [EmailNotSentError("no connection"), {}, {}]
        logger = MagicMock()

        run(use_case, source, logger=logger)

        assert logger.log_ok.call_count == 2
        logger.log_error.assert_not_called()
        logger.log_done.assert_called_once_with(2, 0, 0)


class TestSendBulkEmailsUseCaseUncertainSends:
    """Tests for reporting sends that may have been scheduled without confirmation.

    Every uncertain attempt is reported in SendResult.uncertain with the slot
    the user must check in the Mensagia portal, together with whether the
    contact ended up sent (making that slot a possible duplicate).
    """

    @pytest.fixture(autouse=True)
    def mock_sleep(self):
        """Patch time.sleep so tests do not actually pause between sends."""
        with patch("src.application.use_cases.send_bulk_emails.time.sleep") as m:
            yield m

    def test_uncertain_send_later_confirmed_is_a_possible_duplicate(self, use_case, email_sender, source, one_contact):
        """An uncertain attempt followed by a successful retry is reported as sent with the first slot."""
        email_sender.send.side_effect = [EmailSendUncertainError("timeout"), {}]

        result = run(use_case, source)

        assert len(result.uncertain) == 1
        assert result.uncertain[0]["recipient"].key == "1"
        assert result.uncertain[0]["start_dates"] == [slot(0)]
        assert result.uncertain[0]["sent"] is True

    def test_uncertain_send_never_confirmed_lists_every_slot(self, use_case, email_sender, source, one_contact):
        """When the retry is uncertain too, both slots are reported and the contact is not sent."""
        email_sender.send.side_effect = EmailSendUncertainError("timeout")

        result = run(use_case, source)

        assert result.uncertain[0]["start_dates"] == [slot(0), slot(1)]
        assert result.uncertain[0]["sent"] is False
        assert len(result.errors) == 1

    def test_not_sent_error_is_never_reported_as_uncertain(self, use_case, email_sender, source, one_contact):
        """A request known not to have been processed does not produce a duplicate warning."""
        email_sender.send.side_effect = [EmailNotSentError("no connection"), {}]

        result = run(use_case, source)

        assert result.uncertain == []

    def test_uncertain_attempt_is_logged_with_its_slot(self, use_case, email_sender, source, one_contact):
        """Each uncertain attempt is written to the log with the slot to check."""
        email_sender.send.side_effect = [EmailSendUncertainError("timeout"), {}]
        logger = MagicMock()

        run(use_case, source, logger=logger)

        logger.log_uncertain.assert_called_once_with(
            make_recipient(1, "a@test.com", "https://example.com/a.pdf"), slot(0), "timeout"
        )

    def test_uncertain_attempts_from_previous_run_are_reported(self, use_case, email_sender, source, one_contact, send_registry):
        """Unresolved attempts recorded by an interrupted run are included in the result."""
        previous = datetime(2024, 1, 15, 13, 0, 0)
        send_registry.get_uncertain_attempts.return_value = {"1": [previous]}
        email_sender.send.return_value = {}

        result = run(use_case, source, send_registry=send_registry)

        assert result.uncertain[0]["start_dates"] == [previous]
        assert result.uncertain[0]["sent"] is True

    def test_previous_uncertain_attempt_of_already_sent_contact_is_reported_as_sent(self, use_case, email_sender, source, one_contact, send_registry):
        """A previous unresolved attempt of a contact already sent is reported as a possible duplicate."""
        send_registry.get_sent_keys.return_value = {"1"}
        send_registry.get_uncertain_attempts.return_value = {"1": [datetime(2024, 1, 15, 13, 0, 0)]}

        result = run(use_case, source, send_registry=send_registry)

        assert result.uncertain[0]["sent"] is True

    def test_uncertain_attempts_are_not_reported_in_dry_run(self, use_case, email_sender, source, one_contact, send_registry):
        """A dry run reports nothing as uncertain because it never contacts the API."""
        send_registry.get_uncertain_attempts.return_value = {"1": [datetime(2024, 1, 15, 13, 0, 0)]}

        result = run(use_case, source, send_registry=send_registry, dry_run=True)

        assert result.uncertain == []


class TestSendBulkEmailsUseCaseRegistryAttempts:
    """Tests that every API call is recorded as an attempt and resolved afterwards.

    Recording the attempt before calling the API is what lets an abrupt close
    be detected as a possible duplicate on the next run, and its slot keeps
    the next run's schedule from overlapping.
    """

    @pytest.fixture(autouse=True)
    def mock_sleep(self):
        """Patch time.sleep so tests do not actually pause between sends."""
        with patch("src.application.use_cases.send_bulk_emails.time.sleep") as m:
            yield m

    def test_attempt_is_recorded_before_calling_the_api(self, use_case, email_sender, source, one_contact, send_registry):
        """mark_attempt() is called with the contact and slot before the sender is invoked."""
        order = []
        send_registry.mark_attempt.side_effect = lambda *a: order.append(("attempt", a))
        email_sender.send.side_effect = lambda m: order.append(("send", m.start_date)) or {}

        run(use_case, source, send_registry=send_registry)

        assert order == [("attempt", (Campaign("10", 5, "attachment_url", "Test"), "1", slot(0))), ("send", slot(0))]

    @pytest.mark.parametrize("error", [EmailRejectedError("invalid"), EmailNotSentError("no connection")])
    def test_attempt_is_discarded_when_nothing_was_scheduled(self, use_case, email_sender, source, one_contact, send_registry, error):
        """A rejected or not-processed request resolves its attempt with discard_attempt()."""
        email_sender.send.side_effect = [error, EmailRejectedError("invalid")]

        run(use_case, source, send_registry=send_registry)

        assert call(Campaign("10", 5, "attachment_url", "Test"), "1", slot(0)) in send_registry.discard_attempt.call_args_list

    def test_uncertain_attempt_is_left_unresolved(self, use_case, email_sender, source, one_contact, send_registry):
        """An uncertain send keeps its attempt on record so a later run can warn about it."""
        email_sender.send.side_effect = EmailSendUncertainError("timeout")

        run(use_case, source, send_registry=send_registry)

        send_registry.discard_attempt.assert_not_called()

    def test_no_attempt_recorded_when_failing_before_the_api_call(self, use_case, contact_repo, email_sender, source, send_registry):
        """A contact that fails before calling the API never records an attempt."""
        contact_repo.get_by_group.return_value = [make_contact(1, "a@test.com", "relative.pdf")]

        run(use_case, source, send_registry=send_registry)

        send_registry.mark_attempt.assert_not_called()

    def test_no_attempt_recorded_in_dry_run(self, use_case, email_sender, source, one_contact, send_registry):
        """A dry run never writes attempts to the registry."""
        run(use_case, source, send_registry=send_registry, dry_run=True)

        send_registry.mark_attempt.assert_not_called()

    def test_resumed_run_continues_after_previous_last_slot(self, use_case, email_sender, source, one_contact, send_registry):
        """With a previous last slot far enough ahead, the first email goes 12 seconds after it."""
        send_registry.get_last_start_date.return_value = datetime(2024, 1, 15, 15, 40, 0)
        email_sender.send.return_value = {}

        run(use_case, source, send_registry=send_registry)

        assert sent_slots(email_sender) == [("a@test.com", datetime(2024, 1, 15, 15, 40, 12))]

    def test_resumed_run_with_past_last_slot_applies_initial_gap(self, use_case, email_sender, source, one_contact, send_registry):
        """With a previous last slot already in the past, the usual initial gap applies."""
        send_registry.get_last_start_date.return_value = datetime(2024, 1, 15, 12, 0, 0)
        email_sender.send.return_value = {}

        run(use_case, source, send_registry=send_registry)

        assert sent_slots(email_sender) == [("a@test.com", slot(0))]

    def test_dry_run_preview_uses_the_resumed_schedule(self, use_case, email_sender, source, one_contact, send_registry):
        """The dry run reads the previous last slot so its preview matches a real resumed run."""
        send_registry.get_last_start_date.return_value = datetime(2024, 1, 15, 15, 40, 0)

        result = run(use_case, source, send_registry=send_registry, dry_run=True)

        send_registry.get_last_start_date.assert_called_once_with(Campaign("10", 5, "attachment_url", "Test"))
        assert len(result.sent) == 1


class TestSendBulkEmailsUseCaseFixedStart:
    """Tests for the fixed start mode: the first email goes out at the date and time chosen by the user."""

    START = datetime(2024, 1, 16, 9, 0, 0)

    @pytest.fixture(autouse=True)
    def mock_sleep(self):
        """Patch time.sleep so tests do not actually pause between sends."""
        with patch("src.application.use_cases.send_bulk_emails.time.sleep") as m:
            yield m

    def test_first_email_goes_out_at_the_chosen_time(self, use_case, email_sender, source, two_contacts):
        """The emails are scheduled from the chosen start, 12 seconds apart."""
        email_sender.send.return_value = {}

        run(use_case, source, start_mode=StartMode.FIXED, start_at=self.START)

        assert sent_slots(email_sender) == [
            ("a@test.com", self.START),
            ("b@test.com", self.START + timedelta(seconds=12)),
        ]

    def test_a_chosen_time_without_enough_lead_is_postponed(self, use_case, email_sender, source, two_contacts):
        """A chosen start less than 10 minutes ahead is postponed to the "now" schedule."""
        email_sender.send.return_value = {}

        run(use_case, source, start_mode=StartMode.FIXED, start_at=datetime(2024, 1, 15, 14, 25, 0))

        assert sent_slots(email_sender)[0] == ("a@test.com", FIRST_SLOT)

    def test_the_start_mode_is_part_of_the_campaign(self, use_case, email_sender, source, two_contacts, send_registry):
        """The registry is queried with a campaign carrying the fixed start mode."""
        email_sender.send.return_value = {}

        run(use_case, source, start_mode=StartMode.FIXED, start_at=self.START, send_registry=send_registry)

        send_registry.get_sent_keys.assert_called_once_with(
            Campaign("10", 5, "attachment_url", "Test", StartMode.FIXED)
        )

    def test_the_log_records_the_start_mode_and_first_slot(self, use_case, email_sender, source, two_contacts):
        """log_start() receives the start mode, the chosen start and the first slot actually used."""
        email_sender.send.return_value = {}
        logger = MagicMock()

        run(use_case, source, start_mode=StartMode.FIXED, start_at=self.START, logger=logger)

        kwargs = logger.log_start.call_args.kwargs
        assert (kwargs["start_mode"], kwargs["start_at"], kwargs["first_slot"]) == (StartMode.FIXED, self.START, self.START)

    def test_a_fixed_start_requires_a_date(self, use_case, source, two_contacts):
        """Choosing the fixed start mode without a start date is rejected."""
        with pytest.raises(ValueError):
            run(use_case, source, start_mode=StartMode.FIXED)

    def test_starts_now_by_default(self, use_case, email_sender, source, two_contacts):
        """Without a start mode the first email follows the "now" schedule."""
        email_sender.send.return_value = {}

        run(use_case, source)

        assert sent_slots(email_sender)[0] == ("a@test.com", FIRST_SLOT)
