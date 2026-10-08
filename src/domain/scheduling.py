from datetime import datetime, timedelta
from enum import Enum


# Minimum gap between consecutive scheduled emails, in seconds.
# This rate limit avoids triggering Mensagia's anti-spam thresholds.
SECONDS_BETWEEN_EMAILS = 12

# Size of the time-block boundary used to choose the first send slot.
MINUTES_BLOCK = 10

# Minimum lead time a first slot chosen by the user, or the next slot of a
# resumed campaign, must have to be kept instead of applying the "now"
# schedule. It leaves time to cancel before the first email goes out.
MIN_START_LEAD = timedelta(minutes=10)

# Furthest ahead the user may schedule a send, counted from the moment it is
# prepared. Mensagia sets no limit of its own; this one guards against typos
# in the year and is meant to be easy to change.
MAX_SCHEDULE_AHEAD = timedelta(weeks=6)


class StartMode(str, Enum):
    """How the first email of a send is scheduled.

    Deriving from str keeps the values readable once stored in JSON files.

    Attributes:
        NOW: Between 10 and 20 minutes after the send starts.
        FIXED: At a date and time chosen by the user.
    """

    NOW = "now"
    FIXED = "fixed"


class StartTooSoonError(ValueError):
    """Raised when a chosen start is in the past or closer than MIN_START_LEAD.

    Attributes:
        args: The standard exception arguments (a description).
    """


class StartTooFarError(ValueError):
    """Raised when a chosen start is further ahead than MAX_SCHEDULE_AHEAD.

    Attributes:
        args: The standard exception arguments (a description).
    """


def validate_fixed_start(start_at: datetime, now: datetime) -> None:
    """Check that a start date and time chosen by the user can be scheduled.

    The check is made when the user picks the time, so a mistake is shown
    right away. A time that becomes too close while the user goes through
    the rest of the steps is not an error: calculate_start_dates()
    postpones it when the send starts.

    Args:
        start_at: Date and time chosen for the first email.
        now: Current date and time.

    Raises:
        StartTooSoonError: If *start_at* is in the past or less than
            MIN_START_LEAD ahead of *now*.
        StartTooFarError: If *start_at* is more than MAX_SCHEDULE_AHEAD
            ahead of *now*.
    """
    if start_at - now < MIN_START_LEAD:
        raise StartTooSoonError(f"start {start_at.isoformat()} is less than {MIN_START_LEAD} ahead")
    if start_at - now > MAX_SCHEDULE_AHEAD:
        raise StartTooFarError(f"start {start_at.isoformat()} is more than {MAX_SCHEDULE_AHEAD} ahead")


def next_ten_minute_mark(now: datetime) -> datetime:
    """Return the next multiple-of-10-minutes datetime strictly after *now*.

    The Mensagia API schedules emails at specific time slots. To ensure
    the first email is always queued safely in the future this function
    finds the next clean 10-minute boundary (e.g. :10, :20, :30 ...).
    It is always strictly after *now*: if *now* is already on the mark
    (e.g. 14:20:00 exactly) the function returns the *following* mark
    (14:30:00) so we never queue in a slot that is already current.

    Args:
        now: Reference datetime from which to compute the next mark.

    Returns:
        A datetime whose minutes component is the next multiple of 10
        after *now*, with seconds and microseconds zeroed.
    """
    # Determine how many minutes remain until the next 10-minute boundary
    remaining = now.minute % MINUTES_BLOCK
    if remaining == 0 and now.second == 0 and now.microsecond == 0:
        # Already exactly on a mark — move to the next one to stay strictly ahead
        minutes_to_add = MINUTES_BLOCK
    else:
        # Round up to the nearest 10-minute mark
        minutes_to_add = MINUTES_BLOCK - remaining

    # Zero out sub-minute precision and advance to the computed mark
    base = now.replace(second=0, microsecond=0) + timedelta(minutes=minutes_to_add)
    return base


def default_start_time(now: datetime) -> datetime:
    """Return the first send slot of the "now" start mode.

    It is the *second* 10-minute mark after *now*, i.e. between 10 and 20
    minutes in the future, so that last-minute cancellations are still
    possible before the first message goes out.

    Args:
        now: Reference datetime from which to compute the slot.

    Returns:
        The second 10-minute mark strictly after *now*.
    """
    # Apply next_ten_minute_mark twice: the first call gives the nearest
    # mark, the second ensures a full 10-minute buffer before the first email
    return next_ten_minute_mark(next_ten_minute_mark(now))


def calculate_start_dates(
    count: int,
    now: datetime = None,
    last_scheduled: datetime | None = None,
    start_at: datetime | None = None,
) -> list[datetime]:
    """Calculate staggered send datetimes for a bulk email campaign.

    To avoid Mensagia rejecting a large batch as spam, emails are spread
    out by SECONDS_BETWEEN_EMAILS. The first slot is, by priority:

    1. When resuming an interrupted campaign, the slot right after
       *last_scheduled* (the last email already queued), if it is at least
       MIN_START_LEAD in the future. The sending rhythm is kept and both
       runs never overlap.
    2. The date and time chosen by the user (*start_at*), if it is at
       least MIN_START_LEAD in the future.
    3. Otherwise default_start_time(), 10 to 20 minutes from now. A chosen
       time that no longer has enough lead is thus postponed, never
       brought forward.

    Args:
        count: Number of emails (and therefore dates) to generate.
        now: Reference datetime used as the starting point. Defaults to
            the current system time when None is passed. Accepting an
            explicit value makes the function deterministic in tests.
        last_scheduled: Send datetime of the last email queued by a
            previous run of the same campaign, or None for a new campaign.
        start_at: First slot chosen by the user (fixed start mode), or
            None for the "now" start mode.

    Returns:
        A list of *count* datetime objects in strictly ascending order,
        each separated by SECONDS_BETWEEN_EMAILS seconds. Returns an
        empty list when count is 0.
    """
    # Use the current time when no reference is provided
    if now is None:
        now = datetime.now()

    # A resumed campaign was already validated by the user, so it does not
    # need the cancellation gap: continue right after the previous run as
    # long as that slot leaves enough time to queue the emails safely
    base = None
    if last_scheduled is not None:
        next_slot = last_scheduled + timedelta(seconds=SECONDS_BETWEEN_EMAILS)
        if next_slot - now >= MIN_START_LEAD:
            base = next_slot

    # Use the chosen start only while it still leaves the minimum lead. If
    # a previous run failed the check above, its slots are less than
    # MIN_START_LEAD ahead, so a chosen start that passes is later than them
    if base is None and start_at is not None and start_at - now >= MIN_START_LEAD:
        base = start_at

    # The "now" schedule is at least MIN_START_LEAD ahead, so it is also
    # always later than any previous last_scheduled that failed the check
    if base is None:
        base = default_start_time(now)

    # Spread each email by the inter-message gap starting from base
    return [base + timedelta(seconds=SECONDS_BETWEEN_EMAILS * i) for i in range(count)]
