import json
from datetime import date, datetime

import openpyxl
import pytest

from src.domain.date_input import DateFormat
from src.domain.file_rows import row_key
from src.infrastructure.files.table_file import TableFileError
from src.infrastructure.recipients.file_recipient_source import FileRecipientSource


def write_csv(path, text: str) -> str:
    """Write a UTF-8 .csv file and return its path as text."""
    path.write_bytes(text.encode("utf-8"))
    return str(path)


def source_for(path: str, sheet: str | None = None) -> FileRecipientSource:
    """Build a source reading the 'Correo' and 'Adjunto' columns of *path*."""
    return FileRecipientSource(path, sheet, "Correo", "Adjunto")


class TestFileRecipientSourceRows:
    """Covers turning the rows of a file into recipients."""

    def test_maps_a_row_to_a_recipient(self, tmp_path):
        """A row becomes a recipient with its stripped email, attachment, row number and key."""
        path = write_csv(tmp_path / "f.csv", "Correo;Adjunto\n a@x.com ;factura.pdf\n")
        [recipient] = source_for(path).get_recipients()
        assert (recipient.email, recipient.attachment, recipient.row) == ("a@x.com", "factura.pdf", 2)
        assert recipient.key == row_key("a@x.com", "factura.pdf")
        assert recipient.skip_reason is None

    def test_empty_and_invalid_emails_are_skipped(self, tmp_path):
        """Rows with an empty or invalid address carry the no_email and invalid_email reasons."""
        path = write_csv(tmp_path / "f.csv", "Correo;Adjunto;Otra\n;a.pdf;x\na@x.com;b@x.com;b.pdf\nc@x.com, d@x.com;c.pdf\n")
        reasons = [r.skip_reason for r in source_for(path).get_recipients()]
        assert reasons == ["no_email", None, "invalid_email"]

    def test_rows_without_attachment_are_skipped(self, tmp_path):
        """A row with an address but no attachment carries the no_attachment reason."""
        path = write_csv(tmp_path / "f.csv", "Correo;Adjunto\na@x.com;\n")
        assert source_for(path).get_recipients()[0].skip_reason == "no_attachment"

    def test_repeated_rows_are_skipped_as_duplicates(self, tmp_path):
        """A second row with the same address (any case) and attachment is a duplicate."""
        path = write_csv(tmp_path / "f.csv", "Correo;Adjunto\na@x.com;a.pdf\nA@X.com;a.pdf\na@x.com;b.pdf\n")
        reasons = [r.skip_reason for r in source_for(path).get_recipients()]
        assert reasons == [None, "duplicate_row", None]

    def test_relative_and_absolute_values_of_the_same_file_are_duplicates(self, tmp_path):
        """A relative path and the full URL it resolves to are the same attachment for the same address."""
        path = write_csv(tmp_path / "f.csv", "Correo;Adjunto\na@x.com;a.pdf\na@x.com;https://cdn.x.com/docs/a.pdf\n")
        source = FileRecipientSource(path, None, "Correo", "Adjunto", "https://cdn.x.com/docs/")
        reasons = [r.skip_reason for r in source.get_recipients()]
        assert reasons == [None, "duplicate_row"]

    def test_key_uses_the_resolved_url(self, tmp_path):
        """A row is recorded by the URL its attachment resolves to, while it keeps the value as written."""
        path = write_csv(tmp_path / "f.csv", "Correo;Adjunto\na@x.com;a.pdf\n")
        [recipient] = FileRecipientSource(path, None, "Correo", "Adjunto", "https://cdn.x.com/docs").get_recipients()
        assert recipient.key == row_key("a@x.com", "https://cdn.x.com/docs/a.pdf")
        assert recipient.attachment == "a.pdf"

    def test_relative_values_are_compared_as_written_without_a_base_url(self, tmp_path):
        """Without a base URL, a relative path cannot be resolved and is compared as written."""
        path = write_csv(tmp_path / "f.csv", "Correo;Adjunto\na@x.com;a.pdf\na@x.com;https://cdn.x.com/docs/a.pdf\n")
        reasons = [r.skip_reason for r in source_for(path).get_recipients()]
        assert reasons == [None, None]

    def test_numeric_attachment_cells_lose_their_decimals(self, tmp_path):
        """An attachment written as a whole number in Excel is read without decimals."""
        workbook = openpyxl.Workbook()
        workbook.active.append(["Correo", "Adjunto"])
        workbook.active.append(["a@x.com", 1234.0])
        workbook.save(tmp_path / "f.xlsx")
        [recipient] = source_for(str(tmp_path / "f.xlsx")).get_recipients()
        assert recipient.attachment == "1234"

    def test_reads_the_chosen_sheet(self, tmp_path):
        """With a sheet given, the rows come from that sheet."""
        workbook = openpyxl.Workbook()
        workbook.active.title = "Octubre"
        workbook.active.append(["Correo", "Adjunto"])
        workbook.active.append(["a@x.com", "a.pdf"])
        november = workbook.create_sheet("Noviembre")
        november.append(["Correo", "Adjunto"])
        november.append(["b@x.com", "b.pdf"])
        workbook.save(tmp_path / "f.xlsx")
        [recipient] = source_for(str(tmp_path / "f.xlsx"), "Noviembre").get_recipients()
        assert recipient.email == "b@x.com"

    def test_file_is_read_again_on_every_call(self, tmp_path):
        """Changes saved to the file between the summary and the send are picked up."""
        path = write_csv(tmp_path / "f.csv", "Correo;Adjunto\na@x.com;a.pdf\n")
        source = source_for(path)
        source.get_recipients()
        write_csv(tmp_path / "f.csv", "Correo;Adjunto\na@x.com;a.pdf\nb@x.com;b.pdf\n")
        assert len(source.get_recipients()) == 2

    def test_missing_column_is_reported(self, tmp_path):
        """A chosen column that is no longer in the file is reported with its name."""
        path = write_csv(tmp_path / "f.csv", "Email;Adjunto\na@x.com;a.pdf\n")
        with pytest.raises(TableFileError) as info:
            source_for(path).get_recipients()
        assert (info.value.code, info.value.details) == ("missing_column", {"name": "Correo"})


class TestFileRecipientSourceIdentity:
    """Covers how a file source is identified in a campaign and in the log."""

    def test_identity_uses_the_file_name_without_its_folder(self, tmp_path):
        """Moving the file to another folder keeps the same identity, so a send can be resumed."""
        (tmp_path / "a").mkdir()
        (tmp_path / "b").mkdir()
        first = FileRecipientSource(str(tmp_path / "a" / "clientes.csv"), None, "Correo", "Adjunto")
        second = FileRecipientSource(str(tmp_path / "b" / "clientes.csv"), None, "Correo", "Adjunto")
        assert first.identity == second.identity

    def test_identity_includes_sheet_and_email_column(self, tmp_path):
        """Another sheet or another email column makes a different campaign."""
        path = str(tmp_path / "clientes.xlsx")
        base = FileRecipientSource(path, "Octubre", "Correo", "Adjunto").identity
        assert FileRecipientSource(path, "Noviembre", "Correo", "Adjunto").identity != base
        assert FileRecipientSource(path, "Octubre", "Email", "Adjunto").identity != base

    def test_identity_can_never_match_an_agenda_group(self, tmp_path):
        """The identity names the kind of source, so it never equals a group ID."""
        identity = FileRecipientSource(str(tmp_path / "123"), None, "Correo", "Adjunto").identity
        assert json.loads(identity)[0] == "file"

    def test_attachment_field_is_the_attachment_column(self, tmp_path):
        """The campaign's attachment field is the chosen attachment column."""
        assert source_for(str(tmp_path / "f.csv")).attachment_field == "Adjunto"

    def test_log_fields_name_the_file_sheet_and_email_column(self, tmp_path):
        """The log names the file (without its folder), the sheet and the email column."""
        source = FileRecipientSource(str(tmp_path / "clientes.xlsx"), "Hoja1", "Correo", "Adjunto")
        assert source.log_fields == {"file": "clientes.xlsx", "sheet": "Hoja1", "email_column": "Correo"}

    def test_log_fields_leave_out_the_sheet_of_a_csv(self, tmp_path):
        """A CSV file has no sheet to name."""
        assert "sheet" not in source_for(str(tmp_path / "f.csv")).log_fields


def dated_source(path: str, fmt: DateFormat = DateFormat.DMY_SLASH) -> FileRecipientSource:
    """Build a source reading the send day from the 'Fecha' column of *path*."""
    return FileRecipientSource(path, None, "Correo", "Adjunto", date_column="Fecha", date_format=fmt)


def write_dated_xlsx(path, dates: list) -> str:
    """Write a workbook with one sendable row per value of *dates* in its 'Fecha' column."""
    workbook = openpyxl.Workbook()
    workbook.active.append(["Correo", "Adjunto", "Fecha"])
    for i, value in enumerate(dates):
        workbook.active.append([f"a{i}@x.com", "a.pdf", value])
    workbook.save(path)
    return str(path)


class TestFileRecipientSourceSendDate:
    """Covers reading the send day of each row from a column."""

    def test_text_cells_use_the_chosen_format(self, tmp_path):
        """A date written as text is read with the chosen format."""
        path = write_csv(tmp_path / "f.csv", "Correo;Adjunto;Fecha\na@x.com;a.pdf;2026-11-05\n")
        [recipient] = dated_source(path, DateFormat.YMD_DASH).get_recipients()
        assert (recipient.send_date, recipient.skip_reason) == (date(2026, 11, 5), None)

    def test_excel_dates_are_read_directly(self, tmp_path):
        """A cell that is already an Excel date is read whatever the chosen format."""
        path = write_dated_xlsx(tmp_path / "f.xlsx", [datetime(2026, 11, 5), date(2026, 11, 6)])
        recipients = dated_source(path, DateFormat.YMD_DASH).get_recipients()
        assert [r.send_date for r in recipients] == [date(2026, 11, 5), date(2026, 11, 6)]

    def test_excel_dates_with_a_time_are_skipped(self, tmp_path):
        """An Excel date with a time other than 00:00 is skipped."""
        path = write_dated_xlsx(tmp_path / "f.xlsx", [datetime(2026, 11, 5, 9, 30)])
        assert dated_source(path).get_recipients()[0].skip_reason == "send_date_has_time"

    @pytest.mark.parametrize("value, reason", [
        ("", "no_send_date"),
        ("5-11-2026", "invalid_send_date"),
        ("5/11/2026 09:00", "send_date_has_time"),
    ])
    def test_unusable_text_dates_are_skipped(self, tmp_path, value, reason):
        """An empty, unreadable or timed text date skips the row with its reason."""
        path = write_csv(tmp_path / "f.csv", f"Correo;Adjunto;Fecha\na@x.com;a.pdf;{value}\n")
        assert dated_source(path).get_recipients()[0].skip_reason == reason

    def test_numbers_are_invalid_dates(self, tmp_path):
        """A number in the date column is not a date."""
        path = write_dated_xlsx(tmp_path / "f.xlsx", [12])
        assert dated_source(path).get_recipients()[0].skip_reason == "invalid_send_date"

    def test_same_row_on_another_date_is_not_a_duplicate(self, tmp_path):
        """The same address and attachment on two dates are two rows to send; on the same date, a duplicate."""
        path = write_csv(tmp_path / "f.csv", "Correo;Adjunto;Fecha\n"
                         "a@x.com;a.pdf;5/11/2026\na@x.com;a.pdf;6/11/2026\na@x.com;a.pdf;05/11/26\n")
        reasons = [r.skip_reason for r in dated_source(path).get_recipients()]
        assert reasons == [None, None, "duplicate_row"]

    def test_key_holds_the_date(self, tmp_path):
        """The key of a dated row holds its send day."""
        path = write_csv(tmp_path / "f.csv", "Correo;Adjunto;Fecha\na@x.com;a.pdf;5/11/2026\n")
        assert dated_source(path).get_recipients()[0].key == row_key("a@x.com", "a.pdf", "2026-11-05")

    def test_missing_date_column_is_reported(self, tmp_path):
        """A date column that is no longer in the file is reported with its name."""
        path = write_csv(tmp_path / "f.csv", "Correo;Adjunto\na@x.com;a.pdf\n")
        with pytest.raises(TableFileError) as info:
            dated_source(path).get_recipients()
        assert info.value.details == {"name": "Fecha"}

    def test_date_field_and_log(self, tmp_path):
        """The source names its date column, and the log shows it with its format."""
        source = dated_source(str(tmp_path / "f.csv"))
        assert source.date_field == "Fecha"
        assert source.log_fields["date_column"] == "Fecha"
        assert source.log_fields["date_format"] == "dd/mm/yyyy"


from src.domain.subject_fields import SubjectTemplate


def subject_source(path: str, subject: str, columns: list[str]) -> FileRecipientSource:
    """Build a source over the 'Correo' and 'Adjunto' columns whose subject is bound to *columns*."""
    return FileRecipientSource(path, None, "Correo", "Adjunto", subject=SubjectTemplate.bind(subject, columns))


class TestFileRecipientSourceSubject:
    """Covers the subject of each row built from its columns."""

    def test_builds_the_subject_of_each_row(self, tmp_path):
        """Fills the subject of each row with its own values, also for the same address."""
        path = write_csv(tmp_path / "f.csv", "Correo;Adjunto;Num factura\na@x.com;a.pdf;1\na@x.com;b.pdf;2\n")
        recipients = subject_source(path, "Factura #num_factura#", ["Correo", "Adjunto", "Num factura"]).get_recipients()
        assert [r.subject for r in recipients] == ["Factura 1", "Factura 2"]

    def test_an_empty_cell_skips_the_row(self, tmp_path):
        """Skips a row whose subject column is empty, naming the column."""
        path = write_csv(tmp_path / "f.csv", "Correo;Adjunto;Cliente\na@x.com;a.pdf;\n")
        [recipient] = subject_source(path, "#cliente#", ["Correo", "Adjunto", "Cliente"]).get_recipients()
        assert (recipient.skip_reason, recipient.skip_detail) == ("empty_subject_field", "Cliente")

    def test_the_subject_is_not_part_of_the_key(self, tmp_path):
        """Keys a row by its address and attachment only, so two subjects do not make two rows."""
        path = write_csv(tmp_path / "f.csv", "Correo;Adjunto;Cliente\na@x.com;a.pdf;X\na@x.com;a.pdf;Y\n")
        recipients = subject_source(path, "#cliente#", ["Correo", "Adjunto", "Cliente"]).get_recipients()
        assert recipients[0].key == row_key("a@x.com", "a.pdf")
        assert [r.skip_reason for r in recipients] == [None, "duplicate_row"]

    def test_excel_numbers_and_dates_read_as_shown(self, tmp_path):
        """Writes whole numbers without decimals and dates as dd/mm/yyyy."""
        workbook = openpyxl.Workbook()
        workbook.active.append(["Correo", "Adjunto", "Num", "Fecha"])
        workbook.active.append(["a@x.com", "a.pdf", 123.0, datetime(2026, 11, 5)])
        path = tmp_path / "f.xlsx"
        workbook.save(path)
        source = subject_source(str(path), "#num# del #fecha#", ["Correo", "Adjunto", "Num", "Fecha"])
        assert source.get_recipients()[0].subject == "123 del 05/11/2026"

    def test_line_breaks_in_a_cell_become_spaces(self, tmp_path):
        """Turns the line breaks of a cell into spaces."""
        workbook = openpyxl.Workbook()
        workbook.active.append(["Correo", "Adjunto", "Asunto"])
        workbook.active.append(["a@x.com", "a.pdf", "Primera línea\nsegunda línea"])
        path = tmp_path / "f.xlsx"
        workbook.save(path)
        source = subject_source(str(path), "#asunto#", ["Correo", "Adjunto", "Asunto"])
        assert source.get_recipients()[0].subject == "Primera línea segunda línea"

    @pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "cp1252"])
    def test_accents_survive_every_csv_encoding(self, tmp_path, encoding):
        """Keeps the accents of the subject values in a CSV saved as UTF-8 or as Windows Latin-1."""
        path = tmp_path / "f.csv"
        path.write_bytes("Correo;Adjunto;Cliente\na@x.com;a.pdf;Peñíscola Açaí\n".encode(encoding))
        source = subject_source(str(path), "#cliente#", ["Correo", "Adjunto", "Cliente"])
        assert source.get_recipients()[0].subject == "Peñíscola Açaí"

    def test_missing_subject_column_is_reported(self, tmp_path):
        """Reports a subject column that is no longer in the file, with its name."""
        path = write_csv(tmp_path / "f.csv", "Correo;Adjunto\na@x.com;a.pdf\n")
        source = subject_source(path, "#cliente#", ["Correo", "Adjunto", "Cliente"])
        with pytest.raises(TableFileError) as info:
            source.get_recipients()
        assert info.value.details == {"name": "Cliente"}
