import re
from src.domain.entities.contact import Contact
from src.infrastructure.logging.send_logger import SendLogger


def make_contact(contact_id, email, name=None):
    """Build a Contact for use in logger tests."""
    return Contact(id=contact_id, name=name or f"Contact {contact_id}", email=email, extra_fields={})


class TestSendLogger:
    """Tests for SendLogger — verifies log file creation, keyword tags, and field content."""

    def test_creates_log_file_in_given_directory(self, tmp_path):
        """A log file is created inside the specified directory on construction."""
        logger = SendLogger(log_dir=str(tmp_path))
        assert logger.log_path.exists()
        assert logger.log_path.parent == tmp_path

    def test_log_file_name_has_expected_prefix_and_suffix(self, tmp_path):
        """The log file name starts with mensagia_send_ and ends with .log."""
        logger = SendLogger(log_dir=str(tmp_path))
        assert logger.log_path.name.startswith("mensagia_send_")
        assert logger.log_path.name.endswith(".log")

    def test_log_start_writes_send_start_keyword(self, tmp_path):
        """log_start() writes a line containing the [SEND_START] keyword."""
        logger = SendLogger(log_dir=str(tmp_path))
        logger.log_start("from@test.com", "Subject", 42, 15, "attachment_url", 0, 10, 2)
        assert "[SEND_START]" in logger.log_path.read_text(encoding="utf-8")

    def test_log_start_includes_all_parameters(self, tmp_path):
        """log_start() records from, subject, template_id, group_id, field, certified, eligible and skipped."""
        logger = SendLogger(log_dir=str(tmp_path))
        logger.log_start("from@test.com", "My Subject", 42, 15, "attachment_url", 1, 10, 2)
        content = logger.log_path.read_text(encoding="utf-8")
        assert "from@test.com" in content
        assert "My Subject" in content
        assert "template_id=42" in content
        assert "group_id=15" in content
        assert "attachment_url" in content
        assert "certified=1" in content
        assert "eligible=10" in content
        assert "skipped=2" in content

    def test_log_ok_writes_send_ok_keyword(self, tmp_path):
        """log_ok() writes a line containing the [SEND_OK] keyword."""
        logger = SendLogger(log_dir=str(tmp_path))
        logger.log_ok(make_contact(1, "a@test.com", "John Doe"), "https://example.com/a.pdf")
        assert "[SEND_OK]" in logger.log_path.read_text(encoding="utf-8")

    def test_log_ok_includes_contact_and_attachment(self, tmp_path):
        """log_ok() records contact id, name, email and resolved attachment URL."""
        logger = SendLogger(log_dir=str(tmp_path))
        logger.log_ok(make_contact(123, "john@test.com", "John Doe"), "https://example.com/john.pdf")
        content = logger.log_path.read_text(encoding="utf-8")
        assert "id=123" in content
        assert "John Doe" in content
        assert "john@test.com" in content
        assert "https://example.com/john.pdf" in content

    def test_log_skip_writes_send_skip_keyword(self, tmp_path):
        """log_skip() writes a line containing the [SEND_SKIP] keyword."""
        logger = SendLogger(log_dir=str(tmp_path))
        logger.log_skip(make_contact(2, "", "No Email"), "no_email")
        assert "[SEND_SKIP]" in logger.log_path.read_text(encoding="utf-8")

    def test_log_skip_includes_contact_id_name_and_reason(self, tmp_path):
        """log_skip() records contact id, name and the machine-readable skip reason."""
        logger = SendLogger(log_dir=str(tmp_path))
        logger.log_skip(make_contact(99, "a@test.com", "Alice"), "no_attachment")
        content = logger.log_path.read_text(encoding="utf-8")
        assert "id=99" in content
        assert "Alice" in content
        assert "reason=no_attachment" in content

    def test_log_error_writes_send_error_keyword(self, tmp_path):
        """log_error() writes a line containing the [SEND_ERROR] keyword."""
        logger = SendLogger(log_dir=str(tmp_path))
        logger.log_error(make_contact(3, "err@test.com", "Err Contact"), "attachment not accessible")
        assert "[SEND_ERROR]" in logger.log_path.read_text(encoding="utf-8")

    def test_log_error_includes_contact_email_and_reason(self, tmp_path):
        """log_error() records the contact's email and the full error description."""
        logger = SendLogger(log_dir=str(tmp_path))
        logger.log_error(
            make_contact(3, "err@test.com", "Err Contact"),
            "attachment not accessible: https://broken.url/file.pdf",
        )
        content = logger.log_path.read_text(encoding="utf-8")
        assert "err@test.com" in content
        assert "attachment not accessible" in content

    def test_log_done_writes_send_done_keyword(self, tmp_path):
        """log_done() writes a line containing the [SEND_DONE] keyword."""
        logger = SendLogger(log_dir=str(tmp_path))
        logger.log_done(10, 2, 1)
        assert "[SEND_DONE]" in logger.log_path.read_text(encoding="utf-8")

    def test_log_done_includes_counts(self, tmp_path):
        """log_done() records sent, skipped and error counts."""
        logger = SendLogger(log_dir=str(tmp_path))
        logger.log_done(10, 2, 1)
        content = logger.log_path.read_text(encoding="utf-8")
        assert "sent=10" in content
        assert "skipped=2" in content
        assert "errors=1" in content

    def test_every_logged_line_has_timestamp(self, tmp_path):
        """Every line written to the log starts with a YYYY-MM-DD HH:MM:SS timestamp."""
        logger = SendLogger(log_dir=str(tmp_path))
        contact = make_contact(1, "a@test.com", "Alice")
        logger.log_start("f@t.com", "Subj", 1, 1, "field", 0, 1, 0)
        logger.log_ok(contact, "https://example.com/a.pdf")
        logger.log_done(1, 0, 0)
        lines = [ln for ln in logger.log_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        for line in lines:
            assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} ", line), f"No timestamp in: {line}"

    def test_names_with_spaces_are_quoted(self, tmp_path):
        """Contact names that contain spaces are wrapped in double quotes in the log."""
        logger = SendLogger(log_dir=str(tmp_path))
        logger.log_ok(make_contact(1, "a@test.com", "John Doe"), "https://example.com/a.pdf")
        content = logger.log_path.read_text(encoding="utf-8")
        assert 'name="John Doe"' in content

    def test_subject_with_spaces_is_quoted(self, tmp_path):
        """Subject lines that contain spaces are wrapped in double quotes in the log."""
        logger = SendLogger(log_dir=str(tmp_path))
        logger.log_start("f@t.com", "My Subject Line", 1, 1, "field", 0, 1, 0)
        content = logger.log_path.read_text(encoding="utf-8")
        assert 'subject="My Subject Line"' in content
