from datetime import datetime

from src.domain.date_input import parse_date, parse_time
from src.domain.scheduling import (
    MAX_SCHEDULE_AHEAD, MIN_START_LEAD, StartMode, StartTooFarError, StartTooSoonError,
    default_start_time, validate_fixed_start,
)
from src.infrastructure.ui.i18n import t


# Formats shown to the user: always day first, whatever the language
DATE_FORMAT = "%d/%m/%Y"
TIME_FORMAT = "%H:%M"


class StartInputError(ValueError):
    """Raised when the start date and time typed by the user cannot be used.

    Its message is already translated, so both interfaces can show it as is.

    Attributes:
        args: The standard exception arguments (the translated message).
    """


def read_fixed_start(date_text: str, time_text: str, now: datetime) -> datetime:
    """Turn the date and time typed by the user into a validated fixed start.

    Both interfaces use it, so they accept the same input and report the
    same errors.

    Args:
        date_text: Date as typed (day/month/year, tolerant reading).
        time_text: Time as typed (hour and minute, tolerant reading).
        now: Current date and time.

    Returns:
        The chosen start, with zero seconds.

    Raises:
        StartInputError: With a translated message when the date or the
            time cannot be read, or the start is too soon or too far.
    """
    # Each part is read on its own so the message says which one is wrong
    try:
        day = parse_date(date_text)
    except ValueError:
        raise StartInputError(t("start_error_invalid_date"))
    try:
        clock = parse_time(time_text)
    except ValueError:
        raise StartInputError(t("start_error_invalid_time"))

    # The limits are checked on the combined value, against the current time
    start_at = datetime.combine(day, clock)
    try:
        validate_fixed_start(start_at, now)
    except StartTooSoonError:
        raise StartInputError(t("start_error_too_soon", minutes=int(MIN_START_LEAD.total_seconds() // 60)))
    except StartTooFarError:
        limit = now + MAX_SCHEDULE_AHEAD
        raise StartInputError(t("start_error_too_far", limit=limit.strftime(f"{DATE_FORMAT} {TIME_FORMAT}")))
    return start_at


def default_start_fields(now: datetime, remembered_time: str | None) -> tuple[str, str]:
    """Return the date and time proposed before the user types any.

    The time used last is proposed with today's date, even when it has
    already passed: the date is never remembered. Without one, the first
    slot of the "now" mode is proposed, with its own date in case it falls
    after midnight.

    Args:
        now: Current date and time.
        remembered_time: Time saved from the last send ('hh:mm'), or None.

    Returns:
        The date ('dd/mm/yyyy') and time ('hh:mm') to fill in.
    """
    # A remembered time that cannot be read is ignored rather than shown
    if remembered_time:
        try:
            clock = parse_time(remembered_time)
            return now.strftime(DATE_FORMAT), clock.strftime(TIME_FORMAT)
        except ValueError:
            pass
    start = default_start_time(now)
    return start.strftime(DATE_FORMAT), start.strftime(TIME_FORMAT)


def summary_start_lines(start_mode: StartMode, start_at: datetime | None) -> list[str]:
    """Describe the chosen start for the summary shown before sending.

    Args:
        start_mode: Start mode chosen by the user.
        start_at: Chosen start in the fixed mode, None otherwise.

    Returns:
        The line describing the start, followed by a note that the final
        time is only set when the send starts (it may be postponed or
        continue a previous run).
    """
    if start_mode == StartMode.FIXED:
        line = t("summary_start_fixed", date=start_at.strftime(DATE_FORMAT), time=start_at.strftime(TIME_FORMAT))
    else:
        line = t("summary_start_now")
    return [line, t("summary_start_note")]
