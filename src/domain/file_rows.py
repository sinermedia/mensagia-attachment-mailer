import dataclasses
import json
import re

from src.domain.entities.recipient import Recipient


# Accepted address: allowed characters before the @, and a domain made of
# non-empty labels of ASCII letters, digits and hyphens with at least one
# dot. Stricter than the standard on purpose: a cell holding two addresses,
# a space or a typo must be caught before sending, not by the API
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+")


def email_skip_reason(email: str) -> str | None:
    """Check the email address of a file row.

    Args:
        email: The address as read from the cell, already stripped.

    Returns:
        'no_email' when it is empty, 'invalid_email' when it breaks any rule
        (no specific reason is given: two addresses, a separator or a
        forbidden character all count as invalid), or None when it is valid.
    """
    if not email:
        return "no_email"
    if not _EMAIL.fullmatch(email):
        return "invalid_email"
    return None


def row_key(email: str, attachment: str, date: str = "") -> str:
    """Build the key identifying a file row in the send registry.

    A row is identified by its content rather than by its position, so
    inserting or sorting rows does not change which ones were sent. The
    email is lowercased since addresses are case-insensitive in practice,
    while the attachment is kept as is because URLs can be case-sensitive.
    JSON encoding keeps values that contain separators from colliding.

    Args:
        email: Email address of the row.
        attachment: Attachment value of the row.
        date: Send date of the row; empty while rows carry no date.

    Returns:
        The key, as a JSON array of the date, the email and the attachment.
    """
    return json.dumps([date, email.lower(), attachment], ensure_ascii=False)


def skip_duplicate_rows(recipients: list[Recipient]) -> list[Recipient]:
    """Skip every sendable row whose key was already used by an earlier one.

    Sending the same attachment twice to the same address is almost
    certainly a mistake in the file, and both rows would share one entry in
    the send registry. Rows already skipped for another reason are left
    alone and do not count.

    Args:
        recipients: Rows of the file, in file order.

    Returns:
        The same rows in the same order, the repeated ones with the
        'duplicate_row' reason.
    """
    seen = set()
    result = []
    for recipient in recipients:
        if recipient.skip_reason is None:
            if recipient.key in seen:
                recipient = dataclasses.replace(recipient, skip_reason="duplicate_row")
            else:
                seen.add(recipient.key)
        result.append(recipient)
    return result


def rows_on_several_dates(recipients: list[Recipient]) -> list[list[Recipient]]:
    """Find the address and attachment pairs that will be sent on different days.

    With send days, the same address and attachment on two days are two
    emails and both are sent. That may be intended (a reminder) or a
    mistake in the file, so the summary warns about them and the user can
    remove the extra ones in the Mensagia portal.

    Args:
        recipients: Rows of the file, in file order.

    Returns:
        One group per repeated pair, each with its sendable rows in file
        order; groups are ordered by their first row. Rows without a send
        day or that will not be sent are left out.
    """
    groups = {}
    for recipient in recipients:
        if recipient.skip_reason is None and recipient.send_date is not None:
            _, email, attachment = json.loads(recipient.key)
            groups.setdefault((email, attachment), []).append(recipient)
    return [rows for rows in groups.values() if len({r.send_date for r in rows}) > 1]
