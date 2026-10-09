from pathlib import Path

from src.infrastructure.files.table_file import TableFileError
from src.infrastructure.ui.i18n import t


# Quotes that may wrap a pasted path: Windows' "Copy as path" adds double
# quotes, and some terminals add single ones when a file is dropped
_QUOTES = ('"', "'")


def file_error_message(error: TableFileError) -> str:
    """Translate a file error into the message shown to the user.

    Args:
        error: Error raised while reading the file.

    Returns:
        The translated message, with the error details filled in.
    """
    return t(f"file_error_{error.code}", **error.details)


def clean_path(text: str) -> str:
    """Read a file path typed or pasted by the user.

    Args:
        text: What the user entered.

    Returns:
        The path without surrounding spaces nor a pair of quotes at both
        ends; quotes inside the path are kept.
    """
    path = text.strip()
    if len(path) >= 2 and path[0] == path[-1] and path[0] in _QUOTES:
        path = path[1:-1].strip()
    return path


def file_summary_lines(path: str, sheet: str | None, email_column: str, attachment_column: str) -> list[str]:
    """Build the summary lines that describe a file chosen as recipient source.

    Only the file name is shown: the folder makes the line long and is not
    what the user checks.

    Args:
        path: Path of the chosen file.
        sheet: Chosen sheet, or None for a CSV file.
        email_column: Column holding the address.
        attachment_column: Column holding the attachment.

    Returns:
        The translated lines, in display order.
    """
    lines = [t("summary_file", value=Path(path).name)]
    if sheet:
        lines.append(t("summary_sheet", value=sheet))
    lines.append(t("summary_email_column", value=email_column))
    lines.append(t("summary_attachment_column", value=attachment_column))
    return lines
