from datetime import datetime, timedelta


# Minimum gap between consecutive scheduled emails, in seconds.
# This rate limit avoids triggering Mensagia's anti-spam thresholds.
SECONDS_BETWEEN_EMAILS = 12

# Size of the time-block boundary used to choose the first send slot.
MINUTES_BLOCK = 10


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


def calculate_start_dates(count: int, now: datetime = None) -> list[datetime]:
    """Calculate staggered send datetimes for a bulk email campaign.

    To avoid Mensagia rejecting a large batch as spam, emails are spread
    out by SECONDS_BETWEEN_EMAILS. Additionally, the first slot is placed
    at the *second* 10-minute mark from now (i.e. at least 10–20 minutes
    in the future) so that last-minute cancellations are still possible
    before the first message goes out.

    Args:
        count: Number of emails (and therefore dates) to generate.
        now: Reference datetime used as the starting point. Defaults to
            the current system time when None is passed. Accepting an
            explicit value makes the function deterministic in tests.

    Returns:
        A list of *count* datetime objects in strictly ascending order,
        each separated by SECONDS_BETWEEN_EMAILS seconds. Returns an
        empty list when count is 0.
    """
    # Use the current time when no reference is provided
    if now is None:
        now = datetime.now()

    # Apply next_ten_minute_mark twice: the first call gives the nearest safe
    # mark, the second call ensures at least one full 10-minute buffer exists
    # between 'now' and the first queued email
    base = next_ten_minute_mark(next_ten_minute_mark(now))

    # Spread each email by the inter-message gap starting from base
    return [base + timedelta(seconds=SECONDS_BETWEEN_EMAILS * i) for i in range(count)]
