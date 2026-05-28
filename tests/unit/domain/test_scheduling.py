from datetime import datetime, timedelta
import pytest
from src.domain.scheduling import next_ten_minute_mark, calculate_start_dates, SECONDS_BETWEEN_EMAILS


class TestNextTenMinuteMark:
    def test_mid_block_rounds_up(self):
        now = datetime(2024, 1, 15, 14, 23, 0)
        result = next_ten_minute_mark(now)
        assert result == datetime(2024, 1, 15, 14, 30, 0)

    def test_start_of_block_goes_to_next(self):
        now = datetime(2024, 1, 15, 14, 20, 0)
        result = next_ten_minute_mark(now)
        assert result == datetime(2024, 1, 15, 14, 30, 0)

    def test_on_exact_mark_with_seconds_rounds_up(self):
        now = datetime(2024, 1, 15, 14, 20, 5)
        result = next_ten_minute_mark(now)
        assert result == datetime(2024, 1, 15, 14, 30, 0)

    def test_crosses_hour_boundary(self):
        now = datetime(2024, 1, 15, 14, 55, 0)
        result = next_ten_minute_mark(now)
        assert result == datetime(2024, 1, 15, 15, 0, 0)

    def test_at_end_of_hour_crosses_next_hour(self):
        now = datetime(2024, 1, 15, 14, 50, 30)
        result = next_ten_minute_mark(now)
        assert result == datetime(2024, 1, 15, 15, 0, 0)

    def test_exactly_midnight(self):
        now = datetime(2024, 1, 15, 23, 55, 0)
        result = next_ten_minute_mark(now)
        assert result == datetime(2024, 1, 16, 0, 0, 0)

    def test_one_minute_before_end(self):
        now = datetime(2024, 1, 15, 14, 9, 59)
        result = next_ten_minute_mark(now)
        assert result == datetime(2024, 1, 15, 14, 10, 0)


class TestCalculateStartDates:
    def test_zero_emails_returns_empty(self):
        now = datetime(2024, 1, 15, 14, 23, 0)
        result = calculate_start_dates(0, now)
        assert result == []

    def test_first_email_at_next_ten_minute_mark(self):
        now = datetime(2024, 1, 15, 14, 23, 0)
        result = calculate_start_dates(1, now)
        assert result[0] == datetime(2024, 1, 15, 14, 30, 0)

    def test_second_email_is_12_seconds_after_first(self):
        now = datetime(2024, 1, 15, 14, 23, 0)
        result = calculate_start_dates(2, now)
        assert result[1] == result[0] + timedelta(seconds=SECONDS_BETWEEN_EMAILS)

    def test_five_emails_per_minute_rate(self):
        now = datetime(2024, 1, 15, 14, 23, 0)
        result = calculate_start_dates(5, now)
        total_seconds = (result[-1] - result[0]).total_seconds()
        assert total_seconds == SECONDS_BETWEEN_EMAILS * 4

    def test_count_matches_output_length(self):
        now = datetime(2024, 1, 15, 14, 23, 0)
        for count in [1, 5, 10, 100]:
            result = calculate_start_dates(count, now)
            assert len(result) == count

    def test_dates_are_strictly_increasing(self):
        now = datetime(2024, 1, 15, 14, 23, 0)
        result = calculate_start_dates(10, now)
        for i in range(1, len(result)):
            assert result[i] > result[i - 1]
