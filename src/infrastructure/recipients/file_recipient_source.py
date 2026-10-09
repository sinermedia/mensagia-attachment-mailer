import json
from pathlib import Path

from src.domain.entities.recipient import Recipient
from src.domain.file_rows import email_skip_reason, row_key, skip_duplicate_rows
from src.domain.ports.recipient_source import RecipientSource
from src.infrastructure.files.table_file import TableFileError, cell_text, read_table


class FileRecipientSource(RecipientSource):
    """Reads the rows of an Excel or CSV file as recipients.

    Each row gives one email: the address and the attachment come from the
    columns the user chose. The same address may appear in several rows,
    each with its own attachment. The file is read again on every call, so
    changes saved between the summary and the send are taken into account.

    Attributes:
        path: Path of the file.
        sheet: Workbook sheet to read, or None for a CSV file (or the first
            sheet).
        email_column: Name of the column holding the address.
        attachment_column: Name of the column holding the attachment value.
    """

    def __init__(self, path: str, sheet: str | None, email_column: str, attachment_column: str):
        """Initialise the source for one file, sheet and pair of columns.

        Args:
            path: Path of the file.
            sheet: Workbook sheet to read, or None.
            email_column: Name of the column holding the address.
            attachment_column: Name of the column holding the attachment.
        """
        self.path = path
        self.sheet = sheet
        self.email_column = email_column
        self.attachment_column = attachment_column

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
    def log_fields(self) -> dict[str, str]:
        """Describe the file in the opening line of the log.

        Returns:
            The file name, the sheet (when there is one) and the email column.
        """
        fields = {"file": Path(self.path).name}
        if self.sheet:
            fields["sheet"] = self.sheet
        fields["email_column"] = self.email_column
        return fields

    def get_recipients(self) -> list[Recipient]:
        """Read the file and turn each data row into a recipient.

        Returns:
            One recipient per non-empty row, in file order. Rows with an
            empty or invalid address, without an attachment, or repeating
            an earlier row carry the reason.

        Raises:
            TableFileError: When the file cannot be read or used, or when a
                chosen column is no longer in it ('missing_column').
        """
        # The file may have changed since the columns were chosen
        table = read_table(self.path, self.sheet)
        for column in (self.email_column, self.attachment_column):
            if column not in table.columns:
                raise TableFileError("missing_column", name=column)

        # Check every row on its own, then the rows against each other
        recipients = []
        for row in table.rows:
            email = cell_text(row.values[self.email_column])
            attachment = cell_text(row.values[self.attachment_column])
            reason = email_skip_reason(email)
            if reason is None and not attachment:
                reason = "no_attachment"
            recipients.append(Recipient(
                key=row_key(email, attachment), email=email, attachment=attachment,
                row=row.number, skip_reason=reason,
            ))
        return skip_duplicate_rows(recipients)
