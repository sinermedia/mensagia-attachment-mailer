import csv
import io
import warnings
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import openpyxl
from openpyxl.utils import get_column_letter


# Encodings tried in order for a CSV file: UTF-8 (with or without the byte
# order mark Excel adds), then the Windows ANSI code page Excel uses when
# saving "CSV (delimited by commas)" on a Spanish system
_CSV_ENCODINGS = ("utf-8-sig", "cp1252")


class TableFileError(Exception):
    """Raised when a file cannot be used as a table of recipients.

    The interfaces translate the code into a message for the user, so it
    carries no text of its own beyond the code.

    Attributes:
        code: Machine-readable problem: 'unsupported_format', 'unreadable',
            'missing_sheet', 'empty', 'no_header', 'unnamed_column',
            'duplicate_column' or, once the columns are chosen,
            'missing_column'.
        details: Values to show in the message, such as the column
            letter as a spreadsheet shows it ('column'), the repeated or missing name
            ('name') or the missing sheet ('sheet').
    """

    def __init__(self, code: str, **details):
        """Create the error.

        Args:
            code: Machine-readable problem (see the class attributes).
            **details: Values to show in the message.
        """
        super().__init__(code)
        self.code = code
        self.details = details


@dataclass(frozen=True)
class TableRow:
    """One data row of a table.

    Attributes:
        number: Row number as a spreadsheet shows it (the header is row 1
            when the file starts with it).
        values: Cell values keyed by column name. CSV cells are text;
            workbook cells keep their type (text, number, date...) and an
            empty cell is None.
    """

    number: int
    values: dict


@dataclass(frozen=True)
class Table:
    """The header and data rows of a file.

    Attributes:
        columns: Column names, stripped, in file order. Columns with
            neither a name nor data are left out.
        rows: Data rows in file order, without the rows that are empty.
    """

    columns: list[str]
    rows: list[TableRow] = field(default_factory=list)


def _is_blank(value) -> bool:
    """Tell whether a cell holds nothing, or only spaces.

    Args:
        value: Raw cell value.

    Returns:
        True for None and for text that is empty once stripped.
    """
    return value is None or (isinstance(value, str) and not value.strip())


def cell_text(value) -> str:
    """Write a cell value as the text a spreadsheet user expects to read.

    Whole numbers lose the decimals a workbook stores them with, and dates
    use the day-first format; text is stripped.

    Args:
        value: Raw cell value.

    Returns:
        The value as text; empty for an empty cell.
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, datetime):
        if (value.hour, value.minute, value.second) == (0, 0, 0):
            return value.strftime("%d/%m/%Y")
        return value.strftime("%d/%m/%Y %H:%M")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    return str(value).strip()


def _decode(data: bytes) -> str:
    """Decode the bytes of a CSV file, trying the usual encodings in turn.

    Args:
        data: Raw file content.

    Returns:
        The decoded text. The last encoding accepts any byte, so decoding
        never fails.
    """
    for encoding in _CSV_ENCODINGS[:-1]:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            pass
    return data.decode(_CSV_ENCODINGS[-1], errors="replace")


def _delimiter(text: str) -> str:
    """Guess the separator of a CSV file from its first non-empty lines.

    The first line decides whenever it holds a separator: it is the header,
    whose names rarely contain separators, whereas data cells (attachment
    URLs, notes) often hold commas. A header with a single column has none,
    so the next lines are looked at instead.

    Args:
        text: Decoded file content.

    Returns:
        ';' when semicolons outnumber commas, ',' otherwise.
    """
    lines = [line for line in text.splitlines() if line.strip()][:20]
    header = lines[0] if lines else ""
    sample = header if (";" in header or "," in header) else "\n".join(lines)
    return ";" if sample.count(";") > sample.count(",") else ","


def _csv_rows(path: Path) -> list[tuple[int, list]]:
    """Read the rows of a CSV file with their row numbers.

    Args:
        path: CSV file to read.

    Returns:
        (row number, cell values) pairs, numbered by record so a quoted
        cell spanning several lines does not shift the numbers.

    Raises:
        OSError: If the file cannot be read.
    """
    text = _decode(path.read_bytes())
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=_delimiter(text))
    return [(number, row) for number, row in enumerate(reader, 1)]


def _open_workbook(path: Path):
    """Open a workbook for reading cached cell values.

    Args:
        path: .xlsx file to open.

    Returns:
        The openpyxl workbook, with formula results instead of formulas.

    Raises:
        TableFileError: 'unreadable' when the file is missing or is not a
            valid workbook.
    """
    # openpyxl warns about features it does not keep (data validation,
    # conditional formatting...), which do not matter for reading values
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return openpyxl.load_workbook(path, data_only=True)
    except Exception as exc:
        raise TableFileError("unreadable") from exc


def _xlsx_rows(path: Path, sheet: str | None) -> list[tuple[int, list]]:
    """Read the rows of a workbook sheet with their row numbers.

    Args:
        path: .xlsx file to read.
        sheet: Name of the sheet, or None for the first one.

    Returns:
        (row number, cell values) pairs, numbered as Excel shows them.

    Raises:
        TableFileError: 'unreadable' or 'missing_sheet'.
    """
    workbook = _open_workbook(path)
    names = [ws.title for ws in workbook.worksheets]
    if sheet is not None and sheet not in names:
        raise TableFileError("missing_sheet", sheet=sheet)
    worksheet = workbook[sheet] if sheet is not None else workbook.worksheets[0]
    rows = worksheet.iter_rows(min_row=1, max_row=worksheet.max_row, values_only=True)
    return [(number, list(row)) for number, row in enumerate(rows, 1)]


def list_sheets(path: str) -> list[str]:
    """List the sheets of a workbook, to let the user choose one.

    Args:
        path: File to inspect.

    Returns:
        The names of the worksheets in workbook order; empty for a CSV file,
        which has no sheets.

    Raises:
        TableFileError: 'unsupported_format' or 'unreadable'.
    """
    file = Path(path)
    suffix = file.suffix.lower()
    if suffix == ".csv":
        return []
    if suffix != ".xlsx":
        raise TableFileError("unsupported_format")
    return [ws.title for ws in _open_workbook(file).worksheets]


def read_table(path: str, sheet: str | None = None) -> Table:
    """Read a CSV or Excel file as a table whose first row is the header.

    Rows and columns that are completely empty are ignored, including the
    rows before the header. The problems that make the file unusable raise
    an error, checked in an order that gives the most helpful message: a
    missing header (a first row holding an address), then an empty file
    (or one with only the header), then a column with data but no name,
    then repeated names.

    Args:
        path: .xlsx or .csv file to read.
        sheet: Workbook sheet to read; None for the first one. Ignored for
            a CSV file.

    Returns:
        The table of the file.

    Raises:
        TableFileError: When the file cannot be read or used (see its
            codes).
    """
    # Read the raw rows with the reader of the file's format
    file = Path(path)
    suffix = file.suffix.lower()
    if suffix == ".csv":
        try:
            raw = _csv_rows(file)
        except OSError as exc:
            raise TableFileError("unreadable") from exc
    elif suffix == ".xlsx":
        raw = _xlsx_rows(file, sheet)
    else:
        raise TableFileError("unsupported_format")

    # Drop empty rows; the first remaining one is the header
    raw = [(number, cells) for number, cells in raw if not all(_is_blank(c) for c in cells)]
    if not raw:
        raise TableFileError("empty")
    (_, header), data = raw[0], raw[1:]

    # A header holding an address means the file starts with data: say so
    # before the other checks, which would otherwise report confusing errors
    # (a single row of data would look like a header without data)
    if any("@" in cell_text(cell) for cell in header):
        raise TableFileError("no_header")
    if not data:
        raise TableFileError("empty")

    # Keep the columns that have a name or data, refusing data without a
    # name since there would be no way to choose that column
    width = max(len(cells) for _, cells in raw)
    names = [cell_text(header[i]) if i < len(header) else "" for i in range(width)]
    kept = []
    for i, name in enumerate(names):
        has_data = any(i < len(cells) and not _is_blank(cells[i]) for _, cells in data)
        if not name and has_data:
            raise TableFileError("unnamed_column", column=get_column_letter(i + 1))
        if name:
            kept.append(i)

    # Column names are compared like a person would read them
    seen = set()
    for i in kept:
        folded = names[i].casefold()
        if folded in seen:
            raise TableFileError("duplicate_column", name=names[i])
        seen.add(folded)

    # CSV rows can be shorter than the header: the missing cells are empty
    empty = "" if suffix == ".csv" else None
    rows = [
        TableRow(number, {names[i]: cells[i] if i < len(cells) else empty for i in kept})
        for number, cells in data
    ]
    return Table([names[i] for i in kept], rows)
