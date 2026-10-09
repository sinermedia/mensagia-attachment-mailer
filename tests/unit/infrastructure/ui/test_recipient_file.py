import pytest

from src.infrastructure.files.table_file import TableFileError
from src.infrastructure.ui.i18n import set_language
from src.infrastructure.ui.recipient_file import clean_path, file_error_message, file_summary_lines


@pytest.fixture(autouse=True)
def english():
    """Run every test with the English texts."""
    set_language("en")


class TestFileErrorMessage:
    """Covers turning a file error into the message shown to the user."""

    def test_message_without_details(self):
        """A code without details gives its translated message."""
        assert file_error_message(TableFileError("empty")) == "The file is empty or only has the header."

    def test_message_with_details(self):
        """The details of the error are filled into the message."""
        message = file_error_message(TableFileError("unnamed_column", column="B"))
        assert message == "Column B has data but no name in the first row."


class TestCleanPath:
    """Covers reading a file path typed or pasted in the console."""

    @pytest.mark.parametrize("typed, path", [
        ('"C:\\Users\\Ana\\envíos.xlsx"', "C:\\Users\\Ana\\envíos.xlsx"),
        ("'/home/ana/envios.csv'", "/home/ana/envios.csv"),
        ("  C:\\datos\\f.csv  ", "C:\\datos\\f.csv"),
        (' "C:\\a b\\f.csv" ', "C:\\a b\\f.csv"),
    ])
    def test_strips_spaces_and_quotes(self, typed, path):
        """Spaces and the quotes added by "Copy as path" are removed from the ends."""
        assert clean_path(typed) == path

    def test_keeps_quotes_inside_the_path(self):
        """Only quotes at both ends are removed."""
        assert clean_path("C:\\it's\\f.csv") == "C:\\it's\\f.csv"


class TestFileSummaryLines:
    """Covers the summary lines describing the chosen file."""

    def test_lines_for_a_workbook(self):
        """A workbook shows its file name, sheet and both columns."""
        lines = file_summary_lines("C:\\datos\\envios.xlsx", "Octubre", "Correo", "Adjunto")
        assert lines == [
            "File: envios.xlsx", "Sheet: Octubre", "Email column: Correo", "Attachment column: Adjunto",
        ]

    def test_lines_for_a_csv(self):
        """A CSV file has no sheet line."""
        lines = file_summary_lines("envios.csv", None, "Correo", "Adjunto")
        assert lines == ["File: envios.csv", "Email column: Correo", "Attachment column: Adjunto"]
