from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Recipient:
    """One email to send, whatever the source it was read from.

    A recipient source (an agenda group, a file...) turns its data into
    recipients, so the bulk send never depends on where they came from.
    A recipient that cannot be sent is still returned, with the reason in
    skip_reason, so it can be reported and logged.

    Attributes:
        key: Identity of the recipient in the send registry, unique within
            its source: the contact ID for an agenda contact.
        email: Address to send to. Empty when the source has none.
        attachment: Attachment value as stored in the source (an absolute
            URL or a path relative to the base URL). Empty when missing.
        name: Display name, used in the log. Empty when the source has none.
        row: Number of the row the recipient was read from, as a
            spreadsheet shows it, or None when the source has no rows.
        skip_reason: Machine-readable reason why the recipient cannot be
            sent (e.g. 'no_email'), or None when it can.
        send_date: Day the recipient must be sent on, in the contact date
            start mode; None otherwise or when it could not be read.
        subject: Final subject of the recipient's email, with its own
            values in place of the subject fields; None when the source
            was given no subject or the recipient cannot be sent.
        skip_detail: Field or column the skip reason is about (e.g. the
            empty subject field), or None.
    """

    key: str
    email: str
    attachment: str
    name: str = ""
    row: int | None = None
    skip_reason: str | None = None
    send_date: date | None = None
    subject: str | None = None
    skip_detail: str | None = None
