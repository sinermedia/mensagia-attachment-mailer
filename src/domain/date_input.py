import re
from datetime import date, time


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
