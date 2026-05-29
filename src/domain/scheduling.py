from datetime import datetime, timedelta


SECONDS_BETWEEN_EMAILS = 12
MINUTES_BLOCK = 10


def next_ten_minute_mark(now: datetime) -> datetime:
    """Returns the next multiple-of-10-minutes datetime strictly after now."""
    remaining = now.minute % MINUTES_BLOCK
    minutes_to_add = MINUTES_BLOCK - remaining if remaining != 0 else MINUTES_BLOCK
    if remaining == 0 and now.second == 0 and now.microsecond == 0:
        minutes_to_add = MINUTES_BLOCK
    else:
        minutes_to_add = MINUTES_BLOCK - remaining
    base = now.replace(second=0, microsecond=0) + timedelta(minutes=minutes_to_add)
    return base


def calculate_start_dates(count: int, now: datetime = None) -> list[datetime]:
    if now is None:
        now = datetime.now()
    base = next_ten_minute_mark(next_ten_minute_mark(now))
    return [base + timedelta(seconds=SECONDS_BETWEEN_EMAILS * i) for i in range(count)]
