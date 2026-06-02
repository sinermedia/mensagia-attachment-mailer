from datetime import datetime, timedelta
import pytest
from src.domain.scheduling import next_ten_minute_mark, calculate_start_dates, SECONDS_BETWEEN_EMAILS


class TestNextTenMinuteMark:
    """Tests for the next_ten_minute_mark() scheduling helper.

    Verifies that the function always returns a datetime that is:
    - strictly after the input (never equal),
    - on a 10-minute boundary (:00, :10, :20, ...),
    - correct when crossing hour or day boundaries.
    """

    def test_mid_block_rounds_up(self):
        """A time in the middle of a 10-minute block rounds up to the next mark."""
        now = datetime(2024, 1, 15, 14, 23, 0)
        result = next_ten_minute_mark(now)
        assert result == datetime(2024, 1, 15, 14, 30, 0)

    def test_start_of_block_goes_to_next(self):
        """A time exactly on a 10-minute mark moves to the following mark."""
        now = datetime(2024, 1, 15, 14, 20, 0)
        result = next_ten_minute_mark(now)
        assert result == datetime(2024, 1, 15, 14, 30, 0)

    def test_on_exact_mark_with_seconds_rounds_up(self):
        """A time on a mark but with non-zero seconds is treated as past that mark."""
        now = datetime(2024, 1, 15, 14, 20, 5)
        result = next_ten_minute_mark(now)
        assert result == datetime(2024, 1, 15, 14, 30, 0)

    def test_crosses_hour_boundary(self):
        """A time near the end of an hour correctly crosses into the next hour."""
        now = datetime(2024, 1, 15, 14, 55, 0)
        result = next_ten_minute_mark(now)
        assert result == datetime(2024, 1, 15, 15, 0, 0)

    def test_at_end_of_hour_crosses_next_hour(self):
        """A time at :50 with extra seconds crosses into the next hour."""
        now = datetime(2024, 1, 15, 14, 50, 30)
        result = next_ten_minute_mark(now)
        assert result == datetime(2024, 1, 15, 15, 0, 0)

    def test_exactly_midnight(self):
        """A time near midnight correctly crosses into the next day."""
        now = datetime(2024, 1, 15, 23, 55, 0)
        result = next_ten_minute_mark(now)
        assert result == datetime(2024, 1, 16, 0, 0, 0)

    def test_one_minute_before_end(self):
        """A time one minute before the end of a 10-minute block rounds up correctly."""
        now = datetime(2024, 1, 15, 14, 9, 59)
        result = next_ten_minute_mark(now)
        assert result == datetime(2024, 1, 15, 14, 10, 0)


class TestCalculateStartDates:
    """Tests for the calculate_start_dates() bulk scheduling function.

    Verifies that dates are staggered correctly, that the first slot is
    placed at least one full 10-minute block in the future, and that the
    number and order of returned dates match expectations.
    """

    def test_zero_emails_returns_empty(self):
        """Requesting 0 dates returns an empty list."""
        now = datetime(2024, 1, 15, 14, 23, 0)
        result = calculate_start_dates(0, now)
        assert result == []

    def test_first_email_at_second_ten_minute_mark(self):
        """The first email is scheduled at the second 10-minute mark after now."""
        now = datetime(2024, 1, 15, 14, 23, 0)
        result = calculate_start_dates(1, now)
        assert result[0] == datetime(2024, 1, 15, 14, 40, 0)

    def test_first_email_skips_imminent_mark(self):
        """A mark only 20 seconds away is skipped; the first email goes to the next safe mark."""
        # At 14:09:40 the next mark is 14:10 (only 20s away) — should skip to 14:20
        now = datetime(2024, 1, 15, 14, 9, 40)
        result = calculate_start_dates(1, now)
        assert result[0] == datetime(2024, 1, 15, 14, 20, 0)

    def test_second_email_is_12_seconds_after_first(self):
        """Consecutive emails are separated by exactly SECONDS_BETWEEN_EMAILS."""
        now = datetime(2024, 1, 15, 14, 23, 0)
        result = calculate_start_dates(2, now)
        assert result[1] == result[0] + timedelta(seconds=SECONDS_BETWEEN_EMAILS)

    def test_five_emails_per_minute_rate(self):
        """Five emails span exactly 4 × SECONDS_BETWEEN_EMAILS total."""
        now = datetime(2024, 1, 15, 14, 23, 0)
        result = calculate_start_dates(5, now)
        total_seconds = (result[-1] - result[0]).total_seconds()
        assert total_seconds == SECONDS_BETWEEN_EMAILS * 4

    def test_count_matches_output_length(self):
        """The returned list always has exactly as many items as requested."""
        now = datetime(2024, 1, 15, 14, 23, 0)
        for count in [1, 5, 10, 100]:
            result = calculate_start_dates(count, now)
            assert len(result) == count

    def test_dates_are_strictly_increasing(self):
        """Every date in the list is strictly later than the previous one."""
        now = datetime(2024, 1, 15, 14, 23, 0)
        result = calculate_start_dates(10, now)
        for i in range(1, len(result)):
            assert result[i] > result[i - 1]
