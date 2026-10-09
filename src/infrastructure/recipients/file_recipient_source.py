import json
from datetime import date, datetime
from pathlib import Path

from src.domain.attachment_url import resolve_attachment_url
from src.domain.date_input import DateFormat, read_send_date
from src.domain.entities.recipient import Recipient
from src.domain.file_rows import email_skip_reason, row_key, skip_duplicate_rows
from src.domain.ports.recipient_source import RecipientSource
from src.infrastructure.files.table_file import TableFileError, cell_text, read_table


class FileRecipientSource(RecipientSource):
    """Reads the rows of an Excel or CSV file as recipients.

    Each row gives one email: the address and the attachment (and, in the
    contact date start mode, the send day) come from the columns the user
    chose. The same address may appear in several rows,
    each with its own attachment. The file is read again on every call, so
    changes saved between the summary and the send are taken into account.

    Attributes:
        path: Path of the file.
        sheet: Workbook sheet to read, or None for a CSV file (or the first
            sheet).
        email_column: Name of the column holding the address.
        attachment_column: Name of the column holding the attachment value.
        attachment_base_url: Base URL that relative attachment values are
            resolved against, or None when there is none.
        date_column: Name of the column holding the send day, or None
            outside the contact date start mode.
        date_format: Format of the send days written as text, or None.
    """

    def __init__(self, path: str, sheet: str | None, email_column: str, attachment_column: str,
                 attachment_base_url: str | None = None, date_column: str | None = None,
                 date_format: DateFormat | None = None):
        """Initialise the source for one file, sheet and pair of columns.

        Args:
            path: Path of the file.
            sheet: Workbook sheet to read, or None.
            email_column: Name of the column holding the address.
            attachment_column: Name of the column holding the attachment.
            attachment_base_url: Base URL for relative attachment values,
                used to tell which rows point to the same file.
            date_column: Name of the column holding the send day, in the
                contact date start mode.
            date_format: Format of the send days written as text, required
                with a date column.
        """
        self.path = path
        self.sheet = sheet
        self.email_column = email_column
        self.attachment_column = attachment_column
        self.attachment_base_url = attachment_base_url
        self.date_column = date_column
        self.date_format = date_format

    def _send_date(self, value) -> tuple[date | None, str | None]:
        """Read the send day of a row from its date cell.

        A cell that is already a date in the workbook is read directly; the
        chosen format only applies to dates written as text. A workbook
        date with a time other than 00:00 is rejected, like a text date
        with a time.

        Args:
            value: Raw value of the date cell.

        Returns:
            The date and None when it can be used; otherwise None and the
            skip reason.
        """
        if isinstance(value, datetime):
            if value.time() != datetime.min.time():
                return None, "send_date_has_time"
            return value.date(), None
        if isinstance(value, date):
            return value, None
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return None, "invalid_send_date"
        return read_send_date(cell_text(value), self.date_format)

    def _attachment_identity(self, attachment: str) -> str:
        """Return the value that tells whether two rows attach the same file.

        A relative path and the full URL it resolves to are the same file,
        so the resolved URL is compared. Without a base URL a relative path
        cannot be resolved (the send will report it) and is compared as
        written.

        Args:
            attachment: Attachment value as written in the cell.

        Returns:
            The resolved URL, or the value itself when it cannot be resolved.
        """
        try:
            return resolve_attachment_url(attachment, self.attachment_base_url)
        except ValueError:
            return attachment

    @property
    def identity(self) -> str:
        """Identify the file within a campaign.

        Only the file name is used, not its folder nor its content: moving
        the file or fixing one of its rows must not stop an interrupted send
        from being resumed. The sheet and the email column make a different
        campaign, since they select other recipients.

        Returns:
            A JSON array starting with 'file', so it can never equal the
            identity of an agenda group.
        """
        return json.dumps(["file", Path(self.path).name, self.sheet or "", self.email_column], ensure_ascii=False)

    @property
    def attachment_field(self) -> str:
        """Name the column that holds each row's attachment.

        Returns:
            The name of the chosen attachment column.
        """
        return self.attachment_column

    @property
    def date_field(self) -> str | None:
        """Name the column that holds each row's send day.

        Returns:
            The name of the chosen date column, or None.
        """
        return self.date_column

    @property
    def log_fields(self) -> dict[str, str]:
        """Describe the file in the opening line of the log.

        Returns:
            The file name, the sheet (when there is one), the email column
            and, in the contact date mode, the date column and its format.
        """
        fields = {"file": Path(self.path).name}
        if self.sheet:
            fields["sheet"] = self.sheet
        fields["email_column"] = self.email_column
        if self.date_column is not None:
            fields["date_column"] = self.date_column
            fields["date_format"] = self.date_format.value
        return fields

    def get_recipients(self) -> list[Recipient]:
        """Read the file and turn each data row into a recipient.

        Returns:
            One recipient per non-empty row, in file order. Rows with an
            empty or invalid address, without an attachment, without a
            usable send day (contact date mode), or repeating the date,
            address and attachment file of an earlier row carry the reason.

        Raises:
            TableFileError: When the file cannot be read or used, or when a
                chosen column is no longer in it ('missing_column').
        """
        # The file may have changed since the columns were chosen
        table = read_table(self.path, self.sheet)
        for column in (self.email_column, self.attachment_column, self.date_column):
            if column is not None and column not in table.columns:
                raise TableFileError("missing_column", name=column)

        # Check every row on its own, then the rows against each other
        recipients = []
        for row in table.rows:
            email = cell_text(row.values[self.email_column])
            attachment = cell_text(row.values[self.attachment_column])
            reason = email_skip_reason(email)
            if reason is None and not attachment:
                reason = "no_attachment"

            # The send day joins the key: the same address and attachment on
            # two days are two emails to send, not a duplicate
            send_date = None
            if self.date_column is not None:
                send_date, date_reason = self._send_date(row.values[self.date_column])
                reason = reason or date_reason
            day = send_date.isoformat() if send_date else ""
            recipients.append(Recipient(
                key=row_key(email, self._attachment_identity(attachment), day), email=email,
                attachment=attachment, row=row.number, skip_reason=reason, send_date=send_date,
            ))
        return skip_duplicate_rows(recipients)
