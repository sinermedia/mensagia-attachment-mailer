from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
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
        CONTACT_DATE: Each contact on the day given in its data, at a time
            chosen by the user.
    """

    NOW = "now"
    FIXED = "fixed"
    CONTACT_DATE = "contact_date"


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

class SendSchedule:
    """Hands out the send slot of each email of a bulk send, when it is scheduled.

    Emails are spread out by SECONDS_BETWEEN_EMAILS so Mensagia does not
    reject a large batch as spam. In the "now" and fixed start modes every
    email belongs to one sequence; with the contact date mode each send day
    has its own sequence, starting at the chosen time of that day.

    The rules are applied when each slot is requested, with the current
    time of that moment, so an email scheduled late in a long run (or
    retried at the end) never gets a slot that has lost its lead. The slot
    of a sequence is, by priority:

    1. Right after the last slot of the sequence (handed out by this
       schedule, or recorded by a previous run being resumed), if it is
       at least MIN_START_LEAD in the future. Runs never overlap.
    2. The first slot chosen by the user (the fixed start, or the chosen
       time on the contact's day), if it is at least MIN_START_LEAD in the
       future.
    3. Otherwise default_start_time(), 10 to 20 minutes from now. A chosen
       time that no longer has enough lead is thus postponed, never
       brought forward.

    Attributes:
        start_mode: How the first email of each sequence is scheduled.
        start_at: First slot chosen in the fixed mode, or None.
        start_time: Time chosen in the contact date mode, or None.
    """

    def __init__(
        self,
        start_mode: StartMode,
        start_at: datetime | None = None,
        start_time: time | None = None,
        last_scheduled: dict | None = None,
    ):
        """Initialise the schedule, optionally resuming an interrupted send.

        Args:
            start_mode: How the first email of each sequence is scheduled.
            start_at: First slot chosen in the fixed mode.
            start_time: Time chosen in the contact date mode.
            last_scheduled: Last slot recorded by a previous run of the same
                campaign for each sequence: keyed by send day in the contact
                date mode, and by None in the other modes.
        """
        self.start_mode = start_mode
        self.start_at = start_at
        self.start_time = start_time
        self._last = dict(last_scheduled or {})

    def _chosen_slot(self, day: date | None) -> datetime | None:
        """Return the first slot the user chose for a sequence.

        Args:
            day: Send day of the sequence, or None outside the contact date mode.

        Returns:
            The fixed start, the chosen time on *day*, or None in the "now" mode.
        """
        if self.start_mode == StartMode.CONTACT_DATE:
            return datetime.combine(day, self.start_time)
        if self.start_mode == StartMode.FIXED:
            return self.start_at
        return None

    def next_slot(self, day: date | None, now: datetime) -> datetime:
        """Return the slot of the next email of a sequence, and record it.

        Args:
            day: Send day of the email in the contact date mode; None in the
                other modes.
            now: Current date and time.

        Returns:
            The datetime the email must be scheduled for.
        """
        # Continue the sequence while its next slot still leaves the lead
        last = self._last.get(day)
        slot = None
        if last is not None:
            following = last + timedelta(seconds=SECONDS_BETWEEN_EMAILS)
            if following - now >= MIN_START_LEAD:
                slot = following

        # Otherwise the chosen start, if it still leaves the lead. When the
        # check above failed, the last slot is less than MIN_START_LEAD
        # ahead, so a chosen start that passes is later than it
        chosen = self._chosen_slot(day)
        if slot is None and chosen is not None and chosen - now >= MIN_START_LEAD:
            slot = chosen

        # The "now" schedule is at least MIN_START_LEAD ahead, so it is also
        # always later than a last slot that failed the check
        if slot is None:
            slot = default_start_time(now)

        self._last[day] = slot
        return slot


def calculate_start_dates(
    count: int,
    now: datetime = None,
    last_scheduled: datetime | None = None,
    start_at: datetime | None = None,
) -> list[datetime]:
    """Calculate the staggered send datetimes of a single sequence at once.

    Follows the rules of SendSchedule (see there) with one current time
    for every slot.

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

    mode = StartMode.FIXED if start_at is not None else StartMode.NOW
    last = {None: last_scheduled} if last_scheduled is not None else None
    schedule = SendSchedule(mode, start_at=start_at, last_scheduled=last)
    return [schedule.next_slot(None, now) for _ in range(count)]


def send_date_skip_reason(send_date: date, start_time: time, now: datetime) -> str | None:
    """Check whether a contact's send day can still be scheduled.

    Today is always accepted: if the chosen time no longer leaves the
    lead, the schedule falls back to the "now" slots.

    Args:
        send_date: Day given in the contact's data.
        start_time: Time chosen by the user.
        now: Current date and time.

    Returns:
        'past_send_date' for a day before today, 'send_date_too_far' when
        the chosen time on that day is more than MAX_SCHEDULE_AHEAD ahead,
        or None when the day can be scheduled.
    """
    if send_date < now.date():
        return "past_send_date"
    if datetime.combine(send_date, start_time) - now > MAX_SCHEDULE_AHEAD:
        return "send_date_too_far"
    return None


@dataclass(frozen=True)
class DayPreview:
    """Expected schedule of one send day, for the summary shown before sending.

    Attributes:
        day: Send day.
        count: Number of emails of that day.
        first: Approximate slot of its first email.
        last: Approximate slot of its last email.
    """

    day: date
    count: int
    first: datetime
    last: datetime


def preview_days(
    send_dates: list[date],
    start_time: time,
    now: datetime,
    last_scheduled: dict | None = None,
) -> list[DayPreview]:
    """Estimate the schedule of a contact date send, one entry per day.

    The slots are only approximate: the real ones are set when each email
    is scheduled, and the time goes on while the send runs.

    Args:
        send_dates: Send day of each email that will be sent.
        start_time: Time chosen by the user.
        now: Current date and time.
        last_scheduled: Last slot per day recorded by a previous run of the
            same campaign, when resuming it.

    Returns:
        One DayPreview per distinct day, in date order.
    """
    schedule = SendSchedule(StartMode.CONTACT_DATE, start_time=start_time, last_scheduled=last_scheduled)
    days = {}
    for day in sorted(send_dates):
        slot = schedule.next_slot(day, now)
        count, first, _ = days.get(day, (0, slot, slot))
        days[day] = (count + 1, first, slot)
    return [DayPreview(day, count, first, last) for day, (count, first, last) in days.items()]
