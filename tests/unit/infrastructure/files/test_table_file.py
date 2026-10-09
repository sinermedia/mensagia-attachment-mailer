from datetime import datetime

import openpyxl
import pytest

from src.infrastructure.files.table_file import TableFileError, cell_text, list_sheets, read_table


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


def write_csv(path, text: str, encoding: str = "utf-8") -> str:
    """Write *text* to a .csv file with the given encoding."""
    path.write_bytes(text.encode(encoding))
    return str(path)


class TestReadCsv:
    """Covers reading a CSV file into a table, whatever its separator and encoding."""

    def test_reads_header_and_rows(self, tmp_path):
        """The first row gives the column names and every other row is keyed by them."""
        table = read_table(write_csv(tmp_path / "f.csv", "Correo,Adjunto\na@x.com,a.pdf\n"))
        assert table.columns == ["Correo", "Adjunto"]
        assert table.rows[0].values == {"Correo": "a@x.com", "Adjunto": "a.pdf"}

    def test_detects_the_semicolon_separator(self, tmp_path):
        """A file separated by semicolons, as Excel saves it in Spanish, is read correctly."""
        table = read_table(write_csv(tmp_path / "f.csv", "Correo;Adjunto\na@x.com;a,b.pdf\n"))
        assert table.rows[0].values == {"Correo": "a@x.com", "Adjunto": "a,b.pdf"}

    def test_reads_utf8_with_bom(self, tmp_path):
        """A UTF-8 file with a byte order mark does not get the mark in its first column name."""
        table = read_table(write_csv(tmp_path / "f.csv", "Correo;Población\na@x.com;Logroño\n", "utf-8-sig"))
        assert table.columns == ["Correo", "Población"]
        assert table.rows[0].values["Población"] == "Logroño"

    def test_reads_windows_ansi(self, tmp_path):
        """A file saved in the Windows ANSI encoding keeps its accented letters."""
        table = read_table(write_csv(tmp_path / "f.csv", "Correo;Población\na@x.com;Logroño\n", "cp1252"))
        assert table.rows[0].values["Población"] == "Logroño"

    def test_row_numbers_match_the_spreadsheet(self, tmp_path):
        """Rows are numbered as a spreadsheet shows them: header 1, and empty rows still count."""
        table = read_table(write_csv(tmp_path / "f.csv", "Correo\na@x.com\n\nb@x.com\n"))
        assert [r.number for r in table.rows] == [2, 4]

    def test_quoted_cell_with_a_line_break_is_one_row(self, tmp_path):
        """A quoted cell spanning two lines stays in a single row."""
        table = read_table(write_csv(tmp_path / "f.csv", 'Correo;Nota\na@x.com;"uno\ndos"\nb@x.com;x\n'))
        assert [r.number for r in table.rows] == [2, 3]

    def test_short_rows_are_padded(self, tmp_path):
        """A row with fewer cells than the header gets empty values for the missing ones."""
        table = read_table(write_csv(tmp_path / "f.csv", "Correo;Adjunto\na@x.com\n"))
        assert table.rows[0].values == {"Correo": "a@x.com", "Adjunto": ""}

    def test_csv_has_no_sheets(self, tmp_path):
        """A CSV file has no sheets to choose from."""
        assert list_sheets(write_csv(tmp_path / "f.csv", "Correo\na@x.com\n")) == []


class TestReadXlsx:
    """Covers reading an Excel workbook into a table."""

    def test_reads_the_only_sheet(self, tmp_path):
        """With no sheet named, the first sheet is read."""
        path = write_xlsx(tmp_path / "f.xlsx", {"Hoja1": [["Correo", "Adjunto"], ["a@x.com", "a.pdf"]]})
        table = read_table(path)
        assert table.columns == ["Correo", "Adjunto"]
        assert table.rows[0].values == {"Correo": "a@x.com", "Adjunto": "a.pdf"}
        assert table.rows[0].number == 2

    def test_lists_and_reads_a_chosen_sheet(self, tmp_path):
        """Every sheet is listed in order, and the chosen one is read."""
        path = write_xlsx(tmp_path / "f.xlsx", {
            "Octubre": [["Correo"], ["a@x.com"]],
            "Noviembre": [["Correo"], ["b@x.com"]],
        })
        assert list_sheets(path) == ["Octubre", "Noviembre"]
        assert read_table(path, "Noviembre").rows[0].values == {"Correo": "b@x.com"}

    def test_keeps_the_cell_types(self, tmp_path):
        """Numbers and dates are returned as such, for the caller to format."""
        path = write_xlsx(tmp_path / "f.xlsx", {"H": [["Num", "Fecha"], [123, datetime(2026, 10, 9)]]})
        assert read_table(path).rows[0].values == {"Num": 123, "Fecha": datetime(2026, 10, 9)}

    def test_empty_rows_count_in_the_numbering(self, tmp_path):
        """Empty rows are left out but still count, so numbers match what Excel shows."""
        path = write_xlsx(tmp_path / "f.xlsx", {"H": [["Correo"], ["a@x.com"], [None], ["b@x.com"]]})
        assert [r.number for r in read_table(path).rows] == [2, 4]

    def test_leading_empty_rows_are_skipped_before_the_header(self, tmp_path):
        """When the sheet starts with empty rows, the first non-empty one is the header."""
        path = write_xlsx(tmp_path / "f.xlsx", {"H": [[None], ["Correo"], ["a@x.com"]]})
        table = read_table(path)
        assert table.columns == ["Correo"]
        assert table.rows[0].number == 3


class TestTableShape:
    """Covers the columns and rows that are ignored or rejected."""

    def test_empty_columns_are_ignored(self, tmp_path):
        """A column with neither a name nor data is left out."""
        table = read_table(write_csv(tmp_path / "f.csv", "Correo;;Adjunto\na@x.com;;a.pdf\n"))
        assert table.columns == ["Correo", "Adjunto"]

    def test_named_column_without_data_is_kept(self, tmp_path):
        """A column with a name but no data is still offered."""
        table = read_table(write_csv(tmp_path / "f.csv", "Correo;Notas\na@x.com;\n"))
        assert table.columns == ["Correo", "Notas"]

    def test_column_names_are_stripped(self, tmp_path):
        """Spaces around a column name are removed."""
        assert read_table(write_csv(tmp_path / "f.csv", " Correo ;Adjunto\na@x.com;a\n")).columns == ["Correo", "Adjunto"]

    def test_rows_with_only_blank_cells_are_ignored(self, tmp_path):
        """A row whose cells are all empty or blank is left out."""
        table = read_table(write_csv(tmp_path / "f.csv", "Correo;Adjunto\n ; \na@x.com;a\n"))
        assert [r.number for r in table.rows] == [3]


class TestTableErrors:
    """Covers the file problems that prevent continuing."""

    def error_of(self, path, sheet=None) -> TableFileError:
        """Return the TableFileError raised when reading *path*."""
        with pytest.raises(TableFileError) as info:
            read_table(path, sheet)
        return info.value

    def test_empty_file(self, tmp_path):
        """A file without any row is reported as empty."""
        assert self.error_of(write_csv(tmp_path / "f.csv", "")).code == "empty"

    def test_header_only(self, tmp_path):
        """A file with the header and no data row is reported as empty."""
        assert self.error_of(write_csv(tmp_path / "f.csv", "Correo;Adjunto\n;\n")).code == "empty"

    def test_header_with_an_address_means_no_header(self, tmp_path):
        """A first row holding an @ is reported as a missing header."""
        error = self.error_of(write_csv(tmp_path / "f.csv", "a@x.com;a.pdf\nb@x.com;b.pdf\n"))
        assert error.code == "no_header"

    def test_column_with_data_but_no_name(self, tmp_path):
        """A column with data and an empty header cell is reported with its letter, as Excel shows it."""
        error = self.error_of(write_csv(tmp_path / "f.csv", "Correo;;Adjunto\na@x.com;x;a.pdf\n"))
        assert (error.code, error.details) == ("unnamed_column", {"column": "B"})

    def test_cells_beyond_the_header_are_an_unnamed_column(self, tmp_path):
        """Data past the last named column is reported as a column without a name."""
        error = self.error_of(write_csv(tmp_path / "f.csv", "Correo\na@x.com;a.pdf\n"))
        assert (error.code, error.details) == ("unnamed_column", {"column": "B"})

    def test_repeated_column_names(self, tmp_path):
        """Two columns with the same name, ignoring case and spaces around it, are reported."""
        error = self.error_of(write_csv(tmp_path / "f.csv", "Correo;Adjunto;correo \na;b;c\n"))
        assert (error.code, error.details) == ("duplicate_column", {"name": "correo"})

    def test_unsupported_extension(self, tmp_path):
        """A file that is neither .xlsx nor .csv is rejected."""
        path = tmp_path / "f.xls"
        path.write_bytes(b"whatever")
        assert self.error_of(str(path)).code == "unsupported_format"

    def test_corrupt_workbook(self, tmp_path):
        """An .xlsx file that cannot be opened is reported as unreadable."""
        path = tmp_path / "f.xlsx"
        path.write_bytes(b"not a zip")
        assert self.error_of(str(path)).code == "unreadable"

    def test_missing_file(self, tmp_path):
        """A file that no longer exists is reported as unreadable."""
        assert self.error_of(str(tmp_path / "gone.csv")).code == "unreadable"

    def test_unknown_sheet(self, tmp_path):
        """A sheet that is no longer in the workbook is reported with its name."""
        path = write_xlsx(tmp_path / "f.xlsx", {"Hoja1": [["Correo"], ["a@x.com"]]})
        error = self.error_of(path, "Hoja2")
        assert (error.code, error.details) == ("missing_sheet", {"sheet": "Hoja2"})


class TestCellText:
    """Covers turning a cell value into the text used for emails and attachments."""

    @pytest.mark.parametrize("value, text", [
        (None, ""),
        ("  a@x.com ", "a@x.com"),
        (123, "123"),
        (123.0, "123"),
        (12.5, "12.5"),
        (datetime(2026, 10, 9), "09/10/2026"),
        (datetime(2026, 10, 9, 8, 30), "09/10/2026 08:30"),
        (True, "TRUE"),
    ])
    def test_values(self, value, text):
        """Each kind of value is written the way a spreadsheet user expects to read it."""
        assert cell_text(value) == text
