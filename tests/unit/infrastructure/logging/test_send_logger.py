import re
from datetime import datetime
from src.domain.entities.recipient import Recipient
from src.domain.scheduling import StartMode
from src.infrastructure.logging.send_logger import SendLogger


def make_contact(contact_id, email, name=None):
    """Build an agenda Recipient for use in logger tests."""
    return Recipient(key=str(contact_id), email=email, attachment="", name=name or f"Contact {contact_id}")


def make_row(row, email, attachment):
    """Build a Recipient read from a file row for use in logger tests."""
    return Recipient(key=f"{email}|{attachment}", email=email, attachment=attachment, row=row)


class TestSendLogger:
    """Tests for SendLogger — verifies log file creation, keyword tags, and field content."""

    def test_creates_log_file_in_given_directory(self, tmp_path):
        """A log file is created inside the specified directory on construction."""
        logger = SendLogger(log_dir=str(tmp_path))
        assert logger.log_path.exists()
        assert logger.log_path.parent == tmp_path

    def test_defaults_to_logs_folder_in_user_data_dir(self, tmp_path, monkeypatch):
        """Without an explicit directory, logs go to a logs/ folder in the user data directory."""
        monkeypatch.setattr("src.infrastructure.logging.send_logger.user_data_dir", lambda: tmp_path)
        logger = SendLogger()
        assert logger.log_path.parent == tmp_path / "logs"
        assert logger.log_path.exists()

    def test_log_file_name_has_expected_prefix_and_suffix(self, tmp_path):
        """The log file name starts with mensagia_send_ and ends with .log."""
        logger = SendLogger(log_dir=str(tmp_path))
        assert logger.log_path.name.startswith("mensagia_send_")
        assert logger.log_path.name.endswith(".log")

    def test_log_start_writes_send_start_keyword(self, tmp_path):
        """log_start() writes a line containing the [SEND_START] keyword."""
        logger = SendLogger(log_dir=str(tmp_path))
        logger.log_start("from@test.com", "Subject", 42, "group_id=15", "attachment_url", 0, 10, 2)
        assert "[SEND_START]" in logger.log_path.read_text(encoding="utf-8")

    def test_log_start_includes_all_parameters(self, tmp_path):
        """log_start() records from, subject, template_id, group_id, field, certified, eligible and skipped."""
        logger = SendLogger(log_dir=str(tmp_path))
        logger.log_start("from@test.com", "My Subject", 42, "group_id=15", "attachment_url", 1, 10, 2)
        content = logger.log_path.read_text(encoding="utf-8")
        assert "from@test.com" in content
        assert "My Subject" in content
        assert "template_id=42" in content
        assert "group_id=15" in content
        assert "attachment_url" in content
        assert "certified=1" in content
        assert "eligible=10" in content
        assert "skipped=2" in content

    def test_log_start_records_a_now_start(self, tmp_path):
        """log_start() records the "now" start mode and the first slot."""
        logger = SendLogger(log_dir=str(tmp_path))
        logger.log_start("f@t.com", "Subj", 1, "group_id=1", "field", 0, 1, 0,
                         start_mode=StartMode.NOW, first_slot=datetime(2026, 10, 8, 10, 20, 0))
        content = logger.log_path.read_text(encoding="utf-8")
        assert "start_mode=now" in content
        assert "start_at=" not in content
        assert "first_slot=2026-10-08T10:20:00" in content

    def test_log_start_records_a_fixed_start(self, tmp_path):
        """log_start() records the fixed start mode, the chosen start and the first slot."""
        logger = SendLogger(log_dir=str(tmp_path))
        logger.log_start("f@t.com", "Subj", 1, "group_id=1", "field", 0, 1, 0, start_mode=StartMode.FIXED,
                         start_at=datetime(2026, 10, 15, 9, 0, 0), first_slot=datetime(2026, 10, 15, 9, 0, 0))
        content = logger.log_path.read_text(encoding="utf-8")
        assert "start_mode=fixed start_at=2026-10-15T09:00:00 first_slot=2026-10-15T09:00:00" in content

    def test_log_start_omits_the_first_slot_when_nothing_is_sent(self, tmp_path):
        """log_start() leaves out the first slot when no email is scheduled."""
        logger = SendLogger(log_dir=str(tmp_path))
        logger.log_start("f@t.com", "Subj", 1, "group_id=1", "field", 0, 0, 3)
        assert "first_slot=" not in logger.log_path.read_text(encoding="utf-8")

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

    def test_log_uncertain_writes_send_uncertain_keyword(self, tmp_path):
        """log_uncertain() writes a line containing the [SEND_UNCERTAIN] keyword."""
        logger = SendLogger(log_dir=str(tmp_path))
        logger.log_uncertain(make_contact(1, "a@test.com"), datetime(2024, 1, 15, 14, 40, 12), "timeout")
        assert "[SEND_UNCERTAIN]" in logger.log_path.read_text(encoding="utf-8")

    def test_log_uncertain_includes_contact_slot_and_reason(self, tmp_path):
        """log_uncertain() records contact id, email, the slot to check in the portal and the reason."""
        logger = SendLogger(log_dir=str(tmp_path))
        logger.log_uncertain(make_contact(123, "john@test.com"), datetime(2024, 1, 15, 14, 40, 12), "read timeout")
        content = logger.log_path.read_text(encoding="utf-8")
        assert "id=123" in content
        assert "to=john@test.com" in content
        assert "start_date=2024-01-15T14:40:12" in content
        assert 'reason="read timeout"' in content

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
        logger.log_start("f@t.com", "Subj", 1, "group_id=1", "field", 0, 1, 0)
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
        logger.log_start("f@t.com", "My Subject Line", 1, "group_id=1", "field", 0, 1, 0)
        content = logger.log_path.read_text(encoding="utf-8")
        assert 'subject="My Subject Line"' in content

    def test_real_send_log_has_no_simulation_header(self, tmp_path):
        """A real send log does not carry the [SIMULATION] header."""
        logger = SendLogger(log_dir=str(tmp_path))
        logger.log_done(1, 0, 0)
        assert "[SIMULATION]" not in logger.log_path.read_text(encoding="utf-8")


class TestSendLoggerSimulation:
    """Tests for SendLogger in simulation mode — file name and header that tell it apart from a real send."""

    def test_simulation_log_file_name_has_simulation_prefix(self, tmp_path):
        """A simulation log file name starts with mensagia_simulation_ and ends with .log."""
        logger = SendLogger(log_dir=str(tmp_path), simulation=True)
        assert logger.log_path.name.startswith("mensagia_simulation_")
        assert logger.log_path.name.endswith(".log")

    def test_simulation_log_goes_to_the_same_folder_as_send_logs(self, tmp_path, monkeypatch):
        """Without an explicit directory, simulation logs share the logs/ folder of real sends."""
        monkeypatch.setattr("src.infrastructure.logging.send_logger.user_data_dir", lambda: tmp_path)
        assert SendLogger(simulation=True).log_path.parent == SendLogger().log_path.parent

    def test_simulation_log_starts_with_simulation_header(self, tmp_path):
        """The first line of a simulation log is a [SIMULATION] header saying nothing was sent."""
        logger = SendLogger(log_dir=str(tmp_path), simulation=True)
        logger.log_start("f@t.com", "Subj", 1, "group_id=1", "field", 0, 1, 0)
        first_line = logger.log_path.read_text(encoding="utf-8").splitlines()[0]
        assert "[SIMULATION]" in first_line
        assert "no email was sent" in first_line


class TestSendLoggerFileRows:
    """Tests for the log lines of recipients read from a file.

    A file row has no contact ID nor name: it is identified by its row
    number as a spreadsheet shows it, its email and its attachment, so the
    user can find it in the file.
    """

    def test_log_skip_identifies_the_row(self, tmp_path):
        """log_skip() records the row number, email, attachment and reason of a file row."""
        logger = SendLogger(log_dir=str(tmp_path))
        logger.log_skip(make_row(14, "agencia@x.com", "factura_123.pdf"), "duplicate_row")
        content = logger.log_path.read_text(encoding="utf-8")
        assert "[SEND_SKIP]  row=14 to=agencia@x.com attachment=factura_123.pdf reason=duplicate_row" in content

    def test_log_ok_identifies_the_row(self, tmp_path):
        """log_ok() records the row number, email and resolved attachment URL of a file row."""
        logger = SendLogger(log_dir=str(tmp_path))
        logger.log_ok(make_row(3, "a@x.com", "a.pdf"), "https://example.com/a.pdf")
        content = logger.log_path.read_text(encoding="utf-8")
        assert "[SEND_OK]    row=3 to=a@x.com attachment=https://example.com/a.pdf" in content

    def test_log_error_identifies_the_row(self, tmp_path):
        """log_error() records the row number, email, attachment and reason of a file row."""
        logger = SendLogger(log_dir=str(tmp_path))
        logger.log_error(make_row(3, "a@x.com", "a.pdf"), "attachment not accessible")
        content = logger.log_path.read_text(encoding="utf-8")
        assert '[SEND_ERROR] row=3 to=a@x.com attachment=a.pdf reason="attachment not accessible"' in content

    def test_log_uncertain_identifies_the_row(self, tmp_path):
        """log_uncertain() records the row number, email, attachment, slot and reason of a file row."""
        logger = SendLogger(log_dir=str(tmp_path))
        logger.log_uncertain(make_row(3, "a@x.com", "a.pdf"), datetime(2024, 1, 15, 14, 40, 12), "timeout")
        content = logger.log_path.read_text(encoding="utf-8")
        assert "[SEND_UNCERTAIN] row=3 to=a@x.com attachment=a.pdf start_date=2024-01-15T14:40:12 reason=timeout" in content

    def test_attachment_with_spaces_is_quoted(self, tmp_path):
        """An attachment value with spaces is wrapped in double quotes."""
        logger = SendLogger(log_dir=str(tmp_path))
        logger.log_skip(make_row(2, "", "my file.pdf"), "no_email")
        assert 'row=2 to= attachment="my file.pdf" reason=no_email' in logger.log_path.read_text(encoding="utf-8")

    def test_log_start_records_the_source_label(self, tmp_path):
        """log_start() writes the label of a file source in place of the group ID."""
        logger = SendLogger(log_dir=str(tmp_path))
        logger.log_start("f@t.com", "Subj", 1, 'file=clientes.xlsx sheet=Hoja1', "Adjunto", 0, 1, 0)
        content = logger.log_path.read_text(encoding="utf-8")
        assert "template_id=1 file=clientes.xlsx sheet=Hoja1 field=Adjunto" in content
