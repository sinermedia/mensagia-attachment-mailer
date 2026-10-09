import re
from datetime import date, time
from enum import Enum


# Day, month and year separated by '/', '-' or '.', with optional leading
# zeros and a 2- or 4-digit year. The order is always day/month/year
_DATE = re.compile(r"(\d{1,2})\s*[/.-]\s*(\d{1,2})\s*[/.-]\s*(\d{4}|\d{2})")

# Hour, optionally followed by ':', '.' or 'h' and the minutes
_TIME = re.compile(r"(\d{1,2})(?:\s*[:.hH]\s*(\d{1,2}))?")


def parse_date(text: str) -> date:
    """Read a day/month/year date typed by the user, tolerating common variants.

    Accepts '/', '-' and '.' as separators, optional leading zeros and
    surrounding spaces. A two-digit year is read as 20yy, which is never
    ambiguous given how close to today a send can be scheduled.

    Args:
        text: The date as typed, e.g. '08/10/2026', '8-10-26'.

    Returns:
        The date it represents.

    Raises:
        ValueError: If the text is not a day/month/year date or the date
            does not exist (e.g. 31/02/2026).
    """
    match = _DATE.fullmatch(text.strip())
    if not match:
        raise ValueError(f"not a day/month/year date: {text!r}")

    # A two-digit year belongs to this century
    day, month, year = (int(part) for part in match.groups())
    if year < 100:
        year += 2000

    # date() rejects days and months out of range, such as 31 February
    return date(year, month, day)


def parse_time(text: str) -> time:
    """Read an hour and minute typed by the user, tolerating common variants.

    Accepts ':', '.' and 'h' as separators, optional leading zeros,
    surrounding spaces and an hour on its own (minute 00). Seconds are not
    accepted: they are always set by the send schedule.

    Args:
        text: The time as typed, e.g. '09:05', '9h30', '9'.

    Returns:
        The time it represents, with zero seconds.

    Raises:
        ValueError: If the text is not an hour and minute, or either is
            out of range.
    """
    match = _TIME.fullmatch(text.strip())
    if not match:
        raise ValueError(f"not an hour and minute: {text!r}")

    # time() rejects an hour or minute out of range, such as 24:00
    hour, minute = match.groups()
    return time(int(hour), int(minute or 0))


class DateFormat(str, Enum):
    """Format of the send dates stored in a contact field or a file column.

    The Mensagia API does not tell the format of a custom field, so the
    user picks it from this closed list. Only day-first and year-first
    orders are offered: a month-first date would be ambiguous with them.
    Deriving from str keeps the values readable once stored in JSON files.

    Attributes:
        DMY_SLASH: Day, month and year separated by '/'.
        DMY_DASH: Day, month and year separated by '-'.
        YMD_SLASH: Year, month and day separated by '/'.
        YMD_DASH: Year, month and day separated by '-'.
    """

    DMY_SLASH = "dd/mm/yyyy"
    DMY_DASH = "dd-mm-yyyy"
    YMD_SLASH = "yyyy/mm/dd"
    YMD_DASH = "yyyy-mm-dd"


# Pattern of the date part of each format: optional leading zeros, and a
# year of 2 or 4 digits. Each group is named so both orders read the same
_DAY, _MONTH, _YEAR = r"(?P<day>\d{1,2})", r"(?P<month>\d{1,2})", r"(?P<year>\d{4}|\d{2})"
_SEND_DATE = {
    DateFormat.DMY_SLASH: re.compile(rf"{_DAY}\s*/\s*{_MONTH}\s*/\s*{_YEAR}"),
    DateFormat.DMY_DASH: re.compile(rf"{_DAY}\s*-\s*{_MONTH}\s*-\s*{_YEAR}"),
    DateFormat.YMD_SLASH: re.compile(rf"{_YEAR}\s*/\s*{_MONTH}\s*/\s*{_DAY}"),
    DateFormat.YMD_DASH: re.compile(rf"{_YEAR}\s*-\s*{_MONTH}\s*-\s*{_DAY}"),
}

# What may follow the date when the value also holds a time, such as
# ' 10:00', 'T09:30:00' or ' 9h30'
_TRAILING_TIME = re.compile(r"(\s+|\s*T)\d{1,2}\s*[:.hH]\s*\d{1,2}.*")


class SendDateError(ValueError):
    """Raised when a contact's send date cannot be used.

    Attributes:
        reason: Machine-readable reason, used as the skip reason of the
            contact: 'invalid_send_date' or 'send_date_has_time'.
    """

    def __init__(self, reason: str, text: str):
        """Create the error.

        Args:
            reason: Machine-readable reason (see the class attributes).
            text: The value that could not be used, for the message.
        """
        super().__init__(f"{reason}: {text!r}")
        self.reason = reason


def parse_send_date(text: str, fmt: DateFormat) -> date:
    """Read a contact's send date written in the chosen format.

    Leading zeros are optional and a two-digit year is read as 20yy, which
    is never ambiguous given how close to today a send can be scheduled.
    The order and the separator must be those of the format. A value that
    also holds a time is rejected, whatever the time: the time of the send
    is chosen by the user, and a time in the data suggests the wrong field.

    Args:
        text: The value as stored, e.g. '15/10/2026' or '2026-10-15'.
        fmt: Format chosen by the user for the field or column.

    Returns:
        The date it represents.

    Raises:
        SendDateError: 'send_date_has_time' when the value holds a time,
            'invalid_send_date' when it does not match the format or the
            date does not exist (e.g. 31/02/2026).
    """
    # The date may be followed by a time, which is a reason of its own
    value = text.strip()
    match = _SEND_DATE[fmt].match(value)
    if not match:
        raise SendDateError("invalid_send_date", text)
    rest = value[match.end():]
    if rest:
        reason = "send_date_has_time" if _TRAILING_TIME.fullmatch(rest) else "invalid_send_date"
        raise SendDateError(reason, text)

    # A two-digit year belongs to this century; date() rejects impossible days
    year = int(match["year"])
    if year < 100:
        year += 2000
    try:
        return date(year, int(match["month"]), int(match["day"]))
    except ValueError:
        raise SendDateError("invalid_send_date", text)
