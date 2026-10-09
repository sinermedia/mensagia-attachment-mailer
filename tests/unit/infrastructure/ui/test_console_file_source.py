from unittest.mock import patch

import openpyxl
import pytest

from src.domain.date_input import DateFormat
from src.domain.entities.extra_field import ExtraField
from src.infrastructure.ui.console import console_app
from src.infrastructure.ui.i18n import set_language


@pytest.fixture(autouse=True)
def _english_ui():
    """Pin the UI language so assertions on printed text are deterministic."""
    set_language("en")


def write_csv(path, text: str) -> str:
    """Write a UTF-8 .csv file and return its path as text."""
    path.write_bytes(text.encode("utf-8"))
    return str(path)


def write_xlsx(path, sheets: dict) -> str:
    """Write an .xlsx file with one sheet per entry of *sheets* (name -> list of rows)."""
    workbook = openpyxl.Workbook()
    workbook.remove(workbook.active)
    for name, rows in sheets.items():
        sheet = workbook.create_sheet(name)
        for row in rows:
            sheet.append(row)
    workbook.save(path)
    return str(path)


def _select(*answers):
    """Run the console file selection, answering its prompts in order.

    Args:
        answers: Text typed at each prompt.

    Returns:
        The FileRecipientSource it returns.
    """
    with patch("builtins.input", side_effect=list(answers)):
        return console_app._select_file()


class TestConsoleSourceChoice:
    """Covers the console question about where the recipients come from."""

    def test_agenda_is_option_one(self):
        """Option 1 picks an agenda group."""
        with patch("builtins.input", return_value="1"):
            assert console_app._choose_source() == "agenda"

    def test_file_is_option_two(self):
        """Option 2 picks a file."""
        with patch("builtins.input", return_value="2"):
            assert console_app._choose_source() == "file"


class TestConsoleFileSelection:
    """Covers choosing the file, its sheet and its columns in the console."""

    def test_reads_a_csv_and_its_columns(self, tmp_path):
        """A CSV path, then the email and attachment columns, give the source."""
        path = write_csv(tmp_path / "f.csv", "Nombre;Correo;Adjunto\nAna;a@x.com;a.pdf\n")
        source = _select(path, "2", "2")
        assert (source.path, source.sheet) == (path, None)
        assert (source.email_column, source.attachment_column) == ("Correo", "Adjunto")

    def test_attachment_list_leaves_out_the_email_column(self, tmp_path, capsys):
        """The column chosen for the email is not offered again for the attachment."""
        path = write_csv(tmp_path / "f.csv", "Correo;Adjunto\na@x.com;a.pdf\n")
        source = _select(path, "1", "1")
        assert source.attachment_column == "Adjunto"

    def test_strips_the_quotes_of_a_pasted_path(self, tmp_path):
        """A path pasted with the quotes of "Copy as path" is accepted."""
        path = write_csv(tmp_path / "f.csv", "Correo;Adjunto\na@x.com;a.pdf\n")
        assert _select(f'"{path}"', "1", "1").path == path

    def test_asks_for_the_sheet_when_there_are_several(self, tmp_path):
        """A workbook with several sheets asks which one to use."""
        path = write_xlsx(tmp_path / "f.xlsx", {
            "Octubre": [["Correo", "Adjunto"], ["a@x.com", "a.pdf"]],
            "Noviembre": [["Correo", "Adjunto"], ["b@x.com", "b.pdf"]],
        })
        assert _select(path, "2", "1", "1").sheet == "Noviembre"

    def test_does_not_ask_for_the_only_sheet(self, tmp_path):
        """A workbook with a single sheet uses it without asking."""
        path = write_xlsx(tmp_path / "f.xlsx", {"Hoja1": [["Correo", "Adjunto"], ["a@x.com", "a.pdf"]]})
        assert _select(path, "1", "1").sheet == "Hoja1"

    def test_explains_a_file_error_and_asks_again(self, tmp_path, capsys):
        """An unusable file is explained and a new path is asked for."""
        bad = write_csv(tmp_path / "bad.csv", "a@x.com;a.pdf\n")
        good = write_csv(tmp_path / "good.csv", "Correo;Adjunto\na@x.com;a.pdf\n")
        assert _select(bad, good, "1", "1").path == good
        assert "The file seems to have no header." in capsys.readouterr().out

    def test_asks_again_for_an_empty_path(self, tmp_path):
        """An empty answer is not taken as a path."""
        path = write_csv(tmp_path / "f.csv", "Correo;Adjunto\na@x.com;a.pdf\n")
        assert _select("", path, "1", "1").path == path


class TestConsoleSendDateChoice:
    """Covers choosing where each contact's send day is and its format."""

    def test_file_date_column_and_format(self, tmp_path):
        """With dates, the date column is picked among the columns left, then the format."""
        path = write_csv(tmp_path / "f.csv", "Correo;Adjunto;Fecha\na@x.com;a.pdf;5/11/2026\n")
        with patch("builtins.input", side_effect=[path, "1", "1", "1", "4"]):
            source = console_app._select_file(with_date=True)
        assert (source.date_column, source.date_format) == ("Fecha", DateFormat.YMD_DASH)

    def test_file_without_a_column_for_the_date_is_refused(self, tmp_path, capsys):
        """A file with no column left for the date is explained and another path is asked for."""
        short = write_csv(tmp_path / "short.csv", "Correo;Adjunto\na@x.com;a.pdf\n")
        full = write_csv(tmp_path / "full.csv", "Correo;Adjunto;Fecha\na@x.com;a.pdf;5/11/2026\n")
        with patch("builtins.input", side_effect=[short, full, "1", "1", "1", "1"]):
            source = console_app._select_file(with_date=True)
        assert source.path == full
        assert "no other column for the send date" in capsys.readouterr().out

    def test_agenda_date_field_leaves_out_the_attachment_field(self, capsys):
        """The date field list leaves out the attachment field, then the format is asked."""
        fields = [ExtraField(1, "Adjunto"), ExtraField(2, "Fecha"), ExtraField(3, "Otra")]
        with patch("builtins.input", side_effect=["1", "2"]):
            field, fmt = console_app._select_date_field(fields, fields[0], show_ids=False)
        assert (field.name, fmt) == ("Fecha", DateFormat.DMY_DASH)
        assert "Adjunto" not in capsys.readouterr().out

    def test_formats_are_shown_with_the_letters_of_the_language(self, capsys):
        """The format list shows each format as the user reads it."""
        with patch("builtins.input", side_effect=["1"]):
            console_app._select_date_format()
        assert "1. dd/mm/yyyy" in capsys.readouterr().out
